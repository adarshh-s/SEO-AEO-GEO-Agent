import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class Plan(UUIDPk, Timestamps, Base):
    """Plan limits. Placeholder values (CLAUDE.md §12), editable in DB / admin."""

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)  # shown on the pricing page
    max_sites: Mapped[int] = mapped_column(Integer)
    max_keywords: Mapped[int] = mapped_column(Integer)
    max_prompts: Mapped[int] = mapped_column(Integer)
    max_engines: Mapped[int] = mapped_column(Integer)
    allowed_engines: Mapped[list[str]] = mapped_column(ARRAY(String(20)))
    max_languages_per_site: Mapped[int] = mapped_column(Integer)
    # Languages that may be added beyond the limit when the org has that add-on (Starter: Arabic).
    addon_languages: Mapped[list[str]] = mapped_column(ARRAY(String(10)), default=list)
    check_frequency: Mapped[str] = mapped_column(String(20))
    audits_per_month: Mapped[int] = mapped_column(Integer)
    # D14: real values set after Phase 2 cost measurement.
    monthly_cost_ceiling_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    trial_days: Mapped[int | None] = mapped_column(Integer)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)


class Subscription(UUIDPk, OrgOwned, Timestamps, Base):
    """Placeholder for Phase 7 billing (D20). No provider writes to it yet."""

    __tablename__ = "subscriptions"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"))
    provider: Mapped[str | None] = mapped_column(String(40))  # moyasar | tap | stripe (Phase 7)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="inactive")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
