"""Unit tests for audit engine and PDF/digest generation."""

from app_core.reports.digest import generate_weekly_digest
from app_core.reports.pdf import generate_audit_pdf
from app_worker.seo_engine.audit import run_comprehensive_audit
from app_worker.seo_engine.fetch import FetchResult
from app_worker.seo_engine.render import RenderResult


def test_run_comprehensive_audit_html():
    raw_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Acme Tools - Best Online Hardware Store</title>
  <meta name="description" content="Discover premium power tools, drills, and hardware accessories with fast shipping and warranty.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://example.com">
  <meta property="og:title" content="Acme Tools">
  <meta property="og:image" content="https://example.com/og.jpg">
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "Store", "name": "Acme Tools"}
  </script>
</head>
<body>
  <h1>Welcome to Acme Tools</h1>
  <p>We provide the best equipment for professional builders and hobbyists.</p>
  <p>Explore our extensive catalog of power saws, drills, measuring devices, and safety gear.</p>
  <p>Our expert support team is always ready to answer your technical questions.</p>
  <div class="faq-item">
    <h3>Do you offer international shipping?</h3>
    <p>Yes, we ship globally within 3-5 business days.</p>
  </div>
</body>
</html>"""
    fetch_res = FetchResult(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        headers={"content-type": "text/html"},
        raw_html=raw_html,
        raw_text="Welcome to Acme Tools We provide the best equipment... Explore our catalog...",
        raw_html_hash="abc123hash",
        meta_title="Acme Tools - Best Online Hardware Store",
        meta_description="Discover premium power tools, drills, and hardware accessories with fast shipping and warranty.",
    )
    render_res = RenderResult(
        rendered_html=raw_html,
        rendered_text=fetch_res.raw_text,
        rendered_html_hash="abc123hash",
        js_only_content_detected=False,
        js_only_text="",
    )

    result = run_comprehensive_audit(
        "https://example.com",
        fetch_res=fetch_res,
        render_res=render_res,
    )

    assert result.overall_score > 60
    assert "technical" in result.category_scores
    assert "content" in result.category_scores
    assert "ai_readiness" in result.category_scores
    assert "performance" in result.category_scores
    assert len(result.issues) > 10


def test_generate_audit_pdf_bytes():
    pdf_bytes = generate_audit_pdf(
        domain="example.com",
        overall_score=85,
        category_scores={
            "technical": 90,
            "content": 80,
            "ai_readiness": 88,
            "performance": 82,
        },
        summary={"total_checks": 15, "passed_checks": 13, "total_issues": 2},
        issues=[
            {
                "id": "tech-open-graph",
                "severity": "low",
                "category": "technical",
                "passed": False,
                "title": {"en": "Missing OG Tags", "ar": "وسوم OG مفقودة"},
                "recommendation": {"en": "Add OG tags", "ar": "أضف الوسوم"},
            }
        ],
        language="en",
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_weekly_digest_bilingual():
    sub_en, text_en, html_en = generate_weekly_digest(
        site_name="My Store",
        domain="mystore.com",
        health_score=88,
        keywords_count=25,
        ai_visibility_pct=72,
        fixes_count=6,
        language="en",
    )
    assert "Weekly Performance Digest" in sub_en
    assert "mystore.com" in sub_en
    assert "88/100" in text_en
    assert "<!DOCTYPE html>" in html_en

    sub_ar, text_ar, html_ar = generate_weekly_digest(
        site_name="متجري",
        domain="mystore.com",
        health_score=88,
        keywords_count=25,
        ai_visibility_pct=72,
        fixes_count=6,
        language="ar",
    )
    assert "الملخص الأسبوعي" in sub_ar
    assert 'dir="rtl"' in html_ar
    assert "88/100" in text_ar
