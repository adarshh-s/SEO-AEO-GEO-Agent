import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app_api.schemas.common import ApiModel
from app_core.enums import Platform, PromptIntent, Rendering
from app_core.languages import SUPPORTED_SITE_LANGUAGES

LangCode = str


def _check_lang(v: str) -> str:
    v = v.strip().lower()
    if v not in SUPPORTED_SITE_LANGUAGES:
        raise ValueError(f"unsupported language '{v}'")
    return v


def _check_country(v: str) -> str:
    v = v.strip().upper()
    if len(v) != 2 or not v.isalpha():
        raise ValueError("country must be a 2-letter ISO code")
    return v


class SiteBase(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    platform: Platform = Platform.UNKNOWN
    platform_confirmed: bool = False
    primary_language: LangCode = "en"
    additional_languages: list[LangCode] = Field(default_factory=list, max_length=6)
    default_country: str = "US"
    default_city: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    brand_names: dict[LangCode, list[str]] = Field(default_factory=dict)
    competitor_domains: list[str] = Field(default_factory=list, max_length=20)

    _lang = field_validator("primary_language")(_check_lang)
    _country = field_validator("default_country")(_check_country)

    @field_validator("additional_languages")
    @classmethod
    def _langs(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(_check_lang(x) for x in v))

    @field_validator("brand_names")
    @classmethod
    def _brands(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for lang, names in v.items():
            cleaned = [n.strip()[:120] for n in names if n and n.strip()][:10]
            if cleaned:
                out[_check_lang(lang)] = cleaned
        return out


class SiteCreateIn(SiteBase):
    homepage_url: str = Field(min_length=3, max_length=2000)


class SiteUpdateIn(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: Platform | None = None
    platform_confirmed: bool | None = None
    primary_language: LangCode | None = None
    additional_languages: list[LangCode] | None = Field(default=None, max_length=6)
    default_country: str | None = None
    default_city: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    brand_names: dict[LangCode, list[str]] | None = None
    competitor_domains: list[str] | None = Field(default=None, max_length=20)

    @field_validator("primary_language")
    @classmethod
    def _lang(cls, v: str | None) -> str | None:
        return _check_lang(v) if v else v

    @field_validator("additional_languages")
    @classmethod
    def _langs(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else list(dict.fromkeys(_check_lang(x) for x in v))

    @field_validator("default_country")
    @classmethod
    def _country(cls, v: str | None) -> str | None:
        return _check_country(v) if v else v

    @field_validator("brand_names")
    @classmethod
    def _brands(cls, v: dict[str, list[str]] | None) -> dict[str, list[str]] | None:
        return None if v is None else SiteBase._brands(v)


class SiteOut(ApiModel):
    id: uuid.UUID
    name: str
    domain: str
    homepage_url: str
    platform: str
    platform_confirmed: bool
    rendering: Rendering | str
    primary_language: str
    additional_languages: list[str]
    default_country: str
    default_city: str | None
    industry: str | None
    brand_names: dict[str, list[str]]
    competitor_domains: list[str]
    site_key: str
    verification_token: str
    verification_method: str | None
    verified_at: datetime | None
    created_at: datetime


class KeywordIn(ApiModel):
    keyword: str = Field(min_length=1, max_length=300)
    language: LangCode
    country: str | None = None
    city: str | None = Field(default=None, max_length=120)
    device: Literal["desktop", "mobile"] = "desktop"
    tags: list[str] = Field(default_factory=list, max_length=10)

    _lang = field_validator("language")(_check_lang)

    @field_validator("country")
    @classmethod
    def _country(cls, v: str | None) -> str | None:
        return _check_country(v) if v else v


class KeywordOut(ApiModel):
    id: uuid.UUID
    site_id: uuid.UUID
    keyword: str
    language: str
    country: str
    city: str | None
    device: str
    tags: list[str]
    status: str
    created_at: datetime


class PromptIn(ApiModel):
    prompt_text: str = Field(min_length=3, max_length=1000)
    language: LangCode
    country: str | None = None
    intent: PromptIntent = PromptIntent.INFORMATIONAL
    tags: list[str] = Field(default_factory=list, max_length=10)

    _lang = field_validator("language")(_check_lang)

    @field_validator("country")
    @classmethod
    def _country(cls, v: str | None) -> str | None:
        return _check_country(v) if v else v


class PromptOut(ApiModel):
    id: uuid.UUID
    site_id: uuid.UUID
    prompt_text: str
    language: str
    country: str
    intent: str
    tags: list[str]
    status: str
    created_at: datetime


class StatusIn(ApiModel):
    status: Literal["active", "paused"]


class BulkKeywordsIn(ApiModel):
    items: list[KeywordIn] = Field(min_length=1, max_length=500)


class BulkPromptsIn(ApiModel):
    items: list[PromptIn] = Field(min_length=1, max_length=200)


class BulkResult(ApiModel):
    created: int
    skipped_duplicates: int
