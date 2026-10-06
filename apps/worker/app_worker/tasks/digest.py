"""Weekly email digest tasks (default queue)."""

import uuid

import structlog
from sqlalchemy import func, select

from app_core.db import system_session
from app_core.email import Email, get_email_provider
from app_core.models import (
    AiCheck,
    Audit,
    Fix,
    Keyword,
    Membership,
    Site,
    User,
)
from app_core.reports.digest import generate_weekly_digest
from app_worker.celery_app import app

logger = structlog.get_logger(__name__)


@app.task(name="app_worker.tasks.digest.send_site_weekly_digest")
def send_site_weekly_digest(
    site_id_str: str,
    recipient_email: str | None = None,
    language: str = "en",
) -> dict:
    """Send weekly SEO & AEO digest for a specific site."""
    site_id = uuid.UUID(site_id_str)
    with system_session() as db:
        site = db.get(Site, site_id)
        if not site:
            return {"error": "Site not found"}

        # Gather site metrics
        latest_audit = db.scalar(
            select(Audit)
            .where(Audit.site_id == site.id, Audit.status == "completed")
            .order_by(Audit.created_at.desc())
        )
        health_score = latest_audit.score if latest_audit else 80

        keywords_count = (
            db.scalar(select(func.count()).select_from(Keyword).where(Keyword.site_id == site.id))
            or 0
        )

        total_ai_checks = (
            db.scalar(select(func.count()).select_from(AiCheck).where(AiCheck.site_id == site.id))
            or 0
        )
        cited_ai_checks = (
            db.scalar(
                select(func.count())
                .select_from(AiCheck)
                .where(AiCheck.site_id == site.id, AiCheck.brand_mentioned.is_(True))
            )
            or 0
        )
        ai_pct = (
            int(round((cited_ai_checks / total_ai_checks) * 100)) if total_ai_checks > 0 else 50
        )

        fixes_count = (
            db.scalar(
                select(func.count())
                .select_from(Fix)
                .where(Fix.site_id == site.id, Fix.status == "deployed")
            )
            or 0
        )

        subject, text_body, html_body = generate_weekly_digest(
            site_name=site.name,
            domain=site.domain,
            health_score=health_score,
            keywords_count=keywords_count,
            ai_visibility_pct=ai_pct,
            fixes_count=fixes_count,
            language=language,
        )

        email_provider = get_email_provider()
        recipients = [recipient_email] if recipient_email else []

        if not recipients:
            # Query org owners/admins
            members = db.scalars(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .where(
                    Membership.org_id == site.org_id,
                    Membership.role.in_(["owner", "admin", "member"]),
                )
            ).all()
            recipients = [m.email for m in members]

        sent_count = 0
        for email_addr in recipients:
            email_provider.send(
                Email(to=email_addr, subject=subject, text=text_body, html=html_body)
            )
            sent_count += 1

        logger.info(
            "weekly_digest_sent",
            site_id=site_id_str,
            recipients_count=sent_count,
            language=language,
        )
        return {"site_id": site_id_str, "emails_sent": sent_count}


@app.task(name="app_worker.tasks.digest.dispatch_weekly_digests")
def dispatch_weekly_digests() -> dict:
    """Celery beat task: dispatch weekly digests for all active sites."""
    with system_session() as db:
        sites = db.scalars(select(Site)).all()
        processed = 0
        for site in sites:
            try:
                lang = "en"  # English-only interface (D22); emails follow the UI language
                send_site_weekly_digest.delay(str(site.id), None, lang)
                processed += 1
            except Exception as e:
                logger.error("dispatch_digest_failed", site_id=str(site.id), error=str(e))

        logger.info("weekly_digests_dispatched", sites_count=processed)
        return {"sites_dispatched": processed}
