"""Brand accessors. The values live in config/brand.json (see scripts/brand_sync.py)."""

from app_core.brand_gen import BRAND

PRODUCT_NAME: str = BRAND["product_name"]
BRAND_SLUG: str = BRAND["brand_slug"]


def crawler_user_agent(bot_info_url: str) -> str:
    """User agent for every outbound fetch of a customer URL."""
    token = BRAND["crawler_user_agent_token"]
    return f"Mozilla/5.0 (compatible; {token}/1.0; +{bot_info_url})"


__all__ = ["BRAND", "BRAND_SLUG", "PRODUCT_NAME", "crawler_user_agent"]
