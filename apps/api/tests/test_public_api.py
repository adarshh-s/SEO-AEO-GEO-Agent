"""Tests for public endpoints: agent.js script, public fixes API, and AI referral telemetry."""

import uuid

from app_core.db import system_session
from app_core.models import AiReferralEvent, Fix, Site
from conftest import SITE, make_client, signup


def test_serve_agent_script(app):
    client = make_client(app)
    res = client.get("/public/v1/agent.js")
    assert res.status_code == 200
    assert "application/javascript" in res.headers["content-type"]
    assert res.headers.get("access-control-allow-origin") == "*"
    assert "quardlink" in res.text
    assert "chatgpt" in res.text


def test_public_fixes_delivery(app):
    owner = signup(app)
    site_res = owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site_res["id"])

    with system_session() as db:
        site = db.get(Site, site_id)
        site_key = site.site_key

        # Proposed fix (should NOT be returned publicly)
        db.add(
            Fix(
                id=uuid.uuid4(),
                org_id=owner.org_id,
                site_id=site_id,
                type="schema",
                status="proposed",
                language="en",
                target_url="https://example.com/blog/article-1",
                title="Draft Schema",
                payload={"schema": "Draft"},
            )
        )
        # Approved fix (SHOULD be returned publicly)
        f_approved = Fix(
            id=uuid.uuid4(),
            org_id=owner.org_id,
            site_id=site_id,
            type="schema",
            status="approved",
            language="en",
            target_url="https://example.com/blog/article-1",
            title="Article Schema",
            payload={"@type": "Article", "headline": "Test"},
        )
        # Deployed fix for another URL (SHOULD be returned if querying that URL)
        f_deployed = Fix(
            id=uuid.uuid4(),
            org_id=owner.org_id,
            site_id=site_id,
            type="meta",
            status="deployed",
            language="en",
            target_url="https://example.com/about",
            title="About Meta",
            payload={"title": "About Us"},
        )
        db.add(f_approved)
        db.add(f_deployed)
        db.commit()

    anon = make_client(app)

    # 1. Query for /blog/article-1
    res1 = anon.get(f"/public/v1/fixes?site_key={site_key}&url=https://example.com/blog/article-1")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["fixes"]) == 1
    assert data1["fixes"][0]["id"] == str(f_approved.id)
    assert data1["fixes"][0]["payload"] == {"@type": "Article", "headline": "Test"}

    # 2. Query for /about
    res2 = anon.get(f"/public/v1/fixes?site_key={site_key}&url=https://example.com/about")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["fixes"]) == 1
    assert data2["fixes"][0]["id"] == str(f_deployed.id)

    # 3. Non-existent site key returns 404
    res_bad = anon.get("/public/v1/fixes?site_key=qls_invalid_key&url=https://example.com")
    assert res_bad.status_code == 404


def test_record_ai_referral_telemetry(app):
    owner = signup(app)
    site_res = owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site_res["id"])

    with system_session() as db:
        site = db.get(Site, site_id)
        site_key = site.site_key

    anon = make_client(app)

    res = anon.post(
        "/public/v1/telemetry/referral",
        json={
            "site_key": site_key,
            "url": "https://example.com/pricing",
            "referrer_engine": "chatgpt",
        },
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    # Verify event logged in database
    with system_session() as db:
        events = db.query(AiReferralEvent).filter_by(site_id=site_id).all()
        assert len(events) == 1
        assert events[0].referrer_engine == "chatgpt"
        assert events[0].url == "https://example.com/pricing"
