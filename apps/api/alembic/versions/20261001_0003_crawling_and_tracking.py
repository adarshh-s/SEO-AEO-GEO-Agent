"""crawling and tracking tables (Phase 2)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TENANT_TABLES = (
    "crawl_snapshots",
    "rank_checks",
    "ai_checks",
    "visibility_scores",
    "usage_counters",
)


def upgrade() -> None:
    # 1. crawl_snapshots
    op.create_table(
        "crawl_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("raw_html_hash", sa.String(length=64), nullable=False),
        sa.Column("rendered_html_hash", sa.String(length=64), nullable=True),
        sa.Column("js_only_content_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("js_only_text", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("rendered_text", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.Text(), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column(
            "ai_robots_allowed",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_crawl_snapshots_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_crawl_snapshots_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crawl_snapshots")),
    )
    op.create_index(op.f("ix_crawl_snapshots_org_id"), "crawl_snapshots", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_crawl_snapshots_site_id"), "crawl_snapshots", ["site_id"], unique=False
    )

    # 2. rank_checks
    op.create_table(
        "rank_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("keyword_id", sa.UUID(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("previous_position", sa.Integer(), nullable=True),
        sa.Column("url_ranked", sa.Text(), nullable=True),
        sa.Column(
            "serp_features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("ai_overview_present", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_overview_cites_site", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["keyword_id"],
            ["keywords.id"],
            name=op.f("fk_rank_checks_keyword_id_keywords"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_rank_checks_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_rank_checks_site_id_sites"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rank_checks")),
    )
    op.create_index(op.f("ix_rank_checks_checked_at"), "rank_checks", ["checked_at"], unique=False)
    op.create_index(op.f("ix_rank_checks_keyword_id"), "rank_checks", ["keyword_id"], unique=False)
    op.create_index(op.f("ix_rank_checks_org_id"), "rank_checks", ["org_id"], unique=False)
    op.create_index(op.f("ix_rank_checks_site_id"), "rank_checks", ["site_id"], unique=False)

    # 3. ai_checks
    op.create_table(
        "ai_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("prompt_id", sa.UUID(), nullable=False),
        sa.Column("engine", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("run_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("raw_answer", sa.Text(), nullable=False),
        sa.Column("brand_mentioned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mention_position", sa.Integer(), nullable=True),
        sa.Column("site_cited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "cited_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "competitors_mentioned",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("sentiment", sa.String(length=20), nullable=False, server_default="neutral"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "sentiment IN ('positive', 'neutral', 'negative')", name=op.f("ck_ai_checks_sentiment")
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_ai_checks_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["ai_prompts.id"],
            name=op.f("fk_ai_checks_prompt_id_ai_prompts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_ai_checks_site_id_sites"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_checks")),
    )
    op.create_index(op.f("ix_ai_checks_checked_at"), "ai_checks", ["checked_at"], unique=False)
    op.create_index(op.f("ix_ai_checks_engine"), "ai_checks", ["engine"], unique=False)
    op.create_index(op.f("ix_ai_checks_org_id"), "ai_checks", ["org_id"], unique=False)
    op.create_index(op.f("ix_ai_checks_prompt_id"), "ai_checks", ["prompt_id"], unique=False)
    op.create_index(op.f("ix_ai_checks_site_id"), "ai_checks", ["site_id"], unique=False)

    # 4. visibility_scores
    op.create_table(
        "visibility_scores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column(
            "seo_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "ai_share_of_voice",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "per_engine",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_visibility_scores_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_visibility_scores_site_id_sites"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visibility_scores")),
    )
    op.create_index(op.f("ix_visibility_scores_date"), "visibility_scores", ["date"], unique=False)
    op.create_index(
        op.f("ix_visibility_scores_org_id"), "visibility_scores", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_visibility_scores_site_id"), "visibility_scores", ["site_id"], unique=False
    )
    op.create_index(
        "uq_visibility_scores_site_date_lang",
        "visibility_scores",
        ["site_id", "date", "language"],
        unique=True,
    )

    # 5. usage_counters
    op.create_table(
        "usage_counters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0.0000"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_usage_counters_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_counters")),
        sa.UniqueConstraint(
            "org_id",
            "period_start",
            "category",
            "provider",
            name="uq_usage_counters_org_period_cat_prov",
        ),
    )
    op.create_index(
        op.f("ix_usage_counters_category"), "usage_counters", ["category"], unique=False
    )
    op.create_index(op.f("ix_usage_counters_org_id"), "usage_counters", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_usage_counters_period_start"), "usage_counters", ["period_start"], unique=False
    )
    op.create_index(
        op.f("ix_usage_counters_provider"), "usage_counters", ["provider"], unique=False
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

    op.drop_table("usage_counters")
    op.drop_table("visibility_scores")
    op.drop_table("ai_checks")
    op.drop_table("rank_checks")
    op.drop_table("crawl_snapshots")
