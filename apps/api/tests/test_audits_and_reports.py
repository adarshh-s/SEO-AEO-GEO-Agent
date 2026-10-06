from app_core.db import system_session
from app_core.models import Plan
from conftest import set_plan, signup

SITE_DATA = {
    "domain": "test-audit-store.com",
    "name": "Audit Test Store",
    "homepage_url": "https://test-audit-store.com",
    "primary_language": "en",
    "additional_languages": ["ar"],
    "default_country": "SA",
}


def test_audit_lifecycle_and_reporting(app, outbox, monkeypatch):
    # 1. Signup and set up growth plan
    user = signup(app, email="owner@audit-test.com", org_name="Audit Org")
    set_plan(user.org_id, "growth")

    # 2. Create site
    site_res = user.client.post("/sites", json=SITE_DATA)
    assert site_res.status_code == 201
    site = site_res.json()
    site_id = site["id"]

    # 3. Trigger audit
    audit_res = user.client.post(f"/sites/{site_id}/audits", json={})
    assert audit_res.status_code == 201
    audit = audit_res.json()
    assert audit["status"] == "pending"  # queued for the worker
    audit_id = audit["id"]
    # The worker runs the audit (crawling never happens inside the API).
    from app_worker.tasks.audit import run_site_audit

    run_site_audit(audit_id)

    # 4. List audits
    list_res = user.client.get(f"/sites/{site_id}/audits")
    assert list_res.status_code == 200
    audits = list_res.json()
    assert len(audits) >= 1
    assert audits[0]["id"] == audit_id

    # 5. Get audit detail
    detail_res = user.client.get(f"/sites/{site_id}/audits/{audit_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == audit_id
    assert "summary" in detail
    assert "issues" in detail
    assert len(detail["issues"]) > 0

    # 6. Generate report in English
    report_res = user.client.post(
        f"/sites/{site_id}/reports",
        json={"audit_id": audit_id, "language": "en", "report_type": "audit"},
    )
    assert report_res.status_code == 201
    report = report_res.json()
    assert report["status"] == "completed"
    assert "metrics_summary" in report
    report_id = report["id"]

    # 7. List reports
    rep_list_res = user.client.get(f"/sites/{site_id}/reports")
    assert rep_list_res.status_code == 200
    assert len(rep_list_res.json()) >= 1

    # 8. Download report PDF
    download_res = user.client.get(f"/sites/{site_id}/reports/{report_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content.startswith(b"%PDF-")

    # 9. Generate report in Arabic
    report_ar_res = user.client.post(
        f"/sites/{site_id}/reports",
        json={"audit_id": audit_id, "language": "ar", "report_type": "audit"},
    )
    assert report_ar_res.status_code == 201
    report_ar = report_ar_res.json()
    assert report_ar["language"] == "ar"

    download_ar = user.client.get(f"/sites/{site_id}/reports/{report_ar['id']}/download")
    assert download_ar.status_code == 200
    assert download_ar.content.startswith(b"%PDF-")

    # 10. Send test weekly email digest
    digest_res = user.client.post(
        f"/sites/{site_id}/reports/digest/send-test",
        json={"language": "en"},
    )
    assert digest_res.status_code == 200
    assert digest_res.json()["status"] == "queued"
    # The worker builds and sends it.
    import app_worker.tasks.digest as digest_task

    monkeypatch.setattr(digest_task, "get_email_provider", lambda: outbox)
    digest_task.send_site_weekly_digest(site_id, user.email, "en")
    assert any("Weekly Performance Digest" in m.subject for m in outbox.outbox)


def test_audit_quota_limit(app):
    user = signup(app, email="quota@audit-test.com", org_name="Quota Org")

    # Create plan with only 1 audit allowed per month
    with system_session() as db:
        db.query(Plan).filter(Plan.code == "trial").update({"audits_per_month": 1})
        db.commit()

    trial_site_data = {
        "domain": "trial-store.com",
        "name": "Trial Store",
        "homepage_url": "https://trial-store.com",
        "primary_language": "en",
    }
    site_res = user.client.post("/sites", json=trial_site_data)
    assert site_res.status_code == 201
    site_id = site_res.json()["id"]

    # First audit succeeds
    res1 = user.client.post(f"/sites/{site_id}/audits", json={})
    assert res1.status_code == 201

    # Second audit exceeds quota
    res2 = user.client.post(f"/sites/{site_id}/audits", json={})
    assert res2.status_code == 402
    assert res2.json()["detail"]["code"] == "plan_limit_reached"
