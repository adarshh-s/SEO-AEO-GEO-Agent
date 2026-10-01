"""Celery task for dispatching signed customer webhooks."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

import requests
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app_core.db import get_engine
from app_core.models import Webhook
from app_worker.celery_app import app

logger = get_task_logger(__name__)


@app.task(name="app_worker.tasks.webhooks.dispatch_webhook", queue="default")
def dispatch_webhook(webhook_id_str: str, event: str, payload: dict) -> None:
    """Send signed HTTP POST to registered webhook URL with HMAC-SHA256 signature."""
    webhook_id = uuid.UUID(webhook_id_str)
    engine = get_engine()

    with Session(engine) as session:
        webhook = session.get(Webhook, webhook_id)
        if not webhook or webhook.status != "active":
            return

        body = json.dumps(
            {
                "event": event,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": payload,
            },
            sort_keys=True,
        )

        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-QuardLink-Event": event,
            "X-QuardLink-Signature": f"sha256={signature}",
            "User-Agent": "QuardLink-Webhooks/1.0",
        }

        try:
            resp = requests.post(
                webhook.url,
                data=body,
                headers=headers,
                timeout=10,
            )
            webhook.last_delivery_at = datetime.now(UTC)
            webhook.last_status_code = resp.status_code
            if resp.status_code >= 400:
                logger.warning(
                    f"Webhook {webhook.id} returned status {resp.status_code} for {event}"
                )
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to deliver webhook {webhook.id} to {webhook.url}: {e}")
            webhook.last_delivery_at = datetime.now(UTC)
            webhook.last_status_code = 0
            session.commit()
