import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisTriggerIn(BaseModel):
    target_type: str = Field(pattern="^(keyword|prompt)$")
    target_id: uuid.UUID


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    status: str
    findings: dict[str, Any]
    competitor_pages: list[dict[str, Any]]
    error: str | None
    completed_at: datetime | None
    created_at: datetime
