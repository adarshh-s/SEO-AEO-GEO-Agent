"""Tenant isolation, layer 1 (code) and layer 2 (Postgres RLS).

Layer 1: tenant-owned rows are read through `scoped()`, which adds `org_id = :org`.
Layer 2: tenant sessions run `SET LOCAL ROLE app_tenant` and set `app.org_id` /
`app.user_id` at the start of every transaction. RLS policies (see the Alembic
migration) only expose rows of that org. A forgotten filter returns nothing
instead of another org's data.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, event, text
from sqlalchemy.orm import Session

from app_core.db import get_sessionmaker

TENANT_ROLE = "app_tenant"


@dataclass(frozen=True)
class TenantContext:
    org_id: uuid.UUID
    user_id: uuid.UUID | None
    role: str  # membership role: owner | admin | member | viewer


def open_tenant_session(org_id: uuid.UUID, user_id: uuid.UUID | None = None) -> Session:
    """Session whose every transaction is confined to one org by RLS."""
    session = get_sessionmaker()()

    @event.listens_for(session, "after_begin")
    def _after_begin(sess: Session, transaction: Any, connection: Any) -> None:
        connection.execute(text(f"SET LOCAL ROLE {TENANT_ROLE}"))
        connection.execute(
            text(
                "SELECT set_config('app.org_id', :org, true),"
                " set_config('app.user_id', :usr, true)"
            ),
            {"org": str(org_id), "usr": str(user_id) if user_id else ""},
        )

    return session


@contextmanager
def tenant_session(org_id: uuid.UUID, user_id: uuid.UUID | None = None) -> Iterator[Session]:
    """Context-managed tenant session. Commits on success."""
    session = open_tenant_session(org_id, user_id)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def scoped[T: Select[Any]](stmt: T, model: Any, ctx: TenantContext) -> T:
    """Layer-1 filter: restrict a select on a tenant-owned model to the context's org."""
    return stmt.where(model.org_id == ctx.org_id)
