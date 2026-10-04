"""Enqueue background work on the Celery workers.

Workers run as long-lived containers (CLAUDE.md §3, decision D10). There is
deliberately no HTTP task endpoint: an endpoint that runs tasks by name is a
remote-code-execution risk and would put workers on a serverless runtime.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import structlog
from celery import Celery

from app_core.settings import get_settings

log = structlog.get_logger()


@lru_cache
def celery_client() -> Celery:
    """Producer-only Celery app on the same Redis broker the workers consume from.

    (Celery's implicit default app points at amqp://localhost, so it must not be used.)
    """
    return Celery("app_api", broker=get_settings().redis_url)


def dispatch_task(
    task_name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str = "default",
) -> None:
    celery_client().send_task(task_name, args=args or [], kwargs=kwargs or {}, queue=queue)
    log.info("task_dispatched", task=task_name, queue=queue)
