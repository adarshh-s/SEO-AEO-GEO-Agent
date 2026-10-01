"""deep integrations (Phase 4)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. site_integrations
    op.create_table(
        "site_integrations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "credentials",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('wordpress', 'shopify', 'github', 'cloudflare', 'google_search_console', 'webflow', 'wix')",
            name=op.f("ck_site_integrations_site_integration_provider"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'error', 'pending', 'disconnected')",
            name=op.f("ck_site_integrations_site_integration_status"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_site_integrations_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_site_integrations_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_integrations")),
        sa.UniqueConstraint("site_id", "provider", name=op.f("uq_site_integrations_site_provider")),
    )
    op.create_index(
        op.f("ix_site_integrations_org_id"), "site_integrations", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_site_integrations_site_id"), "site_integrations", ["site_id"], unique=False
    )
    op.create_index(
        op.f("ix_site_integrations_provider"), "site_integrations", ["provider"], unique=False
    )

    # 2. Add external_reference to fixes
    op.add_column("fixes", sa.Column("external_reference", sa.Text(), nullable=True))

    # 3. RLS for site_integrations
    op.execute("ALTER TABLE site_integrations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON site_integrations USING (org_id = app_current_org())"
        " WITH CHECK (org_id = app_current_org())"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON site_integrations TO app_tenant")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON site_integrations")
    op.drop_table("site_integrations")
    op.drop_column("fixes", "external_reference")
