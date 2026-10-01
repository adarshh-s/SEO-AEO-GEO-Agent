"""Audit background task (default / crawl queue)."""

import uuid
from datetime import UTC, datetime

import structlog

from app_core.db import system_session
from app_core.models import Audit, Site
from app_worker.celery_app import app
from app_worker.seo_engine.audit import run_comprehensive_audit

logger = structlog.get_logger(__name__)


@app.task(name="app_worker.tasks.audit.run_site_audit")
def run_site_audit(audit_id_str: str) -> dict:
    """Execute full website audit on homepage and evaluate issues."""
    audit_id = uuid.UUID(audit_id_str)
    with system_session() as db:
        audit = db.get(Audit, audit_id)
        if not audit:
            logger.error("audit_not_found", audit_id=audit_id_str)
            return {"error": "Audit not found"}

        site = db.get(Site, audit.site_id)
        if not site:
            audit.status = "failed"
            audit.error_message = "Associated site not found"
            db.commit()
            return {"error": "Site not found"}

        logger.info(
            "starting_site_audit",
            audit_id=audit_id_str,
            site_id=str(site.id),
            url=site.homepage_url,
        )
        audit.status = "running"
        audit.started_at = datetime.now(UTC)
        db.commit()

        try:
            res = run_comprehensive_audit(site.homepage_url)
            audit.score = res.overall_score
            audit.category_scores = res.category_scores
            audit.issues = res.issues
            audit.summary = res.summary
            audit.pages_crawled = res.pages_crawled
            audit.status = "completed"
            audit.completed_at = datetime.now(UTC)
            db.commit()

            logger.info(
                "site_audit_completed",
                audit_id=audit_id_str,
                overall_score=res.overall_score,
                total_issues=res.summary.get("total_issues", 0),
            )
            return {
                "audit_id": audit_id_str,
                "score": res.overall_score,
                "category_scores": res.category_scores,
                "summary": res.summary,
            }
        except Exception as e:
            logger.exception("site_audit_failed", audit_id=audit_id_str, error=str(e))
            audit.status = "failed"
            audit.error_message = str(e)
            audit.completed_at = datetime.now(UTC)
            db.commit()
            return {"error": str(e)}
