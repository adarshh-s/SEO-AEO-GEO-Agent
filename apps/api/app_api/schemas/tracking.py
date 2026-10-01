"""Schemas for Phase 2 crawling, rankings, AI visibility and overview."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RankedKeywordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keyword: str
    language: str
    country: str
    city: str | None = None
    device: str
    status: str
    position: int | None = None
    previous_position: int | None = None
    position_change: int | None = None
    url_ranked: str | None = None
    serp_features: list[str] = []
    ai_overview_present: bool = False
    ai_overview_cites_site: bool = False
    last_checked_at: datetime | None = None


class AiCheckRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    engine: str
    model: str
    run_index: int
    checked_at: datetime
    raw_answer: str
    brand_mentioned: bool
    mention_position: int | None = None
    site_cited: bool
    cited_urls: list[str] = []
    competitors_mentioned: list[str] = []
    sentiment: str


class EngineStatus(BaseModel):
    mentioned: bool
    cited: bool
    sentiment: str = "neutral"


class PromptVisibilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt_text: str
    language: str
    country: str
    intent: str
    status: str
    brand_mentioned: bool = False
    site_cited: bool = False
    engines_status: dict[str, EngineStatus] = {}
    last_checked_at: datetime | None = None


class CompetitorShareOut(BaseModel):
    domain: str
    mentions: int
    share_pct: float


class AiVisibilitySummaryOut(BaseModel):
    overall_share_of_voice: float
    brand_mention_rate: float
    citation_rate: float
    prompts: list[PromptVisibilityOut]
    competitor_leaderboard: list[CompetitorShareOut]
    per_engine: dict[str, float]


class CrawlSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    url: str
    http_status: int
    platform: str
    rendering: str
    js_only_content_detected: bool
    js_only_text: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    ai_robots_allowed: dict[str, bool] = {}
    fetched_at: datetime


class RankingWinLossOut(BaseModel):
    keyword_id: uuid.UUID
    keyword: str
    language: str
    current_position: int | None = None
    previous_position: int | None = None
    change: int


class SiteOverviewOut(BaseModel):
    seo_score: float
    ai_share_of_voice: float
    per_engine: dict[str, float]
    fixes_waiting: int
    ranking_wins: list[RankingWinLossOut]
    ranking_losses: list[RankingWinLossOut]
    history: list[dict]
    monthly_spend_usd: float
    monthly_cost_ceiling_usd: float
    spend_ratio: float
