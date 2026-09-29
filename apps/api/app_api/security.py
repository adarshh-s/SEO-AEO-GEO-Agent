"""Passwords, JWTs, refresh tokens and CSRF tokens."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app_core.settings import get_settings

_hasher = PasswordHasher()
JWT_ALG = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def now() -> datetime:
    return datetime.now(UTC)


def encode_jwt(claims: dict[str, Any], ttl: timedelta) -> str:
    issued = now()
    payload = {**claims, "iat": issued, "exp": issued + ttl}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=JWT_ALG)


def decode_jwt(token: str, purpose: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload


def access_token_for(user_id: uuid.UUID) -> str:
    ttl = timedelta(minutes=get_settings().access_token_ttl_minutes)
    return encode_jwt({"sub": str(user_id), "purpose": "access"}, ttl)


def password_fingerprint(password_hash: str | None) -> str:
    """Short hash of the current password hash: makes reset tokens single-use."""
    return sha256_hex(password_hash or "none")[:16]
