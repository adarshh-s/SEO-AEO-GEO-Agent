import uuid

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class Report(UUIDPk, OrgOwned, Timestamps, Base):
    """Generated PDF report or executive summary for a website."""

    __tablename__ = "reports"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        index=True,
    )
    audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audits.id", ondelete="SET NULL"),
        nullable=True,
    )
    report_type: Mapped[str] = mapped_column(
        String(40), default="audit"
    )  # audit, weekly_digest, executive_summary
    title: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[str] = mapped_column(
        String(30), default="completed"
    )  # generating, completed, failed
    metrics_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    # e.g. {"overall_score": 84, "rankings_top_10": 14, "ai_citations": 68, "fixes_deployed": 5}
    pdf_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    site = relationship("Site", back_populates="reports", lazy="joined")
    audit = relationship("Audit", lazy="joined")
