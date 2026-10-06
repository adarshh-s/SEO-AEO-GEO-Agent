"""Onboarding wizard backend: real website analysis + AI suggestions (services/onboarding.py)."""

from decimal import Decimal

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
from app_core.cost_guard import CostCeilingExceeded, TrialExpired, check_cost_guard, record_usage
from app_core.models import Site

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _ai_allowed(db: TenantDb, ctx: Tenant) -> bool:
    """Claude calls are paid: respect the org's monthly cost ceiling (C4/D7)."""
    try:
        check_cost_guard(db, ctx.org_id, is_scheduled=False)
        return True
    except (CostCeilingExceeded, TrialExpired):
        return False


def _record_ai_cost(db: TenantDb, ctx: Tenant, cost: Decimal, provider: str) -> None:
    if cost > 0:
        record_usage(
            db, org_id=ctx.org_id, category="llm", provider=provider or "llm", cost_usd=cost
        )
        db.commit()


@router.post("/analyze", response_model=AnalyzeOut)
def analyze(body: AnalyzeIn, ctx: Tenant, db: TenantDb) -> AnalyzeOut:
    """Fetch the real homepage and identify platform, brand, languages, market, competitors."""
    homepage_url, domain = normalize_site_url(body.url)
    use_ai = _ai_allowed(db, ctx)
    d = onboarding.analyze_site(homepage_url, domain, use_ai=use_ai)
    _record_ai_cost(db, ctx, d.cost_usd, d.ai_provider)
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
        summary=d.summary,
        notice=d.notice if use_ai else "budget",
    )


@router.post("/suggestions", response_model=SuggestOut)
def suggestions(body: SuggestIn, ctx: Tenant, db: TenantDb) -> SuggestOut:
    """Keywords and AI questions written from the real site, only in enabled languages."""
    result = onboarding.suggest(
        brand=body.brand_name,
        industry=body.industry,
        city=body.city,
        country=body.country,
        languages=body.languages,
        summary=body.site_summary,
        use_ai=_ai_allowed(db, ctx),
    )
    _record_ai_cost(db, ctx, result.cost_usd, result.ai_provider)
    return SuggestOut(
        source=result.source,
        keywords=[SuggestedKeyword(keyword=s.text, language=s.language) for s in result.keywords],
        prompts=[
            SuggestedPrompt(
                prompt_text=s.text, language=s.language, intent=(s.intent or "informational")
            )
            for s in result.prompts
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
