import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class Keyword(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "keywords"
    __table_args__ = (
        Index(
            "uq_keywords_identity",
            "site_id",
            func.lower(text("keyword")),
            "language",
            "country",
            func.coalesce(text("city"), text("''")),
            "device",
            unique=True,
        ),
        CheckConstraint("device IN ('desktop', 'mobile')", name="device"),
        CheckConstraint("status IN ('active', 'paused')", name="status"),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    keyword: Mapped[str] = mapped_column(String(300))
    language: Mapped[str] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    device: Mapped[str] = mapped_column(String(10), default="desktop")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")


class AiPrompt(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "ai_prompts"
    __table_args__ = (
        CheckConstraint(
            "intent IN ('informational', 'commercial', 'local', 'comparison', 'navigational')",
            name="intent",
        ),
        CheckConstraint("status IN ('active', 'paused')", name="status"),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    prompt_text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(2))
    intent: Mapped[str] = mapped_column(String(20), default="informational")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")
