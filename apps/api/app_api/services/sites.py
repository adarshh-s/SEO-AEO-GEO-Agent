"""Site, keyword and prompt creation shared by the sites router and onboarding."""

import secrets

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app_api.errors import ApiError
from app_api.schemas.sites import KeywordIn, PromptIn, SiteCreateIn
from app_api.services import quota
from app_api.services.urls import normalize_domain, normalize_site_url
from app_core.brand import BRAND
from app_core.models import AiPrompt, Keyword, Site
from app_core.tenancy import TenantContext


def new_site_key() -> str:
    return f"{BRAND['site_key_prefix']}_{secrets.token_urlsafe(18)}"


def clean_competitors(domains: list[str], own_domain: str) -> list[str]:
    out: list[str] = []
    for raw in domains:
        try:
            d = normalize_domain(raw)
        except ApiError:
            continue
        if d != own_domain and d not in out:
            out.append(d)
    return out


def create_site(db: Session, ctx: TenantContext, body: SiteCreateIn) -> Site:
    homepage_url, domain = normalize_site_url(body.homepage_url)
    quota.check_sites(db, ctx.org_id)
    languages = [body.primary_language, *body.additional_languages]
    quota.check_languages(db, ctx.org_id, languages)
    if db.scalar(select(Site.id).where(Site.org_id == ctx.org_id, Site.domain == domain)):
        raise ApiError(409, "site_exists", "This website is already added.")
    site = Site(
        org_id=ctx.org_id,
        domain=domain,
        homepage_url=homepage_url,
        name=body.name,
        platform=body.platform.value,
        platform_confirmed=body.platform_confirmed,
        primary_language=body.primary_language,
        additional_languages=[x for x in body.additional_languages if x != body.primary_language],
        default_country=body.default_country,
        default_city=body.default_city,
        industry=body.industry,
        brand_names=body.brand_names,
        competitor_domains=clean_competitors(body.competitor_domains, domain),
        site_key=new_site_key(),
        verification_token=secrets.token_hex(16),
        created_by=ctx.user_id,
    )
    db.add(site)
    db.flush()
    return site


def _check_language(site: Site, language: str) -> None:
    if language not in site.languages:
        raise ApiError(
            422,
            "language_not_enabled",
            f"'{language}' is not enabled for this site. Add it in site settings first.",
            language=language,
        )


def add_keywords(
    db: Session, ctx: TenantContext, site: Site, items: list[KeywordIn]
) -> tuple[int, int]:
    for item in items:
        _check_language(site, item.language)
    quota.check_keywords(db, ctx.org_id, len(items))
    rows = [
        {
            "org_id": ctx.org_id,
            "site_id": site.id,
            "keyword": " ".join(i.keyword.split()),
            "language": i.language,
            "country": i.country or site.default_country,
            "city": i.city or None,
            "device": i.device,
            "tags": i.tags,
        }
        for i in items
    ]
    before = _count(db, Keyword, site)
    db.execute(insert(Keyword).values(rows).on_conflict_do_nothing())
    created = _count(db, Keyword, site) - before
    return created, len(rows) - created


def add_prompts(
    db: Session, ctx: TenantContext, site: Site, items: list[PromptIn]
) -> tuple[int, int]:
    for item in items:
        _check_language(site, item.language)
    existing = {
        (p.lower(), lang)
        for p, lang in db.execute(
            select(AiPrompt.prompt_text, AiPrompt.language).where(AiPrompt.site_id == site.id)
        )
    }
    new: list[AiPrompt] = []
    for i in items:
        text = " ".join(i.prompt_text.split())
        key = (text.lower(), i.language)
        if key in existing:
            continue
        existing.add(key)
        new.append(
            AiPrompt(
                org_id=ctx.org_id,
                site_id=site.id,
                prompt_text=text,
                language=i.language,
                country=i.country or site.default_country,
                intent=i.intent.value,
                tags=i.tags,
            )
        )
    quota.check_prompts(db, ctx.org_id, len(new))
    db.add_all(new)
    db.flush()
    return len(new), len(items) - len(new)


def _count(db: Session, model: type, site: Site) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.site_id == site.id)) or 0
