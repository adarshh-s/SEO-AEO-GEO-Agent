"""Organizations, members and invitations."""

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app_api.deps import CSRF_COOKIE, Admin, CurrentUser, SystemDb, Tenant, TenantDb
from app_api.errors import ApiError, forbidden, not_found
from app_api.providers.email import Email, EmailProvider, get_email_provider
from app_api.ratelimit import client_ip
from app_api.routers.auth import session_out
from app_api.schemas.auth import OrgSummary, SessionOut, TokenIn
from app_api.schemas.common import Ok
from app_api.schemas.orgs import (
    InvitationIn,
    InvitationOut,
    MemberOut,
    MemberUpdateIn,
    OrgCreateIn,
    OrgOut,
    OrgUpdateIn,
    PlanOut,
    UsageOut,
)
from app_api.security import new_token, now, sha256_hex
from app_api.services import accounts, audit
from app_core.enums import MembershipRole
from app_core.i18n import t
from app_core.models import AiPrompt, Invitation, Keyword, Membership, Organization, Site, User
from app_core.settings import get_settings
from app_core.tenancy import scoped

router = APIRouter(tags=["organizations"])
EmailDep = Annotated[EmailProvider, Depends(get_email_provider)]


@router.get("/orgs", response_model=list[OrgSummary])
def list_my_orgs(user: CurrentUser, db: SystemDb) -> list[OrgSummary]:
    return [
        OrgSummary(id=o.id, name=o.name, slug=o.slug, role=role, plan_code=o.plan.code)
        for o, role in accounts.user_orgs(db, user.id)
    ]


@router.post("/orgs", response_model=OrgSummary, status_code=201)
def create_org(body: OrgCreateIn, request: Request, user: CurrentUser, db: SystemDb) -> OrgSummary:
    org = accounts.create_org(db, body.name, user)
    audit.record(db, "org.created", org_id=org.id, actor_user_id=user.id, ip=client_ip(request))
    db.commit()
    return OrgSummary(
        id=org.id, name=org.name, slug=org.slug, role="owner", plan_code=org.plan.code
    )


def _count(db: TenantDb, model: type, ctx: Tenant) -> int:
    return db.scalar(scoped(select(func.count()).select_from(model), model, ctx)) or 0


@router.get("/org", response_model=OrgOut)
def get_current_org(ctx: Tenant, db: TenantDb) -> OrgOut:
    org = db.get(Organization, ctx.org_id)
    if org is None:
        raise not_found("organization")
    return OrgOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        role=ctx.role,
        plan=PlanOut.model_validate(org.plan),
        addons=org.addons,
        usage=UsageOut(
            sites=_count(db, Site, ctx),
            keywords=_count(db, Keyword, ctx),
            prompts=_count(db, AiPrompt, ctx),
        ),
    )


@router.patch("/org", response_model=Ok)
def update_current_org(body: OrgUpdateIn, request: Request, ctx: Admin, db: TenantDb) -> Ok:
    org = db.get(Organization, ctx.org_id)
    if org is None:
        raise not_found("organization")
    org.name = body.name.strip()
    audit.record(
        db,
        "org.updated",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        data={"name": org.name},
        ip=client_ip(request),
    )
    db.commit()
    return Ok()


# --- members -----------------------------------------------------------------------------


def _member_out(m: Membership) -> MemberOut:
    return MemberOut(
        id=m.id,
        user_id=m.user_id,
        email=m.user.email,
        full_name=m.user.full_name,
        role=m.role,
        created_at=m.created_at,
    )


@router.get("/org/members", response_model=list[MemberOut])
def list_members(ctx: Tenant, db: TenantDb) -> list[MemberOut]:
    rows = db.scalars(scoped(select(Membership), Membership, ctx).order_by(Membership.created_at))
    return [_member_out(m) for m in rows]


def _get_membership(db: TenantDb, ctx: Tenant, membership_id: uuid.UUID) -> Membership:
    m = db.scalar(scoped(select(Membership), Membership, ctx).where(Membership.id == membership_id))
    if m is None:
        raise not_found("member")
    return m


def _owner_count(db: TenantDb, ctx: Tenant) -> int:
    stmt = scoped(select(func.count()).select_from(Membership), Membership, ctx)
    return db.scalar(stmt.where(Membership.role == MembershipRole.OWNER.value)) or 0


@router.patch("/org/members/{membership_id}", response_model=MemberOut)
def update_member(
    membership_id: uuid.UUID, body: MemberUpdateIn, request: Request, ctx: Admin, db: TenantDb
) -> MemberOut:
    m = _get_membership(db, ctx, membership_id)
    touches_owner = MembershipRole.OWNER.value in (m.role, body.role)
    if touches_owner and ctx.role != MembershipRole.OWNER.value:
        raise forbidden("Only an owner can grant or remove the owner role.")
    if m.role == MembershipRole.OWNER.value and body.role != m.role and _owner_count(db, ctx) <= 1:
        raise ApiError(409, "last_owner", "An organization needs at least one owner.")
    old = m.role
    m.role = body.role
    audit.record(
        db,
        "member.role_changed",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="membership",
        target_id=m.id,
        data={"from": old, "to": body.role},
        ip=client_ip(request),
    )
    db.commit()
    return _member_out(m)


@router.delete("/org/members/{membership_id}", response_model=Ok)
def remove_member(membership_id: uuid.UUID, request: Request, ctx: Tenant, db: TenantDb) -> Ok:
    m = _get_membership(db, ctx, membership_id)
    is_self = m.user_id == ctx.user_id
    if not is_self and ctx.role not in (MembershipRole.ADMIN.value, MembershipRole.OWNER.value):
        raise forbidden()
    if m.role == MembershipRole.OWNER.value:
        if not is_self and ctx.role != MembershipRole.OWNER.value:
            raise forbidden("Only an owner can remove an owner.")
        if _owner_count(db, ctx) <= 1:
            raise ApiError(409, "last_owner", "An organization needs at least one owner.")
    audit.record(
        db,
        "member.removed",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="user",
        target_id=m.user_id,
        ip=client_ip(request),
    )
    db.delete(m)
    db.commit()
    return Ok()


# --- invitations -------------------------------------------------------------------------

INVITE_TTL = timedelta(days=7)


@router.get("/org/invitations", response_model=list[InvitationOut])
def list_invitations(ctx: Admin, db: TenantDb) -> list[InvitationOut]:
    rows = db.scalars(
        scoped(select(Invitation), Invitation, ctx)
        .where(Invitation.accepted_at.is_(None))
        .order_by(Invitation.created_at.desc())
    )
    return [InvitationOut.model_validate(i) for i in rows]


@router.post("/org/invitations", response_model=InvitationOut, status_code=201)
def create_invitation(
    body: InvitationIn,
    request: Request,
    ctx: Admin,
    db: TenantDb,
    user: CurrentUser,
    email_provider: EmailDep,
) -> InvitationOut:
    email = accounts.normalize_email(body.email)
    already = db.scalar(
        scoped(select(Membership.id), Membership, ctx)
        .join(User, User.id == Membership.user_id)
        .where(User.email == email)
    )
    if already:
        raise ApiError(409, "already_member", "This person is already a member.")
    raw = new_token()
    inv = Invitation(
        org_id=ctx.org_id,
        email=email,
        role=body.role,
        token_hash=sha256_hex(raw),
        invited_by=ctx.user_id,
        expires_at=now() + INVITE_TTL,
    )
    db.add(inv)
    org = db.get(Organization, ctx.org_id)
    audit.record(
        db,
        "invitation.created",
        org_id=ctx.org_id,
        actor_user_id=ctx.user_id,
        target_type="invitation",
        data={"email": email, "role": body.role},
        ip=client_ip(request),
    )
    db.commit()
    lang = user.ui_language
    link = f"{get_settings().app_url}/accept-invite?token={raw}"
    email_provider.send(
        Email(
            to=email,
            subject=t(lang, "email.invite.subject", inviter=user.full_name, org=org.name),
            text=t(
                lang,
                "email.invite.body",
                inviter=user.full_name,
                org=org.name,
                role=t(lang, f"role.{body.role}"),
                link=link,
            ),
        )
    )
    return InvitationOut.model_validate(inv)


@router.delete("/org/invitations/{invitation_id}", response_model=Ok)
def revoke_invitation(invitation_id: uuid.UUID, ctx: Admin, db: TenantDb) -> Ok:
    inv = db.scalar(
        scoped(select(Invitation), Invitation, ctx).where(Invitation.id == invitation_id)
    )
    if inv is None:
        raise not_found("invitation")
    db.delete(inv)
    db.commit()
    return Ok()


@router.post("/invitations/accept", response_model=SessionOut)
def accept_invitation(
    body: TokenIn, request: Request, user: CurrentUser, db: SystemDb
) -> SessionOut:
    """Cross-org by nature (the user isn't a member yet), so it uses the system session."""
    inv = db.scalar(select(Invitation).where(Invitation.token_hash == sha256_hex(body.token)))
    if inv is None or inv.accepted_at is not None or inv.expires_at <= now():
        raise ApiError(400, "invalid_token", "This invitation is invalid or has expired.")
    if inv.email != user.email:
        raise ApiError(
            403, "invite_email_mismatch", "This invitation was sent to a different email address."
        )
    exists = db.scalar(
        select(Membership.id).where(Membership.org_id == inv.org_id, Membership.user_id == user.id)
    )
    if not exists:
        db.add(Membership(org_id=inv.org_id, user_id=user.id, role=inv.role))
    inv.accepted_at = now()
    audit.record(
        db,
        "invitation.accepted",
        org_id=inv.org_id,
        actor_user_id=user.id,
        target_type="invitation",
        target_id=inv.id,
        ip=client_ip(request),
    )
    db.commit()
    return session_out(db, user, request.cookies.get(CSRF_COOKIE, ""))
