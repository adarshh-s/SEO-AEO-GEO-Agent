"""diagnose, fix, integrations and ai referrals (Phase 3)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TENANT_TABLES = (
    "diagnoses",
    "fixes",
    "api_keys",
    "webhooks",
    "ai_referral_events",
)


def upgrade() -> None:
    # 1. diagnoses
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "competitor_pages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "target_type IN ('keyword', 'prompt')", name=op.f("ck_diagnoses_diagnosis_target_type")
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name=op.f("ck_diagnoses_diagnosis_status"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_diagnoses_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_diagnoses_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnoses")),
    )
    op.create_index(op.f("ix_diagnoses_org_id"), "diagnoses", ["org_id"], unique=False)
    op.create_index(op.f("ix_diagnoses_site_id"), "diagnoses", ["site_id"], unique=False)
    op.create_index(op.f("ix_diagnoses_target_id"), "diagnoses", ["target_id"], unique=False)
    op.create_index(
        "ix_diagnoses_site_target",
        "diagnoses",
        ["site_id", "target_type", "target_id"],
        unique=False,
    )

    # 2. fixes
    op.create_table(
        "fixes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("diagnosis_id", sa.UUID(), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=10), server_default="en", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "recommended_delivery", sa.String(length=30), server_default="snippet", nullable=False
        ),
        sa.Column("status", sa.String(length=30), server_default="proposed", nullable=False),
        sa.Column("deployed_via", sa.String(length=30), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by_user_id", sa.UUID(), nullable=True),
        sa.Column("previous_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "type IN ('schema', 'meta', 'faq', 'content_block', 'technical')",
            name=op.f("ck_fixes_fix_type"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'deployed', 'rejected', 'rolled_back')",
            name=op.f("ck_fixes_fix_status"),
        ),
        sa.ForeignKeyConstraint(
            ["applied_by_user_id"],
            ["users.id"],
            name=op.f("fk_fixes_applied_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["diagnosis_id"],
            ["diagnoses.id"],
            name=op.f("fk_fixes_diagnosis_id_diagnoses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_fixes_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_fixes_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fixes")),
    )
    op.create_index(op.f("ix_fixes_diagnosis_id"), "fixes", ["diagnosis_id"], unique=False)
    op.create_index(op.f("ix_fixes_org_id"), "fixes", ["org_id"], unique=False)
    op.create_index(op.f("ix_fixes_site_id"), "fixes", ["site_id"], unique=False)
    op.create_index(op.f("ix_fixes_status"), "fixes", ["status"], unique=False)
    op.create_index(op.f("ix_fixes_type"), "fixes", ["type"], unique=False)
    op.create_index("ix_fixes_site_status", "fixes", ["site_id", "status"], unique=False)
    op.create_index("ix_fixes_site_url", "fixes", ["site_id", "target_url"], unique=False)

    # 3. api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("prefix", sa.String(length=20), nullable=False),
        sa.Column("hashed_key", sa.String(length=64), nullable=False),
        sa.Column(
            "scopes",
            sa.ARRAY(sa.String(length=50)),
            server_default="{'read:fixes'}",
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
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
            ["created_by"],
            ["users.id"],
            name=op.f("fk_api_keys_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_api_keys_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("hashed_key", name=op.f("uq_api_keys_hashed_key")),
    )
    op.create_index(op.f("ix_api_keys_hashed_key"), "api_keys", ["hashed_key"], unique=True)
    op.create_index(op.f("ix_api_keys_org_id"), "api_keys", ["org_id"], unique=False)
    op.create_index(op.f("ix_api_keys_prefix"), "api_keys", ["prefix"], unique=False)

    # 4. webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column(
            "events",
            sa.ARRAY(sa.String(length=50)),
            server_default="{'fix.proposed','fix.approved','fix.deployed'}",
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
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
            name=op.f("fk_webhooks_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhooks")),
    )
    op.create_index(op.f("ix_webhooks_org_id"), "webhooks", ["org_id"], unique=False)

    # 5. ai_referral_events
    op.create_table(
        "ai_referral_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("referrer_engine", sa.String(length=40), nullable=False),
        sa.Column("user_agent_category", sa.String(length=40), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            name=op.f("fk_ai_referral_events_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_ai_referral_events_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_referral_events")),
    )
    op.create_index(
        op.f("ix_ai_referral_events_occurred_at"),
        "ai_referral_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_referral_events_org_id"),
        "ai_referral_events",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_referral_events_referrer_engine"),
        "ai_referral_events",
        ["referrer_engine"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_referral_events_site_id"),
        "ai_referral_events",
        ["site_id"],
        unique=False,
    )

    # --- Row-level security on new tenant tables -----------------------------------------
    for t in NEW_TENANT_TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {t} USING (org_id = app_current_org())"
            f" WITH CHECK (org_id = app_current_org())"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {t} TO app_tenant")


def downgrade() -> None:
    for t in NEW_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")

    op.drop_table("ai_referral_events")
    op.drop_table("webhooks")
    op.drop_table("api_keys")
    op.drop_table("fixes")
    op.drop_table("diagnoses")
