import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FixOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    diagnosis_id: uuid.UUID | None
    type: str  # schema | meta | faq | content_block | technical
    target_url: str
    language: str
    title: str
    description: str | None
    payload: dict[str, Any]
    recommended_delivery: str
    status: str  # draft | proposed | approved | deployed | rejected | rolled_back
    deployed_via: str | None
    deployed_at: datetime | None
    previous_state: dict[str, Any] | None
    external_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class FixUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    payload: dict[str, Any] | None = None


class FixDeployIn(BaseModel):
    deployed_via: str = "snippet"
    previous_state: dict[str, Any] | None = None
