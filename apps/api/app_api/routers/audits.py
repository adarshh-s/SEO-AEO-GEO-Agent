import uuid

from fastapi import APIRouter, Request
from sqlalchemy import select

from app_api.deps import Member, Tenant, TenantDb
from app_api.errors import not_found
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.audits import AuditListItemOut, AuditOut
from app_api.services import audit as audit_service
from app_api.services.quota import check_audits
from app_api.task_dispatcher import dispatch_task
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

    # Crawling happens only in the worker (SSRF protection is process-isolated there).
    dispatch_task(
        "app_worker.tasks.audit.run_site_audit", args=[str(audit_entry.id)], queue="crawl"
    )
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
