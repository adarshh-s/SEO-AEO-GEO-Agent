"""Extract SEO-relevant facts from a page's HTML (pure, no network)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


@dataclass
class PageFacts:
    title: str | None = None
    meta_description: str | None = None
    site_name: str | None = None  # og:site_name or schema.org name
    html_lang: str | None = None
    hreflang_langs: list[str] = field(default_factory=list)
    schema_types: list[str] = field(default_factory=list)
    schema_city: str | None = None
    schema_country: str | None = None
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    text: str = ""
    word_count: int = 0
    canonical: str | None = None

    def as_prompt(self, max_text: int = 12_000) -> str:
        """Compact representation for an LLM prompt."""
        lines = [
            f"Title: {self.title or '-'}",
            f"Meta description: {self.meta_description or '-'}",
            f"Site name: {self.site_name or '-'}",
            f"<html lang>: {self.html_lang or '-'}; hreflang: {', '.join(self.hreflang_langs) or '-'}",
            f"Schema.org types: {', '.join(self.schema_types) or 'none'}",
            f"Schema address: city={self.schema_city or '-'}, country={self.schema_country or '-'}",
            f"H1: {' | '.join(self.h1[:5]) or '-'}",
            f"H2: {' | '.join(self.h2[:15]) or '-'}",
            f"Word count: {self.word_count}",
            "Visible text:",
            self.text[:max_text],
        ]
        return "\n".join(lines)


def _clean(s: str | None) -> str | None:
    if not s:
        return None
    s = " ".join(s.split())
    return s or None


def _walk_json_ld(node: object, out: list[dict]) -> None:
    if isinstance(node, list):
        for n in node:
            _walk_json_ld(n, out)
    elif isinstance(node, dict):
        out.append(node)
        for key in ("@graph", "itemListElement"):
            if key in node:
                _walk_json_ld(node[key], out)


def extract_page_facts(html: str) -> PageFacts:
    soup = BeautifulSoup(html, "html.parser")
    f = PageFacts()

    f.title = _clean(soup.title.string if soup.title else None)
    desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    f.meta_description = _clean(desc.get("content") if desc else None)
    og = soup.find("meta", attrs={"property": "og:site_name"})
    f.site_name = _clean(og.get("content") if og else None)
    html_tag = soup.find("html")
    f.html_lang = _clean(html_tag.get("lang")) if html_tag else None
    f.hreflang_langs = sorted(
        {
            str(link.get("hreflang")).split("-")[0].lower()
            for link in soup.find_all("link", attrs={"hreflang": True})
            if link.get("hreflang") and link.get("hreflang") != "x-default"
        }
    )
    canon = soup.find("link", attrs={"rel": "canonical"})
    f.canonical = canon.get("href") if canon else None

    nodes: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            _walk_json_ld(json.loads(script.string or ""), nodes)
        except (json.JSONDecodeError, TypeError):
            continue
    for n in nodes:
        types = n.get("@type")
        for t in types if isinstance(types, list) else [types]:
            if isinstance(t, str) and t not in f.schema_types:
                f.schema_types.append(t)
        addr = n.get("address")
        if isinstance(addr, dict):
            f.schema_city = f.schema_city or _clean(str(addr.get("addressLocality") or "")) or None
            country = addr.get("addressCountry")
            if isinstance(country, dict):
                country = country.get("name")
            f.schema_country = f.schema_country or _clean(str(country or "")) or None
        if not f.site_name and n.get("@type") in ("Organization", "LocalBusiness", "WebSite"):
            f.site_name = _clean(str(n.get("name") or "")) or None

    f.h1 = [t for t in (_clean(h.get_text()) for h in soup.find_all("h1")) if t]
    f.h2 = [t for t in (_clean(h.get_text()) for h in soup.find_all("h2")) if t]
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    f.text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    f.word_count = len(f.text.split())
    return f


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.")
