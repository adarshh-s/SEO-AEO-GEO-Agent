"""Site ownership verification via HTML meta tag or DNS TXT record."""

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app_api.deps import Admin, Tenant, TenantDb
from app_api.errors import ApiError
from app_api.ratelimit import client_ip
from app_api.routers.sites import get_site
from app_api.schemas.verification import VerificationStatusOut, VerifyAttemptOut
from app_api.services import audit
from app_core.brand import BRAND
from app_core.net import safe_get  # SSRF-safe, thread-safe (runs in the API)

VERIFIER_UA = f"{BRAND['product_name']}-Verifier/1.0"

router = APIRouter(prefix="/sites/{site_id}", tags=["verification"])


@router.get("/verification", response_model=VerificationStatusOut)
def get_verification_status(
    site_id: uuid.UUID,
    ctx: Tenant,
    db: TenantDb,
) -> VerificationStatusOut:
    site = get_site(db, ctx, site_id)
    meta_name = BRAND["verification_meta_name"]
    dns_prefix = BRAND["dns_txt_prefix"]

    return VerificationStatusOut(
        domain=site.domain,
        verified=site.verified_at is not None,
        verified_at=site.verified_at,
        verification_method=site.verification_method,
        token=site.verification_token,
        meta_tag=f'<meta name="{meta_name}" content="{site.verification_token}">',
        dns_txt_record=f"{dns_prefix}{site.verification_token}",
    )


@router.post("/verify", response_model=VerifyAttemptOut)
def verify_site_ownership(
    site_id: uuid.UUID,
    request: Request,
    ctx: Admin,
    db: TenantDb,
) -> VerifyAttemptOut:
    site = get_site(db, ctx, site_id)
    meta_name = BRAND["verification_meta_name"]
    dns_prefix = BRAND["dns_txt_prefix"]
    token = site.verification_token

    # 1. Check HTML Meta tag
    meta_verified = False
    try:
        resp = safe_get(site.homepage_url, timeout=10, headers={"User-Agent": VERIFIER_UA})
        if resp.status_code == 200:
            pattern = re.compile(
                rf'<meta[^>]+name=["\']{re.escape(meta_name)}["\'][^>]+content=["\']{re.escape(token)}["\']',
                re.IGNORECASE,
            )
            pattern_rev = re.compile(
                rf'<meta[^>]+content=["\']{re.escape(token)}["\'][^>]+name=["\']{re.escape(meta_name)}["\']',
                re.IGNORECASE,
            )
            if pattern.search(resp.text) or pattern_rev.search(resp.text):
                meta_verified = True
    except Exception:
        meta_verified = False

    if meta_verified:
        site.verified_at = datetime.now(UTC)
        site.verification_method = "meta_tag"
        audit.record(
            db,
            "site.verified",
            org_id=ctx.org_id,
            actor_user_id=ctx.user_id,
            target_type="site",
            target_id=site.id,
            data={"method": "meta_tag"},
            ip=client_ip(request),
        )
        db.commit()
        return VerifyAttemptOut(
            verified=True,
            method="meta_tag",
            message="Domain ownership successfully verified via HTML meta tag!",
        )

    # 2. Check DNS TXT record
    dns_verified = False
    expected_txt = f"{dns_prefix}{token}"
    try:
        # Check standard dns query if dnspython installed, otherwise basic check
        import dns.resolver

        answers = dns.resolver.resolve(site.domain, "TXT")
        for rdata in answers:
            for txt_string in rdata.strings:
                if expected_txt in txt_string.decode("utf-8", errors="ignore"):
                    dns_verified = True
                    break
    except Exception:
        dns_verified = False

    if dns_verified:
        site.verified_at = datetime.now(UTC)
        site.verification_method = "dns_txt"
        audit.record(
            db,
            "site.verified",
            org_id=ctx.org_id,
            actor_user_id=ctx.user_id,
            target_type="site",
            target_id=site.id,
            data={"method": "dns_txt"},
            ip=client_ip(request),
        )
        db.commit()
        return VerifyAttemptOut(
            verified=True,
            method="dns_txt",
            message="Domain ownership successfully verified via DNS TXT record!",
        )

    raise ApiError(
        400,
        "verification_failed",
        f'Verification failed. Could not find <meta name="{meta_name}" content="{token}"> on {site.homepage_url} or DNS TXT record \'{expected_txt}\' on {site.domain}.',
    )
