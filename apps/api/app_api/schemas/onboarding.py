from pydantic import Field, field_validator

from app_api.schemas.common import ApiModel
from app_api.schemas.sites import KeywordIn, PromptIn, SiteCreateIn, _check_lang


class AnalyzeIn(ApiModel):
    url: str = Field(min_length=3, max_length=2000)


class AnalyzeOut(ApiModel):
    source: str
    homepage_url: str
    domain: str
    platform: str
    brand_name: str
    detected_languages: list[str]
    industry: str | None
    city: str | None
    country: str
    competitors: list[str]
    summary: str | None = None
    # "unreachable" | "ai_unavailable" | "ai_failed" | "budget" — why some fields are empty
    notice: str | None = None


class SuggestIn(ApiModel):
    brand_name: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=2)
    site_summary: str | None = Field(default=None, max_length=2000)
    languages: list[str] = Field(min_length=1, max_length=6)

    @field_validator("languages")
    @classmethod
    def _langs(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(_check_lang(x) for x in v))


class SuggestedKeyword(ApiModel):
    keyword: str
    language: str


class SuggestedPrompt(ApiModel):
    prompt_text: str
    language: str
    intent: str


class SuggestOut(ApiModel):
    source: str
    keywords: list[SuggestedKeyword]
    prompts: list[SuggestedPrompt]


class CompleteIn(ApiModel):
    site: SiteCreateIn
    keywords: list[KeywordIn] = Field(default_factory=list, max_length=500)
    prompts: list[PromptIn] = Field(default_factory=list, max_length=200)
