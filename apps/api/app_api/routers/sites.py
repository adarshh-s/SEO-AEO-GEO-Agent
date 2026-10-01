"""Sites and their tracked keywords and AI prompts."""

import uuid

from fastapi import APIRouter, Request
from sqlalchemy import select

from app_api.deps import Admin, Member, Tenant, TenantDb, VerifiedUser
from app_api.errors import not_found
from app_api.ratelimit import client_ip
from app_api.schemas.common import Ok
from app_api.schemas.sites import (
    BulkKeywordsIn,
    BulkPromptsIn,
    BulkResult,
    KeywordOut,
    PromptOut,
    SiteCreateIn,
    SiteOut,
    SiteUpdateIn,
    StatusIn,
)
from app_api.services import audit, quota
from app_api.services import sites as site_service
from app_core.models import AiPrompt, Keyword, Site
from app_core.tenancy import TenantContext, scoped

router = APIRouter(prefix="/sites", tags=["sites"])


def get_site(db: TenantDb, ctx: TenantContext, site_id: uuid.UUID) -> Site:
    site = db.scalar(scoped(select(Site), Site, ctx).where(Site.id == site_id))
    if site is None:
        raise not_found("site")
    return site


@router.get("", response_model=list[SiteOut])
def list_sites(ctx: Tenant, db: TenantDb) -> list[Site]:
    return list(db.scalars(scoped(select(Site), Site, ctx).order_by(Site.created_at)))


@router.post("", response_model=SiteOut, status_code=201)
def create_site(
    body: SiteCreateIn, request: Request, ctx: Admin, db: TenantDb, _user: VerifiedUser
) -> Site:
    site = site_service.create_site(db, ctx, body)
    audit.record(
        db,
        "site.created",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site",
        target_id=site.id,
        data={"domain": site.domain},
        ip=client_ip(request),
    )
    db.commit()
    return site


@router.get("/{site_id}", response_model=SiteOut)
def read_site(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> Site:
    return get_site(db, ctx, site_id)


@router.patch("/{site_id}", response_model=SiteOut)
def update_site(
    site_id: uuid.UUID, body: SiteUpdateIn, request: Request, ctx: Admin, db: TenantDb
) -> Site:
    site = get_site(db, ctx, site_id)
    changes = body.model_dump(exclude_unset=True)
    if "primary_language" in changes or "additional_languages" in changes:
        primary = changes.get("primary_language") or site.primary_language
        extra = changes.get("additional_languages", site.additional_languages)
        quota.check_languages(db, ctx.org_id, [primary, *extra])
        changes["additional_languages"] = [x for x in extra if x != primary]
    if "competitor_domains" in changes:
        changes["competitor_domains"] = site_service.clean_competitors(
            changes["competitor_domains"], site.domain
        )
    if "platform" in changes and changes["platform"] is not None:
        changes["platform"] = changes["platform"].value
    for key, value in changes.items():
        if value is None and key not in ("default_city", "industry"):
            continue
        setattr(site, key, value)
    audit.record(
        db,
        "site.updated",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site",
        target_id=site.id,
        data={"fields": sorted(changes)},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(site)
    return site


@router.delete("/{site_id}", response_model=Ok)
def delete_site(site_id: uuid.UUID, request: Request, ctx: Admin, db: TenantDb) -> Ok:
    site = get_site(db, ctx, site_id)
    audit.record(
        db,
        "site.deleted",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site",
        target_id=site.id,
        data={"domain": site.domain},
        ip=client_ip(request),
    )
    db.delete(site)
    db.commit()
    return Ok()


# --- keywords ------------------------------------------------------------------------------


@router.get("/{site_id}/keywords", response_model=list[KeywordOut])
def list_keywords(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> list[Keyword]:
    site = get_site(db, ctx, site_id)
    stmt = scoped(select(Keyword), Keyword, ctx).where(Keyword.site_id == site.id)
    return list(db.scalars(stmt.order_by(Keyword.created_at)))


@router.post("/{site_id}/keywords", response_model=BulkResult, status_code=201)
def add_keywords(site_id: uuid.UUID, body: BulkKeywordsIn, ctx: Member, db: TenantDb) -> BulkResult:
    site = get_site(db, ctx, site_id)
    created, skipped = site_service.add_keywords(db, ctx, site, body.items)
    db.commit()
    return BulkResult(created=created, skipped_duplicates=skipped)


def _get_keyword(
    db: TenantDb, ctx: TenantContext, site_id: uuid.UUID, keyword_id: uuid.UUID
) -> Keyword:
    kw = db.scalar(
        scoped(select(Keyword), Keyword, ctx).where(
            Keyword.id == keyword_id, Keyword.site_id == site_id
        )
    )
    if kw is None:
        raise not_found("keyword")
    return kw


@router.patch("/{site_id}/keywords/{keyword_id}", response_model=KeywordOut)
def set_keyword_status(
    site_id: uuid.UUID, keyword_id: uuid.UUID, body: StatusIn, ctx: Member, db: TenantDb
) -> Keyword:
    kw = _get_keyword(db, ctx, site_id, keyword_id)
    kw.status = body.status
    db.commit()
    return kw


@router.delete("/{site_id}/keywords/{keyword_id}", response_model=Ok)
def delete_keyword(site_id: uuid.UUID, keyword_id: uuid.UUID, ctx: Member, db: TenantDb) -> Ok:
    db.delete(_get_keyword(db, ctx, site_id, keyword_id))
    db.commit()
    return Ok()


# --- AI prompts ----------------------------------------------------------------------------


@router.get("/{site_id}/prompts", response_model=list[PromptOut])
def list_prompts(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> list[AiPrompt]:
    site = get_site(db, ctx, site_id)
    stmt = scoped(select(AiPrompt), AiPrompt, ctx).where(AiPrompt.site_id == site.id)
    return list(db.scalars(stmt.order_by(AiPrompt.created_at)))


@router.post("/{site_id}/prompts", response_model=BulkResult, status_code=201)
def add_prompts(site_id: uuid.UUID, body: BulkPromptsIn, ctx: Member, db: TenantDb) -> BulkResult:
    site = get_site(db, ctx, site_id)
    created, skipped = site_service.add_prompts(db, ctx, site, body.items)
    db.commit()
    return BulkResult(created=created, skipped_duplicates=skipped)


def _get_prompt(
    db: TenantDb, ctx: TenantContext, site_id: uuid.UUID, prompt_id: uuid.UUID
) -> AiPrompt:
    p = db.scalar(
        scoped(select(AiPrompt), AiPrompt, ctx).where(
            AiPrompt.id == prompt_id, AiPrompt.site_id == site_id
        )
    )
    if p is None:
        raise not_found("prompt")
    return p


@router.patch("/{site_id}/prompts/{prompt_id}", response_model=PromptOut)
def set_prompt_status(
    site_id: uuid.UUID, prompt_id: uuid.UUID, body: StatusIn, ctx: Member, db: TenantDb
) -> AiPrompt:
    p = _get_prompt(db, ctx, site_id, prompt_id)
    p.status = body.status
    db.commit()
    return p


@router.delete("/{site_id}/prompts/{prompt_id}", response_model=Ok)
def delete_prompt(site_id: uuid.UUID, prompt_id: uuid.UUID, ctx: Member, db: TenantDb) -> Ok:
    db.delete(_get_prompt(db, ctx, site_id, prompt_id))
    db.commit()
    return Ok()
