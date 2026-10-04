"""Public read-only endpoints for the client-side JavaScript snippet and telemetry.

These are unauthenticated (the site key is public), so they are rate limited, only
ever return approved/deployed fixes, and re-sanitize every payload before serving it.
"""

import uuid
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from redis import Redis
from sqlalchemy import select

from app_api.deps import SystemDb
from app_api.errors import not_found
from app_api.ratelimit import client_ip, enforce, get_redis
from app_core.brand import BRAND
from app_core.logging import get_logger
from app_core.models import AiReferralEvent, Fix, Site
from app_core.sanitize import PayloadError, sanitize_payload

router = APIRouter(prefix="/public/v1", tags=["public"])
log = get_logger(__name__)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
RedisDep = Annotated[Redis, Depends(get_redis)]

# Per IP per minute. Fix responses are also cached by browsers/CDN for 5 minutes.
FIXES_RATE_LIMIT = 120
TELEMETRY_RATE_LIMIT = 60

AiEngine = Literal["chatgpt", "perplexity", "gemini", "claude", "copilot", "other_ai"]


class PublicFixItem(BaseModel):
    id: uuid.UUID
    type: str
    target_url: str
    payload: dict[str, Any]


class PublicFixesResponse(BaseModel):
    site_key: str
    url: str
    fixes: list[PublicFixItem]


class TelemetryReferralIn(BaseModel):
    site_key: str = Field(max_length=64)
    url: str = Field(max_length=2000)
    referrer_engine: AiEngine


def page_key(url: str) -> tuple[str, str] | None:
    """(host without www, path without trailing slash) — the identity of a page."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    host = parts.hostname.lower().removeprefix("www.")
    return host, parts.path.rstrip("/") or "/"


def render_agent_js() -> str:
    """The snippet source with brand names filled in from config/brand.json."""
    source = (STATIC_DIR / "agent.js").read_text(encoding="utf-8")
    return source.replace("__BRAND_GLOBAL__", BRAND["snippet_global"]).replace(
        "__BRAND_SLUG__", BRAND["brand_slug"]
    )


@router.get(f"/{BRAND['snippet_filename']}")
def get_agent_script() -> Response:
    """Serve the universal JavaScript snippet."""
    return Response(
        content=render_agent_js(),
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"},
    )


@router.get("/fixes", response_model=PublicFixesResponse)
def get_public_fixes(
    request: Request,
    response: Response,
    redis: RedisDep,
    db: SystemDb,
    site_key: str = Query(
        ..., max_length=64, description=f"The site's public key ({BRAND['site_key_prefix']}_...)"
    ),
    url: str = Query(..., max_length=2000, description="The current page URL"),
) -> PublicFixesResponse:
    """Read-only endpoint delivering approved/deployed fixes to client snippets and SDKs."""
    enforce(redis, f"public-fixes:{client_ip(request)}", FIXES_RATE_LIMIT)
    site = db.scalar(select(Site).where(Site.site_key == site_key))
    target = page_key(url)
    if not site or target is None:
        raise not_found("site")
    if target[0] != site.domain.removeprefix("www."):
        # Fixes are only served for pages of the site the key belongs to.
        return PublicFixesResponse(site_key=site_key, url=url, fixes=[])

    fixes = db.scalars(
        select(Fix).where(Fix.site_id == site.id, Fix.status.in_(["approved", "deployed"]))
    ).all()
    items: list[PublicFixItem] = []
    for f in fixes:
        if page_key(f.target_url) != target:
            continue
        try:
            payload = sanitize_payload(f.payload)  # defence in depth: clean again on the way out
        except PayloadError:
            log.warning("public.fix_skipped_invalid_payload", fix_id=str(f.id))
            continue
        items.append(PublicFixItem(id=f.id, type=f.type, target_url=f.target_url, payload=payload))

    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return PublicFixesResponse(site_key=site_key, url=url, fixes=items)


@router.post("/telemetry/referral")
def record_ai_referral(
    body: TelemetryReferralIn,
    request: Request,
    redis: RedisDep,
    db: SystemDb,
) -> dict[str, bool]:
    """Cookieless endpoint recording traffic referred by AI answer engines. No personal data."""
    enforce(redis, f"public-telemetry:{client_ip(request)}", TELEMETRY_RATE_LIMIT)
    site = db.scalar(select(Site).where(Site.site_key == body.site_key))
    target = page_key(body.url)
    if not site or target is None or target[0] != site.domain.removeprefix("www."):
        return {"ok": True}  # fail silently to the client

    user_agent = request.headers.get("user-agent", "")
    db.add(
        AiReferralEvent(
            id=uuid.uuid4(),
            org_id=site.org_id,
            site_id=site.id,
            url=body.url,
            referrer_engine=body.referrer_engine,
            user_agent_category="bot" if "bot" in user_agent.lower() else "human",
        )
    )
    db.commit()
    return {"ok": True}
