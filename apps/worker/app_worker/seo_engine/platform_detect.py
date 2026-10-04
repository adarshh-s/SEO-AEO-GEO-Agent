"""Worker adapter over app_core.platform_detect (the detection itself is shared with the API)."""

from app_core.platform_detect import PlatformFacts, detect_platform_from
from app_worker.seo_engine.fetch import FetchResult
from app_worker.seo_engine.render import RenderResult


def detect_platform(fetch: FetchResult, render: RenderResult | None = None) -> PlatformFacts:
    return detect_platform_from(
        fetch.raw_html,
        fetch.headers,
        fetch.final_url,
        render.js_only_content_detected if render and render.render_error is None else None,
    )


__all__ = ["PlatformFacts", "detect_platform"]
