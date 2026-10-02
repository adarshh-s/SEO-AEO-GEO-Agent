import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app_core.cost_guard import get_current_period
from app_core.db import get_engine
from app_core.models import (
    AiCheck,
    AiPrompt,
    CrawlSnapshot,
    Keyword,
    RankCheck,
    UsageCounter,
    VisibilityScore,
)
from conftest import SITE, set_plan, signup


def _seed_tracking_data(org_id: uuid.UUID, site_id: uuid.UUID) -> None:
    """Helper to populate tracking rows directly into the DB for testing queries."""
    with Session(get_engine()) as session:
        now = datetime.now(UTC)
        kw = Keyword(
            id=uuid.uuid4(),
            org_id=org_id,
            site_id=site_id,
            keyword="riyadh seo agency",
            country="SA",
            language="en",
            device="desktop",
        )
        session.add(kw)
        session.flush()

        rank = RankCheck(
            org_id=org_id,
            site_id=site_id,
            keyword_id=kw.id,
            checked_at=now,
            position=3,
            previous_position=5,
            url_ranked="https://www.example.com/services/seo",
            serp_features=["organic", "ai_overview"],
            ai_overview_present=True,
            ai_overview_cites_site=True,
        )
        session.add(rank)

        prompt = AiPrompt(
            id=uuid.uuid4(),
            org_id=org_id,
            site_id=site_id,
            prompt_text="What is the top SEO agency in Riyadh?",
            language="en",
            country="SA",
            intent="commercial",
        )
        session.add(prompt)
        session.flush()

        ai_check = AiCheck(
            org_id=org_id,
            site_id=site_id,
            prompt_id=prompt.id,
            engine="chatgpt",
            model="gpt-4o-mini",
            run_index=0,
            checked_at=now,
            raw_answer="OmniRank is the top rated agency in Riyadh for enterprise SEO.",
            brand_mentioned=True,
            mention_position=0,
            site_cited=True,
            competitors_mentioned=["rival.com"],
            sentiment="positive",
        )
        session.add(ai_check)

        vis = VisibilityScore(
            org_id=org_id,
            site_id=site_id,
            date=now,
            language="en",
            seo_score=Decimal("78.50"),
            ai_share_of_voice=Decimal("85.00"),
            per_engine={"chatgpt": 85.0, "gemini": 60.0},
        )
        session.add(vis)

        crawl = CrawlSnapshot(
            org_id=org_id,
            site_id=site_id,
            url="https://www.example.com/",
            http_status=200,
            raw_html_hash="hash1",
            rendered_html_hash="hash2",
            js_only_content_detected=True,
            ai_robots_allowed={"GPTBot": True, "ClaudeBot": True},
            meta_title="Example Title",
            meta_description="Example Description",
            fetched_at=now,
        )
        session.add(crawl)

        start, end = get_current_period(now)
        usage = UsageCounter(
            org_id=org_id,
            period_start=start,
            period_end=end,
            category="serp",
            provider="dataforseo",
            units=1,
            cost_usd=Decimal("0.0020"),
        )
        session.add(usage)
        session.commit()


def test_tracking_endpoints_empty_state(account):
    site = account.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    # Rankings list
    r_rankings = account.client.get(f"/sites/{site_id}/rankings")
    assert r_rankings.status_code == 200
    assert r_rankings.json() == []

    # AI visibility list
    r_ai = account.client.get(f"/sites/{site_id}/ai-visibility")
    assert r_ai.status_code == 200
    assert r_ai.json()["prompts"] == []
    assert r_ai.json()["overall_share_of_voice"] == 0

    # Crawl latest (empty returns 404 until first crawl)
    r_snap = account.client.get(f"/sites/{site_id}/crawl/latest")
    assert r_snap.status_code == 404

    # Dashboard overview
    r_ov = account.client.get(f"/sites/{site_id}/overview")
    assert r_ov.status_code == 200
    ov = r_ov.json()
    assert ov["seo_score"] == 0
    assert ov["ai_share_of_voice"] == 0
    assert ov["ranking_wins"] == []
    assert ov["ranking_losses"] == []


def test_tracking_with_populated_data(account):
    site = account.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site["id"])
    _seed_tracking_data(account.org_id, site_id)

    # Rankings check
    r_rankings = account.client.get(f"/sites/{site_id}/rankings")
    assert r_rankings.status_code == 200
    items = r_rankings.json()
    assert len(items) == 1
    assert items[0]["keyword"] == "riyadh seo agency"
    assert items[0]["position"] == 3
    assert items[0]["previous_position"] == 5
    assert items[0]["position_change"] == 2
    assert items[0]["ai_overview_present"] is True

    # AI visibility check
    r_ai = account.client.get(f"/sites/{site_id}/ai-visibility")
    assert r_ai.status_code == 200
    ai_data = r_ai.json()
    assert ai_data["brand_mention_rate"] == 100.0
    assert ai_data["citation_rate"] == 100.0
    assert len(ai_data["prompts"]) == 1
    assert ai_data["prompts"][0]["engines_status"]["chatgpt"]["mentioned"] is True

    # Crawl snapshot latest check
    r_snap = account.client.get(f"/sites/{site_id}/crawl/latest")
    assert r_snap.status_code == 200
    snap = r_snap.json()
    assert snap["http_status"] == 200
    assert snap["js_only_content_detected"] is True
    assert snap["ai_robots_allowed"]["GPTBot"] is True

    # Dashboard overview check
    r_ov = account.client.get(f"/sites/{site_id}/overview")
    assert r_ov.status_code == 200
    ov = r_ov.json()
    assert ov["seo_score"] == 78.5
    assert ov["ai_share_of_voice"] == 85.0
    assert ov["per_engine"]["chatgpt"] == 85.0
    assert len(ov["ranking_wins"]) == 1
    assert ov["ranking_wins"][0]["keyword"] == "riyadh seo agency"
    assert ov["monthly_cost_ceiling_usd"] > 0
    assert ov["monthly_spend_usd"] == 0.002


def test_trigger_tracking_checks(account):
    set_plan(account.org_id, "growth")
    site = account.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    # Trigger keyword ranking check
    r_rank = account.client.post(f"/sites/{site_id}/keywords/check-all")
    assert r_rank.status_code == 200
    assert r_rank.json() == {"ok": True}

    # Trigger AI check
    r_ai = account.client.post(f"/sites/{site_id}/prompts/check-all")
    assert r_ai.status_code == 200
    assert r_ai.json() == {"ok": True}

    # Trigger crawl check
    r_crawl = account.client.post(f"/sites/{site_id}/crawl")
    assert r_crawl.status_code == 200
    assert r_crawl.json() == {"ok": True}


def test_tracking_tenant_isolation(account, app):
    # Create site in account's org
    site = account.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    # other_account belongs to a different org
    other_account = signup(app, org_name="Other Org")

    r = other_account.client.get(f"/sites/{site_id}/rankings")
    assert r.status_code == 404
    r = other_account.client.get(f"/sites/{site_id}/ai-visibility")
    assert r.status_code == 404
    r = other_account.client.post(f"/sites/{site_id}/keywords/check-all")
    assert r.status_code == 404
