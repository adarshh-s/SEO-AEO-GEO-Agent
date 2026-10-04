"""Celery task for dispatching signed customer webhooks.

Webhook URLs are customer-supplied, so delivery goes through the SSRF-safe, DNS-pinned
session from claude-seo and never follows redirects. Each delivery is signed with
HMAC-SHA256 over "<timestamp>.<body>"; receivers verify the signature and reject old
timestamps to stop replays.
"""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app_core.brand import BRAND
from app_core.db import get_engine
from app_core.models import Webhook
from app_worker.celery_app import app
from app_worker.seo_engine.url_safety import URLSafetyError, safe_requests_session

logger = get_task_logger(__name__)


def sign(secret: str, timestamp: str, body: str) -> str:
    message = f"{timestamp}.{body}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


@app.task(name="app_worker.tasks.webhooks.dispatch_webhook", queue="default")
def dispatch_webhook(webhook_id_str: str, event: str, payload: dict) -> None:
    """Send a signed HTTP POST to the registered webhook URL."""
    with Session(get_engine()) as session:
        webhook = session.get(Webhook, uuid.UUID(webhook_id_str))
        if not webhook or webhook.status != "active":
            return

        timestamp = str(int(datetime.now(UTC).timestamp()))
        body = json.dumps({"event": event, "timestamp": timestamp, "data": payload}, sort_keys=True)
        prefix = f"X-{BRAND['product_name']}"
        headers = {
            "Content-Type": "application/json",
            f"{prefix}-Event": event,
            f"{prefix}-Timestamp": timestamp,
            f"{prefix}-Signature": f"sha256={sign(webhook.secret, timestamp, body)}",
            "User-Agent": f"{BRAND['product_name']}-Webhooks/1.0",
        }

        status = 0
        try:
            with safe_requests_session(webhook.url) as http:
                resp = http.post(
                    webhook.url, data=body, headers=headers, timeout=10, allow_redirects=False
                )
            status = resp.status_code
            if status >= 300:
                logger.warning("Webhook %s returned %s for %s", webhook.id, status, event)
        except URLSafetyError as exc:
            logger.warning("Webhook %s blocked by SSRF protection: %s", webhook.id, exc)
        except Exception as exc:  # network errors: record and move on
            logger.warning("Webhook %s delivery failed: %s", webhook.id, exc)
        webhook.last_delivery_at = datetime.now(UTC)
        webhook.last_status_code = status
        session.commit()
