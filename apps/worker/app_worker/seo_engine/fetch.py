"""Raw HTML fetcher with URL safety and brand user agent."""

import hashlib
import re
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from app_core.brand import crawler_user_agent
from app_core.settings import get_settings
from app_worker.seo_engine.url_safety import safe_requests_get

# Clear, honest crawler identity (CLAUDE.md §5) with a page explaining the bot.
USER_AGENT = crawler_user_agent(f"{get_settings().app_url}/bot")


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    raw_html: str
    raw_text: str
    raw_html_hash: str
    meta_title: str | None
    meta_description: str | None


def fetch_page(url: str, *, timeout: int = 15) -> FetchResult:
    """Fetch raw HTML using safe DNS-pinned HTTP."""
    resp = safe_requests_get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=timeout,
        allow_redirects=True,
    )
    raw_html = resp.text
    html_hash = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()

    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        raw_text = re.sub(r"\s+", " ", soup.get_text()).strip()
        title_tag = soup.find("title")
        meta_title = title_tag.string.strip() if title_tag and title_tag.string else None
        desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        meta_description = desc_tag.get("content", "").strip() if desc_tag else None
    else:
        clean_html = re.sub(
            r"<(script|style|noscript|svg)[^>]*>.*?</\1>",
            "",
            raw_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        clean_html = re.sub(r"<[^>]+>", " ", clean_html)
        raw_text = re.sub(r"\s+", " ", clean_html).strip()

        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
        meta_title = title_match.group(1).strip() if title_match else None

        desc_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']',
            raw_html,
            re.IGNORECASE,
        )
        if not desc_match:
            desc_match = re.search(
                r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']',
                raw_html,
                re.IGNORECASE,
            )
        meta_description = desc_match.group(1).strip() if desc_match else None

    return FetchResult(
        url=url,
        final_url=resp.url,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        raw_html=raw_html,
        raw_text=raw_text,
        raw_html_hash=html_hash,
        meta_title=meta_title,
        meta_description=meta_description,
    )
