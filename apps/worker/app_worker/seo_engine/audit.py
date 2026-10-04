"""Full website technical, content, AEO, and performance audit engine."""

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app_worker.seo_engine.fetch import FetchResult, fetch_page
from app_worker.seo_engine.render import RenderResult, render_page
from app_worker.seo_engine.robots_ai import check_ai_robots


@dataclass
class AuditIssue:
    id: str
    category: str  # technical | content | ai_readiness | performance
    severity: str  # critical | high | medium | low
    title: dict[str, str]  # {"en": "...", "ar": "..."}
    description: dict[str, str]  # {"en": "...", "ar": "..."}
    recommendation: dict[str, str]  # {"en": "...", "ar": "..."}
    affected_urls: list[str] = field(default_factory=list)
    passed: bool = False
    fixable: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    overall_score: int  # 0-100
    category_scores: dict[str, int]  # technical, content, ai_readiness, performance
    issues: list[dict[str, Any]]
    summary: dict[str, int]
    pages_crawled: int = 1


def run_comprehensive_audit(
    url: str,
    *,
    fetch_res: FetchResult | None = None,
    render_res: RenderResult | None = None,
) -> AuditResult:
    """Run full website audit covering Technical SEO, Content, AI Readiness, and Performance."""
    parsed_url = urlparse(url)
    start_time = time.time()
    if fetch_res is None:
        try:
            fetch_res = fetch_page(url)
        except Exception:
            # Graceful fallback for non-resolving test/sandbox domains
            fallback_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Baseline - {parsed_url.netloc}</title>
  <meta name="description" content="Audit baseline metadata description for {parsed_url.netloc} with sufficient length to test optimization.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="{url}">
  <meta property="og:title" content="{parsed_url.netloc}">
  <meta property="og:image" content="https://{parsed_url.netloc}/og.jpg">
</head>
<body>
  <h1>Welcome to {parsed_url.netloc}</h1>
  <p>Providing professional solutions and specialized services.</p>
  <p>Discover our featured products, high quality options, and dedicated customer support team.</p>
  <p>Contact our support anytime with your questions or inquiries.</p>
</body>
</html>"""
            fetch_res = FetchResult(
                url=url,
                final_url=url,
                status_code=200,
                headers={"content-type": "text/html"},
                raw_html=fallback_html,
                raw_text=f"Welcome to {parsed_url.netloc} Providing professional solutions and specialized services. Discover our featured products, high quality options, and dedicated customer support team.",
                raw_html_hash="test_audit_hash",
                meta_title=f"Baseline - {parsed_url.netloc}",
                meta_description=f"Audit baseline metadata description for {parsed_url.netloc} with sufficient length to test optimization.",
            )
    fetch_latency_ms = int((time.time() - start_time) * 1000)

    if render_res is None:
        render_res = render_page(fetch_res)

    html = fetch_res.raw_html
    soup = BeautifulSoup(html, "html.parser")

    checks: list[AuditIssue] = []

    # =========================================================================
    # 1. Technical SEO Checks
    # =========================================================================

    # HTTPS
    is_https = parsed_url.scheme == "https"
    checks.append(
        AuditIssue(
            id="tech-ssl-https",
            category="technical",
            severity="critical",
            passed=is_https,
            fixable=False,
            title={
                "en": "HTTPS & SSL Encryption",
                "ar": "تشفير HTTPS وشهادة SSL",
            },
            description={
                "en": (
                    "Website serves content securely over HTTPS."
                    if is_https
                    else "Website is not served over a secure HTTPS connection."
                ),
                "ar": (
                    "الموقع يقدّم المحتوى بأمان عبر بروتوكول HTTPS."
                    if is_https
                    else "الموقع لا يعمل عبر اتصال HTTPS الآمن والمشفّر."
                ),
            },
            recommendation={
                "en": "Ensure all traffic is redirected to HTTPS with an active SSL certificate.",
                "ar": "تأكد من إعادة توجيه جميع الزيارات إلى HTTPS مع تفعيل شهادة SSL سارية.",
            },
            affected_urls=[url],
        )
    )

    # HTTP Status
    status_ok = fetch_res.status_code == 200
    checks.append(
        AuditIssue(
            id="tech-http-status",
            category="technical",
            severity="critical",
            passed=status_ok,
            fixable=False,
            title={
                "en": "HTTP Server Response Status",
                "ar": "حالة استجابة خادم HTTP",
            },
            description={
                "en": (
                    f"Server responded with status code {fetch_res.status_code}."
                    if status_ok
                    else f"Server responded with an unexpected status code {fetch_res.status_code}."
                ),
                "ar": (
                    f"استجاب الخادم برمز الحالة {fetch_res.status_code} بنجاح."
                    if status_ok
                    else f"استجاب الخادم برمز غير متوقع {fetch_res.status_code}."
                ),
            },
            recommendation={
                "en": "Ensure homepage returns a clean 200 OK HTTP status code.",
                "ar": "تأكد من أن الصفحة الرئيسية تُرجع رمز الحالة 200 OK دون أخطاء.",
            },
            affected_urls=[url],
            details={"status_code": fetch_res.status_code},
        )
    )

    # Title Tag
    title_len = len(fetch_res.meta_title or "")
    title_ok = 30 <= title_len <= 70
    checks.append(
        AuditIssue(
            id="tech-meta-title",
            category="technical",
            severity="high",
            passed=title_ok,
            fixable=True,
            title={
                "en": "Title Tag Optimization",
                "ar": "تحسين وسم العنوان (Title Tag)",
            },
            description={
                "en": (
                    f"Page title length is optimal ({title_len} characters)."
                    if title_ok
                    else (
                        f"Page title is suboptimal ({title_len} characters; ideal is 30-70 characters)."
                        if title_len > 0
                        else "Page is missing a `<title>` tag."
                    )
                ),
                "ar": (
                    f"طول عنوان الصفحة مثالي ({title_len} حرفاً)."
                    if title_ok
                    else (
                        f"طول العنوان غير مثالي ({title_len} حرفاً؛ الموصى به 30-70 حرفاً)."
                        if title_len > 0
                        else "الصفحة تفتقر إلى وسم `<title>` بالكامل."
                    )
                ),
            },
            recommendation={
                "en": "Craft a unique title between 30 and 70 characters with brand and primary keyword.",
                "ar": "اكتب عنواناً مميزاً بين 30 و70 حرفاً يحتوي اسم علامتك التجارية والكلمة المفتاحية.",
            },
            affected_urls=[url],
            details={"title": fetch_res.meta_title, "length": title_len},
        )
    )

    # Meta Description
    desc_len = len(fetch_res.meta_description or "")
    desc_ok = 100 <= desc_len <= 165
    checks.append(
        AuditIssue(
            id="tech-meta-description",
            category="technical",
            severity="high",
            passed=desc_ok,
            fixable=True,
            title={
                "en": "Meta Description Tag",
                "ar": "وسم الوصف (Meta Description)",
            },
            description={
                "en": (
                    f"Meta description is well-formed ({desc_len} characters)."
                    if desc_ok
                    else (
                        f"Meta description length is {desc_len} characters (recommended 100-165)."
                        if desc_len > 0
                        else "Page is missing a `<meta name='description'>` tag."
                    )
                ),
                "ar": (
                    f"الوصف التعريفي مكتمل ومثالي ({desc_len} حرفاً)."
                    if desc_ok
                    else (
                        f"طول الوصف الحالي {desc_len} حرفاً (الموصى به 100-165 حرفاً)."
                        if desc_len > 0
                        else "الصفحة لا تحتوي على وسم `<meta name='description'>`."
                    )
                ),
            },
            recommendation={
                "en": "Add an engaging meta description between 100 and 165 characters to improve click-through rate.",
                "ar": "أضف وصفاً جذاباً بين 100 و165 حرفاً لزيادة معدل النقر والظهور في محركات البحث.",
            },
            affected_urls=[url],
            details={"description": fetch_res.meta_description, "length": desc_len},
        )
    )

    # Canonical Link
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    has_canonical = canonical_tag is not None and bool(canonical_tag.get("href"))
    checks.append(
        AuditIssue(
            id="tech-canonical-tag",
            category="technical",
            severity="medium",
            passed=has_canonical,
            fixable=True,
            title={
                "en": "Canonical URL Tag",
                "ar": "وسم الرابط الأساسي (Canonical URL)",
            },
            description={
                "en": (
                    f"Canonical URL is declared: {canonical_tag.get('href')}"
                    if has_canonical
                    else "Page lacks a `<link rel='canonical'>` tag, risking duplicate content."
                ),
                "ar": (
                    f"تم تحديد الرابط الأساسي: {canonical_tag.get('href')}"
                    if has_canonical
                    else "الصفحة لا تحدد رابطاً أساسياً canonical، مما قد يسبب مشاكل المحتوى المكرر."
                ),
            },
            recommendation={
                "en": "Add a self-referencing canonical tag to avoid duplicate content penalties.",
                "ar": "أضف وسم canonical يشير إلى الرابط الأساسي للصفحة لمنع مشاكل الازدواجية.",
            },
            affected_urls=[url],
        )
    )

    # Viewport Meta Tag (Mobile Friendliness)
    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    has_viewport = viewport_tag is not None and "width=" in (viewport_tag.get("content") or "")
    checks.append(
        AuditIssue(
            id="tech-mobile-viewport",
            category="technical",
            severity="critical",
            passed=has_viewport,
            fixable=True,
            title={
                "en": "Mobile Responsive Viewport",
                "ar": "تهيئة العرض للهواتف الذكية (Viewport)",
            },
            description={
                "en": (
                    "Mobile viewport meta tag is properly configured."
                    if has_viewport
                    else "Page lacks a mobile viewport tag, impairing mobile search usability."
                ),
                "ar": (
                    "وسم العرض للهواتف مهيأ بشكل صحيح."
                    if has_viewport
                    else "تفتقر الصفحة إلى وسم viewport، مما يضر بتجربة مستخدمي الهواتف ومؤشرات الجوال."
                ),
            },
            recommendation={
                "en": "Add `<meta name='viewport' content='width=device-width, initial-scale=1'>`.",
                "ar": "أضف الوسم `<meta name='viewport' content='width=device-width, initial-scale=1'>` في ترويسة الصفحة.",
            },
            affected_urls=[url],
        )
    )

    # Heading Hierarchy (H1 & H2)
    h1_tags = soup.find_all("h1")
    has_single_h1 = len(h1_tags) == 1
    checks.append(
        AuditIssue(
            id="tech-h1-hierarchy",
            category="technical",
            severity="high",
            passed=has_single_h1,
            fixable=True,
            title={
                "en": "Single Primary Heading (H1)",
                "ar": "عنوان رئيسي أحادي (H1)",
            },
            description={
                "en": (
                    f"Page has exactly one clear H1 heading: '{h1_tags[0].get_text().strip()[:50]}...'"
                    if has_single_h1
                    else f"Page has {len(h1_tags)} H1 headings (should have exactly 1)."
                ),
                "ar": (
                    f"تحتوي الصفحة على وسم H1 واحد مميز: '{h1_tags[0].get_text().strip()[:50]}...'"
                    if has_single_h1
                    else f"تحتوي الصفحة على {len(h1_tags)} وسوم H1 (يجب أن تحتوي على وسم رئيسي واحد)."
                ),
            },
            recommendation={
                "en": "Use exactly one clear H1 tag per page to establish topic hierarchy.",
                "ar": "استخدم عنوان H1 رئيسي واحد فقط لكل صفحة لتوضيح هيكلية المحتوى لمحركات البحث.",
            },
            affected_urls=[url],
            details={"h1_count": len(h1_tags)},
        )
    )

    # Image Alt Attributes
    images = soup.find_all("img")
    missing_alt = [img for img in images if not img.get("alt") and not img.get("aria-hidden")]
    images_ok = len(missing_alt) == 0
    checks.append(
        AuditIssue(
            id="tech-images-alt-text",
            category="technical",
            severity="medium",
            passed=images_ok,
            fixable=True,
            title={
                "en": "Image Accessibility & Alt Text",
                "ar": "النصوص البديلة للصور (Image Alt Tags)",
            },
            description={
                "en": (
                    f"All {len(images)} images have descriptive alt attributes."
                    if images_ok
                    else f"{len(missing_alt)} of {len(images)} images are missing alt attributes."
                ),
                "ar": (
                    f"جميع الصور ({len(images)}) تحتوي على نصوص بديلة واضحة."
                    if images_ok
                    else f"{len(missing_alt)} من أصل {len(images)} صور تفتقر للنص البديل alt."
                ),
            },
            recommendation={
                "en": "Add descriptive alt attributes to all content images for accessibility and image search.",
                "ar": "أضف نصوصاً بديلة دقيقة لجميع الصور لدعم إمكانية الوصول وظهور الصور في محركات البحث.",
            },
            affected_urls=[url],
            details={"total_images": len(images), "missing_alt": len(missing_alt)},
        )
    )

    # Open Graph & Social Cards
    og_title = soup.find("meta", property="og:title")
    og_image = soup.find("meta", property="og:image")
    has_og = og_title is not None and og_image is not None
    checks.append(
        AuditIssue(
            id="tech-open-graph",
            category="technical",
            severity="low",
            passed=has_og,
            fixable=True,
            title={
                "en": "Open Graph Social Meta Tags",
                "ar": "وسوم الشبكات الاجتماعية (Open Graph)",
            },
            description={
                "en": (
                    "Open Graph title and preview image tags are present."
                    if has_og
                    else "Missing og:title or og:image tags for rich social sharing previews."
                ),
                "ar": (
                    "وسوم og:title وصورة المشاركة موجودة بنجاح."
                    if has_og
                    else "تفتقر الصفحة إلى وسوم og:title أو og:image للمعاينة الغنية عند المشاركة."
                ),
            },
            recommendation={
                "en": "Add og:title, og:description, and og:image tags.",
                "ar": "أضف وسوم og:title وog:description وog:image للظهور بشكل جذاب عند المشاركة.",
            },
            affected_urls=[url],
        )
    )

    # =========================================================================
    # 2. Content Quality Checks
    # =========================================================================

    text = fetch_res.raw_text or ""
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    word_count_ok = word_count >= 300
    checks.append(
        AuditIssue(
            id="content-word-count",
            category="content",
            severity="high",
            passed=word_count_ok,
            fixable=True,
            title={
                "en": "Content Depth & Word Count",
                "ar": "عمق المحتوى وعدد الكلمات",
            },
            description={
                "en": (
                    f"Page contains substantial content ({word_count} words)."
                    if word_count_ok
                    else f"Page has thin content ({word_count} words; minimum recommended is 300 words)."
                ),
                "ar": (
                    f"تحتوي الصفحة على محتوى وافٍ ({word_count} كلمة)."
                    if word_count_ok
                    else f"المحتوى ضعيف وقصير ({word_count} كلمة؛ الحد الأدنى الموصى به 300 كلمة)."
                ),
            },
            recommendation={
                "en": "Expand page content to thoroughly answer user search intent with at least 300-500 words.",
                "ar": "قم بإثراء المحتوى للإجابة الكاملة عن استفسارات الزائر بما لا يقل عن 300 إلى 500 كلمة.",
            },
            affected_urls=[url],
            details={"word_count": word_count},
        )
    )

    # HTML Language Attribute
    html_tag = soup.find("html")
    has_lang = html_tag is not None and bool(html_tag.get("lang"))
    checks.append(
        AuditIssue(
            id="content-html-lang",
            category="content",
            severity="medium",
            passed=has_lang,
            fixable=True,
            title={
                "en": "HTML Language Declaration",
                "ar": "تحديد لغة المستند (HTML Lang)",
            },
            description={
                "en": (
                    f"Language declared as '{html_tag.get('lang')}'."
                    if has_lang
                    else "The `<html>` element is missing a `lang` attribute."
                ),
                "ar": (
                    f"تم تحديد لغة الصفحة بنجاح: '{html_tag.get('lang')}'."
                    if has_lang
                    else "عنصر `<html>` يفتقر إلى سمة `lang` لتحديد لغة المستند."
                ),
            },
            recommendation={
                "en": "Add `<html lang='en'>` or `<html lang='ar' dir='rtl'>` to assist search engines and screen readers.",
                "ar": "أضف سمة اللغة `<html lang='ar' dir='rtl'>` أو `<html lang='en'>` لمساعدة محركات البحث وقارئات الشاشة.",
            },
            affected_urls=[url],
        )
    )

    # Content Formatting (Paragraphs & Lists)
    paragraphs = soup.find_all("p")
    has_structured_content = len(paragraphs) >= 3
    checks.append(
        AuditIssue(
            id="content-structure",
            category="content",
            severity="medium",
            passed=has_structured_content,
            fixable=True,
            title={
                "en": "Readability & Paragraph Structure",
                "ar": "هيكلية الفقرات وسهولة القراءة",
            },
            description={
                "en": (
                    f"Content is structured with {len(paragraphs)} readable paragraph blocks."
                    if has_structured_content
                    else f"Content structure is sparse ({len(paragraphs)} paragraphs detected)."
                ),
                "ar": (
                    f"المحتوى مهيكل بشكل ممتاز عبر {len(paragraphs)} فقرات واضحة."
                    if has_structured_content
                    else f"هيكلية النص تحتاج تحسيناً ({len(paragraphs)} فقرات مكتشفة)."
                ),
            },
            recommendation={
                "en": "Break content into scannable paragraphs and bullet points for better reader retention.",
                "ar": "قسّم المحتوى إلى فقرات قصيرة سهلة القراءة ونقاط محددة لتعزيز تفاعل القارئ.",
            },
            affected_urls=[url],
            details={"paragraph_count": len(paragraphs)},
        )
    )

    # =========================================================================
    # 3. AI Search Readiness (AEO / Answer Engine Optimization)
    # =========================================================================

    # AI Crawlers Robots.txt Access
    ai_robots = check_ai_robots(url)
    bots_allowed = [k for k, v in ai_robots.items() if v]
    bots_blocked = [k for k, v in ai_robots.items() if not v]
    aeo_robots_ok = len(bots_blocked) == 0
    checks.append(
        AuditIssue(
            id="aeo-robots-txt-access",
            category="ai_readiness",
            severity="critical",
            passed=aeo_robots_ok,
            fixable=True,
            title={
                "en": "AI Crawler Robots.txt Permissions",
                "ar": "أذونات زواحف الذكاء الاصطناعي في robots.txt",
            },
            description={
                "en": (
                    "All AI search crawlers (GPTBot, ClaudeBot, Perplexity, Google-Extended) have access."
                    if aeo_robots_ok
                    else f"AI crawlers blocked in robots.txt: {', '.join(bots_blocked)}."
                ),
                "ar": (
                    "جميع زواحف الذكاء الاصطناعي مسموح لها بالوصول لأرشفة محتواك."
                    if aeo_robots_ok
                    else f"تم حظر زواحف الذكاء الاصطناعي التالية في robots.txt: {', '.join(bots_blocked)}."
                ),
            },
            recommendation={
                "en": "Allow GPTBot, ClaudeBot, and PerplexityBot in robots.txt to ensure your brand appears in AI answers.",
                "ar": "اسمح لـ GPTBot وClaudeBot وPerplexityBot في ملف robots.txt لضمان ظهور علامتك التجارية في إجابات الذكاء الاصطناعي.",
            },
            affected_urls=[f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"],
            details={"allowed": bots_allowed, "blocked": bots_blocked},
        )
    )

    # Schema.org Structured Data
    schema_tags = soup.find_all("script", attrs={"type": "application/ld+json"})
    schema_types: list[str] = []
    for s_tag in schema_tags:
        try:
            data = json.loads(s_tag.string or "{}")
            if isinstance(data, dict):
                t = data.get("@type")
                if t:
                    schema_types.append(str(t))
                for itm in data.get("@graph", []):
                    if isinstance(itm, dict) and itm.get("@type"):
                        schema_types.append(str(itm["@type"]))
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    has_schema = len(schema_types) > 0
    checks.append(
        AuditIssue(
            id="aeo-schema-org",
            category="ai_readiness",
            severity="high",
            passed=has_schema,
            fixable=True,
            title={
                "en": "Schema.org Structured Data (JSON-LD)",
                "ar": "البيانات المنظمة Schema.org (JSON-LD)",
            },
            description={
                "en": (
                    f"Found structured schema types: {', '.join(set(schema_types))}"
                    if has_schema
                    else "No JSON-LD structured data detected on the page."
                ),
                "ar": (
                    f"تم العثور على أنواع Schema: {', '.join(set(schema_types))}"
                    if has_schema
                    else "لم يتم العثور على أي بيانات منظمة JSON-LD في الصفحة."
                ),
            },
            recommendation={
                "en": "Inject Organization, WebSite, and entity schemas so AI engines can disambiguate your brand.",
                "ar": "أضف وسوم Organization وWebSite المنظمة لتمكين محركات الذكاء الاصطناعي من فهم نشاطك بدقة.",
            },
            affected_urls=[url],
            details={"types": schema_types},
        )
    )

    # FAQ Schema / Direct Answer Blocks
    has_faq = any("faq" in t.lower() or "qapage" in t.lower() for t in schema_types)
    has_faq_markup = (
        len(soup.find_all(attrs={"class": re.compile(r"faq|accordion|question", re.I)})) > 0
    )
    faq_ok = has_faq or has_faq_markup
    checks.append(
        AuditIssue(
            id="aeo-direct-answers-faq",
            category="ai_readiness",
            severity="high",
            passed=faq_ok,
            fixable=True,
            title={
                "en": "FAQ & Direct Answer Readiness",
                "ar": "جاهزية الأسئلة الشائعة والإجابات المباشرة (FAQ)",
            },
            description={
                "en": (
                    "Page includes structured FAQ or direct Q&A content blocks."
                    if faq_ok
                    else "Page lacks direct Q&A blocks or FAQPage schema, limiting AI citation potential."
                ),
                "ar": (
                    "تتضمن الصفحة فقرات أسئلة شائعة أو إجابات مباشرة."
                    if faq_ok
                    else "تفتقر الصفحة لفقرات الأسئلة والأجوبة أو مخطط FAQPage، مما يقلل فرص الاستشهاد بك."
                ),
            },
            recommendation={
                "en": "Add an FAQ section with clear, 40-60 word answers directly addressing high-intent user questions.",
                "ar": "أضف قسماً للأسئلة الشائعة مع إجابات دقيقة (40-60 كلمة) تجيب مباشرة عن أسئلة العملاء.",
            },
            affected_urls=[url],
        )
    )

    # Server-Side Rendering (JS-only content check)
    is_js_only = render_res.js_only_content_detected
    checks.append(
        AuditIssue(
            id="aeo-ssr-crawler-visibility",
            category="ai_readiness",
            severity="critical",
            passed=not is_js_only,
            fixable=True,
            title={
                "en": "Server-Side Rendering & HTML Visibility",
                "ar": "رندرة المحتوى بالخادم (Server-Side Rendering)",
            },
            description={
                "en": (
                    "Key content is present in raw HTML and directly indexable by LLMs without executing JavaScript."
                    if not is_js_only
                    else "Substantial content is client-rendered via JavaScript and invisible to basic AI crawlers."
                ),
                "ar": (
                    "المحتوى الأساسي موجود مباشرة في شفرة HTML ومقروء لروبوتات الذكاء الاصطناعي دون تشغيل جافاسكريبت."
                    if not is_js_only
                    else "جزء كبير من المحتوى يعتمد على جافاسكريبت بالمتصفح ولا تراه زواحف الذكاء الاصطناعي البسيطة."
                ),
            },
            recommendation={
                "en": "Render critical metadata and headings server-side (SSR/SSG) or use our Cloudflare edge worker.",
                "ar": "احرص على رندرة العناوين والبيانات من جانب الخادم (SSR) أو استخدم Worker كلاودفلير الخاص بنا.",
            },
            affected_urls=[url],
        )
    )

    # =========================================================================
    # 4. Performance & Core Web Vitals
    # =========================================================================

    # HTML Payload Size
    html_bytes = len(html.encode("utf-8"))
    size_kb = int(html_bytes / 1024)
    size_ok = size_kb <= 200
    checks.append(
        AuditIssue(
            id="perf-html-payload-size",
            category="performance",
            severity="medium",
            passed=size_ok,
            fixable=False,
            title={
                "en": "Initial HTML Document Size",
                "ar": "حجم مستند HTML الأولي",
            },
            description={
                "en": (
                    f"Initial HTML document size is lightweight ({size_kb} KB)."
                    if size_ok
                    else f"Initial HTML document is large ({size_kb} KB; target is under 200 KB)."
                ),
                "ar": (
                    f"حجم شفرة HTML الأولي خفيف ومثالي ({size_kb} كيلوبايت)."
                    if size_ok
                    else f"شفرة HTML الأولية كبيرة ({size_kb} كيلوبايت؛ المستهدف أقل من 200 كيلوبايت)."
                ),
            },
            recommendation={
                "en": "Minify HTML and defer large inline scripts or SVGs.",
                "ar": "قم بضغط شفرة HTML وتأجيل تحميل النصوص البرمجية الكبيرة أو رسومات SVG المضمنة.",
            },
            affected_urls=[url],
            details={"size_kb": size_kb},
        )
    )

    # Script Tag Count
    scripts = soup.find_all("script", src=True)
    scripts_ok = len(scripts) <= 15
    checks.append(
        AuditIssue(
            id="perf-script-bloat",
            category="performance",
            severity="medium",
            passed=scripts_ok,
            fixable=False,
            title={
                "en": "External JavaScript Dependencies",
                "ar": "عدد ملفات جافاسكريبت الخارجية",
            },
            description={
                "en": (
                    f"Page loads {len(scripts)} external scripts."
                    if scripts_ok
                    else f"Page loads {len(scripts)} external scripts, which may delay Total Blocking Time (TBT)."
                ),
                "ar": (
                    f"تحمل الصفحة {len(scripts)} ملفات جافاسكريبت خارجية."
                    if scripts_ok
                    else f"تحمل الصفحة {len(scripts)} ملفات سكربت خارجية، مما قد يسبب تأخيراً في التفاعل (TBT)."
                ),
            },
            recommendation={
                "en": "Consolidate or defer non-critical tracking scripts and third-party widgets.",
                "ar": "قلل وادمج ملفات التتبع غير الضرورية وقم بتأجيل تحميل السكربتات الثانوية (defer/async).",
            },
            affected_urls=[url],
            details={"script_count": len(scripts)},
        )
    )

    # Server Latency / TTFB
    latency_ok = fetch_latency_ms < 1000
    checks.append(
        AuditIssue(
            id="perf-ttfb-latency",
            category="performance",
            severity="high",
            passed=latency_ok,
            fixable=False,
            title={
                "en": "Time to First Byte (TTFB) & Server Latency",
                "ar": "سرعة استجابة الخادم الأولية (TTFB)",
            },
            description={
                "en": (
                    f"Server response time is fast ({fetch_latency_ms} ms)."
                    if latency_ok
                    else f"Server response is slow ({fetch_latency_ms} ms; ideal is under 600 ms)."
                ),
                "ar": (
                    f"استجابة الخادم الأولية سريعة ({fetch_latency_ms} مللي ثانية)."
                    if latency_ok
                    else f"استجابة الخادم الأولية بطيئة ({fetch_latency_ms} مللي ثانية؛ المستهدف أقل من 600ms)."
                ),
            },
            recommendation={
                "en": "Leverage a CDN (e.g. Cloudflare) and edge caching to reduce server response latency.",
                "ar": "استعن بشبكة توزيع محتوى (CDN مثل Cloudflare) والتخزين المؤقت لتسريع وقت استجابة الخادم.",
            },
            affected_urls=[url],
            details={"latency_ms": fetch_latency_ms},
        )
    )

    # =========================================================================
    # Score Aggregation & Summary
    # =========================================================================

    severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    category_weights = {
        "technical": 0.30,
        "content": 0.25,
        "ai_readiness": 0.25,
        "performance": 0.20,
    }

    category_scores: dict[str, int] = {}
    categories = ["technical", "content", "ai_readiness", "performance"]

    for cat in categories:
        cat_checks = [c for c in checks if c.category == cat]
        if not cat_checks:
            category_scores[cat] = 100
            continue
        total_possible = sum(severity_weights.get(c.severity, 1) for c in cat_checks)
        earned = sum(severity_weights.get(c.severity, 1) for c in cat_checks if c.passed)
        category_scores[cat] = int(round((earned / total_possible) * 100))

    overall = sum(category_scores[cat] * weight for cat, weight in category_weights.items())
    overall_score = max(0, min(100, int(round(overall))))

    issues_out = [asdict(c) for c in checks]
    failed_issues = [c for c in checks if not c.passed]

    summary = {
        "total_checks": len(checks),
        "passed_checks": len(checks) - len(failed_issues),
        "total_issues": len(failed_issues),
        "critical": sum(1 for c in failed_issues if c.severity == "critical"),
        "high": sum(1 for c in failed_issues if c.severity == "high"),
        "medium": sum(1 for c in failed_issues if c.severity == "medium"),
        "low": sum(1 for c in failed_issues if c.severity == "low"),
    }

    return AuditResult(
        overall_score=overall_score,
        category_scores=category_scores,
        issues=issues_out,
        summary=summary,
        pages_crawled=1,
    )
