"""Fixes router for approval, editing, deployment, and rollback."""

import uuid
from datetime import UTC, datetime

from celery import current_app
from fastapi import APIRouter, Query, Request
from sqlalchemy import desc, select

from app_api.deps import Admin, Member, Tenant, TenantDb, VerifiedUser
from app_api.errors import not_found
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.fixes import FixDeployIn, FixOut, FixUpdateIn
from app_api.services import audit
from app_core.models import Fix, Webhook
from app_core.tenancy import TenantContext, scoped

router = APIRouter(prefix="/sites/{site_id}/fixes", tags=["fixes"])


def _get_site_fix(db: TenantDb, ctx: TenantContext, site_id: uuid.UUID, fix_id: uuid.UUID) -> Fix:
    fix = db.scalar(scoped(select(Fix), Fix, ctx).where(Fix.id == fix_id, Fix.site_id == site_id))
    if fix is None:
        raise not_found("fix")
    return fix


def _dispatch_fix_webhooks(db: TenantDb, org_id: uuid.UUID, event: str, fix: Fix) -> None:
    webhooks = db.scalars(
        scoped(
            select(Webhook), Webhook, TenantContext(org_id=org_id, user_id=org_id, role="admin")
        ).where(Webhook.status == "active")
    ).all()
    for wh in webhooks:
        if event in wh.events:
            current_app.send_task(
                "app_worker.tasks.webhooks.dispatch_webhook",
                args=[
                    str(wh.id),
                    event,
                    {
                        "fix_id": str(fix.id),
                        "site_id": str(fix.site_id),
                        "type": fix.type,
                        "status": fix.status,
                        "target_url": fix.target_url,
                    },
                ],
                queue="default",
            )


@router.get("", response_model=list[FixOut])
def list_fixes(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
    status: str | None = Query(None),
    type: str | None = Query(None),
    language: str | None = Query(None),
) -> list[Fix]:
    site = get_site(db, ctx, site_id)
    query = scoped(select(Fix), Fix, ctx).where(Fix.site_id == site.id)
    if status:
        query = query.where(Fix.status == status)
    if type:
        query = query.where(Fix.type == type)
    if language:
        query = query.where(Fix.language == language)
    return list(db.scalars(query.order_by(desc(Fix.created_at))))


@router.get("/{fix_id}", response_model=FixOut)
def read_fix(site_id: uuid.UUID, fix_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> Fix:
    return _get_site_fix(db, ctx, site_id, fix_id)


@router.patch("/{fix_id}", response_model=FixOut)
def update_fix(
    site_id: uuid.UUID,
    fix_id: uuid.UUID,
    body: FixUpdateIn,
    ctx: Member,
    db: TenantDb,
) -> Fix:
    fix = _get_site_fix(db, ctx, site_id, fix_id)
    if body.title is not None:
        fix.title = body.title
    if body.description is not None:
        fix.description = body.description
    if body.payload is not None:
        # Shallow merge or replace payload
        fix.payload = {**fix.payload, **body.payload}
    db.commit()
    return fix


@router.post("/{fix_id}/approve", response_model=FixOut)
def approve_fix(
    site_id: uuid.UUID,
    fix_id: uuid.UUID,
    request: Request,
    ctx: Member,
    db: TenantDb,
    _user: VerifiedUser,
) -> Fix:
    fix = _get_site_fix(db, ctx, site_id, fix_id)
    fix.status = "approved"
    audit.record(
        db,
        "fix.approved",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="fix",
        target_id=fix.id,
        data={"type": fix.type, "target_url": fix.target_url},
        ip=client_ip(request),
    )
    db.commit()
    _dispatch_fix_webhooks(db, ctx.org_id, "fix.approved", fix)
    return fix


@router.post("/{fix_id}/reject", response_model=FixOut)
def reject_fix(
    site_id: uuid.UUID,
    fix_id: uuid.UUID,
    request: Request,
    ctx: Member,
    db: TenantDb,
) -> Fix:
    fix = _get_site_fix(db, ctx, site_id, fix_id)
    fix.status = "rejected"
    audit.record(
        db,
        "fix.rejected",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="fix",
        target_id=fix.id,
        data={"type": fix.type, "target_url": fix.target_url},
        ip=client_ip(request),
    )
    db.commit()
    return fix


@router.post("/{fix_id}/deploy", response_model=FixOut)
def deploy_fix(
    site_id: uuid.UUID,
    fix_id: uuid.UUID,
    body: FixDeployIn,
    request: Request,
    ctx: Admin,
    db: TenantDb,
    _user: VerifiedUser,
) -> Fix:
    fix = _get_site_fix(db, ctx, site_id, fix_id)
    if body.previous_state:
        fix.previous_state = body.previous_state
    fix.status = "deployed"
    fix.deployed_via = body.deployed_via
    fix.deployed_at = datetime.now(UTC)
    fix.applied_by_user_id = ctx.user_id

    audit.record(
        db,
        "fix.deployed",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="fix",
        target_id=fix.id,
        data={"type": fix.type, "target_url": fix.target_url, "deployed_via": body.deployed_via},
        ip=client_ip(request),
    )
    db.commit()
    _dispatch_fix_webhooks(db, ctx.org_id, "fix.deployed", fix)
    return fix


@router.post("/{fix_id}/rollback", response_model=FixOut)
def rollback_fix(
    site_id: uuid.UUID,
    fix_id: uuid.UUID,
    request: Request,
    ctx: Admin,
    db: TenantDb,
) -> Fix:
    fix = _get_site_fix(db, ctx, site_id, fix_id)
    fix.status = "rolled_back"
    audit.record(
        db,
        "fix.rolled_back",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="fix",
        target_id=fix.id,
        data={"type": fix.type, "target_url": fix.target_url},
        ip=client_ip(request),
    )
    db.commit()
    return fix
