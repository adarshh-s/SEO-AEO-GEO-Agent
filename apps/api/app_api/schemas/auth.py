import uuid
from typing import Literal

from pydantic import EmailStr, Field

from app_api.schemas.common import ApiModel

UiLanguage = Literal["en", "ar"]


class SignupIn(ApiModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)
    org_name: str | None = Field(default=None, max_length=200)
    ui_language: UiLanguage = "en"


class LoginIn(ApiModel):
    email: EmailStr
    password: str = Field(max_length=200)


class EmailIn(ApiModel):
    email: EmailStr


class TokenIn(ApiModel):
    token: str = Field(max_length=2000)


class PasswordResetIn(ApiModel):
    token: str = Field(max_length=2000)
    password: str = Field(min_length=10, max_length=200)


class UserOut(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str
    ui_language: str
    is_platform_admin: bool
    email_verified: bool
    has_password: bool


class OrgSummary(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    role: str
    plan_code: str


class SessionOut(ApiModel):
    user: UserOut
    orgs: list[OrgSummary]
    csrf_token: str


class MeUpdateIn(ApiModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    ui_language: UiLanguage | None = None
