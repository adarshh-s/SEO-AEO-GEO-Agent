"""Public read-only endpoints for the client-side JavaScript snippet and telemetry."""

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from app_api.deps import SystemDb
from app_api.errors import not_found
from app_core.brand import BRAND
from app_core.models import AiReferralEvent, Fix, Site

router = APIRouter(prefix="/public/v1", tags=["public"])

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


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
    site_key: str
    url: str
    referrer_engine: str  # chatgpt | perplexity | gemini | claude | copilot | other_ai


@router.get("/agent.js")
def get_agent_script() -> Response:
    """Serve the universal JavaScript snippet."""
    script_path = STATIC_DIR / "agent.js"
    if not script_path.exists():
        raise not_found("agent.js")
    content = script_path.read_text(encoding="utf-8")
    return Response(
        content=content,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/fixes", response_model=PublicFixesResponse)
def get_public_fixes(
    site_key: str = Query(
        ..., description=f"The site's public key ({BRAND['site_key_prefix']}_...)"
    ),
    url: str = Query(..., description="The current page URL"),
    db: SystemDb = None,
) -> PublicFixesResponse:
    """Read-only endpoint delivering approved/deployed fixes to client snippets and SDKs."""
    site = db.scalar(select(Site).where(Site.site_key == site_key))
    if not site:
        raise not_found("site")

    clean_url = url.split("#")[0].split("?")[0].rstrip("/")
    fixes = db.scalars(
        select(Fix).where(
            Fix.site_id == site.id,
            Fix.status.in_(["approved", "deployed"]),
        )
    ).all()

    # Match target URL (matching domain / path, or homepage match)
    matching_fixes = []
    for f in fixes:
        f_clean = f.target_url.split("#")[0].split("?")[0].rstrip("/")
        if f_clean == clean_url or clean_url.endswith(f_clean) or f_clean.endswith(clean_url):
            matching_fixes.append(
                PublicFixItem(
                    id=f.id,
                    type=f.type,
                    target_url=f.target_url,
                    payload=f.payload,
                )
            )

    return PublicFixesResponse(
        site_key=site_key,
        url=url,
        fixes=matching_fixes,
    )


@router.post("/telemetry/referral")
def record_ai_referral(
    body: TelemetryReferralIn,
    request: Request,
    db: SystemDb = None,
    user_agent: str | None = Header(None, alias="User-Agent"),
) -> dict[str, bool]:
    """Cookieless endpoint recording traffic referred by AI answer engines."""
    site = db.scalar(select(Site).where(Site.site_key == body.site_key))
    if not site:
        return {"ok": True}  # Fail silently to client

    event = AiReferralEvent(
        id=uuid.uuid4(),
        org_id=site.org_id,
        site_id=site.id,
        url=body.url,
        referrer_engine=body.referrer_engine,
        user_agent_category="bot" if user_agent and "bot" in user_agent.lower() else "human",
    )
    db.add(event)
    db.commit()
    return {"ok": True}
