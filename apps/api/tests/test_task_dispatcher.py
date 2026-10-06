from app_api.task_dispatcher import dispatch_task


def test_dispatch_task_sends_to_celery_queue(monkeypatch):
    from app_api import task_dispatcher

    sent = []
    monkeypatch.setattr(
        task_dispatcher.celery_client(), "send_task", lambda name, **kw: sent.append((name, kw))
    )
    dispatch_task("app_worker.tasks.diagnose.run_diagnosis", args=["abc"], queue="agents")
    assert sent == [
        (
            "app_worker.tasks.diagnose.run_diagnosis",
            {"args": ["abc"], "kwargs": {}, "queue": "agents"},
        )
    ]


def test_there_is_no_http_task_endpoint():
    import importlib.util

    assert importlib.util.find_spec("app_worker.main") is None


def test_dispatcher_uses_the_redis_broker():
    from app_api.task_dispatcher import celery_client
    from app_core.settings import get_settings

    assert celery_client().conf.broker_url == get_settings().redis_url


def test_api_never_imports_worker_code():
    """The API image doesn't contain app_worker: work must be queued, not imported."""
    import re
    from pathlib import Path

    api = Path(__file__).resolve().parents[1] / "app_api"
    offenders = [
        f"{f.relative_to(api)}:{i}"
        for f in api.rglob("*.py")
        for i, line in enumerate(f.read_text().splitlines(), 1)
        if re.match(r"\s*(from|import)\s+app_worker\b", line)
    ]
    assert offenders == []
