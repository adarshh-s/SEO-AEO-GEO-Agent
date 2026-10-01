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
