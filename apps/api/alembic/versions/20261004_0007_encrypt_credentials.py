"""encrypt third-party credentials and webhook secrets at rest; fix schema drift

site_integrations.credentials (JSONB) and webhooks.secret (varchar) become Fernet-encrypted
text (see app_core/crypto.py). Existing rows are encrypted in place with APP_ENCRYPTION_KEY,
so set that key before running this migration in an environment with real data.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-04
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app_core.crypto import decrypt, encrypt

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    op.alter_column("site_integrations", "credentials", server_default=None)
    op.alter_column(
        "site_integrations", "credentials", type_=sa.Text(), postgresql_using="credentials::text"
    )
    for row_id, value in conn.execute(sa.text("SELECT id, credentials FROM site_integrations")):
        conn.execute(
            sa.text("UPDATE site_integrations SET credentials = :v WHERE id = :id"),
            {"v": encrypt(json.dumps(json.loads(value or "{}"))), "id": row_id},
        )
    op.alter_column("webhooks", "secret", type_=sa.Text())
    for row_id, value in conn.execute(sa.text("SELECT id, secret FROM webhooks")):
        conn.execute(
            sa.text("UPDATE webhooks SET secret = :v WHERE id = :id"),
            {"v": encrypt(value), "id": row_id},
        )
    # Drift: uniqueness is already enforced by the unique index ix_api_keys_hashed_key.
    op.drop_constraint("uq_api_keys_hashed_key", "api_keys", type_="unique")


def downgrade() -> None:
    conn = op.get_bind()
    op.create_unique_constraint("uq_api_keys_hashed_key", "api_keys", ["hashed_key"])
    for row_id, value in conn.execute(sa.text("SELECT id, secret FROM webhooks")):
        conn.execute(
            sa.text("UPDATE webhooks SET secret = :v WHERE id = :id"),
            {"v": decrypt(value), "id": row_id},
        )
    op.alter_column("webhooks", "secret", type_=sa.String(64))
    for row_id, value in conn.execute(sa.text("SELECT id, credentials FROM site_integrations")):
        conn.execute(
            sa.text("UPDATE site_integrations SET credentials = :v WHERE id = :id"),
            {"v": decrypt(value), "id": row_id},
        )
    op.alter_column(
        "site_integrations",
        "credentials",
        type_=sa.dialects.postgresql.JSONB(),
        postgresql_using="credentials::jsonb",
        server_default=sa.text("'{}'::jsonb"),
    )
