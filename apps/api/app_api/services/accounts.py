"""Users and organizations."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app_api.errors import ApiError
from app_api.security import new_token, now
from app_core.enums import MembershipRole
from app_core.languages import DEFAULT_LANGUAGE, SUPPORTED_UI_LANGUAGES
from app_core.models import Membership, Organization, Plan, User
from app_core.settings import get_settings


def normalize_email(email: str) -> str:
    return email.strip().lower()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "org"


def unique_org_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug = f"{base}-{new_token(3).lower().replace('_', '').replace('-', '')[:4]}"
    return slug


def default_plan(db: Session) -> Plan:
    code = get_settings().default_plan_code
    plan = db.scalar(select(Plan).where(Plan.code == code))
    if plan is None:
        raise ApiError(500, "plan_missing", f"Default plan '{code}' is not configured.")
    return plan


def create_org(db: Session, name: str, owner: User) -> Organization:
    org = Organization(
        name=name.strip()[:200],
        slug=unique_org_slug(db, name),
        plan_id=default_plan(db).id,
        plan_assigned_at=now(),
    )
    db.add(org)
    db.flush()
    db.add(Membership(org_id=org.id, user_id=owner.id, role=MembershipRole.OWNER.value))
    db.flush()
    return org


def create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    password_hash: str | None,
    ui_language: str | None = None,
    google_sub: str | None = None,
    email_verified: bool = False,
) -> User:
    email = normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise ApiError(409, "email_taken", "An account with this email already exists.")
    lang = ui_language if ui_language in SUPPORTED_UI_LANGUAGES else DEFAULT_LANGUAGE
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name.strip()[:200],
        password_hash=password_hash,
        ui_language=lang,
        google_sub=google_sub,
        email_verified_at=now() if email_verified else None,
    )
    db.add(user)
    db.flush()
    return user


def user_orgs(db: Session, user_id: uuid.UUID) -> list[tuple[Organization, str]]:
    rows = db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == user_id)
        .order_by(Organization.created_at)
    ).all()
    return [(org, role) for org, role in rows]
