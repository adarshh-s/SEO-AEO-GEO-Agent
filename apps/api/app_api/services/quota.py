"""Plan limits for things users create (sites, keywords, prompts, languages).

Paid-API quotas and the monthly cost ceiling (decision C4 / D7) arrive in Phase 2.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app_api.errors import ApiError
from app_core.models import AiPrompt, Keyword, Organization, Plan, Site


def _limit_error(what: str, limit: int) -> ApiError:
    return ApiError(
        402,
        "plan_limit_reached",
        f"Your plan allows {limit} {what}. Contact us to change your plan.",
        limit=limit,
        resource=what,
    )


def org_plan(db: Session, org_id: uuid.UUID) -> tuple[Organization, Plan]:
    org = db.get(Organization, org_id)
    assert org is not None
    return org, org.plan


def check_sites(db: Session, org_id: uuid.UUID, adding: int = 1) -> None:
    _, plan = org_plan(db, org_id)
    count = db.scalar(select(func.count()).select_from(Site).where(Site.org_id == org_id)) or 0
    if count + adding > plan.max_sites:
        raise _limit_error("sites", plan.max_sites)


def check_keywords(db: Session, org_id: uuid.UUID, adding: int) -> None:
    _, plan = org_plan(db, org_id)
    count = (
        db.scalar(select(func.count()).select_from(Keyword).where(Keyword.org_id == org_id)) or 0
    )
    if count + adding > plan.max_keywords:
        raise _limit_error("keywords", plan.max_keywords)


def check_prompts(db: Session, org_id: uuid.UUID, adding: int) -> None:
    _, plan = org_plan(db, org_id)
    count = (
        db.scalar(select(func.count()).select_from(AiPrompt).where(AiPrompt.org_id == org_id)) or 0
    )
    if count + adding > plan.max_prompts:
        raise _limit_error("AI prompts", plan.max_prompts)


def check_languages(db: Session, org_id: uuid.UUID, languages: list[str]) -> None:
    """Languages per site. Add-on languages (e.g. Starter's Arabic) don't count if granted."""
    org, plan = org_plan(db, org_id)
    unique = list(dict.fromkeys(languages))
    counted = [
        lang
        for lang in unique
        if not (lang in plan.addon_languages and org.addons.get(_addon_key(lang)))
    ]
    if len(counted) > plan.max_languages_per_site:
        raise _limit_error("languages per site", plan.max_languages_per_site)


def _addon_key(lang: str) -> str:
    return {"ar": "arabic"}.get(lang, f"lang_{lang}")
