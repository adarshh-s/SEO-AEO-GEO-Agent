"""Fixes router for approval, editing, deployment, and rollback."""

import uuid
from datetime import UTC, datetime

from celery import current_app
from fastapi import APIRouter, Query, Request
from sqlalchemy import desc, select

from app_api.deps import Admin, Member, Tenant, TenantDb, VerifiedUser
from app_api.errors import ApiError, not_found
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.fixes import FixDeployIn, FixOut, FixUpdateIn
from app_api.services import audit
from app_core.connectors import get_connector
from app_core.models import Fix, Site, SiteIntegration, Webhook
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

    # Route through deep platform connector if applicable
    connector = get_connector(body.deployed_via)
    if connector:
        site = db.scalar(scoped(select(Site), Site, ctx).where(Site.id == site_id))
        integration = db.scalar(
            scoped(select(SiteIntegration), SiteIntegration, ctx).where(
                SiteIntegration.site_id == site_id,
                SiteIntegration.provider == body.deployed_via,
            )
        )
        config = integration.config if integration else {}
        credentials = integration.credentials if integration else {}
        deploy_res = connector.deploy_fix(
            target_url=fix.target_url,
            fix_type=fix.type,
            title=fix.title,
            payload=fix.payload,
            config=config,
            credentials=credentials,
            site_key=site.site_key if site else "",
            previous_state=body.previous_state or fix.previous_state,
        )
        if not deploy_res.ok:
            raise ApiError(400, "deployment_failed", deploy_res.message)
        if deploy_res.external_reference:
            fix.external_reference = deploy_res.external_reference
        if deploy_res.previous_state and not fix.previous_state:
            fix.previous_state = deploy_res.previous_state

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
        data={
            "type": fix.type,
            "target_url": fix.target_url,
            "deployed_via": body.deployed_via,
            "external_reference": fix.external_reference,
        },
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

    # Roll back on external platform if deployed via connector
    if fix.deployed_via:
        connector = get_connector(fix.deployed_via)
        if connector:
            integration = db.scalar(
                scoped(select(SiteIntegration), SiteIntegration, ctx).where(
                    SiteIntegration.site_id == site_id,
                    SiteIntegration.provider == fix.deployed_via,
                )
            )
            config = integration.config if integration else {}
            credentials = integration.credentials if integration else {}
            connector.rollback_fix(
                target_url=fix.target_url,
                fix_type=fix.type,
                external_reference=fix.external_reference,
                previous_state=fix.previous_state,
                config=config,
                credentials=credentials,
            )

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
