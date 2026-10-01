"""Cost ceiling tracking and trial expiration enforcement (Decisions C4, D7, D23)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app_core.models import Organization, UsageCounter
from app_core.settings import get_settings

logger = structlog.get_logger(__name__)


class CostCeilingExceeded(Exception):
    def __init__(self, message: str, ratio: float) -> None:
        super().__init__(message)
        self.ratio = ratio


class TrialExpired(Exception):
    pass


def get_current_period(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (start_of_month, start_of_next_month) in UTC."""
    n = now or datetime.now(UTC)
    start = datetime(n.year, n.month, 1, tzinfo=UTC)
    if n.month == 12:
        end = datetime(n.year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(n.year, n.month + 1, 1, tzinfo=UTC)
    return start, end


def check_trial_status(org: Organization) -> bool:
    """Returns True if the org's trial is active, False if expired (D23)."""
    if org.plan.code != "trial" or not org.plan.trial_days:
        return True  # Non-trial or unlimited trial
    expiry = org.created_at + timedelta(days=org.plan.trial_days)
    return datetime.now(UTC) <= expiry


def get_monthly_spend(
    db: Session, org_id: uuid.UUID, period_start: datetime | None = None
) -> Decimal:
    """Sum total cost_usd for the org in the given or current period."""
    start, _ = get_current_period(period_start)
    spend = db.scalar(
        select(func.coalesce(func.sum(UsageCounter.cost_usd), Decimal("0.0000"))).where(
            UsageCounter.org_id == org_id, UsageCounter.period_start == start
        )
    )
    return Decimal(str(spend or "0.0000"))


def check_cost_guard(db: Session, org_id: uuid.UUID, *, is_scheduled: bool = False) -> None:
    """Enforce cost ceilings (C4/D7) and trial expiration (D23).

    - At 100% of ceiling: pause non-essential work (scheduled checks).
    - At 120% of ceiling: hard stop on all paid work.
    - If trial expired: pause checks.
    """
    org = db.get(Organization, org_id)
    if not org:
        return

    # 1. Trial expiration check (D23)
    if not check_trial_status(org):
        raise TrialExpired("Trial period has ended. Contact us to activate your account.")

    # 2. Ceiling check (C4 / D7)
    ceiling = org.cost_ceiling_override_usd or org.plan.monthly_cost_ceiling_usd
    if not ceiling or ceiling <= 0:
        return

    current_spend = get_monthly_spend(db, org_id)
    ratio = float(current_spend / ceiling)

    if ratio >= 1.20:
        raise CostCeilingExceeded(f"Hard spending limit exceeded ({ratio:.0%}).", ratio)

    if is_scheduled and ratio >= 1.00:
        raise CostCeilingExceeded(
            f"Monthly ceiling reached ({ratio:.0%}). Scheduled checks paused.", ratio
        )

    if ratio >= 0.80:
        s = get_settings()
        logger.warning(
            "org_cost_ceiling_warning",
            org_id=str(org_id),
            spend=str(current_spend),
            ceiling=str(ceiling),
            ratio=f"{ratio:.1%}",
            alert_email=s.ops_alert_email,
        )


def record_usage(
    db: Session,
    *,
    org_id: uuid.UUID,
    category: str,
    provider: str,
    units: int = 1,
    cost_usd: Decimal = Decimal("0.0000"),
) -> None:
    """Record an API usage event into the monthly usage counter."""
    period_start, period_end = get_current_period()

    counter = db.scalar(
        select(UsageCounter).where(
            UsageCounter.org_id == org_id,
            UsageCounter.period_start == period_start,
            UsageCounter.category == category,
            UsageCounter.provider == provider,
        )
    )

    if counter:
        counter.units += units
        counter.cost_usd += cost_usd
    else:
        counter = UsageCounter(
            org_id=org_id,
            period_start=period_start,
            period_end=period_end,
            category=category,
            provider=provider,
            units=units,
            cost_usd=cost_usd,
        )
        db.add(counter)
    db.flush()
