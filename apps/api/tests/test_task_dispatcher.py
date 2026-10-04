from app_api.task_dispatcher import dispatch_task


def test_dispatch_task_sends_to_celery_queue(monkeypatch):
    from celery import current_app

    sent = []
    monkeypatch.setattr(current_app, "send_task", lambda name, **kw: sent.append((name, kw)))
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
