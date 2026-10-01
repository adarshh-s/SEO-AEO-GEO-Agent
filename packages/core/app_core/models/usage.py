from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class UsageCounter(UUIDPk, OrgOwned, Timestamps, Base):
    """Monthly usage and API cost rollup per org, category and provider."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "period_start",
            "category",
            "provider",
            name="uq_usage_counters_org_period_cat_prov",
        ),
    )

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    category: Mapped[str] = mapped_column(String(40), index=True)  # serp | ai_check | crawl | audit
    provider: Mapped[str] = mapped_column(
        String(40), index=True
    )  # dataforseo | openai | gemini | perplexity | anthropic
    units: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0000"))
