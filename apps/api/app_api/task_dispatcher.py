"""Dispatch background tasks either to an internal HTTP worker (via Vercel Service Binding) or Celery broker."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from celery import current_app

log = structlog.get_logger()


def dispatch_task(
    task_name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str = "default",
) -> None:
    """Dispatch a task to the background worker.

    If WORKER_URL is set (e.g. injected via Vercel Service Binding), calls the
    internal worker service over HTTP. Otherwise, dispatches via Celery.
    """
    worker_url = os.environ.get("WORKER_URL")
    task_args = args or []
    task_kwargs = kwargs or {}

    if worker_url:
        target_url = f"{worker_url.rstrip('/')}/tasks/{task_name}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(target_url, json={"args": task_args, "kwargs": task_kwargs})
                resp.raise_for_status()
                log.info(
                    "task_dispatched_via_http",
                    task=task_name,
                    worker_url=worker_url,
                    status=resp.status_code,
                )
                return
        except Exception as exc:
            log.error(
                "task_dispatch_http_error",
                task=task_name,
                worker_url=worker_url,
                error=str(exc),
            )
            return

    try:
        current_app.send_task(task_name, args=task_args, kwargs=task_kwargs, queue=queue)
        log.info("task_dispatched_via_celery", task=task_name, queue=queue)
    except Exception as exc:
        log.warning("task_dispatch_celery_failed", task=task_name, error=str(exc))
