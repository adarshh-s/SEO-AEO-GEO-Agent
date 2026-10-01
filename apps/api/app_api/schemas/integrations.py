import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SnippetInfoOut(BaseModel):
    site_key: str
    script_url: str
    snippet_tag: str
    platform: str
    instructions: dict[str, str]  # platform-specific steps


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreateIn(BaseModel):
    name: str
    scopes: list[str] = ["read:fixes", "write:fixes"]


class ApiKeyCreatedOut(ApiKeyOut):
    raw_key: str  # Only returned once on creation


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    secret: str
    events: list[str]
    status: str
    last_delivery_at: datetime | None
    last_status_code: int | None
    created_at: datetime


class WebhookCreateIn(BaseModel):
    url: str
    events: list[str] = ["fix.proposed", "fix.approved", "fix.deployed"]
