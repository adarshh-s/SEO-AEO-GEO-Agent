import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk
from app_core.sanitize import sanitize_payload


class Fix(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "fixes"
    __table_args__ = (
        CheckConstraint(
            "type IN ('schema', 'meta', 'faq', 'content_block', 'technical')",
            name="fix_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'deployed', 'rejected', 'rolled_back')",
            name="fix_status",
        ),
        Index("ix_fixes_site_status", "site_id", "status"),
        Index("ix_fixes_site_url", "site_id", "target_url"),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(30), index=True
    )  # schema | meta | faq | content_block | technical
    target_url: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The actual payload (e.g. JSON-LD dictionary, meta title/description, FAQ items, HTML content)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    recommended_delivery: Mapped[str] = mapped_column(
        String(30), default="snippet"
    )  # snippet | wordpress | shopify | sdk | edge_worker | manual
    status: Mapped[str] = mapped_column(
        String(30), default="proposed", server_default="proposed", index=True
    )
    deployed_via: Mapped[str | None] = mapped_column(String(30), nullable=True)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Rollback snapshot: previous state of meta / schema / content
    previous_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # External reference (e.g. GitHub PR URL, Shopify mutation ID, WordPress post ID)
    external_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    @validates("payload")
    def _sanitize_payload(self, _key: str, value: dict) -> dict:
        """Every write path (worker generation, API edits) stores a sanitized payload."""
        return sanitize_payload(value or {})
