"""Integrations router for Snippet guide, API Keys, and Webhooks."""

import hashlib
import secrets
import uuid

from fastapi import APIRouter
from sqlalchemy import desc, select

from app_api.deps import Admin, Tenant, TenantDb
from app_api.errors import not_found
from app_api.routers.sites import get_site
from app_api.schemas.common import Ok
from app_api.schemas.integrations import (
    ApiKeyCreatedOut,
    ApiKeyCreateIn,
    ApiKeyOut,
    SnippetInfoOut,
    WebhookCreateIn,
    WebhookOut,
)
from app_core.brand import BRAND
from app_core.models import ApiKey, Webhook
from app_core.settings import get_settings
from app_core.tenancy import scoped

router = APIRouter(tags=["integrations"])


PLATFORM_INSTRUCTIONS = {
    "wordpress": "Install the QuardLink WordPress Plugin, or paste the script into your theme header or Header & Footer Code plugin.",
    "shopify": "Paste the script tag in your theme.liquid file inside the <head> section right before </head>.",
    "nextjs": 'Add the script in your root layout or Next.js Script tag: <Script src="..." strategy="afterInteractive" data-site="..." />',
    "wix": "Go to Settings > Custom Code in your Wix dashboard, paste the snippet into Head, and apply to All Pages.",
    "webflow": "Go to Project Settings > Custom Code > Head Code, paste the script tag, and publish your site.",
    "salla": "Go to App Store / Custom Scripts in your Salla dashboard, add the snippet to the Header section.",
    "custom": "Paste the script into your site's HTML template inside the <head> section of every page.",
}


@router.get("/sites/{site_id}/integrations/snippet", response_model=SnippetInfoOut)
def get_site_snippet_info(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> SnippetInfoOut:
    site = get_site(db, ctx, site_id)
    s = get_settings()
    api_url = s.api_url.rstrip("/")
    script_url = f"{api_url}/public/v1/agent.js"
    tag = f'<script async src="{script_url}" data-site="{site.site_key}"></script>'

    return SnippetInfoOut(
        site_key=site.site_key,
        script_url=script_url,
        snippet_tag=tag,
        platform=site.platform,
        instructions=PLATFORM_INSTRUCTIONS,
    )


# --- Organization API Keys -------------------------------------------------------------------


@router.get("/org/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(ctx: Tenant, db: TenantDb) -> list[ApiKey]:
    return list(db.scalars(scoped(select(ApiKey), ApiKey, ctx).order_by(desc(ApiKey.created_at))))


@router.post("/org/api-keys", response_model=ApiKeyCreatedOut, status_code=201)
def create_api_key(
    body: ApiKeyCreateIn,
    ctx: Admin,
    db: TenantDb,
) -> ApiKeyCreatedOut:
    prefix = BRAND.get("api_key_prefix", "ql")
    random_part = secrets.token_urlsafe(32)
    raw_key = f"{prefix}_live_{random_part}"
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    key_prefix = raw_key[:12]

    key_obj = ApiKey(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        name=body.name,
        prefix=key_prefix,
        hashed_key=hashed_key,
        scopes=body.scopes,
        created_by=ctx.user_id,
    )
    db.add(key_obj)
    db.commit()

    return ApiKeyCreatedOut(
        id=key_obj.id,
        name=key_obj.name,
        prefix=key_obj.prefix,
        scopes=key_obj.scopes,
        last_used_at=key_obj.last_used_at,
        created_at=key_obj.created_at,
        raw_key=raw_key,
    )


@router.delete("/org/api-keys/{key_id}", response_model=Ok)
def delete_api_key(
    key_id: uuid.UUID,
    ctx: Admin,
    db: TenantDb,
) -> Ok:
    key_obj = db.scalar(scoped(select(ApiKey), ApiKey, ctx).where(ApiKey.id == key_id))
    if not key_obj:
        raise not_found("api key")
    db.delete(key_obj)
    db.commit()
    return Ok()


# --- Organization Webhooks -------------------------------------------------------------------


@router.get("/org/webhooks", response_model=list[WebhookOut])
def list_webhooks(ctx: Tenant, db: TenantDb) -> list[Webhook]:
    return list(
        db.scalars(scoped(select(Webhook), Webhook, ctx).order_by(desc(Webhook.created_at)))
    )


@router.post("/org/webhooks", response_model=WebhookOut, status_code=201)
def create_webhook(
    body: WebhookCreateIn,
    ctx: Admin,
    db: TenantDb,
) -> Webhook:
    secret = secrets.token_hex(24)
    wh = Webhook(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        url=body.url,
        secret=secret,
        events=body.events,
        status="active",
    )
    db.add(wh)
    db.commit()
    return wh


@router.delete("/org/webhooks/{webhook_id}", response_model=Ok)
def delete_webhook(
    webhook_id: uuid.UUID,
    ctx: Admin,
    db: TenantDb,
) -> Ok:
    wh = db.scalar(scoped(select(Webhook), Webhook, ctx).where(Webhook.id == webhook_id))
    if not wh:
        raise not_found("webhook")
    db.delete(wh)
    db.commit()
    return Ok()
