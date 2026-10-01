"""Import every model so Base.metadata is complete (Alembic, tests)."""

from app_core.models.audit_log import AuditLogEntry
from app_core.models.diagnosis import Diagnosis
from app_core.models.fix import Fix
from app_core.models.integration import ApiKey, SiteIntegration, Webhook
from app_core.models.org import Invitation, Membership, Organization
from app_core.models.plan import Plan, Subscription
from app_core.models.site import Site
from app_core.models.tracking import (
    AiCheck,
    AiPrompt,
    AiReferralEvent,
    CrawlSnapshot,
    Keyword,
    RankCheck,
    VisibilityScore,
)
from app_core.models.usage import UsageCounter
from app_core.models.user import RefreshToken, User

__all__ = [
    "AiCheck",
    "AiPrompt",
    "AiReferralEvent",
    "ApiKey",
    "AuditLogEntry",
    "CrawlSnapshot",
    "Diagnosis",
    "Fix",
    "Invitation",
    "Keyword",
    "Membership",
    "Organization",
    "Plan",
    "RankCheck",
    "RefreshToken",
    "Site",
    "SiteIntegration",
    "Subscription",
    "UsageCounter",
    "User",
    "VisibilityScore",
    "Webhook",
]
