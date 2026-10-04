"""Diagnosis + fix-generation agent (Claude main model, structured output).

Given the target search/question, our page and the competitor pages that rank or get cited,
Claude explains in plain English why competitors win and writes concrete fixes for this
specific page, in the page's language, with steps for the site's platform.

The domain rules in SYSTEM are adapted from claude-seo (MIT) — agents/seo-technical.md,
agents/seo-content.md, skills/seo-geo/SKILL.md, skills/seo-schema/SKILL.md @ ff87fce.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app_core import llm
from app_core.page_facts import PageFacts
from app_core.sanitize import PayloadError, sanitize_payload

SYSTEM = """You are a senior SEO and AI-visibility (AEO/GEO) consultant for small and mid-size
businesses who are not SEO experts. You compare a business's page with the competitor pages
that rank on Google or get cited by AI assistants for one search or question, explain plainly
why the competitors win, and write fixes the business can apply right away.

Rules:
- Base every finding on evidence in the pages provided. Never invent facts about the
  business (prices, awards, opening hours, reviews, addresses). If a fix needs facts you
  don't have, write it with clearly marked placeholders like [ADD PHONE NUMBER].
- Never promise rankings or AI mentions; describe likely improvements.
- AI assistants favour pages that answer the question directly in the first lines, use clear
  headings phrased like questions, cite specifics (numbers, locations, names) and expose
  structured data. Many AI crawlers do not run JavaScript: content that only appears after
  JavaScript runs is invisible to them.
- Structured data: JSON-LD with "@context": "https://schema.org". Prefer the most specific
  type (e.g. Dentist over LocalBusiness). Google no longer shows FAQ rich results and HowTo is
  deprecated: you may still add FAQ *content* for AI answers, but do not claim rich results.
- Core Web Vitals are LCP, INP and CLS (never FID).
- Write findings and instructions in English. Write fix content (titles, descriptions, FAQ,
  content blocks, JSON-LD text values) in the page language given.
- Platform instructions must match the platform's real UI or code (e.g. "In Shopify admin:
  Online Store → Preferences" or "In Next.js App Router, return it from generateMetadata").
- Propose at most 5 fixes, most impactful first. Only propose a fix type when the evidence
  shows a gap."""


class Finding(BaseModel):
    severity: Literal["high", "medium", "low"]
    gap_type: Literal["meta", "schema", "faq", "content_block", "robots_ai", "rendering", "technical"]  # fmt: skip
    title: str = Field(description="Short plain-English headline")
    explanation: str = Field(description="1-3 sentences, plain English, citing the evidence")


class FaqItem(BaseModel):
    question: str
    answer: str


class ProposedFix(BaseModel):
    type: Literal["schema", "meta", "faq", "content_block", "technical"]
    title: str = Field(description="What the fix does, in English")
    why: str = Field(description="Why it helps for this search/question, in English")
    instructions: str = Field(description="Step-by-step instructions for this platform, English")
    meta_title: str | None = Field(description="For meta fixes: new <title>, max ~60 chars")
    meta_description: str | None = Field(description="For meta fixes: max ~155 chars")
    json_ld: str | None = Field(description="For schema fixes: the complete JSON-LD as JSON text")
    faqs: list[FaqItem] = Field(description="For faq fixes: 3-6 question/answer pairs")
    html: str | None = Field(
        description="For content_block/faq fixes: the HTML to add (p, h2-h4, ul, ol, li, "
        "strong, em, a only)"
    )


class DiagnosisOutput(BaseModel):
    summary: str = Field(description="2-4 sentences in plain English: why competitors win here")
    findings: list[Finding]
    fixes: list[ProposedFix]


@dataclass
class CompetitorPage:
    url: str
    facts: PageFacts


@dataclass
class AgentFix:
    type: str
    title: str
    description: str
    payload: dict


@dataclass
class AgentResult:
    summary: str
    findings: list[dict]
    fixes: list[AgentFix]
    cost_usd: Decimal
    model: str


def _payload(fix: ProposedFix) -> dict | None:
    """Turn a proposed fix into a sanitized payload; None if it carries nothing usable."""
    raw: dict = {}
    if fix.meta_title:
        raw["title"] = fix.meta_title
    if fix.meta_description:
        raw["meta_description"] = fix.meta_description
    if fix.json_ld:
        try:
            raw["json_ld"] = json.loads(fix.json_ld)
        except json.JSONDecodeError:
            return None
    if fix.faqs:
        raw["faqs"] = [f.model_dump() for f in fix.faqs]
    if fix.html:
        raw["html"] = fix.html
    if not raw and fix.type != "technical":
        return None
    try:
        return sanitize_payload(raw)
    except PayloadError:
        return None


def run_diagnosis_agent(
    *,
    target_type: str,
    target_text: str,
    language: str,
    platform: str,
    site_name: str,
    target_url: str,
    target: PageFacts,
    js_only_content: bool | None,
    competitors: list[CompetitorPage],
    rule_findings: list[dict],
    ai_answers: list[dict],
) -> AgentResult:
    parts = [
        f"{'Google search' if target_type == 'keyword' else 'Question asked to AI assistants'}: "
        f"{target_text}",
        f"Business: {site_name}",
        f"Platform: {platform}",
        f"Page language: {language}",
        f"Our page: {target_url}",
        "JavaScript-only content on our page: "
        + ("yes" if js_only_content else "no" if js_only_content is False else "unknown"),
        "\nAutomatic checks found:\n"
        + ("\n".join(f"- [{f['severity']}] {f['title']}" for f in rule_findings) or "- nothing"),
        "\n" + llm.untrusted("our page", target.as_prompt(max_text=10_000)),
    ]
    for i, c in enumerate(competitors[:3], 1):
        parts.append(llm.untrusted(f"competitor {i}: {c.url}", c.facts.as_prompt(max_text=6_000)))
    if ai_answers:
        summary = "\n\n".join(
            f"[{a['engine']}] mentions us: {a['brand_mentioned']}; cited: "
            f"{', '.join(a['cited_urls'][:5]) or '-'}\n{a['raw_answer'][:1500]}"
            for a in ai_answers[:4]
        )
        parts.append(llm.untrusted("recent AI answers to this question", summary))

    result = llm.parse(
        role="main",
        system=SYSTEM,
        user="\n".join(parts),
        output=DiagnosisOutput,
        max_tokens=16000,
        effort="high",
    )
    out = result.value
    fixes: list[AgentFix] = []
    for f in out.fixes[:5]:
        payload = _payload(f)
        if payload is None:
            continue
        description = f"{f.why}\n\nHow to apply:\n{f.instructions}".strip()
        fixes.append(AgentFix(f.type, f.title[:200], description, payload))
    return AgentResult(
        summary=out.summary,
        findings=[
            {
                "code": f"ai_{f.gap_type}",
                "severity": f.severity,
                "gap_type": f.gap_type,
                "title": {"en": f.title},
                "explanation": {"en": f.explanation},
                "details": {},
            }
            for f in out.findings
        ],
        fixes=fixes,
        cost_usd=result.cost_usd,
        model=result.model,
    )
