import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app_core.db import Base
from app_core.enums import Platform, Rendering
from app_core.models.base import OrgOwned, Timestamps, UUIDPk


class Site(UUIDPk, OrgOwned, Timestamps, Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("org_id", "domain", name="uq_sites_org_domain"),
        CheckConstraint(
            "platform IN (" + ", ".join(f"'{p.value}'" for p in Platform) + ")", name="platform"
        ),
        CheckConstraint(
            "rendering IN (" + ", ".join(f"'{r.value}'" for r in Rendering) + ")", name="rendering"
        ),
    )

    domain: Mapped[str] = mapped_column(String(253))  # normalized host, e.g. example.com
    name: Mapped[str] = mapped_column(String(200))
    homepage_url: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(30), default="unknown")
    platform_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    rendering: Mapped[str] = mapped_column(String(20), default="unknown")
    primary_language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    additional_languages: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)), default=list, server_default="{}"
    )
    default_country: Mapped[str] = mapped_column(String(2), default="US")  # ISO 3166-1 alpha-2
    default_city: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(120))
    # {"en": ["Acme Dental"], "ar": ["عيادة أكمي"]}
    brand_names: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    competitor_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String(253)), default=list, server_default="{}"
    )
    # Public, read-only key used by the snippet/SDK. Not a secret.
    site_key: Mapped[str] = mapped_column(String(64), unique=True)
    verification_token: Mapped[str] = mapped_column(String(64))
    verification_method: Mapped[str | None] = mapped_column(String(30))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    @property
    def languages(self) -> list[str]:
        return [
            self.primary_language,
            *[x for x in self.additional_languages if x != self.primary_language],
        ]
