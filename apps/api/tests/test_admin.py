from conftest import make_platform_admin, signup


def test_non_admin_is_forbidden(account):
    assert account.client.get("/admin/orgs").status_code == 403
    assert (
        account.client.put(
            f"/admin/orgs/{account.org_id}/plan", json={"plan_code": "business"}
        ).status_code
        == 403
    )


def test_admin_assigns_plan_addons_and_ceiling(app, account):
    admin = signup(app, email="ops@example.com")
    make_platform_admin(admin.user_id)
    r = admin.client.put(f"/admin/orgs/{account.org_id}/plan", json={"plan_code": "business"})
    assert r.status_code == 200 and r.json()["plan_code"] == "business"
    assert account.client.get("/org").json()["plan"]["code"] == "business"
    assert (
        admin.client.put(
            f"/admin/orgs/{account.org_id}/plan", json={"plan_code": "nope"}
        ).status_code
        == 422
    )

    r = admin.client.patch(
        f"/admin/orgs/{account.org_id}",
        json={"addons": {"arabic": True}, "cost_ceiling_override_usd": "75.50"},
    )
    assert r.json()["addons"] == {"arabic": True}
    assert r.json()["cost_ceiling_override_usd"] == "75.50"
    assert len(admin.client.get("/admin/orgs").json()) == 2


def test_admin_edits_trial_limits(app, account):
    admin = signup(app, email="ops2@example.com")
    make_platform_admin(admin.user_id)
    r = admin.client.patch(
        "/admin/plans/trial", json={"max_sites": 2, "allowed_engines": ["chatgpt"]}
    )
    assert r.status_code == 200 and r.json()["max_sites"] == 2
    assert (
        admin.client.patch("/admin/plans/trial", json={"allowed_engines": ["bing"]}).status_code
        == 422
    )
    assert account.client.get("/org").json()["plan"]["max_sites"] == 2


def test_admin_cost_summary_and_org_costs(app, account):
    from decimal import Decimal

    from app_core.cost_guard import record_usage
    from app_core.db import system_session

    with system_session() as db:
        record_usage(
            db,
            org_id=account.org_id,
            category="ai_check",
            provider="openai",
            units=10,
            cost_usd=Decimal("0.2500"),
        )
        record_usage(
            db,
            org_id=account.org_id,
            category="serp",
            provider="dataforseo",
            units=5,
            cost_usd=Decimal("0.0500"),
        )
        db.commit()

    admin = signup(app, email="ops3@example.com")
    make_platform_admin(admin.user_id)

    # Summary
    r = admin.client.get("/admin/costs/summary")
    assert r.status_code == 200
    data = r.json()
    assert float(data["total_spend_usd"]) >= 0.30
    assert "openai" in data["provider_breakdown"]
    assert "dataforseo" in data["provider_breakdown"]
    assert len(data["top_spending_orgs"]) >= 1

    # Org Cost Details
    r_detail = admin.client.get(f"/admin/orgs/{account.org_id}/costs")
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert float(detail["current_spend_usd"]) >= 0.30
    assert len(detail["counters"]) >= 2

    # Reset Counters
    r_reset = admin.client.post(f"/admin/orgs/{account.org_id}/reset-counters")
    assert r_reset.status_code == 200
    assert r_reset.json()["ok"] is True

    # Audit logs
    r_logs = admin.client.get("/admin/audit-logs")
    assert r_logs.status_code == 200
    logs = r_logs.json()
    assert any(log["action"] == "admin.counters_reset" for log in logs)
