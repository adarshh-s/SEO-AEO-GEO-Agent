"""Onboarding: analyze a real website and suggest keywords / AI questions.

analyze_site():
  1. fetch the homepage (SSRF-safe, thread-safe: app_core.net) with our crawler UA;
  2. fingerprint the platform and extract page facts (title, schema.org, lang, text);
  3. if Claude is configured: identify brand, industry, city, country, likely competitors
     and a short summary from those facts (fast model, structured output).
suggest():
  Claude writes realistic Google keywords and customer questions from the site summary,
  only in the site's enabled languages. Without Claude: fixed templates, labelled as such.

`source` tells the UI what the data is: "live+ai", "live" (facts only), "unreachable"
(site couldn't be fetched; hostname hints only) or "template" (suggestions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app_core import llm
from app_core.brand import crawler_user_agent
from app_core.enums import Platform, PromptIntent
from app_core.logging import get_logger
from app_core.net import UnsafeUrlError, safe_get
from app_core.page_facts import PageFacts, extract_page_facts
from app_core.platform_detect import detect_platform_from
from app_core.providers.ai_answer import ProviderNotConfigured
from app_core.settings import get_settings

log = get_logger(__name__)

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
_TLD_COUNTRY = {
    "sa": "SA", "ae": "AE", "kw": "KW", "qa": "QA", "bh": "BH", "om": "OM", "eg": "EG",
    "jo": "JO", "uk": "GB", "ca": "CA", "au": "AU", "in": "IN", "pk": "PK", "tr": "TR",
    "de": "DE", "fr": "FR", "es": "ES", "it": "IT", "nl": "NL", "ie": "IE", "nz": "NZ",
    "sg": "SG", "my": "MY",
}  # fmt: skip


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
    summary: str | None = None
    notice: str | None = None
    cost_usd: Decimal = Decimal(0)


class SiteProfile(BaseModel):
    """What Claude infers from the homepage facts."""

    brand_name: str = Field(description="The business/brand name customers would use")
    industry: str = Field(description="2-5 words in English, e.g. 'family dental clinic'")
    city: str | None = Field(description="Main city served, if the site makes it clear")
    country_code: str | None = Field(description="ISO 3166-1 alpha-2 of the main market")
    business_type: Literal["local", "ecommerce", "saas", "publisher", "services", "other"]
    summary: str = Field(description="2-3 sentences: what they offer, to whom, where")
    competitor_domains: list[str] = Field(
        description="Up to 5 domains of real, well-known direct competitors in the same market. "
        "Only include domains you are confident exist; return an empty list otherwise."
    )


def _hostname_platform(domain: str) -> Platform:
    return next((p for hint, p in _HOST_HINTS if domain.endswith(hint)), Platform.UNKNOWN)


def _country_guess(domain: str, facts: PageFacts | None) -> str:
    raw = (facts.schema_country or "") if facts else ""
    if len(raw) == 2 and raw.isalpha():
        return raw.upper()
    return _TLD_COUNTRY.get(domain.rsplit(".", 1)[-1], "US")


def _languages(facts: PageFacts) -> list[str]:
    langs: list[str] = []
    if facts.html_lang:
        langs.append(facts.html_lang.split("-")[0].lower())
    if any("؀" <= ch <= "ۿ" for ch in facts.text[:5000]):
        langs.append("ar")
    langs.extend(facts.hreflang_langs)
    return list(dict.fromkeys(langs)) or ["en"]


def fetch_homepage(homepage_url: str) -> tuple[str, dict[str, str], str]:
    ua = crawler_user_agent(f"{get_settings().app_url}/bot")
    resp = safe_get(homepage_url, timeout=15, headers={"User-Agent": ua, "Accept": "text/html"})
    resp.raise_for_status()
    return resp.text, dict(resp.headers), resp.url


def analyze_site(homepage_url: str, domain: str, *, use_ai: bool) -> Detection:
    try:
        html, headers, final_url = fetch_homepage(homepage_url)
    except (UnsafeUrlError, Exception) as exc:  # unreachable / blocked / non-2xx
        log.info("onboarding.fetch_failed", domain=domain, error=str(exc)[:200])
        return Detection(
            source="unreachable",
            platform=_hostname_platform(domain),
            brand_name=domain.split(".")[0].replace("-", " ").title(),
            detected_languages=["en"],
            industry=None,
            city=None,
            country=_country_guess(domain, None),
            notice="unreachable",
        )

    facts = extract_page_facts(html)
    platform = detect_platform_from(html, headers, final_url).platform
    if platform == Platform.UNKNOWN:
        platform = _hostname_platform(domain)
    detection = Detection(
        source="live",
        platform=platform,
        brand_name=facts.site_name or (facts.title or domain).split("|")[0].split(" - ")[0].strip(),
        detected_languages=_languages(facts),
        industry=None,
        city=facts.schema_city,
        country=_country_guess(domain, facts),
    )
    if not use_ai:
        detection.notice = "ai_unavailable"
        return detection
    try:
        result = llm.parse(
            role="fast",
            system=(
                "You identify a business from its homepage for an SEO and AI-visibility tool. "
                "Be factual; when the page doesn't say something, return null rather than guess."
            ),
            user=(
                f"Website: {final_url}\nDetected platform: {platform.value}\n\n"
                + llm.untrusted("homepage", facts.as_prompt())
            ),
            output=SiteProfile,
            max_tokens=2000,
        )
    except ProviderNotConfigured:
        detection.notice = "ai_unavailable"
        return detection
    except Exception as exc:  # API error / refusal: keep the facts we have
        log.warning("onboarding.ai_failed", domain=domain, error=str(exc)[:200])
        detection.notice = "ai_failed"
        return detection

    p = result.value
    detection.source = "live+ai"
    detection.brand_name = p.brand_name or detection.brand_name
    detection.industry = p.industry
    detection.city = p.city or detection.city
    if p.country_code and len(p.country_code) == 2:
        detection.country = p.country_code.upper()
    detection.summary = p.summary
    detection.competitors = [d.lower().removeprefix("www.") for d in p.competitor_domains][:5]
    detection.cost_usd = result.cost_usd
    return detection


# --- suggestions -----------------------------------------------------------------------------


class KeywordSuggestion(BaseModel):
    keyword: str
    language: str = Field(description="ISO 639-1 code, one of the requested languages")


class PromptSuggestion(BaseModel):
    prompt_text: str
    language: str = Field(description="ISO 639-1 code, one of the requested languages")
    intent: Literal["informational", "commercial", "local", "comparison", "navigational"]


class SuggestionSet(BaseModel):
    keywords: list[KeywordSuggestion]
    prompts: list[PromptSuggestion]


@dataclass
class Suggestion:
    text: str
    language: str
    intent: PromptIntent | None = None


@dataclass
class Suggestions:
    source: str
    keywords: list[Suggestion]
    prompts: list[Suggestion]
    cost_usd: Decimal = Decimal(0)


def suggest(
    *,
    brand: str,
    industry: str,
    city: str | None,
    country: str | None,
    languages: list[str],
    summary: str | None,
    use_ai: bool,
) -> Suggestions:
    if use_ai:
        try:
            return _ai_suggestions(brand, industry, city, country, languages, summary)
        except ProviderNotConfigured:
            pass
        except Exception as exc:
            log.warning("onboarding.suggest_failed", error=str(exc)[:200])
    t = TemplateSuggestionProvider()
    return Suggestions(
        "template",
        t.keywords(brand=brand, industry=industry, city=city, languages=languages),
        t.prompts(brand=brand, industry=industry, city=city, languages=languages),
    )


def _ai_suggestions(
    brand: str, industry: str, city: str | None, country: str | None, languages: list[str],
    summary: str | None,
) -> Suggestions:  # fmt: skip
    result = llm.parse(
        role="fast",
        system=(
            "You plan rank tracking and AI-visibility tracking for a business. Write what real "
            "customers type into Google and ask AI assistants (ChatGPT, Gemini, Perplexity, "
            "Claude) when looking for what this business offers. Mix intents: local, commercial, "
            "comparison, informational, and a few that mention the brand. Most should NOT name "
            "the brand: the goal is to see whether assistants recommend it unprompted. Write each "
            "language natively (not word-for-word translations)."
        ),
        user=(
            f"Brand: {brand}\nIndustry: {industry}\nCity: {city or 'not specific'}\n"
            f"Country: {country or 'unknown'}\nLanguages: {', '.join(languages)}\n\n"
            + llm.untrusted("site summary", summary or "(no summary)")
            + "\n\nFor EACH language: 15 Google keywords (2-6 words) and 30 AI questions "
            "(full natural sentences)."
        ),
        output=SuggestionSet,
        max_tokens=12000,
    )
    allowed = set(languages)
    kws = [Suggestion(k.keyword.strip(), k.language) for k in result.value.keywords
           if k.language in allowed and k.keyword.strip()]  # fmt: skip
    prs = [Suggestion(p.prompt_text.strip(), p.language, PromptIntent(p.intent))
           for p in result.value.prompts if p.language in allowed and p.prompt_text.strip()]  # fmt: skip
    return Suggestions("ai", _dedupe(kws), _dedupe(prs), result.cost_usd)


def _dedupe(items: list[Suggestion]) -> list[Suggestion]:
    seen: set[tuple[str, str]] = set()
    out = []
    for s in items:
        key = (s.text.lower(), s.language)
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


# --- offline fallback: fixed templates (shown to the user as examples) ------------------------

_KW_EN = ["{industry}", "best {industry}{in_city}", "{industry} near me", "{brand}",
          "{brand} reviews", "affordable {industry}{in_city}", "top rated {industry}{in_city}",
          "{industry} prices{in_city}"]  # fmt: skip
_KW_AR = ["{brand}", "أفضل {industry}{in_city_ar}", "{industry} قريب مني", "تقييمات {brand}",
          "أسعار {industry}{in_city_ar}"]  # fmt: skip
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
    """Fixed templates (English, plus Arabic only if enabled) used when Claude is unavailable."""

    def _fill(self, template: str, brand: str, industry: str, city: str | None) -> str:
        return template.format(
            brand=brand, industry=industry, in_city=f" in {city}" if city else "",
            in_city_ar=f" في {city}" if city else "",
        )  # fmt: skip

    def keywords(self, *, brand: str, industry: str, city: str | None, languages: list[str]) -> list[Suggestion]:  # fmt: skip
        out = [Suggestion(self._fill(t, brand, industry, city), "en") for t in _KW_EN] if "en" in languages else []  # fmt: skip
        if "ar" in languages:
            out += [Suggestion(self._fill(t, brand, industry, city), "ar") for t in _KW_AR]
        return out

    def prompts(self, *, brand: str, industry: str, city: str | None, languages: list[str]) -> list[Suggestion]:  # fmt: skip
        out = [Suggestion(self._fill(t, brand, industry, city), "en", i) for t, i in _PR_EN] if "en" in languages else []  # fmt: skip
        if "ar" in languages:
            out += [Suggestion(self._fill(t, brand, industry, city), "ar", i) for t, i in _PR_AR]
        return out
