import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
    events: list[str]
    status: str
    last_delivery_at: datetime | None
    last_status_code: int | None
    created_at: datetime


WebhookEvent = Literal[
    "fix.created",
    "fix.proposed",
    "fix.approved",
    "fix.rejected",
    "fix.deployed",
    "fix.rolled_back",
    "audit.triggered",
    "audit.completed",
    "report.generated",
    "score.changed",
]


class WebhookCreateIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    events: list[WebhookEvent] = Field(
        default_factory=lambda: ["fix.proposed", "fix.approved", "fix.deployed"], min_length=1
    )


class WebhookCreatedOut(WebhookOut):
    """Returned once at creation: the signing secret is never shown again."""

    secret: str


# --- Site Integrations ------------------------------------------------------------------------


class SiteIntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    provider: str
    status: str
    config: dict[str, Any]
    last_synced_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class SiteIntegrationCreateIn(BaseModel):
    provider: str
    config: dict[str, Any] = {}
    credentials: dict[str, Any] = {}


class SiteIntegrationUpdateIn(BaseModel):
    status: str | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None


class TestConnectionOut(BaseModel):
    ok: bool
    message: str
    details: dict[str, Any] = {}


class GscAuthUrlOut(BaseModel):
    auth_url: str


class GscConnectIn(BaseModel):
    code: str
    property_url: str
    redirect_uri: str


class GscPerformanceOut(BaseModel):
    property_url: str
    rows: list[dict[str, Any]]
