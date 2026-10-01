"""audits, reports, and saudi platforms (Phase 5)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update site_integrations provider check constraint to allow 'salla' and 'zid'
    op.drop_constraint(
        op.f("ck_site_integrations_site_integration_provider"),
        "site_integrations",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_site_integrations_site_integration_provider"),
        "site_integrations",
        "provider IN ('wordpress', 'shopify', 'github', 'cloudflare', 'google_search_console', 'webflow', 'wix', 'salla', 'zid')",
    )

    # 2. audits table
    op.create_table(
        "audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "category_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "issues",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("pages_crawled", sa.Integer(), server_default="1", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_audits_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_audits_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audits")),
    )
    op.create_index(op.f("ix_audits_org_id"), "audits", ["org_id"], unique=False)
    op.create_index(op.f("ix_audits_site_id"), "audits", ["site_id"], unique=False)
    op.create_index(op.f("ix_audits_status"), "audits", ["status"], unique=False)

    # 3. reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("audit_id", sa.UUID(), nullable=True),
        sa.Column("report_type", sa.String(length=40), server_default="audit", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
        sa.Column(
            "metrics_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_reports_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_reports_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["audit_id"],
            ["audits.id"],
            name=op.f("fk_reports_audit_id_audits"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
    )
    op.create_index(op.f("ix_reports_org_id"), "reports", ["org_id"], unique=False)
    op.create_index(op.f("ix_reports_site_id"), "reports", ["site_id"], unique=False)

    # 4. RLS for audits and reports
    op.execute("ALTER TABLE audits ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON audits USING (org_id = app_current_org())"
        " WITH CHECK (org_id = app_current_org())"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON audits TO app_tenant")

    op.execute("ALTER TABLE reports ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON reports USING (org_id = app_current_org())"
        " WITH CHECK (org_id = app_current_org())"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON reports TO app_tenant")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON reports")
    op.drop_table("reports")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audits")
    op.drop_table("audits")

    op.drop_constraint(
        op.f("ck_site_integrations_site_integration_provider"),
        "site_integrations",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_site_integrations_site_integration_provider"),
        "site_integrations",
        "provider IN ('wordpress', 'shopify', 'github', 'cloudflare', 'google_search_console', 'webflow', 'wix')",
    )
