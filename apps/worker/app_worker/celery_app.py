"""Celery app. Queues are split so Chromium-heavy crawls can't starve cheap jobs.

Customer-URL fetches MUST run with the prefork pool: claude-seo's url_safety patches
DNS resolution process-wide and is not thread-safe (docs/claude-seo-mapping.md).
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
from kombu import Queue

from app_core.logging import configure_logging
from app_core.settings import get_settings

QUEUES = ("default", "crawl", "tracking", "agents", "deploy")

settings = get_settings()
app = Celery("app_worker", broker=settings.redis_url, backend=settings.redis_url)
app.conf.update(
    task_queues=[Queue(name) for name in QUEUES],
    task_default_queue="default",
    task_routes={
        "app_worker.tasks.crawl.*": {"queue": "crawl"},
        "app_worker.tasks.tracking.*": {"queue": "tracking"},
        "app_worker.tasks.agents.*": {"queue": "agents"},
        "app_worker.tasks.deploy.*": {"queue": "deploy"},
    },
    task_acks_late=True,  # jobs are idempotent; redeliver if a worker dies
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    beat_schedule={
        "purge-expired-refresh-tokens": {
            "task": "app_worker.tasks.maintenance.purge_expired_refresh_tokens",
            "schedule": 6 * 3600,
        },
        "weekly-digests": {
            "task": "app_worker.tasks.digest.dispatch_weekly_digests",
            "schedule": crontab(day_of_week="mon", hour=8, minute=0),  # Mondays 08:00 UTC
        },
        "dispatch-scheduled-checks": {
            "task": "app_worker.tasks.tracking.dispatch_scheduled_checks",
            "schedule": 1800,  # every 30 minutes
        },
    },
)
import app_worker.tasks.audit  # noqa: E402,F401
import app_worker.tasks.crawl  # noqa: E402,F401
import app_worker.tasks.diagnose  # noqa: E402,F401
import app_worker.tasks.digest  # noqa: E402,F401
import app_worker.tasks.maintenance  # noqa: E402,F401
import app_worker.tasks.tracking  # noqa: E402,F401
import app_worker.tasks.webhooks  # noqa: E402,F401


@worker_process_init.connect
def _init_process(**_: object) -> None:
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    if s.sentry_dsn:  # D11
        import sentry_sdk

        sentry_sdk.init(dsn=s.sentry_dsn, environment=s.env, traces_sample_rate=0.0)
