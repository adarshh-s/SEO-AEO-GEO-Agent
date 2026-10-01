"""Platform connectors registry."""

from app_core.connectors.base import (
    ConnectionTestResult,
    DeploymentResult,
    PlatformConnector,
    RollbackResult,
)
from app_core.connectors.cloudflare import (
    CloudflareConnector,
    generate_cloudflare_worker_js,
)
from app_core.connectors.github import GithubConnector
from app_core.connectors.google_search_console import GoogleSearchConsoleConnector
from app_core.connectors.salla import (
    SallaConnector,
    generate_salla_instructions,
    generate_salla_snippet_code,
)
from app_core.connectors.shopify import ShopifyConnector
from app_core.connectors.webflow import WebflowConnector
from app_core.connectors.wix import WixConnector
from app_core.connectors.wordpress import (
    WordpressConnector,
    generate_wordpress_plugin_php,
    generate_wordpress_plugin_zip,
)
from app_core.connectors.zid import (
    ZidConnector,
    generate_zid_instructions,
    generate_zid_snippet_code,
)

_CONNECTORS: dict[str, PlatformConnector] = {
    "wordpress": WordpressConnector(),
    "shopify": ShopifyConnector(),
    "github": GithubConnector(),
    "cloudflare": CloudflareConnector(),
    "google_search_console": GoogleSearchConsoleConnector(),
    "webflow": WebflowConnector(),
    "wix": WixConnector(),
    "salla": SallaConnector(),
    "zid": ZidConnector(),
}


def get_connector(provider: str) -> PlatformConnector | None:
    """Retrieve connector for a given provider."""
    return _CONNECTORS.get(provider)


__all__ = [
    "CloudflareConnector",
    "ConnectionTestResult",
    "DeploymentResult",
    "GithubConnector",
    "GoogleSearchConsoleConnector",
    "PlatformConnector",
    "RollbackResult",
    "SallaConnector",
    "ShopifyConnector",
    "WebflowConnector",
    "WixConnector",
    "WordpressConnector",
    "ZidConnector",
    "generate_cloudflare_worker_js",
    "generate_salla_instructions",
    "generate_salla_snippet_code",
    "generate_wordpress_plugin_php",
    "generate_wordpress_plugin_zip",
    "generate_zid_instructions",
    "generate_zid_snippet_code",
    "get_connector",
]
