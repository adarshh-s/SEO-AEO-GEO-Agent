import re
from urllib.parse import parse_qs, urlparse

import httpx
import respx

from conftest import make_client, signup

PASSWORD = "correct-horse-battery"


def test_signup_creates_user_org_on_trial_and_sets_httponly_cookies(app, outbox):
    client = make_client(app)
    r = client.post(
        "/auth/signup",
        json={
            "email": "Owner@Example.com",
            "password": PASSWORD,
            "full_name": "Owner",
            "org_name": "Acme Dental",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "owner@example.com"
    assert body["user"]["ui_language"] == "en"
    assert body["orgs"] == [
        {
            "id": body["orgs"][0]["id"],
            "name": "Acme Dental",
            "slug": "acme-dental",
            "role": "owner",
            "plan_code": "trial",
        }
    ]
    set_cookies = r.headers.get_list("set-cookie")
    for name in ("app_at", "app_rt", "app_csrf"):
        cookie = next(c for c in set_cookies if c.startswith(f"{name}="))
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert any("Path=/auth" in c for c in set_cookies if c.startswith("app_rt="))
    assert outbox.outbox[0].subject.startswith("Confirm your email")


def test_signup_duplicate_email_is_rejected(app):
    signup(app, email="dup@example.com")
    r = make_client(app).post(
        "/auth/signup", json={"email": "DUP@example.com", "password": PASSWORD, "full_name": "X"}
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "email_taken"


def test_login_and_wrong_password(app):
    signup(app, email="a@example.com")
    client = make_client(app)
    bad = client.post("/auth/login", json={"email": "a@example.com", "password": "nope-nope-nope"})
    assert bad.status_code == 401 and bad.json()["detail"]["code"] == "invalid_credentials"
    ok = client.post("/auth/login", json={"email": "A@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert client.get("/auth/me").json()["user"]["email"] == "a@example.com"


def test_unauthenticated_requests_get_401(app):
    assert make_client(app).get("/auth/me").status_code == 401


def test_mutations_require_csrf_header(account):
    client = account.client
    token = client.headers.pop("X-CSRF-Token")
    r = client.patch("/auth/me", json={"ui_language": "ar"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "csrf_failed"
    client.headers["X-CSRF-Token"] = "wrong"
    assert client.patch("/auth/me", json={"ui_language": "ar"}).status_code == 403
    client.headers["X-CSRF-Token"] = token
    r = client.patch("/auth/me", json={"ui_language": "ar"})
    assert r.status_code == 200 and r.json()["ui_language"] == "ar"


def test_ui_language_is_saved_per_user(account):
    account.client.patch("/auth/me", json={"ui_language": "ar"})
    assert account.client.get("/auth/me").json()["user"]["ui_language"] == "ar"
    assert account.client.patch("/auth/me", json={"ui_language": "fr"}).status_code == 422


def test_refresh_rotates_and_reuse_revokes_family(account):
    client = account.client
    old_refresh = client.cookies.get("app_rt")
    r = client.post("/auth/refresh")
    assert r.status_code == 200
    new_refresh = client.cookies.get("app_rt")
    assert new_refresh and new_refresh != old_refresh

    # Replaying the rotated token (e.g. stolen) revokes the family, including the new token.
    attacker = make_client(client.app)
    attacker.cookies.set("app_rt", old_refresh, domain="api.test", path="/auth")
    assert attacker.post("/auth/refresh").status_code == 401
    assert client.post("/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token(account):
    client = account.client
    refresh = client.cookies.get("app_rt")
    assert client.post("/auth/logout").status_code == 200
    other = make_client(client.app)
    other.cookies.set("app_rt", refresh, domain="api.test", path="/auth")
    assert other.post("/auth/refresh").status_code == 401


def _token_from(text: str) -> str:
    return parse_qs(urlparse(re.search(r"https?://\S+", text).group(0)).query)["token"][0]


def test_email_verification(app, outbox):
    acct = signup(app, verified=False)
    token = _token_from(outbox.outbox[-1].text)
    assert acct.client.get("/auth/me").json()["user"]["email_verified"] is False
    assert acct.client.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert acct.client.get("/auth/me").json()["user"]["email_verified"] is True
    assert acct.client.post("/auth/verify-email", json={"token": "garbage"}).status_code == 400


def test_password_reset_is_single_use_and_revokes_sessions(app, outbox):
    acct = signup(app, email="reset@example.com")
    anon = make_client(app)
    assert (
        anon.post("/auth/password-reset/request", json={"email": "nobody@example.com"}).status_code
        == 200
    )
    n = len(outbox.outbox)
    anon.post("/auth/password-reset/request", json={"email": "reset@example.com"})
    assert len(outbox.outbox) == n + 1
    token = _token_from(outbox.outbox[-1].text)

    assert (
        anon.post(
            "/auth/password-reset", json={"token": token, "password": "a-brand-new-password"}
        ).status_code
        == 200
    )
    assert (
        anon.post(
            "/auth/password-reset", json={"token": token, "password": "another-new-password"}
        ).status_code
        == 400
    )
    assert acct.client.post("/auth/refresh").status_code == 401  # old sessions revoked
    assert (
        anon.post(
            "/auth/login", json={"email": "reset@example.com", "password": "a-brand-new-password"}
        ).status_code
        == 200
    )


def test_arabic_user_gets_arabic_email(app, outbox):
    signup(app, ui_language="ar")
    assert "أكّد" in outbox.outbox[-1].subject


def test_login_is_rate_limited(app):
    client = make_client(app)
    codes = [
        client.post(
            "/auth/login", json={"email": "x@example.com", "password": "whatever-123"}
        ).status_code
        for _ in range(12)
    ]
    assert codes[-1] == 429


# --- Google sign-in ---------------------------------------------------------------------


def _start_google(client):
    r = client.get("/auth/google/start?next=/app/sites", follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["scope"] == ["openid email profile"] and q["code_challenge_method"] == ["S256"]
    return q["state"][0], q["nonce"][0]


@respx.mock
def test_google_sign_in_creates_account(app, monkeypatch):
    from app_api.routers import auth

    client = make_client(app)
    state, nonce = _start_google(client)
    respx.post(auth.GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"id_token": "tok"})
    )
    monkeypatch.setattr(
        auth,
        "verify_google_id_token",
        lambda _: {
            "sub": "google-123",
            "email": "Gina@Gmail.com",
            "email_verified": True,
            "name": "Gina",
            "nonce": nonce,
        },
    )
    r = client.get(f"/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "http://app.test/app/sites"
    me = client.get("/auth/me").json()
    assert me["user"]["email"] == "gina@gmail.com" and me["user"]["has_password"] is False
    assert me["orgs"][0]["plan_code"] == "trial"


@respx.mock
def test_google_links_existing_email_account(app, monkeypatch):
    from app_api.routers import auth

    acct = signup(app, email="linked@example.com")
    client = make_client(app)
    state, nonce = _start_google(client)
    respx.post(auth.GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"id_token": "tok"})
    )
    monkeypatch.setattr(
        auth,
        "verify_google_id_token",
        lambda _: {
            "sub": "g-1",
            "email": "linked@example.com",
            "email_verified": True,
            "nonce": nonce,
        },
    )
    client.get(f"/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert client.get("/auth/me").json()["user"]["id"] == str(acct.user_id)


def test_google_callback_rejects_bad_state(app):
    client = make_client(app)
    _start_google(client)
    r = client.get("/auth/google/callback?code=abc&state=forged", follow_redirects=False)
    assert r.headers["location"] == "http://app.test/login?error=google"


@respx.mock
def test_google_callback_rejects_wrong_nonce_or_unverified_email(app, monkeypatch):
    from app_api.routers import auth

    client = make_client(app)
    state, _ = _start_google(client)
    respx.post(auth.GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"id_token": "tok"})
    )
    monkeypatch.setattr(
        auth,
        "verify_google_id_token",
        lambda _: {
            "sub": "g-2",
            "email": "e@example.com",
            "email_verified": True,
            "nonce": "other",
        },
    )
    r = client.get(f"/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.headers["location"].endswith("error=google")


def test_open_redirect_is_blocked(app):
    client = make_client(app)
    client.get("/auth/google/start?next=//evil.com", follow_redirects=False)
    from app_api.routers.auth import _safe_next

    assert _safe_next("//evil.com") == "/app"
    assert _safe_next("https://evil.com") == "/app"
    assert _safe_next("/app/sites") == "/app/sites"


def test_google_start_without_configuration_redirects_to_login(app, monkeypatch):
    from app_core.settings import get_settings

    monkeypatch.setattr(get_settings(), "google_oauth_client_id", None)
    r = make_client(app).get("/auth/google/start", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "http://app.test/login?error=google_unavailable"
