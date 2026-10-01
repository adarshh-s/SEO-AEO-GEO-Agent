import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

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
    secret: Mapped[str] = mapped_column(String(64))  # HMAC signing secret
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
