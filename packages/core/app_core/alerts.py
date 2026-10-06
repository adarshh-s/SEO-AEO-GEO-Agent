"""Cost-ceiling alert emails (decision C4).

When an org's monthly API spend crosses 80% and 100% of its ceiling, email its owners and
admins plus the platform operator (OPS_ALERT_EMAIL). Each level is sent once per org per
month (de-duplicated in Redis). Failures are logged and never block the cost check.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Literal

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app_core.email import Email, get_email_provider
from app_core.i18n import t
from app_core.logging import get_logger
from app_core.models import Membership, Organization, User
from app_core.settings import get_settings

log = get_logger(__name__)
Level = Literal[80, 100]
DEDUPE_SECONDS = 40 * 24 * 3600  # longer than a month: one alert per level per period


@lru_cache
def redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def _recipients(db: Session, org: Organization) -> list[tuple[str, str]]:
    """(email, ui_language) for the org's owners/admins, plus the operator."""
    rows = db.execute(
        select(User.email, User.ui_language)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == org.id, Membership.role.in_(["owner", "admin"]))
    ).all()
    out = [(e, lang or "en") for e, lang in rows]
    ops = get_settings().ops_alert_email
    if ops and ops not in {e for e, _ in out}:
        out.append((ops, "en"))
    return out


def maybe_send_cost_alert(
    db: Session,
    org: Organization,
    *,
    level: Level,
    spend: Decimal,
    ceiling: Decimal,
    period_start: datetime,
) -> bool:
    """Send the alert for this level unless it was already sent this period. True if sent."""
    try:
        key = f"cost-alert:{org.id}:{period_start:%Y-%m}:{level}"
        if not redis_client().set(key, "1", nx=True, ex=DEDUPE_SECONDS):
            return False
        provider = get_email_provider()
        for email, lang in _recipients(db, org):
            provider.send(
                Email(
                    to=email,
                    subject=t(lang, f"email.cost{level}.subject", org=org.name),
                    text=t(
                        lang,
                        f"email.cost{level}.body",
                        org=org.name,
                        spend=f"{spend:.2f}",
                        ceiling=f"{ceiling:.2f}",
                    ),
                )
            )
        log.info("cost_alert.sent", org_id=str(org.id), level=level)
        return True
    except Exception as exc:  # alerts must never break the cost check itself
        log.warning("cost_alert.failed", org_id=str(org.id), level=level, error=str(exc)[:200])
        return False
