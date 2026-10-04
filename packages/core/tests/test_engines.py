"""AI engines: request shape, answer/citation extraction, analysis (no network)."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app_core.providers import ai_answer as aa


@pytest.fixture
def configured(monkeypatch):
    from app_core.settings import get_settings

    s = get_settings()
    for k, v in {
        "openai_api_key": "k", "openai_model": "gpt-test", "gemini_api_key": "k",
        "gemini_model": "gemini-test", "perplexity_api_key": "k", "perplexity_model": "fast",
    }.items():  # fmt: skip
        monkeypatch.setattr(s, k, v)
    return s


def _capture_post(monkeypatch, response: dict):
    calls = []

    def fake_post(url, *, headers, body):
        calls.append((url, body))
        return response

    monkeypatch.setattr(aa, "_post", fake_post)
    return calls


def test_chatgpt_uses_web_search_with_location_and_reads_citations(configured, monkeypatch):
    calls = _capture_post(monkeypatch, {
        "output": [
            {"type": "web_search_call", "status": "completed"},
            {"type": "message", "content": [{"type": "output_text",
             "text": "Try Riyadh Oud House.",
             "annotations": [{"type": "url_citation", "url": "https://oudhouse.example/shop",
                              "title": "Oud House", "start_index": 4, "end_index": 20}]}]},
        ],
        "usage": {"input_tokens": 1000, "output_tokens": 500},
    })  # fmt: skip
    ans = aa.OpenAiAnswerProvider().fetch("best oud in riyadh?", "en", "sa", "Riyadh")
    url, body = calls[0]
    assert url.endswith("/v1/responses")
    assert body["tools"] == [{"type": "web_search", "user_location":
                              {"type": "approximate", "country": "SA", "city": "Riyadh"}}]  # fmt: skip
    assert ans.text == "Try Riyadh Oud House."
    assert ans.cited_urls == ["https://oudhouse.example/shop"]
    assert ans.cost_usd == Decimal("0.040000")  # 1k*5/1M + 500*20/1M + 1 search*0.025


def test_gemini_interactions_api(configured, monkeypatch):
    calls = _capture_post(monkeypatch, {
        "steps": [
            {"type": "google_search_call", "arguments": {"queries": ["oud riyadh"]}},
            {"type": "model_output", "content": [{"text": "Arabian Oud is popular.",
             "annotations": [{"type": "url_citation", "url": "https://arabianoud.example"}]}]},
        ],
        "usage": {"total_input_tokens": 100, "total_output_tokens": 50},
    })  # fmt: skip
    ans = aa.GeminiAnswerProvider().fetch("best oud?", "en", "SA", None)
    assert calls[0][0].endswith("/v1beta/interactions")
    assert calls[0][1]["tools"] == [{"type": "google_search"}]
    assert ans.text == "Arabian Oud is popular." and ans.cited_urls == [
        "https://arabianoud.example"
    ]


def test_perplexity_agent_api_uses_reported_cost(configured, monkeypatch):
    calls = _capture_post(monkeypatch, {
        "output": [
            {"type": "search_results", "results": [{"url": "https://a.example", "title": "A"}]},
            {"type": "message", "content": [{"type": "output_text", "text": "Answer."}]},
        ],
        "usage": {"cost": {"total_cost": 0.0123, "currency": "USD"}},
    })  # fmt: skip
    ans = aa.PerplexityAnswerProvider().fetch("q", "en", None, None)
    assert calls[0][0] == "https://api.perplexity.ai/v1/agent"
    assert calls[0][1]["preset"] == "fast"
    assert ans.cited_urls == ["https://a.example"] and ans.cost_usd == Decimal("0.0123")


def test_claude_engine_uses_web_search_and_collects_citations(monkeypatch):
    from app_core import llm
    from app_core.settings import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "anthropic_api_key", "k")
    monkeypatch.setattr(s, "claude_model_main", "claude-opus-5-5")
    seen = {}

    def create(**kw):
        seen.update(kw)
        block = SimpleNamespace(type="text", text="Visit Oud House.",
                                citations=[SimpleNamespace(url="https://oudhouse.example/")])  # fmt: skip
        usage = SimpleNamespace(input_tokens=1000, output_tokens=100, cache_read_input_tokens=0,
                                cache_creation_input_tokens=0,
                                server_tool_use=SimpleNamespace(web_search_requests=2))  # fmt: skip
        return SimpleNamespace(content=[block], stop_reason="end_turn", usage=usage,
                               model="claude-opus-5-5")  # fmt: skip

    fake = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "client", lambda: fake)
    ans = aa.AnthropicAnswerProvider().fetch("best oud?", "en", "SA", "Riyadh")
    assert seen["tools"][0]["type"] == "web_search_20260209"
    assert seen["tools"][0]["user_location"]["country"] == "SA"
    assert seen["fallbacks"] == "default"
    assert ans.cited_urls == ["https://oudhouse.example/"]
    assert ans.cost_usd == Decimal("0.026000")  # 1000*4/1M + 100*20/1M + 2*0.01


def test_analysis_by_claude(monkeypatch):
    from app_core import llm

    analysis = aa.AnswerAnalysis(
        brand_mentioned=True, first_mention_quote="Riyadh Oud House", recommendation_rank=2,
        businesses_recommended=["Arabian Oud", "Riyadh Oud House", "Ajmal"], sentiment="positive",
    )  # fmt: skip
    monkeypatch.setattr(
        llm, "parse", lambda **kw: llm.LlmResult(analysis, "claude-haiku-4-5", Decimal("0.002"))
    )
    answer = aa.EngineAnswer("Top picks: Arabian Oud, then Riyadh Oud House.",
                             ["https://www.oudhouse.example/x"], "gpt-test", Decimal("0.03"))  # fmt: skip
    r = aa.analyze_answer(answer, engine="chatgpt", brand_names=["Riyadh Oud House"],
                          target_domain="oudhouse.example", competitors=[])  # fmt: skip
    assert r.brand_mentioned and r.mention_position == answer.text.find("Riyadh Oud House")
    assert r.site_cited
    assert r.competitors_mentioned == ["Ajmal", "Arabian Oud"]  # the brand itself excluded
    assert r.cost_usd == Decimal("0.032")


def test_citation_matching_uses_real_domain():
    assert aa.match_citations(["https://shop.oudhouse.example/a"], "oudhouse.example")
    assert not aa.match_citations(["https://notoudhouse.example/a"], "oudhouse.example")
    assert not aa.match_citations(["https://evil.com/?q=oudhouse.example"], "oudhouse.example")
