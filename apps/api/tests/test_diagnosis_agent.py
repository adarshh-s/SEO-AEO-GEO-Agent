"""Diagnosis task end to end (DB real; page fetches and Claude mocked)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app_core.db import system_session
from app_core.models import Diagnosis, Fix, Keyword, RankCheck, Site, UsageCounter
from conftest import SITE, set_plan

OUR = '<html lang="en"><head><title>Smile</title></head><body><h1>Dentist</h1><p>We fix teeth.</p></body></html>'
RIVAL = (
    '<html><head><title>Best Dentist Austin</title><script type="application/ld+json">'
    '{"@context":"https://schema.org","@type":"Dentist","name":"Rival"}</script></head>'
    "<body><h1>Best dentist in Austin</h1><h2>Prices</h2><p>" + "word " * 900 + "</p></body></html>"
)


def _fetch_result(url, html):
    from app_worker.seo_engine.fetch import FetchResult

    return FetchResult(url=url, final_url=url, status_code=200, headers={}, raw_html=html,
                       raw_text=html, raw_html_hash="h", meta_title=None, meta_description=None)  # fmt: skip


@pytest.fixture
def keyword_diag(account):
    set_plan(account.org_id, "growth")
    site = account.client.post(
        "/sites", json={**SITE, "homepage_url": "https://smile.example", "platform": "wordpress"}
    ).json()
    account.client.post(f"/sites/{site['id']}/keywords",
                        json={"items": [{"keyword": "dentist austin", "language": "en"}]})  # fmt: skip
    with system_session() as db:
        kw = db.scalar(select(Keyword))
        db.add(RankCheck(
            org_id=kw.org_id, site_id=kw.site_id, keyword_id=kw.id, position=14,
            url_ranked="https://smile.example/services",
            raw_response={"items": [
                {"type": "organic", "url": "https://rival.example/dentist"},
                {"type": "organic", "url": "https://www.smile.example/services"},
                {"type": "organic", "url": "https://other.example/"},
            ]},
        ))  # fmt: skip
        diag = Diagnosis(org_id=kw.org_id, site_id=kw.site_id, target_type="keyword",
                         target_id=kw.id, status="pending")  # fmt: skip
        db.add(diag)
        db.flush()
        return str(diag.id)


def _patch_fetch(monkeypatch, fail_for=()):
    from app_worker.tasks import diagnose as task

    fetched = []

    def fake_fetch(url, timeout=15):
        fetched.append(url)
        if any(f in url for f in fail_for):
            raise ConnectionError("down")
        return _fetch_result(url, OUR if "smile.example" in url else RIVAL)

    monkeypatch.setattr(task, "fetch_page", fake_fetch)
    return fetched


def test_ai_diagnosis_uses_ranking_pages_and_sanitizes_fixes(keyword_diag, monkeypatch):
    from app_core import llm
    from app_worker.agents import diagnosis as agent
    from app_worker.tasks.diagnose import run_diagnosis

    fetched = _patch_fetch(monkeypatch)
    out = agent.DiagnosisOutput(
        summary="Rival answers prices and has Dentist schema; your page is thin.",
        findings=[agent.Finding(severity="high", gap_type="content_block",
                                title="Your page is much shorter", explanation="180 vs 900 words.")],
        fixes=[
            agent.ProposedFix(type="schema", title="Add Dentist schema", why="Rivals have it.",
                instructions="In WordPress: install the plugin...", meta_title=None,
                meta_description=None, faqs=[], html=None,
                json_ld='{"@context":"https://schema.org","@type":"Dentist","name":"</script><script>x()</script>"}'),
            agent.ProposedFix(type="content_block", title="Add a prices section", why="Answers the question.",
                instructions="Edit the page.", meta_title=None, meta_description=None, json_ld=None,
                faqs=[], html="<h2>Prices</h2><p>From [ADD PRICE]</p><img src=x onerror=alert(1)>"),
            agent.ProposedFix(type="meta", title="Broken", why="x", instructions="x", meta_title=None,
                meta_description=None, json_ld="{not json", faqs=[], html=None),
        ],
    )  # fmt: skip
    monkeypatch.setattr(llm, "is_configured", lambda role: True)
    calls = []

    def fake_parse(**kw):
        calls.append(kw)
        return llm.LlmResult(out, "claude-opus-5-5", Decimal("0.12"))

    monkeypatch.setattr(llm, "parse", fake_parse)
    run_diagnosis(keyword_diag)

    assert fetched[0] == "https://smile.example/services"  # our ranking page, not the homepage
    assert set(fetched[1:]) == {"https://rival.example/dentist", "https://other.example/"}
    assert calls[0]["role"] == "main" and "<untrusted" in calls[0]["user"]
    with system_session() as db:
        diag = db.get(Diagnosis, uuid.UUID(keyword_diag))
        assert diag.status == "completed" and diag.findings["source"] == "ai"
        assert diag.findings["summary"].startswith("Rival")
        fixes = db.scalars(select(Fix).order_by(Fix.type)).all()
        assert [f.type for f in fixes] == ["content_block", "schema"]  # invalid JSON fix dropped
        content, schema = fixes
        assert "onerror" not in content.payload["html"] and "[ADD PRICE]" in content.payload["html"]
        assert schema.payload["json_ld"]["@type"] == "Dentist"
        assert schema.recommended_delivery == "wordpress"
        assert "In WordPress" in schema.description
        cost = db.scalar(select(UsageCounter.cost_usd).where(UsageCounter.category == "llm"))
        assert cost == Decimal("0.12")


def test_unreachable_page_fails_instead_of_inventing_one(keyword_diag, monkeypatch):
    from app_worker.tasks.diagnose import run_diagnosis

    _patch_fetch(monkeypatch, fail_for=("smile.example",))
    run_diagnosis(keyword_diag)
    with system_session() as db:
        diag = db.get(Diagnosis, uuid.UUID(keyword_diag))
        assert diag.status == "failed" and "couldn't open" in diag.error
        assert db.scalars(select(Fix)).all() == []


def test_without_claude_rules_and_templates_are_used(keyword_diag, monkeypatch):
    from app_worker.tasks.diagnose import run_diagnosis

    _patch_fetch(monkeypatch)
    run_diagnosis(keyword_diag)
    with system_session() as db:
        diag = db.get(Diagnosis, uuid.UUID(keyword_diag))
        assert diag.status == "completed" and diag.findings["source"] == "rules"
        assert len(db.scalars(select(Fix)).all()) == 4
        assert db.scalar(select(Site)).platform == "wordpress"
