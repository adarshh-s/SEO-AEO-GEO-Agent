"""Tenancy layer 2: Postgres row-level security works even when code forgets a filter."""

import uuid

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError

import app_core.models  # noqa: F401
from app_core.db import Base, get_engine
from app_core.models import Keyword, Organization, RefreshToken, Site, User
from app_core.tenancy import tenant_session
from conftest import SITE, set_plan, signup


def test_every_org_owned_table_has_rls_enabled():
    org_tables = {t.name for t in Base.metadata.sorted_tables if "org_id" in t.c} | {
        "organizations",
        "users",
    }
    with get_engine().connect() as conn:
        enabled = {
            r[0]
            for r in conn.execute(
                text("SELECT relname FROM pg_class WHERE relrowsecurity AND relkind = 'r'")
            )
        }
    missing = org_tables - enabled
    assert not missing, f"Tables without RLS: {missing}. Add policies in a migration."


@pytest.fixture
def two_orgs(app):
    a, b = signup(app, org_name="A"), signup(app, org_name="B")
    for acct, domain in ((a, "a.com"), (b, "b.com")):
        set_plan(acct.org_id, "growth")
        site = acct.client.post("/sites", json={**SITE, "homepage_url": domain}).json()
        acct.client.post(
            f"/sites/{site['id']}/keywords", json={"items": [{"keyword": domain, "language": "en"}]}
        )
    return a, b


def test_unfiltered_queries_only_see_own_org(two_orgs):
    a, b = two_orgs
    with tenant_session(a.org_id, a.user_id) as db:
        assert {s.domain for s in db.scalars(select(Site))} == {"a.com"}
        assert {k.keyword for k in db.scalars(select(Keyword))} == {"a.com"}
        assert [o.id for o in db.scalars(select(Organization))] == [a.org_id]
        assert [u.id for u in db.scalars(select(User))] == [a.user_id]


def test_cannot_write_rows_into_another_org(two_orgs):
    a, b = two_orgs
    with pytest.raises(DBAPIError, match="row-level security"):
        with tenant_session(a.org_id, a.user_id) as db:
            site = db.scalar(select(Site))
            site.org_id = b.org_id
    with pytest.raises(DBAPIError, match="row-level security"):
        with tenant_session(a.org_id, a.user_id) as db:
            db.add(
                Site(
                    org_id=b.org_id,
                    domain="evil.com",
                    homepage_url="https://evil.com/",
                    name="x",
                    site_key=f"k{uuid.uuid4().hex}",
                    verification_token="t",
                )
            )


def test_updates_to_other_orgs_affect_nothing(two_orgs):
    a, b = two_orgs
    with tenant_session(a.org_id, a.user_id) as db:
        result = db.execute(
            text("UPDATE sites SET name = 'pwned' WHERE org_id = :b"), {"b": b.org_id}
        )
        assert result.rowcount == 0


def test_tenant_role_cannot_touch_auth_tables(two_orgs):
    a, _ = two_orgs
    with pytest.raises(DBAPIError, match="permission denied"):
        with tenant_session(a.org_id, a.user_id) as db:
            db.execute(select(RefreshToken)).all()


def test_no_org_context_sees_nothing(two_orgs):
    with get_engine().connect() as conn, conn.begin():
        conn.execute(text("SET LOCAL ROLE app_tenant"))
        assert conn.execute(text("SELECT count(*) FROM sites")).scalar() == 0


def test_inspector_sanity():
    assert "sites" in inspect(get_engine()).get_table_names()
