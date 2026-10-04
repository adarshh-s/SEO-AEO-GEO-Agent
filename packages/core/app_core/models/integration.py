import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app_core.crypto import EncryptedJSON, EncryptedText
from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class ApiKey(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(20), index=True)
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=lambda: ["read:fixes"], server_default="{'read:fixes'}"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Webhook(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "webhooks"

    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(EncryptedText)  # HMAC signing secret, encrypted at rest
    events: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=lambda: ["fix.proposed", "fix.approved", "fix.deployed"],
        server_default="{'fix.proposed','fix.approved','fix.deployed'}",
    )
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    last_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SiteIntegration(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "site_integrations"
    __table_args__ = (
        UniqueConstraint("site_id", "provider", name="uq_site_integrations_site_provider"),
        CheckConstraint(
            "provider IN ('wordpress', 'shopify', 'github', 'cloudflare', 'google_search_console', 'webflow', 'wix')",
            name="site_integration_provider",
        ),
        CheckConstraint(
            "status IN ('active', 'error', 'pending', 'disconnected')",
            name="site_integration_status",
        ),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # OAuth tokens / API keys for the platform, encrypted at rest (CLAUDE.md §11).
    credentials: Mapped[dict] = mapped_column(EncryptedJSON, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
