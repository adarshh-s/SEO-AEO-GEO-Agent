"""Enumerations stored as plain strings (with CHECK constraints in the migration)."""

from enum import StrEnum


class MembershipRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_RANK = {
    MembershipRole.VIEWER: 0,
    MembershipRole.MEMBER: 1,
    MembershipRole.ADMIN: 2,
    MembershipRole.OWNER: 3,
}


class Platform(StrEnum):
    WORDPRESS = "wordpress"
    SHOPIFY = "shopify"
    WIX = "wix"
    WEBFLOW = "webflow"
    SQUARESPACE = "squarespace"
    FRAMER = "framer"
    SALLA = "salla"
    ZID = "zid"
    NEXTJS = "nextjs"
    NUXT = "nuxt"
    REACT_SPA = "react_spa"
    VUE_SPA = "vue_spa"
    ASTRO = "astro"
    STATIC = "static"
    CUSTOM_BACKEND = "custom_backend"
    UNKNOWN = "unknown"


NO_CODE_PLATFORMS = frozenset(
    {
        Platform.WORDPRESS,
        Platform.SHOPIFY,
        Platform.WIX,
        Platform.WEBFLOW,
        Platform.SQUARESPACE,
        Platform.FRAMER,
        Platform.SALLA,
        Platform.ZID,
    }
)


class Rendering(StrEnum):
    SERVER = "server"
    CLIENT = "client"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class VerificationMethod(StrEnum):
    DNS_TXT = "dns_txt"
    META_TAG = "meta_tag"
    INTEGRATION = "integration"
    PLATFORM_OAUTH = "platform_oauth"


class Device(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


class PromptIntent(StrEnum):
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    LOCAL = "local"
    COMPARISON = "comparison"
    NAVIGATIONAL = "navigational"


class TrackingStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class CheckFrequency(StrEnum):
    WEEKLY = "weekly"
    TWICE_WEEKLY = "twice_weekly"
    DAILY = "daily"


class AnswerEngineId(StrEnum):
    """AI answer engines. Direct APIs first (D3); DataForSEO LLM Scraper may be added later."""

    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    CLAUDE = "claude"
