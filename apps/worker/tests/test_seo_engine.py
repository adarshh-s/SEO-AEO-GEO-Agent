import pytest

from app_worker.seo_engine.fetch import FetchResult
from app_worker.seo_engine.platform_detect import detect_platform
from app_worker.seo_engine.robots_ai import parse_ai_robots
from app_worker.seo_engine.url_safety import URLSafetyError, validate_url, validate_url_strict


def test_url_safety_validation():
    # Valid external urls
    assert validate_url("https://example.com") is True
    assert validate_url("http://quardlink.com/blog") is True

    # Invalid schemes
    assert validate_url("ftp://example.com") is False
    assert validate_url("file:///etc/passwd") is False
    assert validate_url("javascript:alert(1)") is False

    # Blocked local hosts
    assert validate_url("http://localhost:8000") is False
    assert validate_url("http://127.0.0.1:5432") is False
    assert validate_url("http://169.254.169.254/latest/meta-data/") is False

    # Strict validation rejects invalid urls
    with pytest.raises(URLSafetyError):
        validate_url_strict("http://localhost:8080")


def _make_fetch(
    html: str, headers: dict | None = None, url: str = "https://example.com"
) -> FetchResult:
    return FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        headers=headers or {},
        raw_html=html,
        raw_text="",
        raw_html_hash="hash",
        meta_title=None,
        meta_description=None,
    )


def test_platform_detection_wordpress():
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="generator" content="WordPress 6.4" />
        <link rel="stylesheet" href="/wp-content/themes/twentytwentyfour/style.css" />
      </head>
      <body><h1>My WP Blog</h1></body>
    </html>
    """
    res = detect_platform(_make_fetch(html))
    assert res.platform == "wordpress"
    assert res.confidence >= 0.8
    assert res.rendering == "server"


def test_platform_detection_shopify():
    html = """
    <html><head><script src="https://cdn.shopify.com/s/files/1.js"></script></head><body>Store</body></html>
    """
    res = detect_platform(_make_fetch(html))
    assert res.platform == "shopify"
    assert res.confidence >= 0.8


def test_platform_detection_salla():
    html = """
    <html><head><script src="https://cdn.salla.sa/app.js"></script></head><body>متجر سلة</body></html>
    """
    res = detect_platform(_make_fetch(html))
    assert res.platform == "salla"


def test_platform_detection_nextjs():
    html = """
    <html><head></head><body><div id="__next"><h1>Next App</h1></div><script src="/_next/static/chunks/main.js"></script></body></html>
    """
    res = detect_platform(_make_fetch(html, headers={"x-powered-by": "Next.js"}))
    assert res.platform == "nextjs"
    assert res.rendering == "hybrid"


def test_robots_ai_auditing():
    robots_txt = """
    User-agent: *
    Disallow: /admin/

    User-agent: GPTBot
    Disallow: /

    User-agent: ClaudeBot
    Allow: /public/
    Disallow: /

    User-agent: Google-Extended
    Disallow: /
    """
    results = parse_ai_robots(robots_txt)
    assert results["GPTBot"] is False
    assert results["ClaudeBot"] is False
    assert results["Google-Extended"] is False
    # PerplexityBot is not specifically blocked, falls back to wildcard
    assert results["PerplexityBot"] is True
