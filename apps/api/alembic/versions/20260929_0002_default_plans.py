"""default plans (placeholder limits, CLAUDE.md §12; Trial per decision D20)

Values are editable in the DB/admin afterwards; this migration only inserts missing rows.
Cost ceilings are placeholders until measured in Phase 2 (D14).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALL_ENGINES = ["chatgpt", "gemini", "perplexity", "claude"]

PLANS = [
    dict(
        code="trial",
        name="Trial",
        sort_order=0,
        is_public=False,
        max_sites=1,
        max_keywords=25,
        max_prompts=10,
        max_engines=2,
        allowed_engines=["chatgpt", "gemini"],
        max_languages_per_site=1,
        addon_languages=["ar"],
        check_frequency="weekly",
        audits_per_month=1,
        monthly_cost_ceiling_usd=5,
        trial_days=14,
    ),
    dict(
        code="starter",
        name="Starter",
        sort_order=1,
        is_public=True,
        max_sites=1,
        max_keywords=50,
        max_prompts=25,
        max_engines=2,
        allowed_engines=["chatgpt", "gemini"],
        max_languages_per_site=1,
        addon_languages=["ar"],
        check_frequency="weekly",
        audits_per_month=2,
        monthly_cost_ceiling_usd=15,
        trial_days=None,
    ),
    dict(
        code="growth",
        name="Growth",
        sort_order=2,
        is_public=True,
        max_sites=3,
        max_keywords=250,
        max_prompts=100,
        max_engines=4,
        allowed_engines=ALL_ENGINES,
        max_languages_per_site=2,
        addon_languages=[],
        check_frequency="twice_weekly",
        audits_per_month=10,
        monthly_cost_ceiling_usd=60,
        trial_days=None,
    ),
    dict(
        code="business",
        name="Business",
        sort_order=3,
        is_public=True,
        max_sites=10,
        max_keywords=1000,
        max_prompts=400,
        max_engines=4,
        allowed_engines=ALL_ENGINES,
        max_languages_per_site=4,
        addon_languages=[],
        check_frequency="daily",
        audits_per_month=40,
        monthly_cost_ceiling_usd=200,
        trial_days=None,
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {r[0] for r in conn.execute(sa.text("SELECT code FROM plans"))}
    plans = sa.table(
        "plans",
        sa.column("id", sa.Uuid),
        sa.column("code"),
        sa.column("name"),
        sa.column("sort_order"),
        sa.column("is_public"),
        sa.column("max_sites"),
        sa.column("max_keywords"),
        sa.column("max_prompts"),
        sa.column("max_engines"),
        sa.column("allowed_engines", ARRAY(sa.String)),
        sa.column("max_languages_per_site"),
        sa.column("addon_languages", ARRAY(sa.String)),
        sa.column("check_frequency"),
        sa.column("audits_per_month"),
        sa.column("monthly_cost_ceiling_usd"),
        sa.column("trial_days"),
        sa.column("features", JSONB),
    )
    rows = [{"id": uuid.uuid4(), "features": {}, **p} for p in PLANS if p["code"] not in existing]
    if rows:
        op.bulk_insert(plans, rows)


def downgrade() -> None:
    op.execute("DELETE FROM plans WHERE code IN ('trial', 'starter', 'growth', 'business')")
