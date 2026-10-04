"""Runtime configuration. Every value comes from env; see .env.example for docs."""

import os
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_JWT_SECRET = (
    "local-dev-only-jwt-secret-change-me-in-env"  # noqa: S105 (rejected outside local/test)
)


# Dev-only Fernet key; rejected outside local/test like the dev JWT secret.
DEV_ENCRYPTION_KEY = "bG9jYWwtZGV2LW9ubHktZW5jcnlwdGlvbi1rZXkhIT0="  # noqa: S105


class Settings(BaseSettings):
    # APP_ENV_FILE lets tests ignore a developer's .env (set it to an empty string).
    model_config = SettingsConfigDict(
        env_file=os.environ.get("APP_ENV_FILE", ".env") or None, extra="ignore"
    )

    env: Literal["local", "test", "staging", "production"] = "local"

    # Hosts (D10: every domain comes from env)
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    cdn_url: str = "http://localhost:8000/cdn"
    worker_url: str | None = None
    # Comma-separated in env (NoDecode: don't try to parse it as JSON first).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # Data stores
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = DEV_JWT_SECRET
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cookie_domain: str | None = None
    cookie_secure: bool = False
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    auth_rate_limit_per_minute: int = 10

    # Encryption at rest for third-party credentials (comma-separated Fernet keys; first encrypts)
    app_encryption_key: str = DEV_ENCRYPTION_KEY

    # Email (D19)
    email_provider: Literal["console", "smtp", "resend"] = "console"
    email_from_address: str = "no-reply@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    resend_api_key: str | None = None

    # Operations
    ops_alert_email: str | None = None
    sentry_dsn: str | None = None
    log_level: str = "INFO"
    log_json: bool = False
    seed_demo: bool = False
    demo_user_password: str = "demo-password-123"  # noqa: S105 (demo seed only; never in prod)

    # Plans (D20: manual assignment; new orgs start on this plan)
    default_plan_code: str = "trial"

    # Retention (D13), in days
    retention_raw_ai_answers_days: int = 395
    retention_html_snapshots_days: int = 90

    # AI + data providers. Model IDs come only from env (CLAUDE.md §4), never from code.
    anthropic_api_key: str | None = None
    claude_model_main: str | None = None  # diagnosis, content
    claude_model_fast: str | None = None  # parsing, extraction, classification
    openai_api_key: str | None = None
    openai_model: str | None = None
    perplexity_api_key: str | None = None
    perplexity_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    google_api_key: str | None = None  # PageSpeed Insights + CrUX

    # Mock AI/SERP providers return fake sample data. Allowed only in local/test, or with
    # USE_MOCK_PROVIDERS=true outside production (never in production).
    use_mock_providers: bool = False

    # AI visibility
    ai_runs_per_prompt: int = 3

    @field_validator("app_encryption_key", mode="before")
    @classmethod
    def _default_encryption_key(cls, v: object) -> object:
        # An empty value means "not configured": fall back to the dev key, which the
        # staging/production check below rejects.
        return v if isinstance(v, str) and v.strip() else DEV_ENCRYPTION_KEY

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def _require_real_secrets(self) -> "Settings":
        if self.env in ("staging", "production"):
            if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be set to a random value of 32+ characters")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true outside local development")
            if self.env == "production" and self.use_mock_providers:
                raise ValueError("USE_MOCK_PROVIDERS must not be enabled in production")
            if not self.app_encryption_key or DEV_ENCRYPTION_KEY in self.app_encryption_key:
                raise ValueError("APP_ENCRYPTION_KEY must be set to a real Fernet key")
        return self

    @property
    def mock_providers_allowed(self) -> bool:
        return self.env in ("local", "test") or (self.use_mock_providers and not self.is_production)

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
