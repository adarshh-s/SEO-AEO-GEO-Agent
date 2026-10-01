"""Website platform and rendering mode detection."""

from dataclasses import dataclass

from app_core.enums import Platform, Rendering
from app_worker.seo_engine.fetch import FetchResult
from app_worker.seo_engine.render import RenderResult


@dataclass
class PlatformFacts:
    platform: Platform
    rendering: Rendering
    confidence: float
    reasons: list[str]


def detect_platform(fetch: FetchResult, render: RenderResult | None = None) -> PlatformFacts:
    """Analyze raw and rendered HTML, response headers, and scripts."""
    raw = fetch.raw_html.lower()
    headers = {k.lower(): v.lower() for k, v in fetch.headers.items()}
    url = fetch.final_url.lower()

    reasons: list[str] = []

    # 1. WordPress
    if (
        "wp-content/" in raw
        or "wp-includes/" in raw
        or 'name="generator" content="wordpress' in raw
        or "/wp-json/" in raw
    ):
        reasons.append("Detected WordPress paths or generator meta tag")
        return PlatformFacts(Platform.WORDPRESS, Rendering.SERVER, 0.95, reasons)

    # 2. Shopify
    if (
        "cdn.shopify.com" in raw
        or "shopify.theme" in raw
        or "myshopify.com" in url
        or "x-shopify-stage" in headers
    ):
        reasons.append("Detected Shopify assets or headers")
        return PlatformFacts(Platform.SHOPIFY, Rendering.SERVER, 0.95, reasons)

    # 3. Salla
    if "salla.sa" in url or "cdn.salla.sa" in raw or "salla-theme" in raw:
        reasons.append("Detected Salla assets or domain")
        return PlatformFacts(Platform.SALLA, Rendering.SERVER, 0.95, reasons)

    # 4. Zid
    if "zid.store" in url or "cdn.zid.store" in raw:
        reasons.append("Detected Zid store assets or domain")
        return PlatformFacts(Platform.ZID, Rendering.SERVER, 0.95, reasons)

    # 5. Wix
    if "static.parastorage.com" in raw or "wix.com" in raw or "x-wix-renderer-server" in headers:
        reasons.append("Detected Wix static storage or renderer headers")
        # Note: Decision in decisions.md notes Framer/Wix can serve pre-rendered HTML to crawlers
        rendering = (
            Rendering.SERVER
            if (render and not render.js_only_content_detected)
            else Rendering.CLIENT
        )
        return PlatformFacts(Platform.WIX, rendering, 0.95, reasons)

    # 6. Webflow
    if (
        "assets.website-files.com" in raw
        or "data-wf-page" in raw
        or 'name="generator" content="webflow' in raw
    ):
        reasons.append("Detected Webflow data attributes or assets")
        return PlatformFacts(Platform.WEBFLOW, Rendering.SERVER, 0.95, reasons)

    # 7. Squarespace
    if "static1.squarespace.com" in raw or "squarespace-headers" in raw:
        reasons.append("Detected Squarespace assets")
        return PlatformFacts(Platform.SQUARESPACE, Rendering.SERVER, 0.95, reasons)

    # 8. Framer
    if (
        "framer.com" in raw
        or "framerusercontent.com" in raw
        or 'name="generator" content="framer' in raw
    ):
        reasons.append("Detected Framer generator or assets")
        rendering = (
            Rendering.SERVER
            if (render and not render.js_only_content_detected)
            else Rendering.CLIENT
        )
        return PlatformFacts(Platform.FRAMER, rendering, 0.95, reasons)

    # 9. Next.js
    if "__next_data__" in raw or "/_next/" in raw or "next-head-count" in raw:
        reasons.append("Detected Next.js build manifests or hydration payload")
        return PlatformFacts(Platform.NEXTJS, Rendering.HYBRID, 0.95, reasons)

    # 10. Nuxt
    if "__nuxt__" in raw or "/_nuxt/" in raw or "data-n-head" in raw:
        reasons.append("Detected Nuxt runtime or assets")
        return PlatformFacts(Platform.NUXT, Rendering.HYBRID, 0.95, reasons)

    # 11. Astro
    if "data-astro-cid" in raw or 'name="generator" content="astro' in raw:
        reasons.append("Detected Astro island components or generator")
        return PlatformFacts(Platform.ASTRO, Rendering.SERVER, 0.95, reasons)

    # 12. React SPA vs Vue SPA vs Static
    if render and render.js_only_content_detected:
        if "react" in raw:
            reasons.append("Client-rendered React SPA detected via JS-only DOM expansion")
            return PlatformFacts(Platform.REACT_SPA, Rendering.CLIENT, 0.85, reasons)
        if "data-v-" in raw or "vue" in raw:
            reasons.append("Client-rendered Vue SPA detected via JS-only DOM expansion")
            return PlatformFacts(Platform.VUE_SPA, Rendering.CLIENT, 0.85, reasons)
        reasons.append("Client-rendered SPA detected")
        return PlatformFacts(Platform.REACT_SPA, Rendering.CLIENT, 0.70, reasons)

    # 13. Static vs Custom backend
    if "server" in headers:
        reasons.append(f"Server header detected: {headers['server']}")
        return PlatformFacts(Platform.CUSTOM_BACKEND, Rendering.SERVER, 0.75, reasons)

    return PlatformFacts(
        Platform.UNKNOWN, Rendering.SERVER, 0.50, ["No definitive platform signatures matched"]
    )
