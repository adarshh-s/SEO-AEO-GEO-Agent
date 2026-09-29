"""Public plan list for the pricing page. No checkout: "Contact us" until Phase 7 (D20)."""

from fastapi import APIRouter
from sqlalchemy import select

from app_api.deps import SystemDb
from app_api.schemas.orgs import PlanOut
from app_core.models import Plan

router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=list[PlanOut])
def list_public_plans(db: SystemDb) -> list[Plan]:
    return list(db.scalars(select(Plan).where(Plan.is_public.is_(True)).order_by(Plan.sort_order)))
