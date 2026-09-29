"""Onboarding wizard backend. Detection/suggestions are mocks in Phase 1 (see services/onboarding.py)."""

from fastapi import APIRouter, Request

from app_api.deps import Admin, Tenant, TenantDb
from app_api.ratelimit import client_ip
from app_api.schemas.onboarding import (
    AnalyzeIn,
    AnalyzeOut,
    CompleteIn,
    SuggestedKeyword,
    SuggestedPrompt,
    SuggestIn,
    SuggestOut,
)
from app_api.schemas.sites import SiteOut
from app_api.services import audit, onboarding
from app_api.services import sites as site_service
from app_api.services.urls import normalize_site_url
from app_core.models import Site

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/analyze", response_model=AnalyzeOut)
def analyze(body: AnalyzeIn, ctx: Tenant) -> AnalyzeOut:
    homepage_url, domain = normalize_site_url(body.url)
    d = onboarding.get_site_analyzer().analyze(homepage_url, domain)
    return AnalyzeOut(
        source=d.source,
        homepage_url=homepage_url,
        domain=domain,
        platform=d.platform.value,
        brand_name=d.brand_name,
        detected_languages=d.detected_languages,
        industry=d.industry,
        city=d.city,
        country=d.country,
        competitors=d.competitors,
    )


@router.post("/suggestions", response_model=SuggestOut)
def suggestions(body: SuggestIn, ctx: Tenant) -> SuggestOut:
    provider = onboarding.get_suggestion_provider()
    args = dict(
        brand=body.brand_name, industry=body.industry, city=body.city, languages=body.languages
    )
    return SuggestOut(
        source="mock",
        keywords=[
            SuggestedKeyword(keyword=s.text, language=s.language) for s in provider.keywords(**args)
        ],
        prompts=[
            SuggestedPrompt(
                prompt_text=s.text, language=s.language, intent=(s.intent or "informational")
            )
            for s in provider.prompts(**args)
        ],
    )


@router.post("/complete", response_model=SiteOut, status_code=201)
def complete(body: CompleteIn, request: Request, ctx: Admin, db: TenantDb) -> Site:
    """Create the site with its keywords and prompts in one transaction."""
    site = site_service.create_site(db, ctx, body.site)
    if body.keywords:
        site_service.add_keywords(db, ctx, site, body.keywords)
    if body.prompts:
        site_service.add_prompts(db, ctx, site, body.prompts)
    audit.record(
        db,
        "site.created",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="site",
        target_id=site.id,
        data={
            "domain": site.domain,
            "via": "onboarding",
            "keywords": len(body.keywords),
            "prompts": len(body.prompts),
        },
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(site)
    return site
