"""Authentication: email/password, email verification, password reset, Google sign-in."""

import base64
import hashlib
import uuid
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from redis import Redis
from sqlalchemy import select

from app_api.deps import CSRF_COOKIE, REFRESH_COOKIE, CurrentUser, SystemDb
from app_api.errors import ApiError, unauthorized
from app_api.providers.email import Email, EmailProvider, get_email_provider
from app_api.ratelimit import client_ip, enforce, get_redis
from app_api.schemas.auth import (
    EmailIn,
    LoginIn,
    MeUpdateIn,
    OrgSummary,
    PasswordResetIn,
    SessionOut,
    SignupIn,
    TokenIn,
    UserOut,
)
from app_api.schemas.common import Ok
from app_api.security import (
    decode_jwt,
    encode_jwt,
    hash_password,
    new_token,
    now,
    password_fingerprint,
    verify_password,
)
from app_api.services import accounts, audit, sessions
from app_core.i18n import t
from app_core.models import User
from app_core.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_STATE_COOKIE = "app_goauth"

RedisDep = Annotated[Redis, Depends(get_redis)]
EmailDep = Annotated[EmailProvider, Depends(get_email_provider)]


def _rate_limit(request: Request, redis: Redis, name: str) -> None:
    enforce(redis, f"{name}:{client_ip(request)}", get_settings().auth_rate_limit_per_minute)


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        ui_language=user.ui_language,
        is_platform_admin=user.is_platform_admin,
        email_verified=user.email_verified_at is not None,
        has_password=user.password_hash is not None,
    )


def session_out(db: SystemDb, user: User, csrf: str) -> SessionOut:
    orgs = [
        OrgSummary(id=o.id, name=o.name, slug=o.slug, role=role, plan_code=o.plan.code)
        for o, role in accounts.user_orgs(db, user.id)
    ]
    return SessionOut(user=user_out(user), orgs=orgs, csrf_token=csrf)


def _send_verification(email_provider: EmailProvider, user: User) -> None:
    token = encode_jwt(
        {"sub": str(user.id), "purpose": "verify_email", "email": user.email}, timedelta(days=3)
    )
    link = f"{get_settings().app_url}/verify-email?token={token}"
    lang = user.ui_language
    email_provider.send(
        Email(
            to=user.email,
            subject=t(lang, "email.verify.subject"),
            text=t(lang, "email.verify.body", name=user.full_name, link=link),
        )
    )


@router.post("/signup", response_model=SessionOut, status_code=201)
def signup(
    body: SignupIn,
    request: Request,
    response: Response,
    db: SystemDb,
    redis: RedisDep,
    email_provider: EmailDep,
) -> SessionOut:
    _rate_limit(request, redis, "signup")
    user = accounts.create_user(
        db,
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        ui_language=body.ui_language,
    )
    org = accounts.create_org(db, body.org_name or f"{body.full_name}'s organization", user)
    audit.record(db, "user.signup", org_id=org.id, actor_user_id=user.id, ip=client_ip(request))
    csrf = sessions.issue_session(db, response, user, user_agent=request.headers.get("user-agent"))
    db.commit()
    _send_verification(email_provider, user)
    return session_out(db, user, csrf)


@router.post("/login", response_model=SessionOut)
def login(
    body: LoginIn, request: Request, response: Response, db: SystemDb, redis: RedisDep
) -> SessionOut:
    _rate_limit(request, redis, "login")
    user = db.scalar(select(User).where(User.email == accounts.normalize_email(body.email)))
    if not user or not user.is_active or not verify_password(user.password_hash, body.password):
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect.")
    user.last_login_at = now()
    csrf = sessions.issue_session(db, response, user, user_agent=request.headers.get("user-agent"))
    db.commit()
    return session_out(db, user, csrf)


@router.post("/refresh", response_model=SessionOut)
def refresh(request: Request, response: Response, db: SystemDb, redis: RedisDep) -> SessionOut:
    _rate_limit(request, redis, "refresh")
    raw = request.cookies.get(REFRESH_COOKIE)
    token = sessions.rotate_refresh_token(db, raw) if raw else None
    if token is None:
        db.commit()  # persist a family revocation, if any
        sessions.clear_session_cookies(response)
        raise unauthorized("Session expired. Please sign in again.")
    user = db.get(User, token.user_id)
    if not user or not user.is_active:
        db.commit()
        raise unauthorized()
    csrf = sessions.issue_session(
        db, response, user, family_id=token.family_id, user_agent=request.headers.get("user-agent")
    )
    db.commit()
    return session_out(db, user, csrf)


@router.post("/logout", response_model=Ok)
def logout(request: Request, response: Response, db: SystemDb) -> Ok:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        token = sessions.rotate_refresh_token(db, raw)
        if token:
            sessions.revoke_family(db, token.family_id)
        db.commit()
    sessions.clear_session_cookies(response)
    return Ok()


@router.get("/me", response_model=SessionOut)
def me(request: Request, user: CurrentUser, db: SystemDb) -> SessionOut:
    return session_out(db, user, request.cookies.get(CSRF_COOKIE, ""))


@router.patch("/me", response_model=UserOut)
def update_me(body: MeUpdateIn, user: CurrentUser, db: SystemDb) -> UserOut:
    db_user = db.get(User, user.id)
    assert db_user is not None
    if body.full_name is not None:
        db_user.full_name = body.full_name.strip()
    if body.ui_language is not None:
        db_user.ui_language = body.ui_language
    db.commit()
    return user_out(db_user)


@router.post("/verify-email/request", response_model=Ok)
def request_verification(
    request: Request, user: CurrentUser, redis: RedisDep, email_provider: EmailDep
) -> Ok:
    _rate_limit(request, redis, "verify")
    if user.email_verified_at is None:
        _send_verification(email_provider, user)
    return Ok()


@router.post("/verify-email", response_model=Ok)
def verify_email(body: TokenIn, db: SystemDb) -> Ok:
    payload = decode_jwt(body.token, "verify_email")
    user = db.get(User, uuid.UUID(payload["sub"])) if payload else None
    if not user or user.email != payload.get("email"):
        raise ApiError(400, "invalid_token", "This link is invalid or has expired.")
    if user.email_verified_at is None:
        user.email_verified_at = now()
        db.commit()
    return Ok()


@router.post("/password-reset/request", response_model=Ok)
def request_password_reset(
    body: EmailIn, request: Request, db: SystemDb, redis: RedisDep, email_provider: EmailDep
) -> Ok:
    _rate_limit(request, redis, "reset")
    user = db.scalar(select(User).where(User.email == accounts.normalize_email(body.email)))
    if user and user.is_active:
        token = encode_jwt(
            {
                "sub": str(user.id),
                "purpose": "password_reset",
                "fp": password_fingerprint(user.password_hash),
            },
            timedelta(hours=1),
        )
        link = f"{get_settings().app_url}/reset-password?token={token}"
        email_provider.send(
            Email(
                to=user.email,
                subject=t(user.ui_language, "email.reset.subject"),
                text=t(user.ui_language, "email.reset.body", name=user.full_name, link=link),
            )
        )
    return Ok()  # same answer whether or not the account exists


@router.post("/password-reset", response_model=Ok)
def reset_password(body: PasswordResetIn, request: Request, db: SystemDb, redis: RedisDep) -> Ok:
    _rate_limit(request, redis, "reset")
    payload = decode_jwt(body.token, "password_reset")
    user = db.get(User, uuid.UUID(payload["sub"])) if payload else None
    if not user or payload.get("fp") != password_fingerprint(user.password_hash):
        raise ApiError(400, "invalid_token", "This link is invalid or has expired.")
    user.password_hash = hash_password(body.password)
    sessions.revoke_all_for_user(db, user.id)
    audit.record(
        db, "user.password_reset", org_id=None, actor_user_id=user.id, ip=client_ip(request)
    )
    db.commit()
    return Ok()


# --- Google sign-in (OIDC authorization code + PKCE) -------------------------------------


def _safe_next(next_path: str | None) -> str:
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/app"


def _google_redirect_uri() -> str:
    return f"{get_settings().api_url}/auth/google/callback"


@router.get("/google/start", include_in_schema=True)
def google_start(next: Annotated[str | None, Query(max_length=500)] = None) -> RedirectResponse:
    s = get_settings()
    if not s.google_oauth_client_id:
        return RedirectResponse(f"{s.app_url}/login?error=google_unavailable", status_code=302)
    state, nonce, verifier = new_token(), new_token(), new_token(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    params = {
        "client_id": s.google_oauth_client_id,
        "redirect_uri": _google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge.decode(),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=302)
    cookie = encode_jwt(
        {
            "purpose": "google_oauth",
            "state": state,
            "nonce": nonce,
            "v": verifier,
            "next": _safe_next(next),
        },
        timedelta(minutes=10),
    )
    response.set_cookie(
        GOOGLE_STATE_COOKIE,
        cookie,
        max_age=600,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path="/auth/google",
    )
    return response


def verify_google_id_token(id_token: str) -> dict:
    """Verify signature, audience and issuer of a Google ID token."""
    client = jwt.PyJWKClient(GOOGLE_JWKS_URL)
    key = client.get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        key.key,
        algorithms=["RS256"],
        audience=get_settings().google_oauth_client_id,
        issuer=["https://accounts.google.com", "accounts.google.com"],
    )


@router.get("/google/callback")
def google_callback(
    request: Request,
    db: SystemDb,
    code: Annotated[str | None, Query(max_length=2000)] = None,
    state: Annotated[str | None, Query(max_length=500)] = None,
) -> RedirectResponse:
    s = get_settings()
    fail = RedirectResponse(f"{s.app_url}/login?error=google", status_code=302)
    saved = decode_jwt(request.cookies.get(GOOGLE_STATE_COOKIE, ""), "google_oauth")
    if not code or not saved or state != saved.get("state"):
        return fail

    token_resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": s.google_oauth_client_id,
            "client_secret": s.google_oauth_client_secret,
            "redirect_uri": _google_redirect_uri(),
            "grant_type": "authorization_code",
            "code_verifier": saved["v"],
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        return fail
    try:
        claims = verify_google_id_token(token_resp.json()["id_token"])
    except (jwt.PyJWTError, KeyError):
        return fail
    if claims.get("nonce") != saved.get("nonce") or not claims.get("email_verified"):
        return fail

    sub, email = claims["sub"], accounts.normalize_email(claims["email"])
    user = db.scalar(select(User).where(User.google_sub == sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.google_sub = sub  # link: Google verified ownership of this email
            user.email_verified_at = user.email_verified_at or now()
        else:
            user = accounts.create_user(
                db,
                email=email,
                full_name=claims.get("name") or email.split("@")[0],
                password_hash=None,
                google_sub=sub,
                email_verified=True,
            )
            accounts.create_org(db, f"{user.full_name}'s organization", user)
    if not user.is_active:
        return fail
    user.last_login_at = now()
    response = RedirectResponse(f"{s.app_url}{saved['next']}", status_code=302)
    sessions.issue_session(db, response, user, user_agent=request.headers.get("user-agent"))
    response.delete_cookie(GOOGLE_STATE_COOKIE, path="/auth/google")
    db.commit()
    return response
