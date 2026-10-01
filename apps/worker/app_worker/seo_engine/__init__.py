"""SEO Engine adapter over claude-seo scripts and custom analyzers."""

from app_worker.seo_engine.diagnose import (
    CompetitorPageAnalysis,
    DiagnosisFinding,
    DiagnosisResult,
    analyze_target_and_competitors,
)
from app_worker.seo_engine.fetch import FetchResult, fetch_page
from app_worker.seo_engine.fixes import (
    GeneratedFix,
    generate_content_block_fix,
    generate_faq_fix,
    generate_meta_fix,
    generate_schema_fix,
    resolve_delivery_method,
    sanitize_html,
)
from app_worker.seo_engine.platform_detect import PlatformFacts, detect_platform
from app_worker.seo_engine.render import RenderResult, render_page
from app_worker.seo_engine.robots_ai import AI_BOTS, check_ai_robots, parse_ai_robots
from app_worker.seo_engine.url_safety import URLSafetyError, validate_url, validate_url_strict

__all__ = [
    "AI_BOTS",
    "CompetitorPageAnalysis",
    "DiagnosisFinding",
    "DiagnosisResult",
    "FetchResult",
    "GeneratedFix",
    "PlatformFacts",
    "RenderResult",
    "URLSafetyError",
    "analyze_target_and_competitors",
    "check_ai_robots",
    "detect_platform",
    "fetch_page",
    "generate_content_block_fix",
    "generate_faq_fix",
    "generate_meta_fix",
    "generate_schema_fix",
    "parse_ai_robots",
    "render_page",
    "resolve_delivery_method",
    "sanitize_html",
    "validate_url",
    "validate_url_strict",
]
