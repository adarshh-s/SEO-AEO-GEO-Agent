"""Celery tasks for running diagnoses and generating fixes."""

import uuid
from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app_core.db import get_engine
from app_core.models import (
    AiPrompt,
    CrawlSnapshot,
    Diagnosis,
    Fix,
    Keyword,
    Site,
    Webhook,
)
from app_worker.celery_app import app
from app_worker.seo_engine import (
    FetchResult,
    analyze_target_and_competitors,
    fetch_page,
    generate_content_block_fix,
    generate_faq_fix,
    generate_meta_fix,
    generate_schema_fix,
)

logger = get_task_logger(__name__)


@app.task(name="app_worker.tasks.diagnose.run_diagnosis", queue="agents")
def run_diagnosis(diagnosis_id_str: str) -> None:
    """Analyze keyword or prompt gaps and generate proposed fixes."""
    diagnosis_id = uuid.UUID(diagnosis_id_str)
    engine = get_engine()

    with Session(engine) as session:
        diag = session.get(Diagnosis, diagnosis_id)
        if not diag:
            logger.warning(f"Diagnosis {diagnosis_id} not found")
            return

        site = session.get(Site, diag.site_id)
        if not site:
            diag.status = "failed"
            diag.error = "Site not found"
            session.commit()
            return

        target_text = ""
        target_lang = site.primary_language
        if diag.target_type == "keyword":
            kw = session.get(Keyword, diag.target_id)
            if kw:
                target_text = kw.keyword
                target_lang = kw.language
        elif diag.target_type == "prompt":
            p = session.get(AiPrompt, diag.target_id)
            if p:
                target_text = p.prompt_text
                target_lang = p.language

        if not target_text:
            target_text = site.name or site.domain

        # Determine target URL to inspect (site homepage)
        target_url = site.homepage_url

        # Check latest crawl snapshot for robots_ai status
        latest_crawl = session.scalars(
            select(CrawlSnapshot)
            .where(CrawlSnapshot.site_id == site.id)
            .order_by(CrawlSnapshot.fetched_at.desc())
            .limit(1)
        ).first()

        robots_status = latest_crawl.ai_robots_allowed if latest_crawl else {}

        try:
            # Fetch target page safely
            try:
                target_fetch = fetch_page(target_url, timeout=12)
            except Exception as e:
                logger.warning(f"Could not fetch {target_url}: {e}, using placeholder fetch")
                target_fetch = FetchResult(
                    url=target_url,
                    final_url=target_url,
                    status_code=200,
                    headers={},
                    raw_html=f"<html><head><title>{site.name}</title></head><body><h1>{site.name}</h1></body></html>",
                    raw_text=site.name,
                    raw_html_hash="placeholder",
                    meta_title=site.name,
                    meta_description=None,
                )

            # Build competitor URLs
            comp_urls = [
                f"https://{d}" if not d.startswith("http") else d
                for d in (site.competitor_domains or [])
            ]

            # Run analysis
            result = analyze_target_and_competitors(
                target_fetch=target_fetch,
                target_url=target_url,
                target_keyword_or_prompt=target_text,
                target_language=target_lang,
                competitor_urls=comp_urls,
                robots_txt_status=robots_status,
            )

            diag.findings = {
                "items": [
                    {
                        "code": f.code,
                        "severity": f.severity,
                        "gap_type": f.gap_type,
                        "title": f.title,
                        "explanation": f.explanation,
                        "details": f.details,
                    }
                    for f in result.findings
                ]
            }
            diag.competitor_pages = [
                {
                    "url": c.url,
                    "domain": c.domain,
                    "status_code": c.status_code,
                    "title": c.title,
                    "meta_description": c.meta_description,
                    "word_count": c.word_count,
                    "headings": c.headings,
                    "schema_types": c.schema_types,
                }
                for c in result.competitor_pages
            ]
            diag.status = "completed"
            diag.completed_at = datetime.now(UTC)

            # Generate candidate fixes based on identified gaps
            fixes_to_create = []

            # 1. Schema fix
            fixes_to_create.append(
                generate_schema_fix(
                    site_name=site.name,
                    domain=site.domain,
                    target_url=target_url,
                    platform=site.platform,
                    language=target_lang,
                    industry=site.industry,
                    city=site.default_city,
                )
            )

            # 2. Meta fix
            fixes_to_create.append(
                generate_meta_fix(
                    site_name=site.name,
                    domain=site.domain,
                    target_query=target_text,
                    platform=site.platform,
                    language=target_lang,
                    city=site.default_city,
                )
            )

            # 3. FAQ fix
            fixes_to_create.append(
                generate_faq_fix(
                    site_name=site.name,
                    target_query=target_text,
                    platform=site.platform,
                    language=target_lang,
                )
            )

            # 4. Content block fix
            fixes_to_create.append(
                generate_content_block_fix(
                    site_name=site.name,
                    target_query=target_text,
                    platform=site.platform,
                    language=target_lang,
                )
            )

            created_fix_ids = []
            for gf in fixes_to_create:
                f_obj = Fix(
                    id=uuid.uuid4(),
                    org_id=site.org_id,
                    site_id=site.id,
                    diagnosis_id=diag.id,
                    type=gf.type,
                    target_url=target_url,
                    language=gf.language,
                    title=gf.title,
                    description=gf.description,
                    payload=gf.payload,
                    recommended_delivery=gf.recommended_delivery,
                    status="proposed",
                )
                session.add(f_obj)
                created_fix_ids.append(str(f_obj.id))

            session.commit()
            logger.info(f"Diagnosis {diag.id} finished with {len(created_fix_ids)} proposed fixes")

            # Dispatch webhooks for proposed fixes
            webhooks = session.scalars(
                select(Webhook).where(Webhook.org_id == site.org_id, Webhook.status == "active")
            ).all()

            for wh in webhooks:
                if "fix.proposed" in wh.events:
                    app.send_task(
                        "app_worker.tasks.webhooks.dispatch_webhook",
                        args=[
                            str(wh.id),
                            "fix.proposed",
                            {
                                "site_id": str(site.id),
                                "diagnosis_id": str(diag.id),
                                "fix_count": len(created_fix_ids),
                            },
                        ],
                        queue="default",
                    )

        except Exception as e:
            logger.exception(f"Diagnosis {diag.id} failed: {e}")
            diag.status = "failed"
            diag.error = str(e)
            session.commit()
