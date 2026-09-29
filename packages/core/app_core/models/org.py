import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app_core.db import Base
from app_core.models.base import OrgOwned, Timestamps, UUIDPk
from app_core.models.plan import Plan
from app_core.models.user import User


class Organization(UUIDPk, Timestamps, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    # D20: plans are assigned manually until Phase 7 billing.
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"))
    plan_assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # Add-ons granted by a platform admin, e.g. {"arabic": true} for Starter's Arabic add-on.
    addons: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # Admin override of the plan's monthly cost ceiling (decision C4).
    cost_ceiling_override_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    plan: Mapped[Plan] = relationship(lazy="joined")


class Membership(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_memberships_org_user"),
        CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))

    user: Mapped[User] = relationship(lazy="joined")


class Invitation(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "invitations"
    __table_args__ = (CheckConstraint("role IN ('admin', 'member', 'viewer')", name="role"),)

    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
