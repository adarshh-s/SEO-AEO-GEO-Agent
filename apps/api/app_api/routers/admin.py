"""Platform admin: manual plan assignment (D20), add-ons, cost-ceiling overrides (C4), plan limits."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app_api.deps import PlatformAdmin, SystemDb
from app_api.errors import ApiError, not_found
from app_api.ratelimit import client_ip
from app_api.schemas.orgs import (
    AdminAuditLogOut,
    AdminCostSummaryOut,
    AdminOrgCostDetailOut,
    AdminOrgOut,
    AdminOrgUpdateIn,
    AdminPlanUpdateIn,
    AdminSetPlanIn,
    PlanOut,
)
from app_api.security import now
from app_api.services import audit
from app_core.cost_guard import check_trial_status, get_current_period, get_monthly_spend
from app_core.enums import AnswerEngineId
from app_core.languages import SUPPORTED_SITE_LANGUAGES
from app_core.models import AuditLogEntry, Membership, Organization, Plan, Site, UsageCounter, User

router = APIRouter(prefix="/admin", tags=["admin"])


def _org_out(db: SystemDb, org: Organization) -> AdminOrgOut:
    members = db.scalar(
        select(func.count()).select_from(Membership).where(Membership.org_id == org.id)
    )
    sites = db.scalar(select(func.count()).select_from(Site).where(Site.org_id == org.id))
    spend = get_monthly_spend(db, org.id)
    ceiling = org.cost_ceiling_override_usd or org.plan.monthly_cost_ceiling_usd
    ratio = float(spend / ceiling) if ceiling and ceiling > 0 else 0.0
    trial_active = check_trial_status(org)
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
        current_spend_usd=spend,
        effective_ceiling_usd=ceiling,
        spend_ratio=round(ratio, 4),
        is_trial_expired=not trial_active,
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


@router.get("/costs/summary", response_model=AdminCostSummaryOut)
def get_cost_summary(admin: PlatformAdmin, db: SystemDb) -> AdminCostSummaryOut:
    period_start, _ = get_current_period()
    counters = db.scalars(
        select(UsageCounter).where(UsageCounter.period_start == period_start)
    ).all()

    total_spend = Decimal("0.0000")
    prov_spend: dict[str, Decimal] = {}
    cat_spend: dict[str, Decimal] = {}
    org_spend: dict[uuid.UUID, Decimal] = {}

    for c in counters:
        cost = c.cost_usd or Decimal("0.0000")
        total_spend += cost
        prov_spend[c.provider] = prov_spend.get(c.provider, Decimal("0.0000")) + cost
        cat_spend[c.category] = cat_spend.get(c.category, Decimal("0.0000")) + cost
        org_spend[c.org_id] = org_spend.get(c.org_id, Decimal("0.0000")) + cost

    orgs = db.scalars(select(Organization)).all()
    orgs_at_warning = 0
    orgs_at_paused = 0
    top_orgs = []

    for o in orgs:
        spend = org_spend.get(o.id, Decimal("0.0000"))
        ceiling = o.cost_ceiling_override_usd or o.plan.monthly_cost_ceiling_usd
        if ceiling and ceiling > 0:
            ratio = float(spend / ceiling)
            if ratio >= 1.0:
                orgs_at_paused += 1
            elif ratio >= 0.8:
                orgs_at_warning += 1

        top_orgs.append(
            {
                "org_id": str(o.id),
                "name": o.name,
                "slug": o.slug,
                "plan_code": o.plan.code,
                "spend_usd": str(spend),
                "ceiling_usd": str(ceiling) if ceiling else None,
                "ratio": round(float(spend / ceiling), 2) if ceiling and ceiling > 0 else 0.0,
            }
        )

    top_orgs.sort(key=lambda x: Decimal(x["spend_usd"]), reverse=True)

    return AdminCostSummaryOut(
        total_spend_usd=total_spend,
        total_orgs=len(orgs),
        orgs_at_warning=orgs_at_warning,
        orgs_at_paused=orgs_at_paused,
        provider_breakdown=prov_spend,
        category_breakdown=cat_spend,
        top_spending_orgs=top_orgs[:10],
    )


@router.get("/orgs/{org_id}/costs", response_model=AdminOrgCostDetailOut)
def get_org_costs(org_id: uuid.UUID, admin: PlatformAdmin, db: SystemDb) -> AdminOrgCostDetailOut:
    org = _org(db, org_id)
    spend = get_monthly_spend(db, org_id)
    ceiling = org.cost_ceiling_override_usd or org.plan.monthly_cost_ceiling_usd
    ratio = float(spend / ceiling) if ceiling and ceiling > 0 else 0.0
    trial_active = check_trial_status(org)

    trial_days_remaining = None
    if org.plan.code == "trial" and org.plan.trial_days:
        from datetime import UTC, datetime, timedelta

        expiry = org.created_at + timedelta(days=org.plan.trial_days)
        delta = (expiry - datetime.now(UTC)).days
        trial_days_remaining = max(0, delta)

    counters = db.scalars(
        select(UsageCounter)
        .where(UsageCounter.org_id == org_id)
        .order_by(UsageCounter.period_start.desc())
        .limit(100)
    ).all()

    counter_list = [
        {
            "period_start": c.period_start.isoformat(),
            "period_end": c.period_end.isoformat(),
            "category": c.category,
            "provider": c.provider,
            "units": c.units,
            "cost_usd": str(c.cost_usd),
        }
        for c in counters
    ]

    return AdminOrgCostDetailOut(
        org_id=org.id,
        org_name=org.name,
        plan_code=org.plan.code,
        current_spend_usd=spend,
        effective_ceiling_usd=ceiling,
        spend_ratio=round(ratio, 4),
        is_trial_expired=not trial_active,
        trial_days_remaining=trial_days_remaining,
        counters=counter_list,
    )


@router.post("/orgs/{org_id}/reset-counters")
def reset_org_counters(
    org_id: uuid.UUID, request: Request, admin: PlatformAdmin, db: SystemDb
) -> dict:
    org = _org(db, org_id)
    period_start, _ = get_current_period()
    db.query(UsageCounter).filter(
        UsageCounter.org_id == org_id,
        UsageCounter.period_start == period_start,
    ).delete(synchronize_session=False)
    audit.record(
        db,
        "admin.counters_reset",
        org_id=org.id,
        actor_user_id=admin.id,
        target_type="organization",
        target_id=str(org.id),
        data={},
        ip=client_ip(request),
    )
    db.commit()
    return {"ok": True, "message": "Usage counters reset for the current period."}


@router.get("/audit-logs", response_model=list[AdminAuditLogOut])
def get_audit_logs(
    admin: PlatformAdmin, db: SystemDb, limit: int = 100, offset: int = 0
) -> list[AdminAuditLogOut]:
    logs = db.scalars(
        select(AuditLogEntry)
        .order_by(AuditLogEntry.created_at.desc())
        .offset(offset)
        .limit(min(limit, 500))
    ).all()

    user_ids = {entry.actor_user_id for entry in logs if entry.actor_user_id}
    users_by_id = {}
    if user_ids:
        users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
        users_by_id = {u.id: u.email for u in users}

    return [
        AdminAuditLogOut(
            id=entry.id,
            org_id=entry.org_id,
            actor_user_id=entry.actor_user_id,
            actor_email=users_by_id.get(entry.actor_user_id),
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            data=entry.data or {},
            ip=entry.ip,
            created_at=entry.created_at,
        )
        for entry in logs
    ]
