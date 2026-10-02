"""Unit tests for worker HTTP service endpoints."""

from fastapi.testclient import TestClient

from app_worker.main import app

client = TestClient(app)


def test_worker_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_worker_task_not_found():
    res = client.post("/tasks/non.existent.module.task", json={"args": [], "kwargs": {}})
    assert res.status_code == 404


def test_worker_task_execution(monkeypatch):
    executed = []

    def fake_task(arg1, keyword="default"):
        executed.append((arg1, keyword))
        return "success"

    import sys
    import types

    dummy_mod = types.ModuleType("app_worker.tasks.dummy")
    dummy_mod.fake_task = fake_task
    sys.modules["app_worker.tasks.dummy"] = dummy_mod

    try:
        res = client.post(
            "/tasks/app_worker.tasks.dummy.fake_task",
            json={"args": ["test-id"], "kwargs": {"keyword": "seo"}},
        )
        assert res.status_code == 200
        assert res.json() == {
            "status": "completed",
            "task": "app_worker.tasks.dummy.fake_task",
            "result": "success",
        }
        assert executed == [("test-id", "seo")]
    finally:
        sys.modules.pop("app_worker.tasks.dummy", None)
