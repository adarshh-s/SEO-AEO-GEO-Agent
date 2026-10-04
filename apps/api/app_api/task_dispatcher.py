"""Enqueue background work on the Celery workers.

Workers run as long-lived containers (CLAUDE.md §3, decision D10). There is
deliberately no HTTP task endpoint: an endpoint that runs tasks by name is a
remote-code-execution risk and would put workers on a serverless runtime.
"""

from __future__ import annotations

from typing import Any

import structlog
from celery import current_app

log = structlog.get_logger()


def dispatch_task(
    task_name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str = "default",
) -> None:
    current_app.send_task(task_name, args=args or [], kwargs=kwargs or {}, queue=queue)
    log.info("task_dispatched", task=task_name, queue=queue)
