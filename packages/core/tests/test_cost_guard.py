import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app_core.cost_guard import (
    CostCeilingExceeded,
    TrialExpired,
    check_cost_guard,
    check_trial_status,
    get_current_period,
    record_usage,
)
from app_core.models import Organization, Plan, UsageCounter


def test_get_current_period():
    jan = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    start, end = get_current_period(jan)
    assert start == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)

    dec = datetime(2026, 12, 25, 12, 0, tzinfo=UTC)
    start_dec, end_dec = get_current_period(dec)
    assert start_dec == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)
    assert end_dec == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)


def test_check_trial_status():
    plan_trial = Plan(code="trial", name="Trial", trial_days=14)
    plan_paid = Plan(code="pro", name="Pro", trial_days=None)

    # Active trial
    org_active = Organization(
        id=uuid.uuid4(),
        name="Active Org",
        slug="active-org",
        plan=plan_trial,
        created_at=datetime.now(UTC) - timedelta(days=5),
    )
    assert check_trial_status(org_active) is True

    # Expired trial
    org_expired = Organization(
        id=uuid.uuid4(),
        name="Expired Org",
        slug="expired-org",
        plan=plan_trial,
        created_at=datetime.now(UTC) - timedelta(days=15),
    )
    assert check_trial_status(org_expired) is False

    # Paid plan with old created_at is always active
    org_paid = Organization(
        id=uuid.uuid4(),
        name="Paid Org",
        slug="paid-org",
        plan=plan_paid,
        created_at=datetime.now(UTC) - timedelta(days=100),
    )
    assert check_trial_status(org_paid) is True


class DummyOrg:
    def __init__(self, ceiling: Decimal, trial_days: int = 14, days_old: int = 2):
        self.id = uuid.uuid4()
        self.cost_ceiling_override_usd = None
        self.created_at = datetime.now(UTC) - timedelta(days=days_old)
        self.plan = Plan(
            code="trial",
            name="Trial",
            trial_days=trial_days,
            monthly_cost_ceiling_usd=ceiling,
        )


class MockSession:
    def __init__(self, org, spend: Decimal):
        self.org = org
        self.spend = spend
        self.recorded = []

    def get(self, entity, ident):
        if entity is Organization and ident == self.org.id:
            return self.org
        return None

    def scalar(self, query):
        return self.spend

    def execute(self, query):
        class Result:
            def scalar_one_or_none(self):
                return None

        return Result()

    def add(self, obj):
        self.recorded.append(obj)

    def flush(self):
        pass


def test_check_cost_guard_thresholds():
    org = DummyOrg(ceiling=Decimal("10.00"))

    # Under 80%: normal, both scheduled and manual succeed
    db_normal = MockSession(org, Decimal("5.00"))
    check_cost_guard(db_normal, org.id, is_scheduled=False)
    check_cost_guard(db_normal, org.id, is_scheduled=True)

    # 105%: scheduled is paused, manual allowed
    db_100 = MockSession(org, Decimal("10.50"))
    check_cost_guard(db_100, org.id, is_scheduled=False)
    with pytest.raises(CostCeilingExceeded, match="Monthly ceiling reached"):
        check_cost_guard(db_100, org.id, is_scheduled=True)

    # 125%: hard stop, all checks blocked
    db_120 = MockSession(org, Decimal("12.50"))
    with pytest.raises(CostCeilingExceeded, match="Hard spending limit exceeded"):
        check_cost_guard(db_120, org.id, is_scheduled=False)
    with pytest.raises(CostCeilingExceeded, match="Hard spending limit exceeded"):
        check_cost_guard(db_120, org.id, is_scheduled=True)


def test_check_cost_guard_expired_trial():
    org_expired = DummyOrg(ceiling=Decimal("10.00"), trial_days=14, days_old=16)
    db = MockSession(org_expired, Decimal("1.00"))
    with pytest.raises(TrialExpired, match="Trial period has ended"):
        check_cost_guard(db, org_expired.id, is_scheduled=False)


def test_record_usage_creates_counter():
    org_id = uuid.uuid4()
    db = MockSession(DummyOrg(Decimal("10.00")), Decimal("0.00"))
    record_usage(
        db,
        org_id=org_id,
        category="serp",
        provider="dataforseo",
        units=2,
        cost_usd=Decimal("0.0040"),
    )
    assert len(db.recorded) == 1
    counter = db.recorded[0]
    assert isinstance(counter, UsageCounter)
    assert counter.org_id == org_id
    assert counter.category == "serp"
    assert counter.provider == "dataforseo"
    assert counter.units == 2
    assert counter.cost_usd == Decimal("0.0040")
