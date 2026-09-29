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
