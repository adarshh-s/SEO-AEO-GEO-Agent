"""Request dependencies: DB sessions, authentication, CSRF, tenant context, roles."""

import hmac
import uuid
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app_api.errors import ApiError, forbidden, unauthorized
from app_api.security import decode_jwt
from app_core.db import get_sessionmaker
from app_core.enums import ROLE_RANK, MembershipRole
from app_core.models import Membership, User
from app_core.tenancy import TenantContext, open_tenant_session

ACCESS_COOKIE = "app_at"
REFRESH_COOKIE = "app_rt"
CSRF_COOKIE = "app_csrf"
CSRF_HEADER = "X-CSRF-Token"
ORG_HEADER = "X-Org-Id"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_system_db() -> Iterator[Session]:
    """Owner-role session (bypasses RLS). For auth, /me, and platform admin only."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


SystemDb = Annotated[Session, Depends(get_system_db)]


def check_csrf(request: Request) -> None:
    """Double-submit check for cookie-authenticated, state-changing requests.

    The token lives in an httpOnly cookie and is also handed to the SPA in JSON
    (login/refresh/me), which echoes it in the X-CSRF-Token header.
    """
    if request.method in SAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise ApiError(403, "csrf_failed", "Security check failed. Reload the page and try again.")


def get_current_user(request: Request, db: SystemDb) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    payload = decode_jwt(token, "access") if token else None
    if not payload:
        raise unauthorized()
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise unauthorized()
    check_csrf(request)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_tenant(
    user: CurrentUser,
    db: SystemDb,
    x_org_id: Annotated[str | None, Header(alias=ORG_HEADER)] = None,
) -> TenantContext:
    """Resolve the active org from the X-Org-Id header and check membership."""
    if not x_org_id:
        raise ApiError(400, "org_required", f"Missing {ORG_HEADER} header.")
    try:
        org_id = uuid.UUID(x_org_id)
    except ValueError:
        raise ApiError(400, "org_required", f"Invalid {ORG_HEADER} header.") from None
    membership = db.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user.id)
    )
    if not membership:
        # Same answer whether the org exists or not.
        raise forbidden("You are not a member of this organization.")
    return TenantContext(org_id=org_id, user_id=user.id, role=membership.role)


Tenant = Annotated[TenantContext, Depends(get_tenant)]


def get_tenant_db(ctx: Tenant) -> Iterator[Session]:
    """RLS-confined session for the active org. Endpoints commit explicitly."""
    session = open_tenant_session(ctx.org_id, ctx.user_id)
    try:
        yield session
    finally:
        session.close()


TenantDb = Annotated[Session, Depends(get_tenant_db)]


def require_role(minimum: MembershipRole) -> Callable[[TenantContext], TenantContext]:
    def dependency(ctx: Tenant) -> TenantContext:
        if ROLE_RANK[MembershipRole(ctx.role)] < ROLE_RANK[minimum]:
            raise forbidden()
        return ctx

    return dependency


Viewer = Tenant
Member = Annotated[TenantContext, Depends(require_role(MembershipRole.MEMBER))]
Admin = Annotated[TenantContext, Depends(require_role(MembershipRole.ADMIN))]
Owner = Annotated[TenantContext, Depends(require_role(MembershipRole.OWNER))]


def get_platform_admin(user: CurrentUser) -> User:
    if not user.is_platform_admin:
        raise forbidden()
    return user


PlatformAdmin = Annotated[User, Depends(get_platform_admin)]
