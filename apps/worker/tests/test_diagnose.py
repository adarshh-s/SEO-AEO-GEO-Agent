"""Tests for diagnosis gap analysis and SEO/AEO fix generators."""

from app_worker.seo_engine.diagnose import (
    _extract_page_signals,
    analyze_target_and_competitors,
)
from app_worker.seo_engine.fetch import FetchResult
from app_worker.seo_engine.fixes import (
    generate_content_block_fix,
    generate_faq_fix,
    generate_meta_fix,
    generate_schema_fix,
    resolve_delivery_method,
    sanitize_html,
)


def test_extract_page_signals():
    html_doc = """
    <html>
      <head>
        <title>Test Page</title>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Acme Corp"
        }
        </script>
      </head>
      <body>
        <h1>Primary Headline</h1>
        <h2>Secondary Subhead</h2>
        <p>This is a paragraph with several distinct words for counting.</p>
      </body>
    </html>
    """
    words, headings, schemas = _extract_page_signals(html_doc)
    assert words > 5
    assert "Primary Headline" in headings
    assert "Secondary Subhead" in headings
    assert "Organization" in schemas


def test_analyze_target_and_competitors_detects_schema_and_meta_gaps():
    target_fetch = FetchResult(
        url="https://mysite.com",
        final_url="https://mysite.com",
        status_code=200,
        headers={},
        raw_html="<html><body><h1>My Page</h1><p>Brief text.</p></body></html>",
        raw_text="My Page Brief text.",
        raw_html_hash="dummyhash",
        meta_title="Short",
        meta_description=None,  # Missing meta description
    )

    result = analyze_target_and_competitors(
        target_fetch=target_fetch,
        target_url="https://mysite.com",
        target_keyword_or_prompt="best cloud hosting",
        target_language="en",
        competitor_urls=[],  # No competitors fetched in unit test
        robots_txt_status={"gptbot": False},  # GPTBot blocked!
    )

    finding_codes = [f.code for f in result.findings]
    assert "suboptimal_meta_description" in finding_codes
    assert "suboptimal_title" in finding_codes
    assert "missing_schema" in finding_codes
    assert "robots_ai_blocked" in finding_codes


def test_resolve_delivery_method():
    assert resolve_delivery_method("wordpress", "schema") == "wordpress"
    assert resolve_delivery_method("shopify", "meta") == "shopify"
    assert resolve_delivery_method("nextjs", "faq") == "sdk"
    assert resolve_delivery_method("custom", "schema") == "snippet"


def test_generate_schema_fix():
    fix_en = generate_schema_fix(
        site_name="Acme Solutions",
        domain="acme.com",
        target_url="https://acme.com",
        platform="wordpress",
        language="en",
    )
    assert fix_en.type == "schema"
    assert fix_en.recommended_delivery == "wordpress"
    assert fix_en.payload["json_ld"]["@type"] == "Organization"
    assert fix_en.payload["json_ld"]["name"] == "Acme Solutions"

    # LocalBusiness when city provided
    fix_local = generate_schema_fix(
        site_name="Riyadh Dental",
        domain="riyadhdental.sa",
        target_url="https://riyadhdental.sa",
        platform="custom",
        language="ar",
        city="Riyadh",
    )
    assert fix_local.payload["json_ld"]["@type"] == "LocalBusiness"
    assert fix_local.language == "ar"


def test_generate_meta_fix():
    fix_meta = generate_meta_fix(
        target_query="best accounting software",
        site_name="QuardLink",
        domain="quardlink.com",
        platform="shopify",
        language="en",
    )
    assert fix_meta.type == "meta"
    assert fix_meta.recommended_delivery == "shopify"
    assert "best accounting software" in fix_meta.payload["title"].lower()
    assert len(fix_meta.payload["meta_description"]) > 20


def test_generate_faq_fix():
    fix_faq = generate_faq_fix(
        target_query="Project Management Tools",
        site_name="TaskApp",
        platform="nextjs",
        language="en",
    )
    assert fix_faq.type == "faq"
    assert fix_faq.recommended_delivery == "sdk"
    assert len(fix_faq.payload["faqs"]) >= 2
    assert "json_ld" in fix_faq.payload
    assert fix_faq.payload["json_ld"]["@type"] == "FAQPage"


def test_generate_content_block_fix_arabic():
    fix_content = generate_content_block_fix(
        target_query="أفضل برنامج محاسبة سحابي",
        site_name="محاسب تك",
        platform="salla",
        language="ar",
    )
    assert fix_content.type == "content_block"
    assert fix_content.language == "ar"
    assert fix_content.recommended_delivery == "snippet"
    assert "dir=" in fix_content.payload["html"] or "محاسب تك" in fix_content.payload["html"]


def test_html_sanitizer():
    dirty = '<p>Normal text</p><script>alert("hacked")</script><a href="javascript:void(0)" onclick="evil()">Click</a>'
    clean = sanitize_html(dirty)
    assert "<script" not in clean
    assert "alert" not in clean
    assert "onclick" not in clean
    assert "javascript:" not in clean
    assert "<p>Normal text</p>" in clean
