"""SEO Engine adapter over claude-seo scripts and custom analyzers."""

from app_worker.seo_engine.fetch import FetchResult, fetch_page
from app_worker.seo_engine.platform_detect import PlatformFacts, detect_platform
from app_worker.seo_engine.render import RenderResult, render_page
from app_worker.seo_engine.robots_ai import AI_BOTS, check_ai_robots, parse_ai_robots
from app_worker.seo_engine.url_safety import URLSafetyError, validate_url, validate_url_strict

__all__ = [
    "AI_BOTS",
    "FetchResult",
    "PlatformFacts",
    "RenderResult",
    "URLSafetyError",
    "check_ai_robots",
    "detect_platform",
    "fetch_page",
    "parse_ai_robots",
    "render_page",
    "validate_url",
    "validate_url_strict",
]
