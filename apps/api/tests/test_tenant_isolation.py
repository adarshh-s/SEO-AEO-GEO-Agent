"""Org B must not be able to read or change org A's data through ANY endpoint.

Endpoints are discovered from the OpenAPI schema, so new endpoints are covered
automatically. A new endpoint must be classified below (and get a sample body if it
takes one), otherwise this test fails. That is intentional.
"""

import re

import pytest

from conftest import SITE, make_client, set_plan, signup

# Endpoints that are not org-scoped (auth, self, public). Everything else is tested.
NOT_TENANT_SCOPED = {
    "/healthz",
    "/auth/signup",
    "/auth/login",
    "/auth/refresh",
    "/auth/logout",
    "/auth/me",
    "/auth/verify-email/request",
    "/auth/verify-email",
    "/auth/password-reset/request",
    "/auth/password-reset",
    "/auth/google/start",
    "/auth/google/callback",
    "/orgs",
    "/invitations/accept",
    "/plans",
}
PLATFORM_ADMIN_PREFIX = "/admin"

SAMPLE_BODIES = {
    ("PATCH", "/org"): {"name": "Renamed by B"},
    ("POST", "/org/invitations"): {"email": "invitee-of-b@example.com"},
    ("PATCH", "/org/members/{membership_id}"): {"role": "viewer"},
    ("POST", "/sites"): {**SITE, "homepage_url": "b-site.com"},
    ("PATCH", "/sites/{site_id}"): {"name": "Hijacked"},
    ("POST", "/sites/{site_id}/keywords"): {"items": [{"keyword": "injected", "language": "en"}]},
    ("PATCH", "/sites/{site_id}/keywords/{keyword_id}"): {"status": "paused"},
    ("POST", "/sites/{site_id}/prompts"): {
        "items": [{"prompt_text": "injected prompt", "language": "en"}]
    },
    ("PATCH", "/sites/{site_id}/prompts/{prompt_id}"): {"status": "paused"},
    ("POST", "/onboarding/analyze"): {"url": "b-site.com"},
    ("POST", "/onboarding/suggestions"): {"brand_name": "B", "industry": "x", "languages": ["en"]},
    ("POST", "/onboarding/complete"): {"site": {**SITE, "homepage_url": "b-complete.com"}},
    ("PUT", "/admin/orgs/{org_id}/plan"): {"plan_code": "business"},
    ("PATCH", "/admin/orgs/{org_id}"): {"addons": {"arabic": True}},
    ("PATCH", "/admin/plans/{plan_code}"): {"max_sites": 99},
    ("POST", "/sites/{site_id}/keywords/{keyword_id}/check"): {},
    ("POST", "/sites/{site_id}/keywords/check-all"): {},
    ("POST", "/sites/{site_id}/prompts/{prompt_id}/check"): {},
    ("POST", "/sites/{site_id}/prompts/check-all"): {},
    ("POST", "/sites/{site_id}/crawl"): {},
}


@pytest.fixture
def world(app, outbox):
    """Org A with one of everything; org B (a different owner) as the attacker."""
    a = signup(app, email="alice@a-corp.com", org_name="A Corp")
    set_plan(a.org_id, "growth")
    site = a.client.post(
        "/sites", json={**SITE, "homepage_url": "a-secret-site.com", "name": "A secret"}
    ).json()
    a.client.post(
        f"/sites/{site['id']}/keywords",
        json={"items": [{"keyword": "a secret keyword", "language": "en"}]},
    )
    a.client.post(
        f"/sites/{site['id']}/prompts",
        json={"items": [{"prompt_text": "a secret prompt", "language": "en"}]},
    )
    a.client.post("/org/invitations", json={"email": "bob@a-corp.com", "role": "member"})
    token = re.search(r"token=(\S+)", outbox.outbox[-1].text).group(1)
    bob = signup(app, email="bob@a-corp.com")
    bob.client.post("/invitations/accept", json={"token": token})
    a.client.post("/org/invitations", json={"email": "pending@a-corp.com", "role": "viewer"})

    members = a.client.get("/org/members").json()
    ids = {
        "site_id": site["id"],
        "keyword_id": a.client.get(f"/sites/{site['id']}/keywords").json()[0]["id"],
        "prompt_id": a.client.get(f"/sites/{site['id']}/prompts").json()[0]["id"],
        "membership_id": next(m["id"] for m in members if m["email"] == "bob@a-corp.com"),
        "invitation_id": a.client.get("/org/invitations").json()[0]["id"],
        "org_id": str(a.org_id),
        "plan_code": "growth",
    }
    b = signup(app, email="mallory@b-corp.com", org_name="B Corp")
    set_plan(b.org_id, "growth")
    b_site = b.client.post("/sites", json={**SITE, "homepage_url": "b-own-site.com"}).json()
    secrets = [
        *ids.values(),
        "a-secret-site.com",
        "a secret keyword",
        "a secret prompt",
        "alice@a-corp.com",
        "bob@a-corp.com",
        "pending@a-corp.com",
        "A Corp",
    ]
    secrets.remove("growth")
    return a, b, ids, b_site["id"], secrets


def _endpoints(app):
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            yield method.upper(), path


def _fill(path: str, ids: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: ids[m.group(1)], path)


def _call(client, method, path, template):
    body = SAMPLE_BODIES.get((method, template))
    if method in ("POST", "PUT", "PATCH") and body is None:
        pytest.fail(f"Add a sample body for {method} {template} to SAMPLE_BODIES")
    return client.request(method, path, json=body)


def test_every_endpoint_is_classified(app):
    for _method, path in _endpoints(app):
        params = set(re.findall(r"\{(\w+)\}", path))
        known = {
            "site_id",
            "keyword_id",
            "prompt_id",
            "membership_id",
            "invitation_id",
            "org_id",
            "plan_code",
        }
        assert params <= known, f"New path parameter in {path}: extend the isolation test"


def test_org_b_cannot_reach_org_a_data(app, world):
    a, b, ids, b_site_id, secrets = world
    checked = 0
    for method, template in _endpoints(app):
        if template in NOT_TENANT_SCOPED:
            continue
        if template.startswith(PLATFORM_ADMIN_PREFIX):
            r = _call(b.client, method, _fill(template, ids), template)
            assert r.status_code == 403, f"{method} {template}: non-admin got {r.status_code}"
            continue

        params = re.findall(r"\{(\w+)\}", template)
        variants = [(_fill(template, ids), bool(params))]
        if "site_id" in params and len(params) > 1:
            # B's own site + A's child id must not work either.
            variants.append((_fill(template, {**ids, "site_id": b_site_id}), True))
        for path, has_foreign_id in variants:
            r = _call(b.client, method, path, template)
            if has_foreign_id:
                assert r.status_code == 404, (
                    f"{method} {path}: expected 404, got {r.status_code} {r.text}"
                )
            else:
                assert r.status_code < 500, f"{method} {path}: {r.status_code}"
            for s in secrets:
                assert s not in r.text, f"{method} {path} leaked {s!r}"
            checked += 1
    assert checked >= 20

    # And nothing of A's changed.
    org = a.client.get("/org").json()
    assert org["name"] == "A Corp" and org["usage"] == {"sites": 1, "keywords": 1, "prompts": 1}
    site = a.client.get(f"/sites/{ids['site_id']}").json()
    assert site["name"] == "A secret"
    assert a.client.get(f"/sites/{ids['site_id']}/keywords").json()[0]["status"] == "active"
    roles = {m["email"]: m["role"] for m in a.client.get("/org/members").json()}
    assert roles == {"alice@a-corp.com": "owner", "bob@a-corp.com": "member"}
    assert len(a.client.get("/org/invitations").json()) == 1


def test_org_b_cannot_select_org_a_via_header(app, world):
    a, b, ids, _, secrets = world
    b.client.headers["X-Org-Id"] = ids["org_id"]
    for method, template in _endpoints(app):
        if template in NOT_TENANT_SCOPED or template.startswith(PLATFORM_ADMIN_PREFIX):
            continue
        r = _call(b.client, method, _fill(template, ids), template)
        assert r.status_code == 403, f"{method} {template}: {r.status_code}"


def test_anonymous_gets_401_on_tenant_endpoints(app, world):
    _, _, ids, _, _ = world
    anon = make_client(app)
    anon.headers["X-Org-Id"] = ids["org_id"]
    for method, template in _endpoints(app):
        if template in NOT_TENANT_SCOPED:
            continue
        r = _call(anon, method, _fill(template, ids), template)
        assert r.status_code == 401, f"{method} {template}: {r.status_code}"
