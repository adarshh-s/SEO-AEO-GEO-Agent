"""Integrations router for Snippet guide, API Keys, Webhooks, and Deep Platform Connectors."""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import desc, select

from app_api.deps import Admin, Tenant, TenantDb
from app_api.errors import ApiError, not_found
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.common import Ok
from app_api.schemas.integrations import (
    ApiKeyCreatedOut,
    ApiKeyCreateIn,
    ApiKeyOut,
    GscAuthUrlOut,
    GscConnectIn,
    GscPerformanceOut,
    SiteIntegrationCreateIn,
    SiteIntegrationOut,
    SiteIntegrationUpdateIn,
    SnippetInfoOut,
    TestConnectionOut,
    WebhookCreatedOut,
    WebhookCreateIn,
    WebhookOut,
)
from app_api.services import audit
from app_api.services.urls import normalize_site_url
from app_core.brand import BRAND
from app_core.connectors import (
    GoogleSearchConsoleConnector,
    generate_cloudflare_worker_js,
    generate_wordpress_plugin_zip,
    get_connector,
)
from app_core.models import ApiKey, SiteIntegration, Webhook
from app_core.settings import get_settings
from app_core.tenancy import scoped

logger = logging.getLogger(__name__)

router = APIRouter(tags=["integrations"])


PLATFORM_INSTRUCTIONS = {
    "wordpress": f"Install the {BRAND['product_name']} WordPress plugin, or paste the script into your theme header or Header & Footer Code plugin.",
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


# --- Site Integrations (Phase 4 Deep Integrations) --------------------------------------------


def _get_site_integration(
    db: TenantDb, ctx: Tenant, site_id: uuid.UUID, integration_id: uuid.UUID
) -> SiteIntegration:
    integration = db.scalar(
        scoped(select(SiteIntegration), SiteIntegration, ctx).where(
            SiteIntegration.id == integration_id, SiteIntegration.site_id == site_id
        )
    )
    if not integration:
        raise not_found("site integration")
    return integration


@router.get("/sites/{site_id}/integrations", response_model=list[SiteIntegrationOut])
def list_site_integrations(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> list[SiteIntegration]:
    site = get_site(db, ctx, site_id)
    return list(
        db.scalars(
            scoped(select(SiteIntegration), SiteIntegration, ctx)
            .where(SiteIntegration.site_id == site.id)
            .order_by(desc(SiteIntegration.created_at))
        )
    )


@router.post("/sites/{site_id}/integrations", response_model=SiteIntegrationOut, status_code=201)
def create_site_integration(
    site_id: uuid.UUID,
    body: SiteIntegrationCreateIn,
    request: Request,
    ctx: Admin,
    db: TenantDb,
) -> SiteIntegration:
    site = get_site(db, ctx, site_id)

    # Check if integration for this provider already exists
    existing = db.scalar(
        scoped(select(SiteIntegration), SiteIntegration, ctx).where(
            SiteIntegration.site_id == site.id, SiteIntegration.provider == body.provider
        )
    )
    if existing:
        existing.config = body.config
        if body.credentials:
            existing.credentials = body.credentials
        existing.status = "active"
        existing.last_error = None
        db.commit()
        return existing

    integration = SiteIntegration(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        site_id=site.id,
        provider=body.provider,
        status="active",
        config=body.config,
        credentials=body.credentials,
    )
    db.add(integration)
    audit.record(
        db,
        "integration.connected",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site_integration",
        target_id=integration.id,
        data={"provider": body.provider},
        ip=client_ip(request),
    )
    db.commit()
    return integration


@router.get("/sites/{site_id}/integrations/{integration_id}", response_model=SiteIntegrationOut)
def get_site_integration(
    site_id: uuid.UUID,
    integration_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> SiteIntegration:
    return _get_site_integration(db, ctx, site_id, integration_id)


@router.patch("/sites/{site_id}/integrations/{integration_id}", response_model=SiteIntegrationOut)
def update_site_integration(
    site_id: uuid.UUID,
    integration_id: uuid.UUID,
    body: SiteIntegrationUpdateIn,
    ctx: Admin,
    db: TenantDb,
) -> SiteIntegration:
    integration = _get_site_integration(db, ctx, site_id, integration_id)
    if body.status is not None:
        integration.status = body.status
    if body.config is not None:
        integration.config = body.config
    if body.credentials is not None:
        integration.credentials = body.credentials
    db.commit()
    return integration


@router.delete("/sites/{site_id}/integrations/{integration_id}", response_model=Ok)
def delete_site_integration(
    site_id: uuid.UUID,
    integration_id: uuid.UUID,
    request: Request,
    ctx: Admin,
    db: TenantDb,
) -> Ok:
    integration = _get_site_integration(db, ctx, site_id, integration_id)
    db.delete(integration)
    audit.record(
        db,
        "integration.disconnected",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site_integration",
        target_id=integration.id,
        data={"provider": integration.provider},
        ip=client_ip(request),
    )
    db.commit()
    return Ok()


@router.post(
    "/sites/{site_id}/integrations/{integration_id}/test", response_model=TestConnectionOut
)
def test_site_integration(
    site_id: uuid.UUID,
    integration_id: uuid.UUID,
    ctx: Admin,
    db: TenantDb,
) -> TestConnectionOut:
    integration = _get_site_integration(db, ctx, site_id, integration_id)
    connector = get_connector(integration.provider)
    if not connector:
        return TestConnectionOut(
            ok=False, message=f"No connector available for provider '{integration.provider}'."
        )

    res = connector.test_connection(integration.config, integration.credentials)
    integration.last_synced_at = datetime.now(UTC)
    if res.ok:
        integration.status = "active"
        integration.last_error = None
    else:
        integration.status = "error"
        integration.last_error = res.message
    db.commit()

    return TestConnectionOut(ok=res.ok, message=res.message, details=res.details)


@router.get("/sites/{site_id}/integrations/wordpress/download")
def download_wordpress_plugin(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> Response:
    site = get_site(db, ctx, site_id)
    api_url = get_settings().api_url.rstrip("/")
    zip_bytes = generate_wordpress_plugin_zip(site.site_key, api_url)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{BRAND["wp_plugin_slug"]}-seo.zip"'
        },
    )


@router.get("/sites/{site_id}/integrations/cloudflare/worker.js")
def get_cloudflare_worker_script(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> Response:
    site = get_site(db, ctx, site_id)
    api_url = get_settings().api_url.rstrip("/")
    js_code = generate_cloudflare_worker_js(site.site_key, api_url)
    return Response(content=js_code, media_type="application/javascript")


# --- Google Search Console Endpoints ---------------------------------------------------------


@router.get(
    "/sites/{site_id}/integrations/google-search-console/auth-url",
    response_model=GscAuthUrlOut,
)
def get_gsc_auth_url(
    site_id: uuid.UUID,
    ctx: Admin,
    db: TenantDb,
    redirect_uri: str = "https://example.com/oauth",
) -> GscAuthUrlOut:

    site = get_site(db, ctx, site_id)
    s = get_settings()
    client_id = getattr(s, "google_client_id", "") or "mock-google-client-id"
    gsc = GoogleSearchConsoleConnector()
    url = gsc.get_auth_url(client_id, redirect_uri, state=str(site.id))
    return GscAuthUrlOut(auth_url=url)


@router.post(
    "/sites/{site_id}/integrations/google-search-console/connect",
    response_model=SiteIntegrationOut,
)
def connect_google_search_console(
    site_id: uuid.UUID,
    body: GscConnectIn,
    request: Request,
    ctx: Admin,
    db: TenantDb,
) -> SiteIntegration:
    site = get_site(db, ctx, site_id)
    s = get_settings()
    client_id = getattr(s, "google_client_id", "") or "mock-google-client-id"
    client_secret = getattr(s, "google_client_secret", "") or "mock-google-client-secret"

    gsc = GoogleSearchConsoleConnector()
    token_data = gsc.exchange_code(client_id, client_secret, body.code, body.redirect_uri)
    access_token = token_data.get("access_token", "")

    # Check site ownership matching
    try:
        sites_list = gsc.list_sites(access_token)
        matching_site = next(
            (
                s
                for s in sites_list
                if s.get("siteUrl")
                in (site.homepage_url, f"sc-domain:{site.domain}", f"https://{site.domain}/")
            ),
            None,
        )
        if matching_site and matching_site.get("permissionLevel") in ("siteOwner", "siteFullUser"):
            site.verified_at = datetime.now(UTC)
            site.verification_method = "google_search_console"
            audit.record(
                db,
                "site.verified",
                org_id=ctx.org_id,
                actor_user_id=ctx.user_id,
                target_type="site",
                target_id=site.id,
                data={"method": "google_search_console", "property": matching_site.get("siteUrl")},
                ip=client_ip(request),
            )
    except Exception as e:
        logger.debug("GSC auto-verify check skipped: %s", e)

    # Upsert SiteIntegration
    existing = db.scalar(
        scoped(select(SiteIntegration), SiteIntegration, ctx).where(
            SiteIntegration.site_id == site.id,
            SiteIntegration.provider == "google_search_console",
        )
    )
    if existing:
        existing.config = {"property_url": body.property_url}
        existing.credentials = token_data
        existing.status = "active"
        existing.last_synced_at = datetime.now(UTC)
        db.commit()
        return existing

    integration = SiteIntegration(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        site_id=site.id,
        provider="google_search_console",
        status="active",
        config={"property_url": body.property_url},
        credentials=token_data,
        last_synced_at=datetime.now(UTC),
    )
    db.add(integration)
    audit.record(
        db,
        "integration.connected",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site_integration",
        target_id=integration.id,
        data={"provider": "google_search_console", "property": body.property_url},
        ip=client_ip(request),
    )
    db.commit()
    return integration


@router.get(
    "/sites/{site_id}/integrations/google-search-console/performance",
    response_model=GscPerformanceOut,
)
def get_gsc_performance(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> GscPerformanceOut:
    site = get_site(db, ctx, site_id)
    integration = db.scalar(
        scoped(select(SiteIntegration), SiteIntegration, ctx).where(
            SiteIntegration.site_id == site.id,
            SiteIntegration.provider == "google_search_console",
        )
    )
    if not integration or integration.status != "active":
        raise ApiError(400, "gsc_not_connected", "Google Search Console is not connected.")

    gsc = GoogleSearchConsoleConnector()
    access_token = integration.credentials.get("access_token", "")
    prop_url = integration.config.get("property_url", site.homepage_url)
    rows = gsc.query_search_analytics(access_token, prop_url)
    return GscPerformanceOut(property_url=prop_url, rows=rows)


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
def list_webhooks(ctx: Admin, db: TenantDb) -> list[Webhook]:
    return list(
        db.scalars(scoped(select(Webhook), Webhook, ctx).order_by(desc(Webhook.created_at)))
    )


@router.post("/org/webhooks", response_model=WebhookCreatedOut, status_code=201)
def create_webhook(
    body: WebhookCreateIn,
    ctx: Admin,
    db: TenantDb,
) -> Webhook:
    if not body.url.lower().startswith("https://"):
        raise ApiError(422, "invalid_url", "Webhook URLs must use https://.")
    normalize_site_url(body.url)  # rejects IPs, localhost and internal hostnames
    secret = secrets.token_hex(24)
    wh = Webhook(
        id=uuid.uuid4(),
        org_id=ctx.org_id,
        url=body.url.strip(),
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
