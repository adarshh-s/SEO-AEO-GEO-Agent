"""Tracking router for SERP rankings, AI visibility, and crawl snapshots."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import desc, select

from app_api.deps import Member, Tenant, TenantDb
from app_api.errors import not_found
from app_api.routers.sites import get_site
from app_api.schemas.common import Ok
from app_api.schemas.tracking import (
    AiCheckRunOut,
    AiVisibilitySummaryOut,
    CompetitorShareOut,
    CrawlSnapshotOut,
    EngineStatus,
    PromptVisibilityOut,
    RankedKeywordOut,
    RankingWinLossOut,
    SiteOverviewOut,
)
from app_api.task_dispatcher import dispatch_task
from app_core.cost_guard import get_monthly_spend
from app_core.models import (
    AiCheck,
    AiPrompt,
    CrawlSnapshot,
    Keyword,
    Organization,
    RankCheck,
    VisibilityScore,
)
from app_core.tenancy import TenantContext, scoped

router = APIRouter(prefix="/sites/{site_id}", tags=["tracking"])


def _get_site_keyword(
    db: TenantDb, ctx: TenantContext, site_id: uuid.UUID, keyword_id: uuid.UUID
) -> Keyword:
    kw = db.scalar(
        scoped(select(Keyword), Keyword, ctx).where(
            Keyword.id == keyword_id, Keyword.site_id == site_id
        )
    )
    if kw is None:
        raise not_found("keyword")
    return kw


def _get_site_prompt(
    db: TenantDb, ctx: TenantContext, site_id: uuid.UUID, prompt_id: uuid.UUID
) -> AiPrompt:
    p = db.scalar(
        scoped(select(AiPrompt), AiPrompt, ctx).where(
            AiPrompt.id == prompt_id, AiPrompt.site_id == site_id
        )
    )
    if p is None:
        raise not_found("prompt")
    return p


# --- Rankings --------------------------------------------------------------------------------


@router.get("/rankings", response_model=list[RankedKeywordOut])
def get_rankings(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> list[RankedKeywordOut]:
    site = get_site(db, ctx, site_id)
    keywords = list(
        db.scalars(
            scoped(select(Keyword), Keyword, ctx)
            .where(Keyword.site_id == site.id)
            .order_by(Keyword.created_at)
        )
    )

    result: list[RankedKeywordOut] = []
    for kw in keywords:
        latest = db.scalars(
            scoped(select(RankCheck), RankCheck, ctx)
            .where(RankCheck.keyword_id == kw.id)
            .order_by(desc(RankCheck.checked_at))
            .limit(1)
        ).first()

        change: int | None = None
        if latest and latest.position is not None and latest.previous_position is not None:
            # Positive change means improved rank (e.g. 5 -> 3 is +2)
            change = latest.previous_position - latest.position

        result.append(
            RankedKeywordOut(
                id=kw.id,
                keyword=kw.keyword,
                language=kw.language,
                country=kw.country,
                city=kw.city,
                device=kw.device,
                status=kw.status,
                position=latest.position if latest else None,
                previous_position=latest.previous_position if latest else None,
                position_change=change,
                url_ranked=latest.url_ranked if latest else None,
                serp_features=latest.serp_features if latest else [],
                ai_overview_present=latest.ai_overview_present if latest else False,
                ai_overview_cites_site=latest.ai_overview_cites_site if latest else False,
                last_checked_at=latest.checked_at if latest else None,
            )
        )
    return result


@router.post("/keywords/{keyword_id}/check", response_model=Ok)
def trigger_keyword_check(
    site_id: uuid.UUID, keyword_id: uuid.UUID, ctx: Member, db: TenantDb
) -> Ok:
    kw = _get_site_keyword(db, ctx, site_id, keyword_id)
    dispatch_task(
        "app_worker.tasks.tracking.run_keyword_rank_check",
        args=[str(kw.id)],
        queue="tracking",
    )
    return Ok()


@router.post("/keywords/check-all", response_model=Ok)
def trigger_all_keyword_checks(site_id: uuid.UUID, ctx: Member, db: TenantDb) -> Ok:
    site = get_site(db, ctx, site_id)
    keywords = db.scalars(
        scoped(select(Keyword), Keyword, ctx).where(
            Keyword.site_id == site.id, Keyword.status == "active"
        )
    ).all()
    for kw in keywords:
        dispatch_task(
            "app_worker.tasks.tracking.run_keyword_rank_check",
            args=[str(kw.id)],
            queue="tracking",
        )
    return Ok()


# --- AI Visibility ---------------------------------------------------------------------------


@router.get("/ai-visibility", response_model=AiVisibilitySummaryOut)
def get_ai_visibility(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> AiVisibilitySummaryOut:
    site = get_site(db, ctx, site_id)
    prompts = list(
        db.scalars(
            scoped(select(AiPrompt), AiPrompt, ctx)
            .where(AiPrompt.site_id == site.id)
            .order_by(AiPrompt.created_at)
        )
    )

    prompt_outs: list[PromptVisibilityOut] = []
    all_checks: list[AiCheck] = []
    competitor_counts: dict[str, int] = {}
    engine_stats: dict[str, dict[str, int]] = {}

    for p in prompts:
        checks = list(
            db.scalars(
                scoped(select(AiCheck), AiCheck, ctx)
                .where(AiCheck.prompt_id == p.id)
                .order_by(desc(AiCheck.checked_at))
                .limit(20)
            )
        )
        all_checks.extend(checks)

        is_mentioned = any(c.brand_mentioned for c in checks)
        is_cited = any(c.site_cited for c in checks)
        last_check_date = checks[0].checked_at if checks else None

        engines_status: dict[str, EngineStatus] = {}
        for c in checks:
            if c.engine not in engines_status:
                engines_status[c.engine] = EngineStatus(
                    mentioned=c.brand_mentioned,
                    cited=c.site_cited,
                    sentiment=c.sentiment,
                )
            if c.engine not in engine_stats:
                engine_stats[c.engine] = {"brand": 0, "total": 0}
            engine_stats[c.engine]["total"] += 1
            if c.brand_mentioned:
                engine_stats[c.engine]["brand"] += 1

            for comp in c.competitors_mentioned:
                competitor_counts[comp] = competitor_counts.get(comp, 0) + 1

        prompt_outs.append(
            PromptVisibilityOut(
                id=p.id,
                prompt_text=p.prompt_text,
                language=p.language,
                country=p.country,
                intent=p.intent,
                status=p.status,
                brand_mentioned=is_mentioned,
                site_cited=is_cited,
                engines_status=engines_status,
                last_checked_at=last_check_date,
            )
        )

    # Compute overall rates
    total_checks = len(all_checks)
    brand_checks = sum(1 for c in all_checks if c.brand_mentioned)
    cited_checks = sum(1 for c in all_checks if c.site_cited)

    mention_rate = round((brand_checks / total_checks) * 100, 1) if total_checks else 0.0
    citation_rate = round((cited_checks / total_checks) * 100, 1) if total_checks else 0.0

    total_comp_mentions = sum(competitor_counts.values())
    total_market = brand_checks + total_comp_mentions
    overall_sov = round((brand_checks / total_market) * 100, 1) if total_market else 0.0

    leaderboard: list[CompetitorShareOut] = []
    for comp, count in sorted(competitor_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        leaderboard.append(
            CompetitorShareOut(
                domain=comp,
                mentions=count,
                share_pct=round((count / total_market) * 100, 1) if total_market else 0.0,
            )
        )

    per_engine: dict[str, float] = {}
    for eng, st in engine_stats.items():
        per_engine[eng] = round((st["brand"] / st["total"]) * 100, 1) if st["total"] else 0.0

    return AiVisibilitySummaryOut(
        overall_share_of_voice=overall_sov,
        brand_mention_rate=mention_rate,
        citation_rate=citation_rate,
        prompts=prompt_outs,
        competitor_leaderboard=leaderboard,
        per_engine=per_engine,
    )


@router.get("/prompts/{prompt_id}/runs", response_model=list[AiCheckRunOut])
def get_prompt_runs(
    site_id: uuid.UUID, prompt_id: uuid.UUID, ctx: Tenant, db: TenantDb
) -> list[AiCheckRunOut]:
    prompt = _get_site_prompt(db, ctx, site_id, prompt_id)
    runs = list(
        db.scalars(
            scoped(select(AiCheck), AiCheck, ctx)
            .where(AiCheck.prompt_id == prompt.id)
            .order_by(desc(AiCheck.checked_at))
            .limit(30)
        )
    )
    return [
        AiCheckRunOut(
            id=r.id,
            engine=r.engine,
            model=r.model,
            run_index=r.run_index,
            checked_at=r.checked_at,
            raw_answer=r.raw_answer,
            brand_mentioned=r.brand_mentioned,
            mention_position=r.mention_position,
            site_cited=r.site_cited,
            cited_urls=r.cited_urls,
            competitors_mentioned=r.competitors_mentioned,
            sentiment=r.sentiment,
        )
        for r in runs
    ]


@router.post("/prompts/{prompt_id}/check", response_model=Ok)
def trigger_prompt_check(site_id: uuid.UUID, prompt_id: uuid.UUID, ctx: Member, db: TenantDb) -> Ok:
    p = _get_site_prompt(db, ctx, site_id, prompt_id)
    dispatch_task(
        "app_worker.tasks.tracking.run_ai_prompt_check",
        args=[str(p.id)],
        queue="tracking",
    )
    return Ok()


@router.post("/prompts/check-all", response_model=Ok)
def trigger_all_prompt_checks(site_id: uuid.UUID, ctx: Member, db: TenantDb) -> Ok:
    site = get_site(db, ctx, site_id)
    prompts = db.scalars(
        scoped(select(AiPrompt), AiPrompt, ctx).where(
            AiPrompt.site_id == site.id, AiPrompt.status == "active"
        )
    ).all()
    for p in prompts:
        dispatch_task(
            "app_worker.tasks.tracking.run_ai_prompt_check",
            args=[str(p.id)],
            queue="tracking",
        )
    return Ok()


# --- Crawling --------------------------------------------------------------------------------


@router.get("/crawl/latest", response_model=CrawlSnapshotOut)
def get_latest_crawl(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> CrawlSnapshotOut:
    site = get_site(db, ctx, site_id)
    snapshot = db.scalars(
        scoped(select(CrawlSnapshot), CrawlSnapshot, ctx)
        .where(CrawlSnapshot.site_id == site.id)
        .order_by(desc(CrawlSnapshot.fetched_at))
        .limit(1)
    ).first()

    if not snapshot:
        raise not_found("crawl snapshot")

    return CrawlSnapshotOut(
        id=snapshot.id,
        site_id=snapshot.site_id,
        url=snapshot.url,
        http_status=snapshot.http_status,
        platform=site.platform,
        rendering=site.rendering,
        js_only_content_detected=snapshot.js_only_content_detected,
        js_only_text=snapshot.js_only_text,
        meta_title=snapshot.meta_title,
        meta_description=snapshot.meta_description,
        ai_robots_allowed=snapshot.ai_robots_allowed,
        fetched_at=snapshot.fetched_at,
    )


@router.post("/crawl", response_model=Ok)
def trigger_site_crawl(site_id: uuid.UUID, ctx: Member, db: TenantDb) -> Ok:
    site = get_site(db, ctx, site_id)
    dispatch_task(
        "app_worker.tasks.crawl.crawl_site",
        args=[str(site.id)],
        queue="crawl",
    )
    return Ok()


# --- Overview --------------------------------------------------------------------------------


@router.get("/overview", response_model=SiteOverviewOut)
def get_site_overview(site_id: uuid.UUID, ctx: Tenant, db: TenantDb) -> SiteOverviewOut:
    site = get_site(db, ctx, site_id)
    org = db.get(Organization, ctx.org_id)
    assert org is not None

    # Get latest visibility score for site
    latest_score = db.scalars(
        scoped(select(VisibilityScore), VisibilityScore, ctx)
        .where(VisibilityScore.site_id == site.id)
        .order_by(desc(VisibilityScore.date))
        .limit(1)
    ).first()

    seo_score = float(latest_score.seo_score) if latest_score else 0.0
    ai_sov = float(latest_score.ai_share_of_voice) if latest_score else 0.0
    per_engine = {k: float(v) for k, v in (latest_score.per_engine if latest_score else {}).items()}

    # Calculate wins and losses from keyword rankings
    keywords = db.scalars(
        scoped(select(Keyword), Keyword, ctx).where(Keyword.site_id == site.id)
    ).all()

    wins: list[RankingWinLossOut] = []
    losses: list[RankingWinLossOut] = []

    for kw in keywords:
        latest_rank = db.scalars(
            scoped(select(RankCheck), RankCheck, ctx)
            .where(RankCheck.keyword_id == kw.id)
            .order_by(desc(RankCheck.checked_at))
            .limit(1)
        ).first()

        if latest_rank and latest_rank.position and latest_rank.previous_position:
            diff = latest_rank.previous_position - latest_rank.position
            if diff > 0:
                wins.append(
                    RankingWinLossOut(
                        keyword_id=kw.id,
                        keyword=kw.keyword,
                        language=kw.language,
                        current_position=latest_rank.position,
                        previous_position=latest_rank.previous_position,
                        change=diff,
                    )
                )
            elif diff < 0:
                losses.append(
                    RankingWinLossOut(
                        keyword_id=kw.id,
                        keyword=kw.keyword,
                        language=kw.language,
                        current_position=latest_rank.position,
                        previous_position=latest_rank.previous_position,
                        change=diff,
                    )
                )

    wins.sort(key=lambda w: w.change, reverse=True)
    losses.sort(key=lambda item: item.change)

    # 30-day history
    since = datetime.now(UTC) - timedelta(days=30)
    history_rows = db.scalars(
        scoped(select(VisibilityScore), VisibilityScore, ctx)
        .where(VisibilityScore.site_id == site.id, VisibilityScore.date >= since)
        .order_by(VisibilityScore.date)
    ).all()

    history = [
        {
            "date": r.date.strftime("%Y-%m-%d"),
            "seo_score": float(r.seo_score),
            "ai_share_of_voice": float(r.ai_share_of_voice),
        }
        for r in history_rows
    ]

    spend = float(get_monthly_spend(db, ctx.org_id))
    ceiling = float(org.cost_ceiling_override_usd or org.plan.monthly_cost_ceiling_usd or 0.0)
    ratio = (spend / ceiling) if ceiling > 0 else 0.0

    return SiteOverviewOut(
        seo_score=seo_score,
        ai_share_of_voice=ai_sov,
        per_engine=per_engine,
        fixes_waiting=0,
        ranking_wins=wins[:5],
        ranking_losses=losses[:5],
        history=history,
        monthly_spend_usd=spend,
        monthly_cost_ceiling_usd=ceiling,
        spend_ratio=ratio,
    )
