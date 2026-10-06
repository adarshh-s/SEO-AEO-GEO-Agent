"""Cost-ceiling alerts (C4): emailed to owners/admins + operator, once per level per month."""

from decimal import Decimal

import fakeredis
import pytest

from app_core import alerts
from app_core.cost_guard import CostCeilingExceeded, check_cost_guard, record_usage
from app_core.db import system_session
from conftest import set_plan


@pytest.fixture
def mailbox(monkeypatch):
    from app_core.email import ConsoleEmailProvider
    from app_core.settings import get_settings

    box = ConsoleEmailProvider()
    monkeypatch.setattr(alerts, "get_email_provider", lambda: box)
    monkeypatch.setattr(alerts, "redis_client", lambda: fake)
    monkeypatch.setattr(get_settings(), "ops_alert_email", "ops@example.com")
    fake = fakeredis.FakeRedis(decode_responses=True)
    return box


def test_alerts_at_80_and_100_percent_once_each(account, mailbox):
    set_plan(account.org_id, "starter")  # $15 ceiling
    with system_session() as db:
        record_usage(
            db, org_id=account.org_id, category="llm", provider="gemini", cost_usd=Decimal("12.75")
        )  # fmt: skip  85%
        check_cost_guard(db, account.org_id, is_scheduled=True)
        check_cost_guard(db, account.org_id, is_scheduled=True)  # no duplicate
    sent = [(m.to, m.subject) for m in mailbox.outbox]
    assert sorted(to for to, _ in sent) == sorted([account.email, "ops@example.com"])
    assert all("80%" in subj for _, subj in sent)

    with system_session() as db:
        record_usage(
            db, org_id=account.org_id, category="llm", provider="gemini", cost_usd=Decimal("3.00")
        )  # fmt: skip  105%
        with pytest.raises(CostCeilingExceeded):
            check_cost_guard(db, account.org_id, is_scheduled=True)  # scheduled work paused
    # The 100% alert is still sent (to both recipients) even though the work is refused.
    paused = [m.to for m in mailbox.outbox if "scheduled checks paused" in m.subject]
    assert sorted(paused) == sorted([account.email, "ops@example.com"])
