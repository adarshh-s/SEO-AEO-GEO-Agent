"""Onboarding detection and suggestions.

PHASE 1: these are deterministic MOCKS so the wizard works end to end without API keys.
Phase 2 replaces MockSiteAnalyzer with the real crawler (platform fingerprinting,
raw vs rendered HTML, languages, brand, competitors via DataForSEO with LLM fallback)
and TemplateSuggestionProvider with LLM + DataForSEO suggestions. Results carry
`source` so the UI can say when data is sample data.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app_core.enums import Platform, PromptIntent

_HOST_HINTS: list[tuple[str, Platform]] = [
    ("myshopify.com", Platform.SHOPIFY),
    ("wixsite.com", Platform.WIX),
    ("webflow.io", Platform.WEBFLOW),
    ("framer.website", Platform.FRAMER),
    ("framer.app", Platform.FRAMER),
    ("squarespace.com", Platform.SQUARESPACE),
    ("salla.sa", Platform.SALLA),
    ("zid.store", Platform.ZID),
    ("vercel.app", Platform.NEXTJS),
    ("netlify.app", Platform.STATIC),
    ("wordpress.com", Platform.WORDPRESS),
]


@dataclass
class Detection:
    source: str
    platform: Platform
    brand_name: str
    detected_languages: list[str]
    industry: str | None
    city: str | None
    country: str
    competitors: list[str] = field(default_factory=list)


class SiteAnalyzer(Protocol):
    def analyze(self, homepage_url: str, domain: str) -> Detection: ...


class MockSiteAnalyzer:
    def analyze(self, homepage_url: str, domain: str) -> Detection:
        platform = next((p for hint, p in _HOST_HINTS if domain.endswith(hint)), Platform.UNKNOWN)
        label = domain.split(".")[0].replace("-", " ").strip()
        is_saudi = (
            domain.endswith(".sa") or domain.endswith("salla.sa") or domain.endswith(".zid.store")
        )
        return Detection(
            source="mock",
            platform=platform,
            brand_name=label.title() or domain,
            # Languages *found on the site*; tracking languages are never pre-selected beyond English.
            detected_languages=["en", "ar"] if is_saudi else ["en"],
            industry=None,
            city="Riyadh" if is_saudi else None,
            country="SA" if is_saudi else "US",
            competitors=[],
        )


@dataclass
class Suggestion:
    text: str
    language: str
    intent: PromptIntent | None = None


class SuggestionProvider(Protocol):
    def keywords(
        self, *, brand: str, industry: str, city: str | None, languages: list[str]
    ) -> list[Suggestion]: ...

    def prompts(
        self, *, brand: str, industry: str, city: str | None, languages: list[str]
    ) -> list[Suggestion]: ...


_KW_EN = [
    "{industry}",
    "best {industry}{in_city}",
    "{industry} near me",
    "{brand}",
    "{brand} reviews",
    "affordable {industry}{in_city}",
    "top rated {industry}{in_city}",
    "{industry} prices{in_city}",
]
_KW_AR = [
    "{brand}",
    "أفضل {industry}{in_city_ar}",
    "{industry} قريب مني",
    "تقييمات {brand}",
    "أسعار {industry}{in_city_ar}",
]
_PR_EN = [
    ("What is the best {industry}{in_city}?", PromptIntent.LOCAL),
    ("Can you recommend a reliable {industry}{in_city}?", PromptIntent.LOCAL),
    ("Which {industry} has the best reviews{in_city}?", PromptIntent.COMMERCIAL),
    ("How much does a {industry} usually cost{in_city}?", PromptIntent.INFORMATIONAL),
    ("What should I look for when choosing a {industry}?", PromptIntent.INFORMATIONAL),
    ("Is {brand} a good choice for {industry}?", PromptIntent.NAVIGATIONAL),
    ("Compare the top {industry} options{in_city}.", PromptIntent.COMPARISON),
    ("What are good alternatives to {brand}?", PromptIntent.COMPARISON),
    ("Which {industry} is open late{in_city}?", PromptIntent.LOCAL),
    ("What do customers say about {brand}?", PromptIntent.NAVIGATIONAL),
]
_PR_AR = [
    ("ما هو أفضل {industry}{in_city_ar}؟", PromptIntent.LOCAL),
    ("هل تنصحني بـ {industry} موثوق{in_city_ar}؟", PromptIntent.LOCAL),
    ("كم تبلغ تكلفة {industry} عادةً{in_city_ar}؟", PromptIntent.INFORMATIONAL),
    ("هل {brand} خيار جيد؟", PromptIntent.NAVIGATIONAL),
    ("ما هي البدائل الجيدة لـ {brand}؟", PromptIntent.COMPARISON),
]


class TemplateSuggestionProvider:
    """Mock suggestions from fixed templates (English, plus Arabic only if enabled)."""

    def _fill(self, template: str, brand: str, industry: str, city: str | None) -> str:
        return template.format(
            brand=brand,
            industry=industry,
            in_city=f" in {city}" if city else "",
            in_city_ar=f" في {city}" if city else "",
        )

    def keywords(
        self, *, brand: str, industry: str, city: str | None, languages: list[str]
    ) -> list[Suggestion]:
        out = (
            [Suggestion(self._fill(t, brand, industry, city), "en") for t in _KW_EN]
            if "en" in languages
            else []
        )
        if "ar" in languages:
            out += [Suggestion(self._fill(t, brand, industry, city), "ar") for t in _KW_AR]
        return out

    def prompts(
        self, *, brand: str, industry: str, city: str | None, languages: list[str]
    ) -> list[Suggestion]:
        out = (
            [Suggestion(self._fill(t, brand, industry, city), "en", i) for t, i in _PR_EN]
            if "en" in languages
            else []
        )
        if "ar" in languages:
            out += [Suggestion(self._fill(t, brand, industry, city), "ar", i) for t, i in _PR_AR]
        return out


def get_site_analyzer() -> SiteAnalyzer:
    return MockSiteAnalyzer()


def get_suggestion_provider() -> SuggestionProvider:
    return TemplateSuggestionProvider()
