from app_worker.celery_app import QUEUES, app


def test_queues_and_routes():
    assert set(QUEUES) == {"default", "crawl", "tracking", "agents", "deploy"}
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1


def test_ping_runs_eagerly():
    from app_worker.tasks.maintenance import ping

    assert ping.apply().get() == "pong"


def test_beat_schedule_tasks_are_registered():
    for entry in app.conf.beat_schedule.values():
        assert entry["task"] in app.tasks


def test_phase3_tasks_registered():
    assert "app_worker.tasks.diagnose.run_diagnosis" in app.tasks
    assert "app_worker.tasks.webhooks.dispatch_webhook" in app.tasks


def test_every_task_called_anywhere_is_registered():
    """Tasks enqueued by name must be imported by celery_app, or the worker drops them."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    names = set()
    for f in [*root.glob("apps/api/app_api/**/*.py"), *root.glob("apps/worker/app_worker/**/*.py")]:
        names |= set(re.findall(r'"(app_worker\.tasks\.[a-z_]+\.[a-z_]+)"', f.read_text()))
    assert names, "no task names found"
    missing = sorted(n for n in names if n not in app.tasks)
    assert missing == [], f"tasks not registered with the worker: {missing}"


def test_weekly_digest_is_scheduled():
    entries = {e["task"]: e for e in app.conf.beat_schedule.values()}
    assert "app_worker.tasks.digest.dispatch_weekly_digests" in entries
