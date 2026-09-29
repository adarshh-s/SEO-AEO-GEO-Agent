import re

from conftest import make_client, signup


def test_current_org_shows_plan_and_usage(account):
    r = account.client.get("/org")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "owner"
    assert body["plan"]["code"] == "trial"
    assert body["usage"] == {"sites": 0, "keywords": 0, "prompts": 0}


def test_missing_or_foreign_org_header(app, account):
    other = signup(app)
    client = account.client
    client.headers.pop("X-Org-Id")
    assert client.get("/org").json()["detail"]["code"] == "org_required"
    client.headers["X-Org-Id"] = str(other.org_id)
    assert client.get("/org").status_code == 403


def test_user_can_create_second_org_and_switch(account):
    r = account.client.post("/orgs", json={"name": "Second Co"})
    assert r.status_code == 201
    assert {o["name"] for o in account.client.get("/orgs").json()} == {"Acme", "Second Co"}


def _invite_and_accept(app, owner, outbox, role="member"):
    r = owner.client.post("/org/invitations", json={"email": "new@example.com", "role": role})
    assert r.status_code == 201, r.text
    token = re.search(r"token=(\S+)", outbox.outbox[-1].text).group(1)
    invitee = signup(app, email="new@example.com", org_name="Own org")
    r = invitee.client.post("/invitations/accept", json={"token": token})
    assert r.status_code == 200, r.text
    assert {o["role"] for o in r.json()["orgs"]} == {"owner", role}
    invitee.client.headers["X-Org-Id"] = str(owner.org_id)
    return invitee


def test_invitation_flow_and_roles(app, account, outbox):
    invitee = _invite_and_accept(app, account, outbox, role="viewer")
    members = account.client.get("/org/members").json()
    assert sorted(m["role"] for m in members) == ["owner", "viewer"]
    # viewer can read but not create sites or invite
    assert invitee.client.get("/sites").status_code == 200
    assert (
        invitee.client.post("/sites", json={"homepage_url": "x.com", "name": "X"}).status_code
        == 403
    )
    assert (
        invitee.client.post("/org/invitations", json={"email": "z@example.com"}).status_code == 403
    )


def test_invitation_email_must_match(app, account, outbox):
    account.client.post("/org/invitations", json={"email": "someone@example.com"})
    token = re.search(r"token=(\S+)", outbox.outbox[-1].text).group(1)
    stranger = signup(app, email="stranger@example.com")
    r = stranger.client.post("/invitations/accept", json={"token": token})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "invite_email_mismatch"


def test_last_owner_cannot_be_demoted_or_removed(account):
    me = account.client.get("/org/members").json()[0]
    r = account.client.patch(f"/org/members/{me['id']}", json={"role": "admin"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "last_owner"
    assert account.client.delete(f"/org/members/{me['id']}").status_code == 409


def test_admin_cannot_grant_owner(app, account, outbox):
    invitee = _invite_and_accept(app, account, outbox, role="admin")
    members = {m["email"]: m for m in account.client.get("/org/members").json()}
    target = members["new@example.com"]
    r = invitee.client.patch(f"/org/members/{target['id']}", json={"role": "owner"})
    assert r.status_code == 403
    assert (
        account.client.patch(f"/org/members/{target['id']}", json={"role": "owner"}).status_code
        == 200
    )


def test_org_changes_are_audit_logged(account):
    account.client.patch("/org", json={"name": "Renamed"})
    from sqlalchemy import select

    from app_core.db import system_session
    from app_core.models import AuditLogEntry

    with system_session() as db:
        actions = set(
            db.scalars(select(AuditLogEntry.action).where(AuditLogEntry.org_id == account.org_id))
        )
    assert {"user.signup", "org.updated"} <= actions


def test_plans_endpoint_is_public_and_hides_trial(app):
    codes = [p["code"] for p in make_client(app).get("/plans").json()]
    assert codes == ["starter", "growth", "business"]
