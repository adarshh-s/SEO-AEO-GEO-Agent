"""Platform admin: manual plan assignment (D20), add-ons, cost-ceiling overrides (C4), plan limits."""

import uuid

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app_api.deps import PlatformAdmin, SystemDb
from app_api.errors import ApiError, not_found
from app_api.ratelimit import client_ip
from app_api.schemas.orgs import (
    AdminOrgOut,
    AdminOrgUpdateIn,
    AdminPlanUpdateIn,
    AdminSetPlanIn,
    PlanOut,
)
from app_api.security import now
from app_api.services import audit
from app_core.enums import AnswerEngineId
from app_core.languages import SUPPORTED_SITE_LANGUAGES
from app_core.models import Membership, Organization, Plan, Site

router = APIRouter(prefix="/admin", tags=["admin"])


def _org_out(db: SystemDb, org: Organization) -> AdminOrgOut:
    members = db.scalar(
        select(func.count()).select_from(Membership).where(Membership.org_id == org.id)
    )
    sites = db.scalar(select(func.count()).select_from(Site).where(Site.org_id == org.id))
    return AdminOrgOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan_code=org.plan.code,
        addons=org.addons,
        cost_ceiling_override_usd=org.cost_ceiling_override_usd,
        members=members or 0,
        sites=sites or 0,
        created_at=org.created_at,
    )


@router.get("/orgs", response_model=list[AdminOrgOut])
def list_orgs(admin: PlatformAdmin, db: SystemDb) -> list[AdminOrgOut]:
    orgs = db.scalars(select(Organization).order_by(Organization.created_at.desc()).limit(500))
    return [_org_out(db, o) for o in orgs]


def _org(db: SystemDb, org_id: uuid.UUID) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise not_found("organization")
    return org


@router.put("/orgs/{org_id}/plan", response_model=AdminOrgOut)
def set_org_plan(
    org_id: uuid.UUID, body: AdminSetPlanIn, request: Request, admin: PlatformAdmin, db: SystemDb
) -> AdminOrgOut:
    org = _org(db, org_id)
    plan = db.scalar(select(Plan).where(Plan.code == body.plan_code))
    if plan is None:
        raise ApiError(422, "unknown_plan", f"No plan with code '{body.plan_code}'.")
    old = org.plan.code
    org.plan_id, org.plan_assigned_at, org.plan_assigned_by = plan.id, now(), admin.id
    audit.record(
        db,
        "admin.plan_assigned",
        org_id=org.id,
        actor_user_id=admin.id,
        target_type="organization",
        target_id=org.id,
        data={"from": old, "to": plan.code},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(org)
    return _org_out(db, org)


@router.patch("/orgs/{org_id}", response_model=AdminOrgOut)
def update_org(
    org_id: uuid.UUID, body: AdminOrgUpdateIn, request: Request, admin: PlatformAdmin, db: SystemDb
) -> AdminOrgOut:
    org = _org(db, org_id)
    changes = body.model_dump(exclude_unset=True)
    if "addons" in changes:
        org.addons = {**org.addons, **changes["addons"]}
    if "cost_ceiling_override_usd" in changes:
        org.cost_ceiling_override_usd = changes["cost_ceiling_override_usd"]
    audit.record(
        db,
        "admin.org_updated",
        org_id=org.id,
        actor_user_id=admin.id,
        target_type="organization",
        target_id=org.id,
        data={k: str(v) for k, v in changes.items()},
        ip=client_ip(request),
    )
    db.commit()
    return _org_out(db, org)


@router.get("/plans", response_model=list[PlanOut])
def list_all_plans(admin: PlatformAdmin, db: SystemDb) -> list[Plan]:
    return list(db.scalars(select(Plan).order_by(Plan.sort_order)))


@router.patch("/plans/{plan_code}", response_model=PlanOut)
def update_plan(
    plan_code: str, body: AdminPlanUpdateIn, request: Request, admin: PlatformAdmin, db: SystemDb
) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.code == plan_code))
    if plan is None:
        raise not_found("plan")
    changes = body.model_dump(exclude_unset=True)
    engines = changes.get("allowed_engines")
    if engines is not None and not set(engines) <= {e.value for e in AnswerEngineId}:
        raise ApiError(422, "unknown_engine", "Unknown AI engine in allowed_engines.")
    langs = changes.get("addon_languages")
    if langs is not None and not set(langs) <= set(SUPPORTED_SITE_LANGUAGES):
        raise ApiError(422, "unknown_language", "Unknown language in addon_languages.")
    for key, value in changes.items():
        setattr(plan, key, value)
    audit.record(
        db,
        "admin.plan_updated",
        org_id=None,
        actor_user_id=admin.id,
        target_type="plan",
        target_id=plan_code,
        data={k: str(v) for k, v in changes.items()},
        ip=client_ip(request),
    )
    db.commit()
    return plan
