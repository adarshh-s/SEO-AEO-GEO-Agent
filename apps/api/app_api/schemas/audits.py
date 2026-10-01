import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    status: str
    score: int
    category_scores: dict[str, int]
    summary: dict[str, int]
    pages_crawled: int
    created_at: datetime
    completed_at: datetime | None = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    status: str
    score: int
    category_scores: dict[str, int]
    issues: list[dict[str, Any]]
    summary: dict[str, int]
    pages_crawled: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


class TriggerAuditOut(BaseModel):
    audit_id: uuid.UUID
    status: str
    message: str
