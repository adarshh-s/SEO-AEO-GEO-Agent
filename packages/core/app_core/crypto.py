"""Encryption at rest for third-party credentials (CLAUDE.md §11).

APP_ENCRYPTION_KEY holds one or more comma-separated Fernet keys. The first key encrypts;
all keys decrypt, so keys can be rotated by prepending a new one.
Generate a key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app_core.settings import get_settings


@lru_cache
def _fernet() -> MultiFernet:
    keys = [k.strip() for k in get_settings().app_encryption_key.split(",") if k.strip()]
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("cannot decrypt value: wrong or missing APP_ENCRYPTION_KEY") from exc


class EncryptedText(TypeDecorator[str]):
    """A string stored encrypted. Reads and writes plain str in Python."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        return None if value is None else encrypt(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        return None if value is None else decrypt(value)


class EncryptedJSON(TypeDecorator[dict]):
    """A JSON object stored encrypted. Reads and writes dict in Python."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: dict | None, dialect: Any) -> str | None:
        return None if value is None else encrypt(json.dumps(value))

    def process_result_value(self, value: str | None, dialect: Any) -> dict | None:
        return None if value is None else json.loads(decrypt(value))
