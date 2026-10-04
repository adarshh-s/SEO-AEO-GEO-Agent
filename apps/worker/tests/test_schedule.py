from datetime import UTC, datetime, timedelta

from app_worker.tasks.tracking import is_due

NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


def test_never_checked_is_due():
    assert is_due(None, "weekly", NOW)


def test_checks_follow_plan_frequency_not_the_30_minute_beat():
    assert not is_due(NOW - timedelta(minutes=30), "daily", NOW)
    assert is_due(NOW - timedelta(days=1), "daily", NOW)
    assert not is_due(NOW - timedelta(days=2), "twice_weekly", NOW)
    assert is_due(NOW - timedelta(days=4), "twice_weekly", NOW)
    assert not is_due(NOW - timedelta(days=6), "weekly", NOW)
    assert is_due(NOW - timedelta(days=7), "weekly", NOW)
