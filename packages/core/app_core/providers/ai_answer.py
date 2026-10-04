"""AI answer engines for visibility tracking (CLAUDE.md §8).

Each engine is asked the customer's question the way a real user would ask it, with web
search on and the customer's country/city as location, so answers match what people see:

- ChatGPT    OpenAI Responses API + `web_search` tool
- Claude     Anthropic SDK + `web_search` server tool
- Gemini     Gemini Interactions API + `google_search` tool
- Perplexity Perplexity Agent API (the Sonar chat API was retired on 2026-09-27)

Every answer is then read by Claude (fast model) to decide whether the brand is mentioned,
where, which other businesses are recommended, and the sentiment. Without Claude (local
dev), simple text matching is used instead. Whether the site is cited comes from the
engine's own citations, matched on the real domain.

Model IDs and keys come from env only. Engine prices (for cost tracking) default to
conservative estimates and can be overridden with AI_ENGINE_PRICES (JSON).
"""

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

import requests
from pydantic import BaseModel, Field

from app_core.enums import AnswerEngineId
from app_core.logging import get_logger
from app_core.provider_errors import ProviderNotConfigured
from app_core.settings import get_settings

log = get_logger(__name__)
TIMEOUT = 90  # web-search answers can take a while

__all__ = [
    "AiAnswerResult",
    "AnswerEngineProvider",
    "AnthropicAnswerProvider",
    "EngineAnswer",
    "GeminiAnswerProvider",
    "MockAnswerEngineProvider",
    "OpenAiAnswerProvider",
    "PerplexityAnswerProvider",
    "ProviderNotConfigured",
    "analyze_answer",
    "get_answer_engine",
]


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


@dataclass
class EngineAnswer:
    """What an engine returned, before analysis."""

    text: str
    cited_urls: list[str]
    model: str
    cost_usd: Decimal
    meta: dict[str, Any] = field(default_factory=dict)


class AnswerEngineProvider(Protocol):
    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
        country: str | None = None,
        city: str | None = None,
    ) -> AiAnswerResult: ...


# --- deterministic helpers (fallback analysis and citation matching) ------------------------


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
    """True if any cited URL is on the site's domain (or a subdomain of it)."""
    target = target_domain.lower().removeprefix("www.")
    for url in urls:
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        if host == target or host.endswith("." + target):
            return True
    return False


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


# --- answer analysis by Claude -------------------------------------------------------------


class AnswerAnalysis(BaseModel):
    brand_mentioned: bool = Field(
        description="True if the answer mentions the brand under any of its spellings"
    )
    first_mention_quote: str | None = Field(
        description="The exact words (max 8) where the brand is first mentioned, copied verbatim"
    )
    recommendation_rank: int | None = Field(
        description="If the answer recommends several businesses, the brand's position (1 = first)"
    )
    businesses_recommended: list[str] = Field(
        description="Names of OTHER businesses/brands the answer recommends or mentions, as written"
    )
    sentiment: Literal["positive", "neutral", "negative", "not_mentioned"]


def analyze_answer(
    answer: EngineAnswer,
    *,
    engine: str,
    brand_names: list[str],
    target_domain: str,
    competitors: list[str],
) -> AiAnswerResult:
    from app_core import llm  # local import: llm imports provider_errors only

    cited = match_citations(answer.cited_urls, target_domain)
    known = match_competitors(answer.text, competitors)
    try:
        result = llm.parse(
            role="fast",
            system=(
                "You check an AI assistant's answer for a brand-monitoring tool. Report "
                "exactly what the answer says; do not infer mentions that aren't there."
            ),
            user=(
                f"Brand spellings: {', '.join(brand_names) or '-'}\n"
                f"Brand website: {target_domain}\n"
                f"Known competitors: {', '.join(competitors) or '-'}\n\n"
                + llm.untrusted(f"{engine} answer", answer.text)
            ),
            output=AnswerAnalysis,
            max_tokens=1500,
        )
    except ProviderNotConfigured:
        return _heuristic_result(answer, engine, brand_names, cited, known)
    a = result.value
    position = None
    if a.brand_mentioned:
        quote = (a.first_mention_quote or "").strip()
        idx = answer.text.find(quote) if quote else -1
        position = idx if idx >= 0 else match_brand(answer.text, brand_names)[1]
    brand_lower = {b.lower() for b in brand_names}
    others = [b.strip() for b in a.businesses_recommended if b.strip().lower() not in brand_lower]
    return AiAnswerResult(
        engine=engine,
        model=answer.model,
        raw_answer=answer.text,
        brand_mentioned=a.brand_mentioned,
        mention_position=position,
        site_cited=cited,
        cited_urls=answer.cited_urls,
        competitors_mentioned=sorted(set(known) | set(others)),
        sentiment="neutral" if a.sentiment == "not_mentioned" else a.sentiment,
        cost_usd=answer.cost_usd + result.cost_usd,
    )


def _heuristic_result(
    answer: EngineAnswer, engine: str, brand_names: list[str], cited: bool, known: list[str]
) -> AiAnswerResult:
    mentioned, pos = match_brand(answer.text, brand_names)
    return AiAnswerResult(
        engine=engine,
        model=answer.model,
        raw_answer=answer.text,
        brand_mentioned=mentioned,
        mention_position=pos,
        site_cited=cited,
        cited_urls=answer.cited_urls,
        competitors_mentioned=known,
        sentiment=estimate_sentiment(answer.text, brand_names[0] if brand_names else ""),
        cost_usd=answer.cost_usd,
    )


# --- engines ---------------------------------------------------------------------------------

# USD: (input per 1M tokens, output per 1M tokens, per web search). Estimates for cost
# tracking only; override with AI_ENGINE_PRICES='{"chatgpt": [in, out, search], ...}'.
DEFAULT_ENGINE_PRICES: dict[str, tuple[float, float, float]] = {
    AnswerEngineId.CHATGPT: (5.0, 20.0, 0.025),
    AnswerEngineId.GEMINI: (2.0, 12.0, 0.035),
}


def _engine_price(engine: str) -> tuple[Decimal, Decimal, Decimal]:
    raw = get_settings().ai_engine_prices
    prices = dict(DEFAULT_ENGINE_PRICES)
    if raw:
        try:
            prices.update({k: tuple(v) for k, v in json.loads(raw).items()})
        except (ValueError, TypeError):
            log.warning("ai_engine_prices.invalid")
    p = prices.get(engine, (5.0, 25.0, 0.03))
    return Decimal(str(p[0])), Decimal(str(p[1])), Decimal(str(p[2]))


def _token_cost(engine: str, tokens_in: int, tokens_out: int, searches: int) -> Decimal:
    p_in, p_out, p_search = _engine_price(engine)
    cost = (Decimal(tokens_in) * p_in + Decimal(tokens_out) * p_out) / Decimal(1_000_000)
    return (cost + p_search * searches).quantize(Decimal("0.000001"))


def _location(country: str | None, city: str | None) -> dict[str, str]:
    loc = {"type": "approximate"}
    if country:
        loc["country"] = country.upper()
    if city:
        loc["city"] = city
    return loc


def _walk(node: Any) -> Iterator[dict]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _citation_urls(data: Any) -> list[str]:
    urls: list[str] = []
    for node in _walk(data):
        url = node.get("url")
        if node.get("type") == "url_citation" and isinstance(url, str) and url not in urls:
            urls.append(url)
    return urls


def _post(url: str, *, headers: dict[str, str], body: dict) -> dict:
    resp = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise RuntimeError(f"{url} -> HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


class _Engine:
    engine: str

    def fetch(self, prompt: str, language: str, country: str | None, city: str | None) -> EngineAnswer:  # fmt: skip
        raise NotImplementedError

    def query(
        self,
        *,
        prompt: str,
        brand_names: list[str],
        target_domain: str,
        competitors: list[str],
        language: str = "en",
        country: str | None = None,
        city: str | None = None,
    ) -> AiAnswerResult:
        answer = self.fetch(prompt, language, country, city)
        return analyze_answer(
            answer, engine=self.engine, brand_names=brand_names,
            target_domain=target_domain, competitors=competitors,
        )  # fmt: skip


class OpenAiAnswerProvider(_Engine):
    engine = AnswerEngineId.CHATGPT

    def __init__(self) -> None:
        s = get_settings()
        if not s.openai_api_key or not s.openai_model:
            raise ProviderNotConfigured("ChatGPT: set OPENAI_API_KEY and OPENAI_MODEL")
        self.key, self.model = s.openai_api_key, s.openai_model

    def fetch(self, prompt: str, language: str, country: str | None, city: str | None) -> EngineAnswer:  # fmt: skip
        data = _post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.key}"},
            body={
                "model": self.model,
                "input": prompt,
                "tools": [{"type": "web_search", "user_location": _location(country, city)}],
            },
        )
        text = "\n".join(
            c.get("text", "")
            for item in data.get("output", [])
            if item.get("type") == "message"
            for c in item.get("content", [])
            if c.get("type") == "output_text"
        ).strip()
        searches = sum(1 for i in data.get("output", []) if i.get("type") == "web_search_call")
        usage = data.get("usage") or {}
        cost = _token_cost(self.engine, usage.get("input_tokens", 0),
                           usage.get("output_tokens", 0), searches)  # fmt: skip
        return EngineAnswer(text, _citation_urls(data.get("output")), self.model, cost)


class GeminiAnswerProvider(_Engine):
    engine = AnswerEngineId.GEMINI

    def __init__(self) -> None:
        s = get_settings()
        if not s.gemini_api_key or not s.gemini_model:
            raise ProviderNotConfigured("Gemini: set GEMINI_API_KEY and GEMINI_MODEL")
        self.key, self.model = s.gemini_api_key, s.gemini_model

    def fetch(self, prompt: str, language: str, country: str | None, city: str | None) -> EngineAnswer:  # fmt: skip
        where = ", ".join(x for x in (city, country) if x)
        data = _post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={"x-goog-api-key": self.key},
            body={
                "model": self.model,
                # The Interactions API has no location field; say where the user is, as a
                # person searching locally would implicitly be.
                "input": f"{prompt}\n\n(I am in {where}.)" if where else prompt,
                "tools": [{"type": "google_search"}],
            },
        )
        steps = data.get("steps", [])
        text = "\n".join(
            c.get("text", "")
            for s_ in steps
            if s_.get("type") == "model_output"
            for c in (s_.get("content") or [])
            if isinstance(c, dict) and c.get("text")
        ).strip()
        searches = sum(1 for s_ in steps if s_.get("type") == "google_search_call")
        usage = data.get("usage") or {}
        cost = _token_cost(self.engine, usage.get("total_input_tokens", 0),
                           usage.get("total_output_tokens", 0), searches)  # fmt: skip
        return EngineAnswer(text, _citation_urls(steps), self.model, cost)


PERPLEXITY_PRESETS = {"fast", "low", "medium", "high", "xhigh"}


class PerplexityAnswerProvider(_Engine):
    engine = AnswerEngineId.PERPLEXITY

    def __init__(self) -> None:
        s = get_settings()
        if not s.perplexity_api_key or not s.perplexity_model:
            raise ProviderNotConfigured(
                "Perplexity: set PERPLEXITY_API_KEY and PERPLEXITY_MODEL (a preset like 'fast')"
            )
        self.key, self.model = s.perplexity_api_key, s.perplexity_model

    def fetch(self, prompt: str, language: str, country: str | None, city: str | None) -> EngineAnswer:  # fmt: skip
        body: dict[str, Any] = {"input": prompt, "tools": [{"type": "web_search"}]}
        if self.model in PERPLEXITY_PRESETS:
            body["preset"] = self.model
        else:
            body["model"] = self.model
            body["max_output_tokens"] = 4000
        where = ", ".join(x for x in (city, country) if x)
        if where:
            body["instructions"] = f"The user is located in {where}."
        data = _post(
            "https://api.perplexity.ai/v1/agent",
            headers={"Authorization": f"Bearer {self.key}"},
            body=body,
        )
        output = data.get("output", [])
        text = "\n".join(
            c.get("text", "")
            for item in output
            if item.get("type") == "message"
            for c in item.get("content", [])
            if isinstance(c, dict) and c.get("text")
        ).strip()
        urls = _citation_urls(output) or [
            r["url"]
            for item in output
            if item.get("type") == "search_results"
            for r in item.get("results", [])
            if r.get("url")
        ]
        reported = ((data.get("usage") or {}).get("cost") or {}).get("total_cost")
        cost = Decimal(str(reported)) if reported is not None else Decimal("0.01")
        return EngineAnswer(text, urls, self.model, cost)


class AnthropicAnswerProvider(_Engine):
    """What Claude (with web search) answers. Model: CLAUDE_MODEL_ANSWER, else _MAIN."""

    engine = AnswerEngineId.CLAUDE

    def __init__(self) -> None:
        s = get_settings()
        self.model = s.claude_model_answer or s.claude_model_main
        if not s.anthropic_api_key or not self.model:
            raise ProviderNotConfigured("Claude: set ANTHROPIC_API_KEY and CLAUDE_MODEL_MAIN")

    def _search_tool(self, country: str | None, city: str | None) -> dict:
        # Dynamic-filtering web search on 4.6+ models; the basic variant on older ones.
        basic = self.model.startswith(("claude-haiku", "claude-3"))
        tool = {
            "type": "web_search_20250305" if basic else "web_search_20260209",
            "name": "web_search",
            "max_uses": 5,
        }
        loc = _location(country, city)
        if len(loc) > 1:
            tool["user_location"] = loc
        return tool

    def fetch(self, prompt: str, language: str, country: str | None, city: str | None) -> EngineAnswer:  # fmt: skip
        from app_core import llm

        client = llm.client()
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tools = [self._search_tool(country, city)]
        texts: list[str] = []
        urls: list[str] = []
        cost = Decimal(0)
        for _ in range(4):  # resume pause_turn a few times at most
            response = client.beta.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=messages,
                tools=tools,
                **llm.fallback_kwargs(self.model),
            )
            searches = getattr(getattr(response.usage, "server_tool_use", None),
                               "web_search_requests", 0) or 0  # fmt: skip
            cost += llm.cost_of(response.model, response.usage, searches)
            for block in response.content:
                if block.type == "text":
                    texts.append(block.text)
                    for c in getattr(block, "citations", None) or []:
                        url = getattr(c, "url", None)
                        if url and url not in urls:
                            urls.append(url)
            if response.stop_reason == "refusal":
                break
            if response.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": response.content})
        return EngineAnswer("".join(texts).strip(), urls, self.model, cost)


# --- mock (local/test only) ---------------------------------------------------------------------


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
        country: str | None = None,
        city: str | None = None,
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
    """The real engine, or the mock where allowed (local/test only).

    Raises ProviderNotConfigured when the engine's key/model is missing outside local/test,
    so production never stores made-up answers.
    """
    real = {
        AnswerEngineId.CHATGPT: OpenAiAnswerProvider,
        AnswerEngineId.GEMINI: GeminiAnswerProvider,
        AnswerEngineId.PERPLEXITY: PerplexityAnswerProvider,
        AnswerEngineId.CLAUDE: AnthropicAnswerProvider,
    }.get(engine_id)
    if real is not None:
        try:
            return real()
        except ProviderNotConfigured:
            if not get_settings().mock_providers_allowed:
                raise
    if get_settings().mock_providers_allowed:
        return MockAnswerEngineProvider(engine_id)
    raise ProviderNotConfigured(f"Unknown engine {engine_id}")
