"""Unit tests for task_dispatcher supporting Vercel Service Bindings and Celery."""

import respx

from app_api.task_dispatcher import dispatch_task


def test_dispatch_task_celery_when_worker_url_unset(monkeypatch):
    """When WORKER_URL is unset, tasks are sent through Celery."""
    monkeypatch.delenv("WORKER_URL", raising=False)
    dispatched = []

    def fake_send_task(name, args=None, kwargs=None, **opts):
        dispatched.append((name, args, kwargs, opts))

    from celery import current_app

    monkeypatch.setattr(current_app, "send_task", fake_send_task)

    dispatch_task(
        "app_worker.tasks.tracking.run_keyword_rank_check", args=["kw-123"], queue="tracking"
    )

    assert len(dispatched) == 1
    assert dispatched[0][0] == "app_worker.tasks.tracking.run_keyword_rank_check"
    assert dispatched[0][1] == ["kw-123"]
    assert dispatched[0][3]["queue"] == "tracking"


@respx.mock
def test_dispatch_task_http_when_worker_url_set(monkeypatch):
    """When WORKER_URL is set (via Vercel service binding), task is dispatched via HTTP."""
    worker_url = "https://worker-internal.vercel.internal"
    monkeypatch.setenv("WORKER_URL", worker_url)

    route = respx.post(
        f"{worker_url}/tasks/app_worker.tasks.tracking.run_keyword_rank_check"
    ).respond(status_code=200, json={"status": "completed", "result": "ok"})

    dispatch_task(
        "app_worker.tasks.tracking.run_keyword_rank_check", args=["kw-456"], queue="tracking"
    )

    assert route.called
    req = route.calls.last.request
    import json

    data = json.loads(req.content)
    assert data["args"] == ["kw-456"]
