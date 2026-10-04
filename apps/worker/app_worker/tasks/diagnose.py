"""Celery tasks for running diagnoses and generating fixes."""

import uuid
from collections import Counter
from datetime import UTC, datetime
from urllib.parse import urlsplit

from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app_core import llm
from app_core.cost_guard import CostCeilingExceeded, TrialExpired, check_cost_guard, record_usage
from app_core.db import get_engine
from app_core.models import (
    AiCheck,
    AiPrompt,
    CrawlSnapshot,
    Diagnosis,
    Fix,
    Keyword,
    RankCheck,
    Site,
    Webhook,
)
from app_core.page_facts import extract_page_facts
from app_worker.agents.diagnosis import CompetitorPage, run_diagnosis_agent
from app_worker.celery_app import app
from app_worker.seo_engine import (
    analyze_target_and_competitors,
    fetch_page,
    generate_content_block_fix,
    generate_faq_fix,
    generate_meta_fix,
    generate_schema_fix,
)
from app_worker.seo_engine.fixes import resolve_delivery_method

logger = get_task_logger(__name__)


def _is_ours(url: str, domain: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    return host == domain or host.endswith("." + domain)


def _serp_urls(raw: dict | None) -> list[str]:
    """Organic result URLs from a stored DataForSEO response, in ranking order."""
    urls: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "organic" and isinstance(node.get("url"), str):
                urls.append(node["url"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(raw or {})
    return urls


def pick_pages(session: Session, diag: Diagnosis, site: Site) -> tuple[str, list[str], list[dict]]:
    """(our page, competitor pages to compare with, recent AI answers for prompts).

    Keywords: our ranking URL, and the pages ranking above us in the latest SERP.
    Prompts: the pages the AI engines cited instead of us in the latest runs.
    Fallback: homepages of the site's competitor domains.
    """
    domain = site.domain.removeprefix("www.")
    target_url = site.homepage_url
    competitors: list[str] = []
    answers: list[dict] = []
    if diag.target_type == "keyword":
        rc = session.scalars(
            select(RankCheck)
            .where(RankCheck.keyword_id == diag.target_id)
            .order_by(RankCheck.checked_at.desc())
            .limit(1)
        ).first()
        if rc:
            if rc.url_ranked and _is_ours(rc.url_ranked, domain):
                target_url = rc.url_ranked
            competitors = [u for u in _serp_urls(rc.raw_response) if not _is_ours(u, domain)]
    else:
        checks = session.scalars(
            select(AiCheck)
            .where(AiCheck.prompt_id == diag.target_id)
            .order_by(AiCheck.checked_at.desc())
            .limit(12)
        ).all()
        counts = Counter(u for c in checks for u in (c.cited_urls or []) if not _is_ours(u, domain))
        competitors = [u for u, _ in counts.most_common()]
        answers = [
            {"engine": c.engine, "brand_mentioned": c.brand_mentioned,
             "cited_urls": c.cited_urls or [], "raw_answer": c.raw_answer or ""}
            for c in checks
        ]  # fmt: skip
    if not competitors:
        competitors = [
            d if d.startswith("http") else f"https://{d}" for d in (site.competitor_domains or [])
        ]
    return target_url, list(dict.fromkeys(competitors))[:3], answers


@app.task(name="app_worker.tasks.diagnose.run_diagnosis", queue="agents")
def run_diagnosis(diagnosis_id_str: str) -> None:
    """Explain why competitors win for a keyword/question and propose fixes."""
    with Session(get_engine()) as session:
        diag = session.get(Diagnosis, uuid.UUID(diagnosis_id_str))
        if not diag:
            logger.warning("Diagnosis %s not found", diagnosis_id_str)
            return
        site = session.get(Site, diag.site_id)
        if not site:
            _fail(session, diag, "Site not found.")
            return
        try:
            _run(session, diag, site)
        except Exception as exc:
            logger.exception("Diagnosis %s failed", diag.id)
            session.rollback()
            _fail(session, diag, f"Diagnosis failed: {str(exc)[:300]}")


def _fail(session: Session, diag: Diagnosis, message: str) -> None:
    diag.status = "failed"
    diag.error = message
    session.commit()


def _run(session: Session, diag: Diagnosis, site: Site) -> None:
    target_text, target_lang = site.name or site.domain, site.primary_language
    if diag.target_type == "keyword":
        kw = session.get(Keyword, diag.target_id)
        if kw:
            target_text, target_lang = kw.keyword, kw.language
    else:
        pr = session.get(AiPrompt, diag.target_id)
        if pr:
            target_text, target_lang = pr.prompt_text, pr.language

    target_url, competitor_urls, ai_answers = pick_pages(session, diag, site)
    try:
        target_fetch = fetch_page(target_url, timeout=15)
    except Exception as exc:
        # Never diagnose a made-up page: report that we couldn't read it.
        _fail(session, diag, f"We couldn't open {target_url} ({type(exc).__name__}).")
        return
    competitor_fetches = []
    for url in competitor_urls:
        try:
            cf = fetch_page(url, timeout=12)
            if cf.status_code == 200:
                competitor_fetches.append(cf)
        except Exception:  # noqa: S112 - unreachable competitor: compare with the rest
            continue

    latest_crawl = session.scalars(
        select(CrawlSnapshot)
        .where(CrawlSnapshot.site_id == site.id)
        .order_by(CrawlSnapshot.fetched_at.desc())
        .limit(1)
    ).first()
    rules = analyze_target_and_competitors(
        target_fetch=target_fetch,
        target_url=target_url,
        target_keyword_or_prompt=target_text,
        target_language=target_lang,
        competitor_urls=competitor_urls,
        robots_txt_status=latest_crawl.ai_robots_allowed if latest_crawl else {},
        competitor_fetches=competitor_fetches,
    )
    rule_findings = [
        {"code": f.code, "severity": f.severity, "gap_type": f.gap_type,
         "title": f.title, "explanation": f.explanation, "details": f.details}
        for f in rules.findings
    ]  # fmt: skip
    diag.competitor_pages = [
        {"url": c.url, "domain": c.domain, "status_code": c.status_code, "title": c.title,
         "meta_description": c.meta_description, "word_count": c.word_count,
         "headings": c.headings, "schema_types": c.schema_types}
        for c in rules.competitor_pages
    ]  # fmt: skip

    agent = _try_agent(
        session, diag, site, target_text, target_lang, target_url, target_fetch,
        competitor_fetches, latest_crawl, rule_findings, ai_answers,
    )  # fmt: skip
    if agent is not None:
        diag.findings = {
            "source": "ai",
            "summary": agent.summary,
            "items": _merge_findings(rule_findings, agent.findings),
        }
        generated = [(f.type, f.title, f.description, f.payload) for f in agent.fixes]
    else:
        diag.findings = {"source": "rules", "items": rule_findings}
        generated = [
            (g.type, g.title, g.description, g.payload)
            for g in _template_fixes(site, target_text, target_lang)
        ]

    created = 0
    for fix_type, title, description, payload in generated:
        session.add(
            Fix(
                id=uuid.uuid4(), org_id=site.org_id, site_id=site.id, diagnosis_id=diag.id,
                type=fix_type, target_url=target_url, language=target_lang, title=title,
                description=description, payload=payload,
                recommended_delivery=resolve_delivery_method(site.platform, fix_type),
                status="proposed",
            )
        )  # fmt: skip
        created += 1
    diag.status = "completed"
    diag.error = None
    diag.completed_at = datetime.now(UTC)
    session.commit()
    logger.info("Diagnosis %s finished with %s proposed fixes", diag.id, created)
    _notify(session, site, diag, created)


def _try_agent(session, diag, site, target_text, target_lang, target_url, target_fetch,
               competitor_fetches, latest_crawl, rule_findings, ai_answers):  # fmt: skip
    """Run the Claude agent if configured and within budget; None means use the rules."""
    if not llm.is_configured("main"):
        return None
    try:
        check_cost_guard(session, site.org_id, is_scheduled=False)  # user-clicked: essential
    except (CostCeilingExceeded, TrialExpired):
        return None
    try:
        result = run_diagnosis_agent(
            target_type=diag.target_type,
            target_text=target_text,
            language=target_lang,
            platform=site.platform,
            site_name=site.name,
            target_url=target_fetch.final_url or target_url,
            target=extract_page_facts(target_fetch.raw_html),
            js_only_content=latest_crawl.js_only_content_detected if latest_crawl else None,
            competitors=[
                CompetitorPage(cf.final_url, extract_page_facts(cf.raw_html))
                for cf in competitor_fetches
            ],
            rule_findings=[
                {"severity": f["severity"], "title": f["title"].get("en", "")}
                for f in rule_findings
            ],
            ai_answers=ai_answers,
        )
    except Exception as exc:  # API error / refusal: rules-based result is still useful
        logger.warning("Diagnosis agent failed for %s: %s", diag.id, exc)
        return None
    record_usage(session, org_id=site.org_id, category="llm", provider="anthropic",
                 cost_usd=result.cost_usd)  # fmt: skip
    return result


def _merge_findings(rules: list[dict], ai: list[dict]) -> list[dict]:
    """Deterministic findings (e.g. blocked AI crawlers) are facts: keep them, then the AI's."""
    seen = {f["gap_type"] for f in rules if f["code"] in ("robots_ai_blocked", "js_only_content")}
    return rules + [f for f in ai if f["gap_type"] not in seen]


def _template_fixes(site: Site, target_text: str, lang: str):
    return [
        generate_schema_fix(site_name=site.name, domain=site.domain, target_url=site.homepage_url,
                            platform=site.platform, language=lang, industry=site.industry,
                            city=site.default_city),
        generate_meta_fix(site_name=site.name, domain=site.domain, target_query=target_text,
                          platform=site.platform, language=lang, city=site.default_city),
        generate_faq_fix(site_name=site.name, target_query=target_text, platform=site.platform,
                         language=lang),
        generate_content_block_fix(site_name=site.name, target_query=target_text,
                                   platform=site.platform, language=lang),
    ]  # fmt: skip


def _notify(session: Session, site: Site, diag: Diagnosis, fix_count: int) -> None:
    webhooks = session.scalars(
        select(Webhook).where(Webhook.org_id == site.org_id, Webhook.status == "active")
    ).all()
    for wh in webhooks:
        if "fix.proposed" in (wh.events or []):
            app.send_task(
                "app_worker.tasks.webhooks.dispatch_webhook",
                args=[str(wh.id), "fix.proposed",
                      {"site_id": str(site.id), "diagnosis_id": str(diag.id),
                       "fix_count": fix_count}],
                queue="default",
            )  # fmt: skip
