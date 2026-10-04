import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class Audit(UUIDPk, OrgOwned, Timestamps, Base):
    """Full website technical, content, AEO, and performance audit."""

    __tablename__ = "audits"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending", index=True
    )  # pending, running, completed, failed
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 overall score
    category_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    # e.g. {"technical": 85, "content": 80, "ai_readiness": 90, "performance": 75}
    issues: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    # list of findings: [{id, category, severity, title: {en, ar}, description: {en, ar}, recommendation: {en, ar}, affected_urls, passed, fixable}]
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    # e.g. {"total_issues": 12, "critical": 1, "high": 3, "medium": 5, "low": 3, "passed_checks": 24}
    pages_crawled: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    site = relationship("Site", back_populates="audits", lazy="joined")
