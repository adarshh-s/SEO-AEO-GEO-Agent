"""SERP ranking and AI visibility tracking tasks (tracking queue)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import desc, func, select

from app_core.cost_guard import (
    CostCeilingExceeded,
    TrialExpired,
    check_cost_guard,
    record_usage,
)
from app_core.db import system_session
from app_core.models import (
    AiCheck,
    AiPrompt,
    Keyword,
    Organization,
    RankCheck,
    Site,
    VisibilityScore,
)
from app_core.providers import get_answer_engine
from app_core.providers.ai_answer import ProviderNotConfigured
from app_core.providers.serp import UnsupportedCountry, get_serp_provider
from app_core.settings import get_settings
from app_worker.celery_app import app

logger = structlog.get_logger(__name__)


@app.task(name="app_worker.tasks.tracking.run_keyword_rank_check")
def run_keyword_rank_check(keyword_id_str: str, is_scheduled: bool = False) -> dict:
    """Check a single keyword's Google ranking and AI Overview presence."""
    keyword_id = uuid.UUID(keyword_id_str)
    with system_session() as db:
        keyword = db.get(Keyword, keyword_id)
        if not keyword or keyword.status != "active":
            return {"status": "skipped", "reason": "keyword_inactive_or_not_found"}

        site = db.get(Site, keyword.site_id)
        if not site:
            return {"status": "skipped", "reason": "site_not_found"}

        # 1. Quota & cost ceiling check
        try:
            check_cost_guard(db, keyword.org_id, is_scheduled=is_scheduled)
        except (CostCeilingExceeded, TrialExpired) as e:
            logger.info("rank_check_blocked_by_guard", keyword_id=keyword_id_str, reason=str(e))
            return {"status": "blocked", "reason": str(e)}

        # 2. Get previous check for delta calculation
        prev = db.scalars(
            select(RankCheck)
            .where(RankCheck.keyword_id == keyword.id)
            .order_by(desc(RankCheck.checked_at))
            .limit(1)
        ).first()
        prev_pos = prev.position if prev else None

        # 3. Query SERP provider
        # Never store made-up rankings: a missing provider skips the check.
        try:
            provider = get_serp_provider()
            res = provider.check_ranking(
                keyword=keyword.keyword,
                domain=site.domain,
                country=keyword.country,
                language=keyword.language,
                device=keyword.device,
            )
        except (ProviderNotConfigured, UnsupportedCountry) as e:
            logger.warning("rank_check_skipped", keyword_id=keyword_id_str, reason=str(e))
            return {"status": "skipped", "reason": str(e)}

        now = datetime.now(UTC)
        rank_check = RankCheck(
            org_id=keyword.org_id,
            site_id=site.id,
            keyword_id=keyword.id,
            checked_at=now,
            position=res.position,
            previous_position=prev_pos,
            url_ranked=res.url_ranked,
            serp_features=res.serp_features,
            ai_overview_present=res.ai_overview_present,
            ai_overview_cites_site=res.ai_overview_cites_site,
            raw_response=res.raw_response,
        )
        db.add(rank_check)

        # 4. Log usage cost
        if res.cost_usd > 0:
            record_usage(
                db,
                org_id=keyword.org_id,
                category="serp",
                provider="dataforseo",
                units=1,
                cost_usd=res.cost_usd,
            )

        db.commit()
        schedule_score_rollup(site.id)
        return {
            "status": "success",
            "keyword_id": keyword_id_str,
            "position": res.position,
            "previous_position": prev_pos,
            "ai_overview_present": res.ai_overview_present,
        }


@app.task(name="app_worker.tasks.tracking.run_ai_prompt_check")
def run_ai_prompt_check(prompt_id_str: str, is_scheduled: bool = False) -> dict:
    """Run an AI prompt across the org's allowed engines N times and store mentions/sentiment."""
    prompt_id = uuid.UUID(prompt_id_str)
    settings = get_settings()
    runs_per_prompt = settings.ai_runs_per_prompt

    with system_session() as db:
        prompt = db.get(AiPrompt, prompt_id)
        if not prompt or prompt.status != "active":
            return {"status": "skipped", "reason": "prompt_inactive_or_not_found"}

        site = db.get(Site, prompt.site_id)
        org = db.get(Organization, prompt.org_id)
        if not site or not org:
            return {"status": "skipped", "reason": "site_or_org_not_found"}

        # 1. Cost guard & trial check
        try:
            check_cost_guard(db, prompt.org_id, is_scheduled=is_scheduled)
        except (CostCeilingExceeded, TrialExpired) as e:
            logger.info("ai_check_blocked_by_guard", prompt_id=prompt_id_str, reason=str(e))
            return {"status": "blocked", "reason": str(e)}

        # 2. Extract brand spellings for this prompt's language
        brand_names = list(site.brand_names.get(prompt.language, []))
        if not brand_names:
            brand_names = [site.name, site.domain.split(".")[0]]

        allowed_engines = org.plan.allowed_engines
        now = datetime.now(UTC)
        total_runs = 0
        brand_mentions = 0

        for engine_id in allowed_engines:
            try:
                provider = get_answer_engine(engine_id)
            except ProviderNotConfigured as e:
                # Never store made-up answers: skip engines that aren't configured.
                logger.warning("ai_engine_skipped", engine=engine_id, reason=str(e))
                continue
            for run_idx in range(runs_per_prompt):
                try:
                    res = provider.query(
                        prompt=prompt.prompt_text,
                        brand_names=brand_names,
                        target_domain=site.domain,
                        competitors=site.competitor_domains,
                        language=prompt.language,
                        country=prompt.country,
                        city=site.default_city,
                    )
                    ai_check = AiCheck(
                        org_id=prompt.org_id,
                        site_id=site.id,
                        prompt_id=prompt.id,
                        engine=engine_id,
                        model=res.model,
                        run_index=run_idx,
                        checked_at=now,
                        raw_answer=res.raw_answer,
                        brand_mentioned=res.brand_mentioned,
                        mention_position=res.mention_position,
                        site_cited=res.site_cited,
                        cited_urls=res.cited_urls,
                        competitors_mentioned=res.competitors_mentioned,
                        sentiment=res.sentiment,
                    )
                    db.add(ai_check)
                    total_runs += 1
                    if res.brand_mentioned:
                        brand_mentions += 1

                    if res.cost_usd > 0:
                        record_usage(
                            db,
                            org_id=prompt.org_id,
                            category="ai_check",
                            provider=engine_id,
                            units=1,
                            cost_usd=res.cost_usd,
                        )
                except Exception as e:
                    logger.warning(
                        "engine_query_failed",
                        engine=engine_id,
                        prompt_id=prompt_id_str,
                        error=str(e),
                    )

        db.commit()
        schedule_score_rollup(site.id)
        return {
            "status": "success",
            "prompt_id": prompt_id_str,
            "total_runs": total_runs,
            "brand_mentions": brand_mentions,
        }


@app.task(name="app_worker.tasks.tracking.rollup_visibility_scores")
def rollup_visibility_scores(site_id_str: str) -> dict:
    """Calculate and store SEO score and AI Share of Voice for a site."""
    site_id = uuid.UUID(site_id_str)
    with system_session() as db:
        site = db.get(Site, site_id)
        if not site:
            return {"error": "Site not found"}

        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        since = datetime.now(UTC) - timedelta(days=7)

        for lang in site.languages:
            # 1. SEO score calculation: % based on latest rankings
            keywords = db.scalars(
                select(Keyword).where(
                    Keyword.site_id == site.id,
                    Keyword.language == lang,
                    Keyword.status == "active",
                )
            ).all()

            seo_points = 0.0
            max_points = len(keywords) * 100.0 if keywords else 100.0

            for kw in keywords:
                latest_rank = db.scalars(
                    select(RankCheck)
                    .where(RankCheck.keyword_id == kw.id)
                    .order_by(desc(RankCheck.checked_at))
                    .limit(1)
                ).first()
                if latest_rank and latest_rank.position:
                    pos = latest_rank.position
                    if pos <= 3:
                        seo_points += 100.0
                    elif pos <= 10:
                        seo_points += 70.0
                    elif pos <= 20:
                        seo_points += 40.0
                    elif pos <= 50:
                        seo_points += 20.0
                    elif pos <= 100:
                        seo_points += 10.0

            seo_score = round(Decimal(str((seo_points / max_points) * 100 if max_points else 0)), 2)

            # 2. AI Share of Voice calculation
            prompts = db.scalars(
                select(AiPrompt).where(
                    AiPrompt.site_id == site.id,
                    AiPrompt.language == lang,
                    AiPrompt.status == "active",
                )
            ).all()
            prompt_ids = [p.id for p in prompts]

            ai_sov = Decimal("0.00")
            per_engine: dict[str, float] = {}

            if prompt_ids:
                recent_checks = db.scalars(
                    select(AiCheck).where(
                        AiCheck.prompt_id.in_(prompt_ids),
                        AiCheck.checked_at >= since,
                    )
                ).all()

                brand_count = sum(1 for c in recent_checks if c.brand_mentioned)
                comp_count = sum(len(c.competitors_mentioned) for c in recent_checks)
                total_mentions = brand_count + comp_count

                if total_mentions > 0:
                    ai_sov = round(Decimal(str((brand_count / total_mentions) * 100)), 2)

                # Per-engine breakdown
                engines = {c.engine for c in recent_checks}
                for eng in engines:
                    eng_checks = [c for c in recent_checks if c.engine == eng]
                    b_cnt = sum(1 for c in eng_checks if c.brand_mentioned)
                    c_cnt = sum(len(c.competitors_mentioned) for c in eng_checks)
                    tot = b_cnt + c_cnt
                    per_engine[eng] = round((b_cnt / tot) * 100 if tot else 0.0, 1)

            # Upsert visibility score for today
            score_row = db.scalars(
                select(VisibilityScore).where(
                    VisibilityScore.site_id == site.id,
                    VisibilityScore.date == today,
                    VisibilityScore.language == lang,
                )
            ).first()

            if score_row:
                score_row.seo_score = seo_score
                score_row.ai_share_of_voice = ai_sov
                score_row.per_engine = per_engine
            else:
                score_row = VisibilityScore(
                    org_id=site.org_id,
                    site_id=site.id,
                    date=today,
                    language=lang,
                    seo_score=seo_score,
                    ai_share_of_voice=ai_sov,
                    per_engine=per_engine,
                )
                db.add(score_row)

        db.commit()
        return {"status": "success", "site_id": site_id_str}


# How often each plan re-checks a keyword / AI prompt (CLAUDE.md §12).
CHECK_INTERVALS = {
    "daily": timedelta(days=1),
    "twice_weekly": timedelta(days=3, hours=12),
    "weekly": timedelta(days=7),
}
# Small grace so a check that ran slightly late doesn't push the next one a full period.
DUE_GRACE = timedelta(hours=1)


def schedule_score_rollup(site_id: uuid.UUID) -> None:
    """Recompute the site's scores shortly after checks finish (many checks -> one recompute
    is fine: the rollup is idempotent for the day)."""
    rollup_visibility_scores.apply_async(args=[str(site_id)], countdown=30)


def is_due(last_checked: datetime | None, frequency: str, now: datetime) -> bool:
    if last_checked is None:
        return True
    interval = CHECK_INTERVALS.get(frequency, CHECK_INTERVALS["weekly"])
    return now - last_checked >= interval - DUE_GRACE


@app.task(name="app_worker.tasks.tracking.dispatch_scheduled_checks")
def dispatch_scheduled_checks() -> dict:
    """Enqueue only the keywords/prompts that are due under their org's plan frequency.

    Runs every 30 minutes, but each item is checked at most once per plan period
    (weekly / twice weekly / daily), so paid API calls follow the plan, not the beat.
    """
    enqueued_kw = 0
    enqueued_pr = 0
    now = datetime.now(UTC)

    with system_session() as db:
        for site in db.scalars(select(Site)).all():
            org = db.get(Organization, site.org_id)
            if not org:
                continue
            try:
                check_cost_guard(db, org.id, is_scheduled=True)
            except (CostCeilingExceeded, TrialExpired):
                continue  # paused orgs
            frequency = org.plan.check_frequency

            last_rank = dict(
                db.execute(
                    select(RankCheck.keyword_id, func.max(RankCheck.checked_at))
                    .where(RankCheck.site_id == site.id)
                    .group_by(RankCheck.keyword_id)
                ).all()
            )
            for kw_id in db.scalars(
                select(Keyword.id).where(Keyword.site_id == site.id, Keyword.status == "active")
            ):
                if is_due(last_rank.get(kw_id), frequency, now):
                    run_keyword_rank_check.delay(str(kw_id), is_scheduled=True)
                    enqueued_kw += 1

            last_ai = dict(
                db.execute(
                    select(AiCheck.prompt_id, func.max(AiCheck.checked_at))
                    .where(AiCheck.site_id == site.id)
                    .group_by(AiCheck.prompt_id)
                ).all()
            )
            for pr_id in db.scalars(
                select(AiPrompt.id).where(AiPrompt.site_id == site.id, AiPrompt.status == "active")
            ):
                if is_due(last_ai.get(pr_id), frequency, now):
                    run_ai_prompt_check.delay(str(pr_id), is_scheduled=True)
                    enqueued_pr += 1

    return {"enqueued_keywords": enqueued_kw, "enqueued_prompts": enqueued_pr}
