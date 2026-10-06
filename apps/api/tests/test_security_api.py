"""API-level regression tests for the 2026-10-04 security review."""

import json
import uuid

from sqlalchemy import text

from app_core.brand import BRAND
from app_core.db import get_engine, system_session
from app_core.models import SiteIntegration, Webhook
from conftest import SITE, make_client, signup


def _site(app):
    owner = signup(app)
    site = owner.client.post("/sites", json={**SITE, "homepage_url": "https://example.com"}).json()
    return owner, site


def _insert_fix_raw(site, *, status, payload_json, url="https://example.com/"):
    """Bypass the model validator, as if a bad payload were already stored."""
    fix_id = uuid.uuid4()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fixes (id, org_id, site_id, type, target_url, language, title, payload,"
                " recommended_delivery, status) SELECT :id, org_id, id, 'content_block', :url, 'en',"
                " 't', CAST(:payload AS jsonb), 'snippet', :status FROM sites WHERE id = :site"
            ),
            {
                "id": fix_id,
                "url": url,
                "payload": payload_json,
                "status": status,
                "site": site["id"],
            },
        )
    return fix_id


def test_public_fixes_are_sanitized_on_the_way_out(app):
    _, site = _site(app)
    _insert_fix_raw(
        site,
        status="approved",
        payload_json='{"html": "<p>ok</p><img src=x onerror=alert(1)><script>x()</script>",'
        ' "container_selector": "body"}',
    )
    r = make_client(app).get(
        "/public/v1/fixes",
        params={"site_key": site["site_key"], "url": "https://www.example.com/?a=1"},
    )
    payload = r.json()["fixes"][0]["payload"]
    assert "onerror" not in payload["html"] and "<p>ok</p>" in payload["html"]
    assert "<script" not in payload["html"] and "container_selector" not in payload


def test_public_fixes_only_for_exact_page_of_own_domain(app):
    _, site = _site(app)
    _insert_fix_raw(
        site,
        status="approved",
        payload_json='{"html": "<p>about</p>"}',
        url="https://example.com/about",
    )
    client = make_client(app)
    for url in (
        "",
        "https://example.com/",
        "https://example.com/about-us",
        "https://evil.com/about",
    ):
        r = client.get("/public/v1/fixes", params={"site_key": site["site_key"], "url": url})
        assert r.status_code in (200, 404) and (
            r.status_code == 404 or r.json()["fixes"] == []
        ), url
    r = client.get(
        "/public/v1/fixes",
        params={"site_key": site["site_key"], "url": "https://example.com/about/"},
    )
    assert len(r.json()["fixes"]) == 1


def test_public_endpoints_are_rate_limited(app):
    _, site = _site(app)
    client = make_client(app)
    codes = [
        client.get(
            "/public/v1/fixes", params={"site_key": site["site_key"], "url": "https://example.com/"}
        ).status_code
        for _ in range(125)
    ]
    assert codes[-1] == 429


def test_snippet_is_branded_from_config(app):
    js = make_client(app).get(f"/public/v1/{BRAND['snippet_filename']}").text
    assert "__BRAND" not in js
    assert f"window.{BRAND['snippet_global']}" in js
    assert f"data-{BRAND['brand_slug']}-content" in js


def test_approved_fix_cannot_be_edited(app):
    owner, site = _site(app)
    fix_id = _insert_fix_raw(site, status="approved", payload_json='{"title": "x"}')
    r = owner.client.patch(f"/sites/{site['id']}/fixes/{fix_id}", json={"payload": {"title": "y"}})
    assert r.status_code == 409


def test_invalid_payload_edit_is_rejected(app):
    owner, site = _site(app)
    fix_id = _insert_fix_raw(site, status="proposed", payload_json='{"title": "x"}')
    r = owner.client.patch(
        f"/sites/{site['id']}/fixes/{fix_id}", json={"payload": {"json_ld": {"no": "context"}}}
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_payload"


def test_webhook_urls_must_be_public_https(app):
    owner = signup(app)
    for url in (
        "http://hooks.example.com/x",
        "https://127.0.0.1/x",
        "https://localhost/x",
        "https://intranet/x",
    ):
        r = owner.client.post("/org/webhooks", json={"url": url, "events": ["fix.approved"]})
        assert r.status_code == 422, url


def test_credentials_and_webhook_secrets_are_encrypted_at_rest(app):
    owner, site = _site(app)
    with system_session() as db:
        db.add(
            SiteIntegration(
                org_id=uuid.UUID(str(owner.org_id)),
                site_id=uuid.UUID(site["id"]),
                provider="github",
                credentials={"token": "ghp_supersecret"},
            )
        )
        db.add(
            Webhook(
                org_id=owner.org_id,
                url="https://hooks.example.com/x",
                secret="whsec_plain",
                events=["fix.approved"],
            )
        )
    with get_engine().connect() as conn:
        raw_cred = conn.execute(text("SELECT credentials FROM site_integrations")).scalar()
        raw_secret = conn.execute(text("SELECT secret FROM webhooks")).scalar()
    assert "ghp_supersecret" not in raw_cred and "whsec_plain" not in raw_secret
    with system_session() as db:
        assert db.query(SiteIntegration).one().credentials == {"token": "ghp_supersecret"}
        assert db.query(Webhook).one().secret == "whsec_plain"


def test_referral_ping_accepts_text_plain_beacons(app):
    from sqlalchemy import func, select

    from app_core.models import AiReferralEvent

    _, site = _site(app)
    body = json.dumps(
        {"site_key": site["site_key"], "url": "https://example.com/p", "referrer_engine": "chatgpt"}
    )
    r = make_client(app).post(
        "/public/v1/telemetry/referral", content=body,
        headers={"Content-Type": "text/plain;charset=UTF-8"},
    )  # fmt: skip
    assert r.status_code == 200
    with system_session() as db:
        assert db.scalar(select(func.count()).select_from(AiReferralEvent)) == 1
    bad = make_client(app).post("/public/v1/telemetry/referral", content="nope",
                                headers={"Content-Type": "text/plain"})  # fmt: skip
    assert bad.status_code == 422
