"""Append-only audit log (who approved/changed what)."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app_core.models import AuditLogEntry


def record(
    db: Session,
    action: str,
    *,
    org_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    data: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLogEntry(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            data=data or {},
            ip=ip,
        )
    )
