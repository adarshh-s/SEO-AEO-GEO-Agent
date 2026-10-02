"""FastAPI application for worker service running in serverless / Vercel environments."""

from __future__ import annotations

import importlib
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app_core.brand import PRODUCT_NAME
from app_core.logging import configure_logging
from app_core.settings import get_settings

s = get_settings()
configure_logging(s.log_level, s.log_json)
log = structlog.get_logger()

app = FastAPI(title=f"{PRODUCT_NAME} Worker Service")


class TaskPayload(BaseModel):
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks/{task_path:path}")
def execute_task(task_path: str, payload: TaskPayload) -> dict[str, Any]:
    """Execute a background task synchronously when called via internal HTTP service binding."""
    log.info("worker_task_received", task=task_path, args_count=len(payload.args))
    try:
        module_path, func_name = task_path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
    except Exception as exc:
        log.error("worker_task_lookup_failed", task=task_path, error=str(exc))
        raise HTTPException(status_code=404, detail=f"Task {task_path} not found: {exc}") from exc

    try:
        if hasattr(func, "run"):
            result = func.run(*payload.args, **payload.kwargs)
        else:
            result = func(*payload.args, **payload.kwargs)
        log.info("worker_task_completed", task=task_path)
        return {"status": "completed", "task": task_path, "result": result}
    except Exception as exc:
        log.error("worker_task_execution_failed", task=task_path, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Task execution failed: {exc}") from exc
