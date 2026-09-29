"""Runtime configuration. Every value comes from env; see .env.example for docs."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "change-me-local-only"  # noqa: S105 (rejected outside local/test)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["local", "test", "staging", "production"] = "local"

    # Hosts (D10: every domain comes from env)
    app_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    cdn_url: str = "http://localhost:8000/cdn"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

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

    # AI visibility
    ai_runs_per_prompt: int = 3

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
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
