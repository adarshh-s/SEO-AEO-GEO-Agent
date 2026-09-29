"""Login sessions: access JWT + rotating refresh token + CSRF token, all in httpOnly cookies."""

import uuid
from datetime import timedelta

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app_api.deps import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE
from app_api.security import access_token_for, new_token, now, sha256_hex
from app_core.logging import get_logger
from app_core.models import RefreshToken, User
from app_core.settings import get_settings

log = get_logger(__name__)
REFRESH_PATH = "/auth"


def _set_cookie(response: Response, name: str, value: str, max_age: int, path: str = "/") -> None:
    s = get_settings()
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        path=path,
        domain=s.cookie_domain,
        secure=s.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def issue_session(
    db: Session,
    response: Response,
    user: User,
    *,
    family_id: uuid.UUID | None = None,
    user_agent: str | None = None,
) -> str:
    """Create a refresh token (new or same family), set all cookies. Returns the CSRF token."""
    s = get_settings()
    raw_refresh = new_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=sha256_hex(raw_refresh),
            expires_at=now() + timedelta(days=s.refresh_token_ttl_days),
            created_at=now(),
            user_agent=(user_agent or "")[:400],
        )
    )
    csrf = new_token(24)
    refresh_age = s.refresh_token_ttl_days * 86400
    _set_cookie(response, ACCESS_COOKIE, access_token_for(user.id), s.access_token_ttl_minutes * 60)
    _set_cookie(response, REFRESH_COOKIE, raw_refresh, refresh_age, path=REFRESH_PATH)
    _set_cookie(response, CSRF_COOKIE, csrf, refresh_age)
    return csrf


def rotate_refresh_token(db: Session, raw_refresh: str) -> RefreshToken | None:
    """Mark the presented token as rotated. Reuse of a rotated token revokes the whole family."""
    token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(raw_refresh))
    )
    if token is None or token.revoked_at is not None or token.expires_at <= now():
        return None
    if token.rotated_at is not None:
        log.warning("auth.refresh_reuse_detected", user_id=str(token.user_id))
        revoke_family(db, token.family_id)
        return None
    token.rotated_at = now()
    return token


def revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now())
    )


def revoke_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now())
    )


def clear_session_cookies(response: Response) -> None:
    s = get_settings()
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, REFRESH_PATH), (CSRF_COOKIE, "/")):
        response.delete_cookie(name, path=path, domain=s.cookie_domain)
