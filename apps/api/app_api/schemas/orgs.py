import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import EmailStr, Field

from app_api.schemas.common import ApiModel

InvitableRole = Literal["admin", "member", "viewer"]
AnyRole = Literal["owner", "admin", "member", "viewer"]


class PlanOut(ApiModel):
    code: str
    name: str
    sort_order: int
    is_public: bool
    max_sites: int
    max_keywords: int
    max_prompts: int
    max_engines: int
    allowed_engines: list[str]
    max_languages_per_site: int
    addon_languages: list[str]
    check_frequency: str
    audits_per_month: int
    trial_days: int | None


class UsageOut(ApiModel):
    sites: int
    keywords: int
    prompts: int


class OrgOut(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    role: str
    plan: PlanOut
    addons: dict
    usage: UsageOut


class OrgCreateIn(ApiModel):
    name: str = Field(min_length=1, max_length=200)


class OrgUpdateIn(ApiModel):
    name: str = Field(min_length=1, max_length=200)


class MemberOut(ApiModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    created_at: datetime


class MemberUpdateIn(ApiModel):
    role: AnyRole


class InvitationIn(ApiModel):
    email: EmailStr
    role: InvitableRole = "member"


class InvitationOut(ApiModel):
    id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None


class AdminOrgOut(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    plan_code: str
    addons: dict
    cost_ceiling_override_usd: Decimal | None
    members: int
    sites: int
    created_at: datetime


class AdminSetPlanIn(ApiModel):
    plan_code: str = Field(max_length=40)


class AdminOrgUpdateIn(ApiModel):
    addons: dict[str, bool] | None = None
    cost_ceiling_override_usd: Decimal | None = Field(default=None, ge=0, le=100000)


class AdminPlanUpdateIn(ApiModel):
    name: str | None = Field(default=None, max_length=80)
    is_public: bool | None = None
    max_sites: int | None = Field(default=None, ge=0)
    max_keywords: int | None = Field(default=None, ge=0)
    max_prompts: int | None = Field(default=None, ge=0)
    max_engines: int | None = Field(default=None, ge=0)
    allowed_engines: list[str] | None = None
    max_languages_per_site: int | None = Field(default=None, ge=1)
    addon_languages: list[str] | None = None
    check_frequency: Literal["weekly", "twice_weekly", "daily"] | None = None
    audits_per_month: int | None = Field(default=None, ge=0)
    monthly_cost_ceiling_usd: Decimal | None = Field(default=None, ge=0)
    trial_days: int | None = Field(default=None, ge=0)
