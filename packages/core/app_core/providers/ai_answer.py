"""Multi-engine AI visibility providers (OpenAI, Gemini, Perplexity, Claude, Mock)."""

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app_core.enums import AnswerEngineId
from app_core.settings import get_settings


class ProviderNotConfigured(RuntimeError):
    """A real provider is missing its API key or model (set them in env)."""


@dataclass
class AiAnswerResult:
    engine: str
    model: str
    raw_answer: str
    brand_mentioned: bool
    mention_position: int | None
    site_cited: bool
    cited_urls: list[str]
    competitors_mentioned: list[str]
    sentiment: str  # positive | neutral | negative
    cost_usd: Decimal


class AnswerEngineProvider(Protocol):
    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
    ) -> AiAnswerResult: ...


def match_brand(text: str, brand_names: list[str]) -> tuple[bool, int | None]:
    """Fuzzy and case-insensitive matching across all brand spellings."""
    if not text or not brand_names:
        return False, None
    lower_text = text.lower()
    first_pos: int | None = None

    for name in brand_names:
        clean_name = name.strip().lower()
        if not clean_name:
            continue
        # Check substring
        pos = lower_text.find(clean_name)
        if pos != -1 and (first_pos is None or pos < first_pos):
            first_pos = pos

    return (first_pos is not None), first_pos


def match_competitors(text: str, competitors: list[str]) -> list[str]:
    """Find which competitor domains or names are mentioned in the text."""
    found: list[str] = []
    if not text or not competitors:
        return found
    lower_text = text.lower()
    for comp in competitors:
        comp_clean = (
            comp.strip()
            .lower()
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .rstrip("/")
        )
        if not comp_clean:
            continue
        domain_name = comp_clean.split(".")[0]
        if comp_clean in lower_text or (len(domain_name) > 3 and domain_name in lower_text):
            found.append(comp_clean)
    return sorted(list(set(found)))


def match_citations(urls: list[str], target_domain: str) -> bool:
    """Check if target_domain appears in cited URLs."""
    norm_target = target_domain.lower().replace("www.", "")
    return any(norm_target in u.lower() for u in urls)


def estimate_sentiment(text: str, brand_name: str) -> str:
    """Basic sentiment classification around brand mention."""
    if not brand_name:
        return "neutral"
    lower = text.lower()
    pos_words = [
        "best",
        "excellent",
        "top",
        "recommended",
        "great",
        "leader",
        "preferred",
        "ممتاز",
        "أفضل",
        "رائد",
    ]
    neg_words = ["worst", "poor", "avoid", "complaints", "bad", "expensive", "ضعيف", "سيء"]

    has_pos = any(w in lower for w in pos_words)
    has_neg = any(w in lower for w in neg_words)

    if has_pos and not has_neg:
        return "positive"
    if has_neg and not has_pos:
        return "negative"
    return "neutral"


class OpenAiAnswerProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        s = get_settings()
        self.api_key = api_key or s.openai_api_key
        self.model = model or s.openai_model

    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
    ) -> AiAnswerResult:
        if not self.api_key or not self.model:
            raise ProviderNotConfigured(self.__class__.__name__)

        import requests

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]

        urls = re.findall(r"https?://[^\s)\]]+", text)
        is_mentioned, pos = match_brand(text, brand_names)
        comps = match_competitors(text, competitors)
        cited = match_citations(urls, target_domain)
        sentiment = estimate_sentiment(text, brand_names[0] if brand_names else "")

        return AiAnswerResult(
            engine=AnswerEngineId.CHATGPT,
            model=self.model,
            raw_answer=text,
            brand_mentioned=is_mentioned,
            mention_position=pos,
            site_cited=cited,
            cited_urls=urls,
            competitors_mentioned=comps,
            sentiment=sentiment,
            cost_usd=Decimal("0.0050"),
        )


class GeminiAnswerProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        s = get_settings()
        self.api_key = api_key or s.gemini_api_key
        self.model = model or s.gemini_model

    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
    ) -> AiAnswerResult:
        if not self.api_key or not self.model:
            raise ProviderNotConfigured(self.__class__.__name__)

        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"googleSearch": {}}],  # Search grounding
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
        text = "".join(p.get("text", "") for p in parts)

        urls = re.findall(r"https?://[^\s)\]]+", text)
        is_mentioned, pos = match_brand(text, brand_names)
        comps = match_competitors(text, competitors)
        cited = match_citations(urls, target_domain)
        sentiment = estimate_sentiment(text, brand_names[0] if brand_names else "")

        return AiAnswerResult(
            engine=AnswerEngineId.GEMINI,
            model=self.model,
            raw_answer=text,
            brand_mentioned=is_mentioned,
            mention_position=pos,
            site_cited=cited,
            cited_urls=urls,
            competitors_mentioned=comps,
            sentiment=sentiment,
            cost_usd=Decimal("0.0030"),
        )


class PerplexityAnswerProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        s = get_settings()
        self.api_key = api_key or s.perplexity_api_key
        self.model = model or s.perplexity_model

    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
    ) -> AiAnswerResult:
        if not self.api_key or not self.model:
            raise ProviderNotConfigured(self.__class__.__name__)

        import requests

        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        urls = data.get("citations", [])

        is_mentioned, pos = match_brand(text, brand_names)
        comps = match_competitors(text, competitors)
        cited = match_citations(urls, target_domain)
        sentiment = estimate_sentiment(text, brand_names[0] if brand_names else "")

        return AiAnswerResult(
            engine=AnswerEngineId.PERPLEXITY,
            model=self.model,
            raw_answer=text,
            brand_mentioned=is_mentioned,
            mention_position=pos,
            site_cited=cited,
            cited_urls=urls,
            competitors_mentioned=comps,
            sentiment=sentiment,
            cost_usd=Decimal("0.0050"),
        )


class AnthropicAnswerProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        s = get_settings()
        self.api_key = api_key or s.anthropic_api_key
        self.model = model or s.claude_model_fast

    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
    ) -> AiAnswerResult:
        if not self.api_key or not self.model:
            raise ProviderNotConfigured(self.__class__.__name__)

        import requests

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []))
        urls = re.findall(r"https?://[^\s)\]]+", text)

        is_mentioned, pos = match_brand(text, brand_names)
        comps = match_competitors(text, competitors)
        cited = match_citations(urls, target_domain)
        sentiment = estimate_sentiment(text, brand_names[0] if brand_names else "")

        return AiAnswerResult(
            engine=AnswerEngineId.CLAUDE,
            model=self.model,
            raw_answer=text,
            brand_mentioned=is_mentioned,
            mention_position=pos,
            site_cited=cited,
            cited_urls=urls,
            competitors_mentioned=comps,
            sentiment=sentiment,
            cost_usd=Decimal("0.0020"),
        )


class MockAnswerEngineProvider:
    """Deterministic simulation for tests and demo runs."""

    def __init__(self, engine: str) -> None:
        self.engine = engine

    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
    ) -> AiAnswerResult:
        brand = brand_names[0] if brand_names else "OurBrand"
        seed = int(
            hashlib.sha256(f"{self.engine}:{prompt}:{brand}:{target_domain}".encode()).hexdigest(),
            16,
        )

        # 60% chance brand is mentioned
        brand_mentioned = (seed % 10) < 6
        site_cited = brand_mentioned and ((seed % 10) < 4)

        mentioned_comps = [c for i, c in enumerate(competitors) if (seed + i) % 2 == 0]
        if not mentioned_comps and competitors:
            mentioned_comps = [competitors[0]]

        if language == "ar":
            if brand_mentioned:
                answer = f"بناءً على التقييمات والخيارات المتاحة، يعتبر {brand} خياراً ممتازاً. ومن المنافسين البارزين أيضاً: {', '.join(mentioned_comps)}."
            else:
                answer = f"هناك العديد من الخيارات الرائدة في هذا المجال مثل: {', '.join(mentioned_comps)}."
        else:
            if brand_mentioned:
                answer = f"When considering options for '{prompt}', {brand} is frequently recommended for quality and service. Other prominent alternatives include {', '.join(mentioned_comps)}."
            else:
                answer = f"Top options commonly cited for '{prompt}' include {', '.join(mentioned_comps)}."

        cited_urls = [f"https://{target_domain}/guide"] if site_cited else []
        for c in mentioned_comps:
            cited_urls.append(f"https://{c}/review")

        pos = answer.find(brand) if brand_mentioned else None

        return AiAnswerResult(
            engine=self.engine,
            model=f"mock-{self.engine}",
            raw_answer=answer,
            brand_mentioned=brand_mentioned,
            mention_position=pos if pos != -1 else None,
            site_cited=site_cited,
            cited_urls=cited_urls,
            competitors_mentioned=mentioned_comps,
            sentiment="positive" if brand_mentioned else "neutral",
            cost_usd=Decimal("0.0000"),
        )


def get_answer_engine(engine_id: str) -> AnswerEngineProvider:
    """The real provider for an engine, or the mock where allowed (local/test only).

    Raises ProviderNotConfigured when the engine's API key or model is missing outside
    local/test, so production never stores made-up answers.
    """
    s = get_settings()
    real: dict[str, tuple[type, str | None, str | None]] = {
        AnswerEngineId.CHATGPT: (OpenAiAnswerProvider, s.openai_api_key, s.openai_model),
        AnswerEngineId.GEMINI: (GeminiAnswerProvider, s.gemini_api_key, s.gemini_model),
        AnswerEngineId.PERPLEXITY: (
            PerplexityAnswerProvider,
            s.perplexity_api_key,
            s.perplexity_model,
        ),
        AnswerEngineId.CLAUDE: (AnthropicAnswerProvider, s.anthropic_api_key, s.claude_model_fast),
    }
    if engine_id in real:
        cls, key, model = real[engine_id]
        if key and model:
            return cls()
    if s.mock_providers_allowed:
        return MockAnswerEngineProvider(engine_id)
    raise ProviderNotConfigured(f"{engine_id}: set its API key and model in env")
