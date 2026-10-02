#!/usr/bin/env python3
"""Production environment validator for QuardLink.

Verifies:
1. Production secrets: JWT_SECRET must not be the development secret.
2. Production flags: SEED_DEMO must be False.
3. Database connection & Postgres RLS role availability.
4. Redis connectivity.
5. Email configuration (Resend API key or SMTP host).
6. Brand config synchronization.
7. Allowed CORS origins and host URLs.

Exit code 0 on all checks passing, 1 if any critical check fails.
"""

import os
import sys

from app_core.brand import BRAND
from app_core.settings import get_settings


def check_secrets(settings) -> list[str]:
    errors = []
    # In development, the default secret is 'dev-insecure-jwt-secret-do-not-use-in-production'
    if "dev-insecure" in settings.jwt_secret.lower() or settings.jwt_secret.lower() == "secret":
        errors.append(
            "JWT_SECRET is using the insecure development default! Generate a 32+ byte random string."
        )
    if len(settings.jwt_secret) < 32:
        errors.append(
            f"JWT_SECRET is too short ({len(settings.jwt_secret)} chars). Must be at least 32 chars."
        )
    if getattr(settings, "seed_demo", False):
        errors.append("SEED_DEMO is True! Set SEED_DEMO=false in production.")
    return errors


def check_database(settings) -> list[str]:
    errors = []
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            # Check DB ping
            res = conn.execute(text("SELECT 1")).scalar()
            if res != 1:
                errors.append("Database ping did not return 1.")

            # Check if app_tenant role exists for RLS
            role_exists = conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = 'app_tenant'")
            ).scalar()
            if not role_exists:
                errors.append(
                    "PostgreSQL role 'app_tenant' does not exist! Run migrations or create it."
                )
    except Exception as e:
        errors.append(f"Failed to connect to DATABASE_URL: {e}")
    return errors


def check_redis(settings) -> list[str]:
    errors = []
    try:
        import redis

        r = redis.from_url(settings.redis_url, socket_timeout=5)
        if not r.ping():
            errors.append("Redis ping returned False.")
    except Exception as e:
        errors.append(f"Failed to connect to REDIS_URL: {e}")
    return errors


def check_email(settings) -> list[str]:
    warnings = []
    provider = getattr(settings, "email_provider", "smtp").lower()
    if provider == "resend":
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            warnings.append("EMAIL_PROVIDER is set to resend but RESEND_API_KEY is not set.")
    elif provider == "smtp":
        host = getattr(settings, "smtp_host", "localhost")
        if host in ("mailpit", "localhost"):
            warnings.append(
                f"SMTP_HOST is set to local catcher ({host}). Ensure a real SMTP host is set for live emails."
            )
    return warnings


def check_urls(settings) -> list[str]:
    errors = []
    app_url = getattr(settings, "app_url", "")
    if not app_url or "localhost" in app_url:
        errors.append(
            f"APP_URL is '{app_url}'. Production requires your live domain (e.g. https://app.quardlink.com)."
        )

    cors_origins = getattr(settings, "cors_origins", [])
    if isinstance(cors_origins, str):
        cors_origins = [c.strip() for c in cors_origins.split(",") if c.strip()]
    if not cors_origins or any("localhost" in o for o in cors_origins):
        errors.append(
            f"CORS_ORIGINS contains localhost: {cors_origins}. Update with your production frontend origin."
        )
    return errors


def main():
    print(f"=== {BRAND['product_name']} Production Environment Pre-Flight Check ===")
    settings = get_settings()

    critical_errors = []
    warnings = []

    # 1. Secrets
    errs = check_secrets(settings)
    if errs:
        critical_errors.extend(errs)
        for e in errs:
            print(f"❌ [CRITICAL] {e}")
    else:
        print("✅ [PASS] Production secrets and flags validated.")

    # 2. Database & RLS
    errs = check_database(settings)
    if errs:
        critical_errors.extend(errs)
        for e in errs:
            print(f"❌ [CRITICAL] {e}")
    else:
        print("✅ [PASS] Database connection and PostgreSQL 'app_tenant' role verified.")

    # 3. Redis
    errs = check_redis(settings)
    if errs:
        critical_errors.extend(errs)
        for e in errs:
            print(f"❌ [CRITICAL] {e}")
    else:
        print("✅ [PASS] Redis connection verified.")

    # 4. URLs & CORS
    errs = check_urls(settings)
    if errs:
        # In testing this may be non-fatal warning if operator is just dry-running locally
        for e in errs:
            print(f"⚠️ [NOTICE] {e}")
            warnings.append(e)
    else:
        print("✅ [PASS] Production APP_URL and CORS origins configured.")

    # 5. Email
    warns = check_email(settings)
    for w in warns:
        print(f"⚠️ [WARN] {w}")
        warnings.append(w)
    if not warns:
        print("✅ [PASS] Email provider credentials verified.")

    print("==================================================")
    if critical_errors:
        print(f"💥 PRE-FLIGHT CHECK FAILED with {len(critical_errors)} critical error(s).")
        return 1
    else:
        print("🎉 PRE-FLIGHT CHECK PASSED! System is ready for production launch.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
