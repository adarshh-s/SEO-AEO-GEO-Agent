"""Playwright headless browser rendering and raw vs rendered DOM diffing."""

import hashlib
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from app_worker.seo_engine.fetch import USER_AGENT, FetchResult


@dataclass
class RenderResult:
    rendered_html: str
    rendered_text: str
    rendered_html_hash: str
    js_only_content_detected: bool
    js_only_text: str | None


def render_page(fetch_result: FetchResult, *, timeout_ms: int = 15000) -> RenderResult:
    """Render page with Playwright sync if available; diff against raw HTML."""
    rendered_html = fetch_result.raw_html
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.goto(fetch_result.final_url, timeout=timeout_ms, wait_until="networkidle")
            rendered_html = page.content()
            browser.close()
    except Exception:
        # Graceful fallback if Playwright / Chromium not available in the environment
        rendered_html = fetch_result.raw_html

    rendered_html_hash = hashlib.sha256(rendered_html.encode("utf-8")).hexdigest()

    soup = BeautifulSoup(rendered_html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    rendered_text = re.sub(r"\s+", " ", soup.get_text()).strip()

    # Compare raw text vs rendered text
    raw_words = set(fetch_result.raw_text.split())
    rendered_words = set(rendered_text.split())
    new_words = rendered_words - raw_words

    # If rendered text is significantly larger or has distinct words absent in raw HTML
    js_only = False
    js_only_snippets: list[str] = []
    if len(rendered_words) > len(raw_words) * 1.25 and len(new_words) > 30:
        js_only = True
        # Extract a sample of rendered headings/paragraphs missing from raw
        for p in soup.find_all(["h1", "h2", "h3", "p"]):
            text = p.get_text().strip()
            if text and text not in fetch_result.raw_text and len(text) > 20:
                js_only_snippets.append(text[:200])
                if len(js_only_snippets) >= 5:
                    break

    return RenderResult(
        rendered_html=rendered_html,
        rendered_text=rendered_text,
        rendered_html_hash=rendered_html_hash,
        js_only_content_detected=js_only,
        js_only_text="\n---\n".join(js_only_snippets) if js_only_snippets else None,
    )
