"""Housekeeping tasks (default queue)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_

from app_core.db import system_session
from app_core.models import RefreshToken
from app_worker.celery_app import app


@app.task(name="app_worker.tasks.maintenance.ping")
def ping() -> str:
    return "pong"


@app.task(name="app_worker.tasks.maintenance.purge_expired_refresh_tokens")
def purge_expired_refresh_tokens() -> int:
    """Delete refresh tokens that expired, or were revoked more than a day ago."""
    now = datetime.now(UTC)
    with system_session() as db:
        result = db.execute(
            delete(RefreshToken).where(
                or_(
                    RefreshToken.expires_at < now, RefreshToken.revoked_at < now - timedelta(days=1)
                )
            )
        )
        return result.rowcount or 0
