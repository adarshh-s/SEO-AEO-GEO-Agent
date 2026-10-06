"""Shared AI client: provider selection and the Gemini structured-output path (no network)."""

import json
from decimal import Decimal

import pytest
from pydantic import BaseModel

from app_core import llm


class Profile(BaseModel):
    brand_name: str
    city: str | None


@pytest.fixture
def s(monkeypatch):
    from app_core.settings import get_settings

    st = get_settings()
    for k in ("anthropic_api_key", "claude_model_main", "claude_model_fast", "gemini_api_key",
              "gemini_model", "gemini_model_main", "gemini_model_fast"):  # fmt: skip
        monkeypatch.setattr(st, k, None)
    monkeypatch.setattr(st, "llm_provider", "auto")
    return st


def test_provider_selection(s, monkeypatch):
    assert not llm.is_configured("main")
    monkeypatch.setattr(s, "gemini_api_key", "g")
    monkeypatch.setattr(s, "gemini_model", "gemini-x")
    assert llm.resolve("main") == ("gemini", "gemini-x")  # only Gemini configured
    monkeypatch.setattr(s, "gemini_model_fast", "gemini-fast")
    assert llm.resolve("fast") == ("gemini", "gemini-fast")
    monkeypatch.setattr(s, "anthropic_api_key", "a")
    monkeypatch.setattr(s, "claude_model_main", "claude-opus-5-5")
    assert llm.resolve("main") == ("anthropic", "claude-opus-5-5")  # auto prefers Claude
    monkeypatch.setattr(s, "llm_provider", "gemini")
    assert llm.resolve("main") == ("gemini", "gemini-x")  # explicit choice wins


def test_gemini_structured_call(s, monkeypatch):
    monkeypatch.setattr(s, "gemini_api_key", "g")
    monkeypatch.setattr(s, "gemini_model", "gemini-x")
    sent = {}

    class Resp:
        status_code = 200

        def json(self):
            return {
                "steps": [{"type": "model_output",
                           "content": [{"text": json.dumps({"brand_name": "Oud", "city": None})}]}],
                "usage": {"total_input_tokens": 1000, "total_output_tokens": 200,
                          "total_thought_tokens": 300},
            }  # fmt: skip

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return Resp()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    r = llm.parse(role="fast", system="Identify.", user="page", output=Profile)
    assert r.value == Profile(brand_name="Oud", city=None) and r.provider == "gemini"
    body = sent["body"]
    assert sent["url"].endswith("/v1beta/interactions") and sent["headers"]["x-goog-api-key"] == "g"
    assert body["response_format"]["mime_type"] == "application/json"
    assert body["response_format"]["schema"]["properties"]["brand_name"]["type"] == "string"
    assert "untrusted" in body["system_instruction"].lower() and body["store"] is False
    assert r.cost_usd == Decimal("0.008000")  # 1000*2/1M + (200+300)*12/1M


def test_gemini_invalid_output_is_a_refusal(s, monkeypatch):
    monkeypatch.setattr(s, "gemini_api_key", "g")
    monkeypatch.setattr(s, "gemini_model", "gemini-x")

    class Resp:
        status_code = 200

        def json(self):
            return {"output_text": "not json"}

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Resp())
    with pytest.raises(llm.LlmRefusal):
        llm.parse(role="main", system="x", user="y", output=Profile)
