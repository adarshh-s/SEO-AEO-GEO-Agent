"""Language-aware and platform-aware SEO/AEO fix generators."""

import html
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GeneratedFix:
    type: str  # schema | meta | faq | content_block | technical
    title: str
    description: str
    language: str
    payload: dict[str, Any]
    recommended_delivery: str


def sanitize_html(html_str: str) -> str:
    """Basic HTML sanitizer removing script tags, javascript: links, and event handlers."""
    # Remove script tags
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
    # Remove on* event attributes (onclick, onload, etc.)
    cleaned = re.sub(r'\s+on[a-zA-Z]+\s*=\s*(["\'][^"\']*["\']|[^\s>]+)', "", cleaned)
    # Remove javascript: in href or src
    cleaned = re.sub(
        r'href\s*=\s*["\']javascript:[^"\']*["\']', 'href="#"', cleaned, flags=re.IGNORECASE
    )
    return cleaned.strip()


def resolve_delivery_method(platform: str, fix_type: str) -> str:
    """Determine the recommended delivery mechanism based on site platform (CLAUDE.md §6)."""
    p = platform.lower()
    if "wordpress" in p:
        return "wordpress"
    if "shopify" in p:
        return "shopify"
    if p in ("nextjs", "nuxt", "astro"):
        return "sdk"
    if "cloudflare" in p:
        return "edge_worker"
    return "snippet"


def generate_schema_fix(
    *,
    site_name: str,
    domain: str,
    target_url: str,
    platform: str,
    language: str = "en",
    industry: str | None = None,
    city: str | None = None,
) -> GeneratedFix:
    """Generate Schema.org JSON-LD structured data."""
    schema_type = "LocalBusiness" if city else "Organization"
    schema_data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": site_name or domain,
        "url": target_url,
        "description": (
            f"{site_name} specializes in {industry or 'professional services'}."
            if language == "en"
            else f"يقدم {site_name} خدمات متخصصة في مجال {industry or 'الأعمال والخدمات المهنية'}."
        ),
    }
    if city:
        schema_data["address"] = {
            "@type": "PostalAddress",
            "addressLocality": city,
        }

    title = (
        "Add Organization & LocalBusiness JSON-LD Schema"
        if language == "en"
        else "إضافة بيانات Schema.org المنظمة للمنشأة"
    )
    desc = (
        "Adds structured data (JSON-LD) that describes your business, so search engines and AI assistants can identify it accurately."
        if language == "en"
        else "يقوم بإدراج ترميز JSON-LD في ترويسة الصفحة لتمكين لوحة المعرفة في جوجل وتسهيل فهرسة المنشأة لدى نماذج الذكاء الاصطناعي."
    )

    return GeneratedFix(
        type="schema",
        title=title,
        description=desc,
        language=language,
        payload={"json_ld": schema_data},
        recommended_delivery=resolve_delivery_method(platform, "schema"),
    )


def generate_meta_fix(
    *,
    site_name: str,
    domain: str,
    target_query: str,
    platform: str,
    language: str = "en",
    city: str | None = None,
) -> GeneratedFix:
    """Generate optimized title and meta description."""
    q_title = target_query.title() if language == "en" else target_query
    brand = site_name or domain.split(".")[0].title()

    if language == "ar":
        location = f" في {city}" if city else ""
        meta_title = f"{q_title}{location} | {brand}"
        meta_description = f"اكتشف أفضل حلول {q_title}{location} مع {brand}. جودة عالية وخدمات موثوقة تلبي كافة احتياجاتك بكل احترافية."
    else:
        location = f" in {city}" if city else ""
        meta_title = f"{q_title}{location} | {brand}"
        meta_description = f"Looking for {target_query}{location}? {brand} provides top-rated, reliable solutions tailored to your business needs."

    # Truncate if too long
    if len(meta_title) > 60:
        meta_title = meta_title[:57] + "..."
    if len(meta_description) > 155:
        meta_description = meta_description[:152] + "..."

    title = (
        "Optimize Title and Meta Description"
        if language == "en"
        else "تحسين عنوان الصفحة والوصف التعريفي"
    )
    desc = (
        "Updates title tag and meta description to boost click-through rates from search results and match AI user queries."
        if language == "en"
        else "تحديث وسم العنوان والوصف التعريفي لرفع نسبة النقر ومطابقة استفسارات محركات البحث والذكاء الاصطناعي."
    )

    return GeneratedFix(
        type="meta",
        title=title,
        description=desc,
        language=language,
        payload={"title": meta_title, "meta_description": meta_description},
        recommended_delivery=resolve_delivery_method(platform, "meta"),
    )


def generate_faq_fix(
    *,
    site_name: str,
    target_query: str,
    platform: str,
    language: str = "en",
) -> GeneratedFix:
    """Generate a Q&A content block (no FAQPage schema by default: decision D2)."""
    brand = site_name

    if language == "ar":
        faqs = [
            {
                "question": f"ما الذي يميز {brand} في تقديم خدمات {target_query}؟",
                "answer": f"يتميز {brand} بتقديم حلول متطورة وموثوقة تعتمد على أفضل الممارسات المهنية لضمان تحقيق أعلى معايير الجودة ورضا العملاء.",
            },
            {
                "question": f"كيف يمكنني البدء في الاستفادة من {target_query}؟",
                "answer": "يمكنك التواصل معنا مباشرة عبر الموقع أو حجز استشارة للتعرف على الخطوات والخيارات المناسبة لاحتياجاتك الخاصة.",
            },
            {
                "question": "هل تتوفر خدمات دعم ومتابعة مستمرة؟",
                "answer": "نعم، نقدم دعماً متواصلاً لضمان سير كافة العمليات بأعلى كفاءة وسرعة استجابة لاحتياجاتكم.",
            },
        ]
        title = "إضافة قسم أسئلة وأجوبة"
        desc = "تضمين أسئلة وأجوبة مباشرة للإجابة على استفسارات العملاء والاستشهاد بها في ChatGPT و Google AI Overviews."
    else:
        faqs = [
            {
                "question": f"What makes {brand} the best choice for {target_query}?",
                "answer": f"{brand} combines deep industry expertise with verified solutions to deliver measurable results and exceptional support.",
            },
            {
                "question": f"How do I get started with {target_query}?",
                "answer": "You can get started immediately by exploring our platform or contacting our team for a personalized walkthrough.",
            },
            {
                "question": "Is dedicated support included?",
                "answer": "Yes, we provide ongoing assistance and comprehensive documentation to ensure seamless implementation.",
            },
        ]
        title = "Add a questions & answers section"
        desc = "Adds short, direct answers to common customer questions. AI assistants often quote pages that answer questions plainly. (Google no longer shows FAQ rich results, so no FAQPage schema is added.)"

    # HTML markup
    items_html = "".join(f"""
        <div class="ql-faq-item" style="margin-bottom: 1rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.75rem;">
          <h3 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">{html.escape(item["question"])}</h3>
          <p style="color: #4b5563; line-height: 1.5;">{html.escape(item["answer"])}</p>
        </div>""" for item in faqs)
    faq_html = sanitize_html(
        f'<div class="ql-faq-container" style="margin-top: 2rem;">{items_html}</div>'
    )

    return GeneratedFix(
        type="faq",
        title=title,
        description=desc,
        language=language,
        payload={"faqs": faqs, "html": faq_html},
        recommended_delivery=resolve_delivery_method(platform, "faq"),
    )


def generate_content_block_fix(
    *,
    site_name: str,
    target_query: str,
    platform: str,
    language: str = "en",
) -> GeneratedFix:
    """Generate semantic HTML content block addressing intent gaps."""
    if language == "ar":
        heading = f"دليلك الشامل حول {target_query}"
        body_p1 = f"في عالم الأعمال سريع التطور، يعد اختيار الحل المناسب لـ {target_query} عاملاً حاسماً في تحقيق النجاح. يقدم {site_name} منظومة متكاملة تضمن أعلى مستويات الكفاءة والموثوقية."
        body_p2 = "أبرز المزايا التي نلتزم بها:"
        bullet_items = [
            "حلول متوافقة مع أحدث المعايير التقنية والمتطلبات المحلية.",
            "سهولة الربط والتكامل مع منصتك الحالية دون تعقيدات.",
            "متابعة دورية وتقارير دقيقة لضمان تحقيق النتائج المرجوة.",
        ]
        title = "إضافة قسم محتوى تعريفي شامل"
        desc = "إضافة قسم نصي منسق يغطي الكلمات المفتاحية الأساسية ويزيد من عمق المحتوى بما يلائم متطلبات محركات البحث."
    else:
        heading = f"Everything You Need to Know About {target_query.title()}"
        body_p1 = f"Finding reliable solutions for {target_query} is critical for long-term growth and digital prominence. {site_name} provides robust, scalable capabilities engineered for modern digital standards."
        body_p2 = "Key Advantages:"
        bullet_items = [
            "Seamless compatibility with enterprise and modern web stacks.",
            "Engineered for both human searchers and conversational AI discovery.",
            "Proven performance with transparent tracking and data-driven insights.",
        ]
        title = "Add Semantic Content Block"
        desc = "Injects an informational section addressing key search intent topics to overcome content depth gaps vs competitors."

    bullets_html = "".join(f"<li>{html.escape(b)}</li>" for b in bullet_items)
    block_html = sanitize_html(
        f"""<section class="ql-content-block" style="margin-top: 2rem; padding: 1.5rem; background: #f9fafb; border-radius: 8px;">
          <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem;">{html.escape(heading)}</h2>
          <p style="margin-bottom: 0.75rem; color: #374151; line-height: 1.6;">{html.escape(body_p1)}</p>
          <p style="font-weight: 600; margin-bottom: 0.5rem; color: #1f2937;">{html.escape(body_p2)}</p>
          <ul style="padding-left: 1.25rem; color: #4b5563; line-height: 1.6;">
            {bullets_html}
          </ul>
        </section>"""
    )

    return GeneratedFix(
        type="content_block",
        title=title,
        description=desc,
        language=language,
        payload={"html": block_html, "container_selector": "body"},
        recommended_delivery=resolve_delivery_method(platform, "content_block"),
    )
