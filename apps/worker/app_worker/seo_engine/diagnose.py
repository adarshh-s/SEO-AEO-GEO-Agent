"""On-page SEO/AEO diagnosis and competitor gap analysis."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from app_worker.seo_engine.fetch import FetchResult, fetch_page


@dataclass
class CompetitorPageAnalysis:
    url: str
    domain: str
    status_code: int
    title: str | None
    meta_description: str | None
    word_count: int
    headings: list[str]
    schema_types: list[str]


@dataclass
class DiagnosisFinding:
    code: str
    severity: str  # high | medium | low
    gap_type: str  # meta | schema | faq | content_block | robots_ai | rendering
    title: dict[str, str]  # {"en": "...", "ar": "..."}
    explanation: dict[str, str]  # {"en": "...", "ar": "..."}
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagnosisResult:
    findings: list[DiagnosisFinding]
    competitor_pages: list[CompetitorPageAnalysis]


def _extract_page_signals(html: str) -> tuple[int, list[str], list[str]]:
    """Extract word count, h1/h2 headings, and schema.org types from HTML."""
    if not html:
        return 0, [], []

    soup = BeautifulSoup(html, "html.parser")

    # Headings
    headings = []
    for h in soup.find_all(["h1", "h2"]):
        txt = h.get_text().strip()
        if txt and len(txt) < 120:
            headings.append(txt)

    # Schema types
    schema_types = []
    for s_tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(s_tag.string or "{}")
            if isinstance(data, dict):
                t = data.get("@type")
                if t:
                    schema_types.append(t if isinstance(t, str) else str(t))
                graph = data.get("@graph", [])
                if isinstance(graph, list):
                    for item in graph:
                        if isinstance(item, dict) and item.get("@type"):
                            schema_types.append(str(item["@type"]))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type"):
                        schema_types.append(str(item["@type"]))
        except Exception:  # noqa: S112
            continue

    # Word count
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text()).strip()
    words = len(text.split()) if text else 0

    return words, headings[:10], sorted(list(set(schema_types)))


def analyze_target_and_competitors(
    *,
    target_fetch: FetchResult,
    target_url: str,
    target_keyword_or_prompt: str,
    target_language: str,
    competitor_urls: list[str],
    robots_txt_status: dict[str, bool] | None = None,
    competitor_fetches: list[FetchResult] | None = None,
) -> DiagnosisResult:
    """Compare the target page with competitor pages to identify gaps."""
    # Analyze target page
    target_words, target_headings, target_schemas = _extract_page_signals(target_fetch.raw_html)
    target_title = target_fetch.meta_title or ""
    target_desc = target_fetch.meta_description or ""

    # Fetch and analyze competitor pages safely
    competitor_analyses: list[CompetitorPageAnalysis] = []
    fetched = list(competitor_fetches or [])
    if competitor_fetches is None:
        for c_url in competitor_urls[:3]:  # Top 3 competitors
            try:
                fetched.append(fetch_page(c_url, timeout=10))
            except Exception:  # noqa: S112
                continue
    for cf in fetched[:3]:
        try:
            if cf.status_code == 200:
                cw, ch, cs = _extract_page_signals(cf.raw_html)
                from urllib.parse import urlparse

                domain = urlparse(cf.final_url).netloc
                competitor_analyses.append(
                    CompetitorPageAnalysis(
                        url=cf.final_url,
                        domain=domain,
                        status_code=cf.status_code,
                        title=cf.meta_title,
                        meta_description=cf.meta_description,
                        word_count=cw,
                        headings=ch,
                        schema_types=cs,
                    )
                )
        except Exception:  # noqa: S112
            continue

    findings: list[DiagnosisFinding] = []

    # 1. Robots.txt AI bot check
    robots = robots_txt_status or {}
    blocked_ai_bots = [b for b, allowed in robots.items() if not allowed]
    if blocked_ai_bots:
        findings.append(
            DiagnosisFinding(
                code="robots_ai_blocked",
                severity="high",
                gap_type="robots_ai",
                title={
                    "en": f"AI search crawlers blocked in robots.txt ({len(blocked_ai_bots)} crawlers)",
                    "ar": f"محركات بحث الذكاء الاصطناعي محظورة في robots.txt ({len(blocked_ai_bots)} برامج زحف)",
                },
                explanation={
                    "en": f"Your robots.txt file blocks {', '.join(blocked_ai_bots)}. This prevents answer engines like ChatGPT and Claude from reading your pages or citing your site in answers.",
                    "ar": f"ملف robots.txt الخاص بك يحظر {', '.join(blocked_ai_bots)}. هذا يمنع محركات الذكاء الاصطناعي مثل ChatGPT و Claude من قراءة موقعك أو الاستشهاد به في الإجابات.",
                },
                details={"blocked_bots": blocked_ai_bots},
            )
        )

    # 2. Schema Markup Gap
    has_structured_data = len(target_schemas) > 0
    comp_has_schema = any(len(c.schema_types) > 0 for c in competitor_analyses)
    if not has_structured_data or "LocalBusiness" not in target_schemas:
        findings.append(
            DiagnosisFinding(
                code="missing_schema",
                severity="high" if comp_has_schema else "medium",
                gap_type="schema",
                title={
                    "en": "Missing Structured Data (Schema.org JSON-LD)",
                    "ar": "غياب البيانات المنظمة (Schema.org JSON-LD)",
                },
                explanation={
                    "en": "Search and AI crawlers rely on Schema.org JSON-LD markup to understand your business, entity details, and offerings. Adding structured data enables Google rich results and AI citations.",
                    "ar": "تعتمد محركات البحث ونماذج الذكاء الاصطناعي على ترميز Schema.org لفهم الكيانات والخدمات المقدمة. إضافة البيانات المنظمة تؤهل موقعك لنتائج جوجل المنسقة والاستشهادات الذكية.",
                },
                details={"current_schemas": target_schemas},
            )
        )

    # 3. Meta Title Gap
    query_lower = target_keyword_or_prompt.lower()
    title_has_query = any(w in target_title.lower() for w in query_lower.split() if len(w) > 3)
    if not target_title or len(target_title) < 25 or len(target_title) > 65 or not title_has_query:
        findings.append(
            DiagnosisFinding(
                code="suboptimal_title",
                severity="high",
                gap_type="meta",
                title={
                    "en": "Page Title Needs Optimization",
                    "ar": "عنوان الصفحة بحاجة إلى تحسين",
                },
                explanation={
                    "en": f"Your current title is '{target_title or '(missing)'}' ({len(target_title)} chars). Best practice is 50-60 characters including primary search terms.",
                    "ar": f"العنوان الحالي هو '{target_title or '(غير محدد)'}' ({len(target_title)} حرفاً). الطول المثالي بين 50 و 60 حرفاً شاملاً الكلمات المفتاحية الأساسية.",
                },
                details={"current_title": target_title, "length": len(target_title)},
            )
        )

    # 4. Meta Description Gap
    if not target_desc or len(target_desc) < 70 or len(target_desc) > 165:
        findings.append(
            DiagnosisFinding(
                code="suboptimal_meta_description",
                severity="medium",
                gap_type="meta",
                title={
                    "en": "Meta Description Missing or Ineffective",
                    "ar": "الوصف التعريفي مفقود أو غير فعال",
                },
                explanation={
                    "en": f"Your current description has {len(target_desc)} characters. A compelling meta description between 130 and 155 characters improves click-through rates and informs AI summaries.",
                    "ar": f"الوصف التعريفي الحالي يحتوي على {len(target_desc)} حرفاً. الوصف الجذاب بين 130 و 155 حرفاً يحسن نسبة النقر ويوفر ملخصاً واضحاً لمحركات الذكاء الاصطناعي.",
                },
                details={"current_description": target_desc, "length": len(target_desc)},
            )
        )

    # 5. Content Depth / Word Count Gap
    avg_comp_words = (
        int(sum(c.word_count for c in competitor_analyses) / len(competitor_analyses))
        if competitor_analyses
        else 600
    )
    if target_words < avg_comp_words * 0.7:
        findings.append(
            DiagnosisFinding(
                code="content_depth_gap",
                severity="medium",
                gap_type="content_block",
                title={
                    "en": "Content Depth Deficit vs Top Competitors",
                    "ar": "فجوة في عمق المحتوى مقارنة بالمنافسين",
                },
                explanation={
                    "en": f"Your page has ~{target_words} words, while top competitors average ~{avg_comp_words} words. Adding helpful content sections and FAQ blocks provides necessary entity breadth.",
                    "ar": f"تحتوي صفحتك على حوالي {target_words} كلمة، بينما يبلغ متوسط المنافسين {avg_comp_words} كلمة. إضافة أقسام محتوى وأسئلة شائعة يثري الصفحة بمعلومات شاملة.",
                },
                details={"target_words": target_words, "competitor_avg_words": avg_comp_words},
            )
        )

    # 6. FAQ Block Opportunity
    findings.append(
        DiagnosisFinding(
            code="missing_faq_block",
            severity="medium",
            gap_type="faq",
            title={
                "en": "Missing FAQ Section for Direct Search & AI Answers",
                "ar": "غياب قسم الأسئلة الشائعة لإجابات البحث والذكاء الاصطناعي المباشرة",
            },
            explanation={
                "en": "Q&A formats directly match conversational queries asked in ChatGPT, Gemini, and Google SGE. Structured FAQ accordions increase inclusion in AI citations.",
                "ar": "صيغة السؤال والجواب تطابق بشكل مباشر استفسارات المستخدمين في ChatGPT و Gemini وجوجل. إضافة قسم أسئلة شائعة منظم يرفع فرص الاستشهاد بموقعك.",
            },
            details={},
        )
    )

    return DiagnosisResult(findings=findings, competitor_pages=competitor_analyses)
