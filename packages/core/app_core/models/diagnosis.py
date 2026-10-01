import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class Diagnosis(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('keyword', 'prompt')",
            name="diagnosis_target_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="diagnosis_status",
        ),
        Index("ix_diagnoses_site_target", "site_id", "target_type", "target_id"),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    target_type: Mapped[str] = mapped_column(String(20))  # keyword | prompt
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    # Structured findings: gaps in schema, content, meta tags, js-only, robots.txt
    findings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # Top competitor pages analyzed: url, title, word_count, schemas
    competitor_pages: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
