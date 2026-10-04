"""Tests for Fixes inbox, approval, editing, deployment, rollback, and D24 email verification."""

import uuid

from app_core.db import system_session
from app_core.models import AuditLogEntry, Fix
from conftest import SITE, set_plan, signup


def _seed_fix(org_id, site_id, **kwargs):
    fix_id = uuid.uuid4()
    with system_session() as db:
        fix = Fix(
            id=fix_id,
            org_id=org_id,
            site_id=site_id,
            type=kwargs.get("type", "schema"),
            status=kwargs.get("status", "proposed"),
            language=kwargs.get("language", "en"),
            target_url=kwargs.get("target_url", "https://mysite.com/blog/article"),
            title=kwargs.get("title", "Add Article Schema"),
            description=kwargs.get("description", "Improves AI knowledge graph parsing"),
            payload=kwargs.get(
                "payload",
                {
                    "schema_type": "Article",
                    "json_ld": {
                        "@context": "https://schema.org",
                        "@type": "Article",
                        "headline": "Sample Article",
                    },
                },
            ),
            recommended_delivery=kwargs.get("recommended_delivery", "snippet"),
        )
        db.add(fix)
        db.commit()
    return fix_id


def test_list_and_filter_fixes(app):
    owner = signup(app)
    set_plan(owner.org_id, "growth")
    site = owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site["id"])

    f1 = _seed_fix(owner.org_id, site_id, type="schema", status="proposed", language="en")
    f2 = _seed_fix(owner.org_id, site_id, type="meta", status="approved", language="ar")
    _f3 = _seed_fix(owner.org_id, site_id, type="faq", status="deployed", language="en")

    # List all
    all_fixes = owner.client.get(f"/sites/{site_id}/fixes").json()
    assert len(all_fixes) == 3

    # Filter by status
    proposed = owner.client.get(f"/sites/{site_id}/fixes?status=proposed").json()
    assert len(proposed) == 1
    assert proposed[0]["id"] == str(f1)

    # Filter by type
    meta_fixes = owner.client.get(f"/sites/{site_id}/fixes?type=meta").json()
    assert len(meta_fixes) == 1
    assert meta_fixes[0]["id"] == str(f2)

    # Filter by language
    ar_fixes = owner.client.get(f"/sites/{site_id}/fixes?language=ar").json()
    assert len(ar_fixes) == 1
    assert ar_fixes[0]["id"] == str(f2)


def test_update_fix(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site["id"])
    f1 = _seed_fix(owner.org_id, site_id, title="Old Title")

    patch_res = owner.client.patch(
        f"/sites/{site_id}/fixes/{f1}",
        json={
            "title": "New Title",
            "payload": {"extra_key": "val", "title": "<b>Better</b> title"},
        },
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["title"] == "New Title"
    assert "extra_key" not in data["payload"]  # unknown keys are dropped by the sanitizer
    assert data["payload"]["title"] == "Better title"  # tags stripped


def test_approve_fix_verified_vs_unverified(app):
    # Verified user approves
    verified_owner = signup(app, email="verified@example.com", verified=True)
    site = verified_owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site["id"])
    f1 = _seed_fix(verified_owner.org_id, site_id)

    # Add a webhook to verify dispatch
    wh_res = verified_owner.client.post(
        "/org/webhooks",
        json={"url": "https://example.com/webhook", "events": ["fix.approved"]},
    )
    assert wh_res.status_code == 201

    res = verified_owner.client.post(f"/sites/{site_id}/fixes/{f1}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    # Verify audit log
    with system_session() as db:
        logs = db.query(AuditLogEntry).filter_by(action="fix.approved").all()
        assert len(logs) == 1
        assert logs[0].target_id == str(f1)

    # Unverified user cannot approve
    unverified = signup(app, email="unverified@example.com", verified=False)
    # Add unverified user to same org
    with system_session() as db:
        from app_core.models import Membership

        db.add(Membership(user_id=unverified.user_id, org_id=verified_owner.org_id, role="admin"))
        db.commit()

    unverified.client.headers["X-Org-Id"] = str(verified_owner.org_id)
    f2 = _seed_fix(verified_owner.org_id, site_id)
    res_unverified = unverified.client.post(f"/sites/{site_id}/fixes/{f2}/approve")
    assert res_unverified.status_code == 403
    assert res_unverified.json()["detail"]["code"] == "email_not_verified"


def test_reject_fix(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site["id"])
    f1 = _seed_fix(owner.org_id, site_id)

    res = owner.client.post(f"/sites/{site_id}/fixes/{f1}/reject")
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"

    with system_session() as db:
        logs = db.query(AuditLogEntry).filter_by(action="fix.rejected").all()
        assert len(logs) == 1


def test_deploy_and_rollback_fix(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = uuid.UUID(site["id"])
    f1 = _seed_fix(owner.org_id, site_id)

    # Deploy with snapshot of previous state
    deploy_res = owner.client.post(
        f"/sites/{site_id}/fixes/{f1}/deploy",
        json={
            "deployed_via": "snippet",
            "previous_state": {"old_title": "Original Title Without Keywords"},
        },
    )
    assert deploy_res.status_code == 200
    deployed = deploy_res.json()
    assert deployed["status"] == "deployed"
    assert deployed["deployed_via"] == "snippet"
    assert deployed["deployed_at"] is not None
    assert deployed["previous_state"]["old_title"] == "Original Title Without Keywords"

    # Rollback
    rb_res = owner.client.post(f"/sites/{site_id}/fixes/{f1}/rollback")
    assert rb_res.status_code == 200
    rolled_back = rb_res.json()
    assert rolled_back["status"] == "rolled_back"

    with system_session() as db:
        rb_logs = db.query(AuditLogEntry).filter_by(action="fix.rolled_back").all()
        assert len(rb_logs) == 1
