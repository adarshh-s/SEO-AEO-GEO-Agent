"""Weekly email digest builder in English and Arabic."""

from app_core.brand import BRAND
from app_core.settings import get_settings


def generate_weekly_digest(
    *,
    site_name: str,
    domain: str,
    health_score: int = 80,
    keywords_count: int = 0,
    ai_visibility_pct: int = 0,
    fixes_count: int = 0,
    language: str = "en",
) -> tuple[str, str, str]:
    """Generate weekly digest email content returning (subject, text_body, html_body)."""
    settings = get_settings()
    app_url = settings.app_url.rstrip("/")
    product = BRAND["product_name"]

    if language == "ar":
        subject = f"[{product}] الملخص الأسبوعي لموقعك: {domain}"
        text_body = f"""
مرحباً،

إليك ملخص أداء تحسين محركات البحث والذكاء الاصطناعي (AEO) لموقع {site_name} ({domain}) خلال هذا الأسبوع:

• تقييم صحة الموقع العام: {health_score}/100
• نسبة الظهور في محركات الذكاء الاصطناعي: {ai_visibility_pct}%
• عدد الكلمات المفتاحية النشطة: {keywords_count}
• التعديلات والتحسينات المطبقة: {fixes_count}

شاهد التقرير المفصل وأحدث التوصيات في لوحة التحكم:
{app_url}/app

فريق {product}
"""
        html_body = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px; direction: rtl; text-align: right; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background-color: #2563eb; color: #ffffff; padding: 24px; }}
    .content {{ padding: 28px 24px; }}
    .card-grid {{ display: table; width: 100%; margin: 20px 0; border-collapse: separate; border-spacing: 8px; }}
    .card-col {{ display: table-cell; width: 50%; background: #f1f5f9; border-radius: 8px; padding: 16px; text-align: center; }}
    .metric-value {{ font-size: 24px; font-weight: bold; color: #2563eb; margin: 0; }}
    .metric-label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; margin-top: 16px; }}
    .footer {{ font-size: 11px; color: #94a3b8; text-align: center; padding: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin:0;">{product}</h2>
      <p style="margin:4px 0 0 0; opacity:0.9;">الملخص الأسبوعي لأداء موقع {domain}</p>
    </div>
    <div class="content">
      <p>مرحباً، إليك نظرة سريعة على أداء موقع <strong>{site_name}</strong> في محركات البحث وإجابات الذكاء الاصطناعي (ChatGPT، Gemini، Perplexity):</p>
      <div class="card-grid">
        <div class="card-col">
          <div class="metric-value">{health_score}/100</div>
          <div class="metric-label">صحة الموقع الشاملة</div>
        </div>
        <div class="card-col">
          <div class="metric-value">{ai_visibility_pct}%</div>
          <div class="metric-label">ظهور الذكاء الاصطناعي</div>
        </div>
      </div>
      <div class="card-grid">
        <div class="card-col">
          <div class="metric-value">{keywords_count}</div>
          <div class="metric-label">كلمات مفتاحية متتبعة</div>
        </div>
        <div class="card-col">
          <div class="metric-value">{fixes_count}</div>
          <div class="metric-label">تحسينات تم تطبيقها</div>
        </div>
      </div>
      <center>
        <a href="{app_url}/app" class="btn">الانتقال إلى لوحة التحكم</a>
      </center>
    </div>
    <div class="footer">
      تم إرسال هذا التقرير تلقائياً بواسطة منصة {product}.
    </div>
  </div>
</body>
</html>"""
    else:
        subject = f"[{product}] Weekly Performance Digest: {domain}"
        text_body = f"""
Hello,

Here is your weekly SEO & AI search performance overview for {site_name} ({domain}):

• Overall SEO Health Score: {health_score}/100
• AI Search Visibility: {ai_visibility_pct}%
• Active Keywords Tracked: {keywords_count}
• Deployed Optimizations: {fixes_count}

View your full dashboard and actionable recommendations:
{app_url}/app

The {product} Team
"""
        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background-color: #2563eb; color: #ffffff; padding: 24px; }}
    .content {{ padding: 28px 24px; }}
    .card-grid {{ display: table; width: 100%; margin: 20px 0; border-collapse: separate; border-spacing: 8px; }}
    .card-col {{ display: table-cell; width: 50%; background: #f1f5f9; border-radius: 8px; padding: 16px; text-align: center; }}
    .metric-value {{ font-size: 24px; font-weight: bold; color: #2563eb; margin: 0; }}
    .metric-label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; margin-top: 16px; }}
    .footer {{ font-size: 11px; color: #94a3b8; text-align: center; padding: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin:0;">{product}</h2>
      <p style="margin:4px 0 0 0; opacity:0.9;">Weekly SEO & AI Search Digest for {domain}</p>
    </div>
    <div class="content">
      <p>Hello, here is your summary of <strong>{site_name}</strong>'s search and AI answer performance this week:</p>
      <div class="card-grid">
        <div class="card-col">
          <div class="metric-value">{health_score}/100</div>
          <div class="metric-label">Overall Health Score</div>
        </div>
        <div class="card-col">
          <div class="metric-value">{ai_visibility_pct}%</div>
          <div class="metric-label">AI Visibility Rate</div>
        </div>
      </div>
      <div class="card-grid">
        <div class="card-col">
          <div class="metric-value">{keywords_count}</div>
          <div class="metric-label">Keywords Tracked</div>
        </div>
        <div class="card-col">
          <div class="metric-value">{fixes_count}</div>
          <div class="metric-label">Fixes Deployed</div>
        </div>
      </div>
      <center>
        <a href="{app_url}/app" class="btn">View Full Dashboard</a>
      </center>
    </div>
    <div class="footer">
      Generated automatically by {product} for {domain}.
    </div>
  </div>
</body>
</html>"""

    return subject, text_body, html_body
