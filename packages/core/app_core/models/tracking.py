import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
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


class CrawlSnapshot(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "crawl_snapshots"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    http_status: Mapped[int] = mapped_column(default=200)
    raw_html_hash: Mapped[str] = mapped_column(String(64))
    rendered_html_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    js_only_content_detected: Mapped[bool] = mapped_column(default=False)
    js_only_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_robots_allowed: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class RankCheck(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "rank_checks"

    keyword_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("keywords.id", ondelete="CASCADE"), index=True
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
    position: Mapped[int | None] = mapped_column(nullable=True)
    previous_position: Mapped[int | None] = mapped_column(nullable=True)
    url_ranked: Mapped[str | None] = mapped_column(Text, nullable=True)
    serp_features: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    ai_overview_present: Mapped[bool] = mapped_column(default=False)
    ai_overview_cites_site: Mapped[bool] = mapped_column(default=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AiCheck(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "ai_checks"
    __table_args__ = (
        CheckConstraint(
            "sentiment IN ('positive', 'neutral', 'negative')",
            name="sentiment",
        ),
    )

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_prompts.id", ondelete="CASCADE"), index=True
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    engine: Mapped[str] = mapped_column(
        String(20), index=True
    )  # chatgpt | gemini | perplexity | claude
    model: Mapped[str] = mapped_column(String(80))
    run_index: Mapped[int] = mapped_column(default=0)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
    raw_answer: Mapped[str] = mapped_column(Text)
    brand_mentioned: Mapped[bool] = mapped_column(default=False)
    mention_position: Mapped[int | None] = mapped_column(nullable=True)
    site_cited: Mapped[bool] = mapped_column(default=False)
    cited_urls: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    competitors_mentioned: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")


class VisibilityScore(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "visibility_scores"
    __table_args__ = (
        Index("uq_visibility_scores_site_date_lang", "site_id", "date", "language", unique=True),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    seo_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"))
    ai_share_of_voice: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"))
    per_engine: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class AiReferralEvent(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "ai_referral_events"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    referrer_engine: Mapped[str] = mapped_column(
        String(40), index=True
    )  # chatgpt | perplexity | gemini | claude | other_ai
    user_agent_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
