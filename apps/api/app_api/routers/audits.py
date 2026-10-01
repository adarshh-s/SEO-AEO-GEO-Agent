import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy import select

from app_api.deps import Member, Tenant, TenantDb
from app_api.errors import not_found
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.audits import AuditListItemOut, AuditOut
from app_api.services import audit as audit_service
from app_api.services.quota import check_audits
from app_core.models import Audit
from app_core.tenancy import scoped

router = APIRouter(prefix="/sites/{site_id}/audits", tags=["audits"])


@router.post("", response_model=AuditOut, status_code=201)
def trigger_audit(
    site_id: uuid.UUID,
    request: Request,
    ctx: Member,
    db: TenantDb,
) -> Audit:
    """Trigger a comprehensive SEO/AEO audit for a website."""
    site = get_site(db, ctx, site_id)
    check_audits(db, ctx.org_id)

    audit_entry = Audit(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        site_id=site.id,
        status="pending",
        pages_crawled=1,
    )
    db.add(audit_entry)
    db.commit()

    audit_service.record(
        db,
        "audit.triggered",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="audit",
        target_id=audit_entry.id,
        data={"site_id": str(site.id)},
        ip=client_ip(request),
    )
    db.commit()

    from app_core.settings import get_settings

    if get_settings().env == "test":
        from app_worker.tasks.audit import run_site_audit

        run_site_audit(str(audit_entry.id))
        db.refresh(audit_entry)
        return audit_entry

    # Attempt to dispatch asynchronously via Celery; fallback to inline execution
    try:
        from app_worker.tasks.audit import run_site_audit

        run_site_audit.delay(str(audit_entry.id))
    except Exception:
        # Inline fallback for tests / environments without a live celery broker
        try:
            from app_worker.seo_engine.audit import run_comprehensive_audit

            audit_entry.status = "running"
            audit_entry.started_at = datetime.now(UTC)
            res = run_comprehensive_audit(site.homepage_url)
            audit_entry.score = res.overall_score
            audit_entry.category_scores = res.category_scores
            audit_entry.issues = res.issues
            audit_entry.summary = res.summary
            audit_entry.pages_crawled = res.pages_crawled
            audit_entry.status = "completed"
            audit_entry.completed_at = datetime.now(UTC)
            db.commit()
        except Exception as e:
            audit_entry.status = "failed"
            audit_entry.error_message = str(e)
            audit_entry.completed_at = datetime.now(UTC)
            db.commit()

    return audit_entry


@router.get("", response_model=list[AuditListItemOut])
def list_audits(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> list[Audit]:
    """List past audits for a website."""
    site = get_site(db, ctx, site_id)
    audits = db.scalars(
        scoped(select(Audit), Audit, ctx)
        .where(Audit.site_id == site.id)
        .order_by(Audit.created_at.desc())
    ).all()
    return list(audits)


@router.get("/{audit_id}", response_model=AuditOut)
def get_audit(
    site_id: uuid.UUID,
    audit_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> Audit:
    """Get full audit report with all categories and issues."""
    get_site(db, ctx, site_id)
    audit_entry = db.scalar(
        scoped(select(Audit), Audit, ctx).where(
            Audit.id == audit_id,
            Audit.site_id == site_id,
        )
    )
    if not audit_entry:
        raise not_found("audit")

    return audit_entry
