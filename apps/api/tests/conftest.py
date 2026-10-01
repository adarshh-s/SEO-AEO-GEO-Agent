"""API test fixtures: a freshly migrated Postgres test DB, fake Redis, in-memory email."""

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import fakeredis
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/app_test"
)
os.environ["DATABASE_URL"] = BASE_URL
os.environ.setdefault("ENV", "test")
os.environ["EMAIL_PROVIDER"] = "console"
os.environ["APP_URL"] = "http://app.test"
os.environ["API_URL"] = "http://api.test"
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test-client-id"
os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "test-client-secret"
os.environ["JWT_SECRET"] = "test-secret-with-enough-length-for-hs256-0123456789"

API_DIR = Path(__file__).resolve().parents[1]


def _recreate_database() -> None:
    url = make_url(BASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    from alembic import command
    from alembic.config import Config

    _recreate_database()
    command.upgrade(Config(str(API_DIR / "alembic.ini")), "head")
    from app_core.db import get_engine

    with get_engine().begin() as conn:  # pristine copy of the default plans
        conn.execute(text("CREATE TABLE _plans_snapshot AS SELECT * FROM plans"))
    yield


TABLES_TO_RESET = [
    "ai_referral_events",
    "webhooks",
    "api_keys",
    "fixes",
    "diagnoses",
    "usage_counters",
    "visibility_scores",
    "ai_checks",
    "rank_checks",
    "crawl_snapshots",
    "audit_log",
    "refresh_tokens",
    "invitations",
    "keywords",
    "ai_prompts",
    "sites",
    "subscriptions",
    "memberships",
    "organizations",
    "users",
]


@pytest.fixture(autouse=True)
def clean_db(database: None) -> Iterator[None]:
    yield
    from app_core.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLES_TO_RESET)} CASCADE"))
        conn.execute(text("DELETE FROM plans"))
        conn.execute(text("INSERT INTO plans SELECT * FROM _plans_snapshot"))


@pytest.fixture
def redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def mock_celery(monkeypatch):
    import celery

    sent = []

    def _fake_send_task(self, name, args=None, kwargs=None, **opts):
        sent.append((name, args or [], kwargs or {}, opts))

        class FakeAsyncResult:
            id = "fake-task-id"

        return FakeAsyncResult()

    monkeypatch.setattr(celery.Celery, "send_task", _fake_send_task)
    return sent


@pytest.fixture
def outbox():
    from app_api.providers.email import ConsoleEmailProvider

    return ConsoleEmailProvider()


@pytest.fixture
def app(redis, outbox):
    from app_api import ratelimit
    from app_api.main import app as fastapi_app
    from app_api.providers.email import get_email_provider

    fastapi_app.dependency_overrides[ratelimit.get_redis] = lambda: redis
    fastapi_app.dependency_overrides[get_email_provider] = lambda: outbox
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@dataclass
class Account:
    client: object  # TestClient
    user_id: uuid.UUID
    org_id: uuid.UUID
    email: str


def make_client(app):
    from fastapi.testclient import TestClient

    return TestClient(app, base_url="http://api.test")


def signup(
    app,
    email: str | None = None,
    org_name: str = "Acme",
    ui_language: str = "en",
    verified: bool = True,
) -> Account:
    client = make_client(app)
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "correct-horse-battery",
            "full_name": "Test User",
            "org_name": org_name,
            "ui_language": ui_language,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    org_id = body["orgs"][0]["id"]
    client.headers.update({"X-CSRF-Token": body["csrf_token"], "X-Org-Id": org_id})
    user_id = uuid.UUID(body["user"]["id"])
    if verified:
        from datetime import UTC, datetime

        from app_core.db import system_session
        from app_core.models import User

        with system_session() as db:
            user = db.get(User, user_id)
            if user:
                user.email_verified_at = datetime.now(UTC)
    return Account(client, user_id, uuid.UUID(org_id), email)


@pytest.fixture
def account(app) -> Account:
    return signup(app)


def make_platform_admin(user_id: uuid.UUID) -> None:
    from app_core.db import system_session
    from app_core.models import User

    with system_session() as db:
        db.get(User, user_id).is_platform_admin = True


def set_plan(org_id: uuid.UUID, code: str, addons: dict | None = None) -> None:
    from sqlalchemy import select

    from app_core.db import system_session
    from app_core.models import Organization, Plan

    with system_session() as db:
        org = db.get(Organization, org_id)
        org.plan_id = db.scalar(select(Plan.id).where(Plan.code == code))
        if addons is not None:
            org.addons = addons


SITE = {
    "homepage_url": "https://www.Example.com/about",
    "name": "Example",
    "primary_language": "en",
    "default_country": "SA",
}
