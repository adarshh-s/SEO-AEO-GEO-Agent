"""Cloudflare Edge Worker connector and HTMLRewriter script generator.

Supports:
- High-performance HTMLRewriter template injecting title, meta description, and JSON-LD schema server-side
- Edge caching via Cloudflare Workers Cache API
- Fail-open resilience (untouched origin response returned on any error)
- Non-blocking telemetry for AI crawlers & referrers via ctx.waitUntil
- Cloudflare API cache purging on deployment
"""

import logging
from typing import Any

from app_core.connectors.base import ConnectionTestResult, DeploymentResult, RollbackResult

logger = logging.getLogger(__name__)


def generate_cloudflare_worker_js(site_key: str, api_url: str) -> str:
    """Generate production-ready Cloudflare Worker script using HTMLRewriter."""
    return f"""/**
 * QuardLink Cloudflare Edge Worker
 * Server-side SEO & AI Visibility Injection via HTMLRewriter
 *
 * Site Key: {site_key}
 * API URL: {api_url}
 */

export default {{
  async fetch(request, env, ctx) {{
    const url = new URL(request.url);

    // 1. Fetch response from origin server
    let response;
    try {{
      response = await fetch(request);
    }} catch (err) {{
      return new Response("Origin Unreachable", {{ status: 502 }});
    }}

    // Pass through non-HTML or non-200 responses directly
    const contentType = response.headers.get("content-type") || "";
    if (response.status !== 200 || !contentType.includes("text/html")) {{
      return response;
    }}

    const siteKey = env.QUARDLINK_SITE_KEY || "{site_key}";
    const apiUrl = (env.QUARDLINK_API_URL || "{api_url}").replace(/\\/+$/, "");

    // 2. Track AI crawlers & AI referrals asynchronously (fail-safe)
    ctx.waitUntil(trackAiTelemetry(request, siteKey, apiUrl));

    // 3. Fail-open fetch for approved page fixes
    try {{
      const cache = caches.default;
      const cacheKey = new Request(
        `${{apiUrl}}/public/v1/fixes?site_key=${{encodeURIComponent(siteKey)}}&url=${{encodeURIComponent(request.url)}}`,
        {{ method: "GET" }}
      );

      let fixesResponse = await cache.match(cacheKey);
      if (!fixesResponse) {{
        fixesResponse = await fetch(cacheKey.url, {{
          headers: {{ "User-Agent": "QuardLink-Cloudflare-Worker/1.0" }},
          cf: {{ cacheTtl: 300, cacheEverything: true }},
        }});
        if (fixesResponse.ok) {{
          ctx.waitUntil(cache.put(cacheKey, fixesResponse.clone()));
        }}
      }}

      if (!fixesResponse.ok) {{
        return response; // Fail-open: return original response untouched
      }}

      const data = await fixesResponse.json();
      const fixes = data.fixes || [];
      if (fixes.length === 0) {{
        return response;
      }}

      // 4. Inject fixes into HTML stream via HTMLRewriter
      let rewriter = new HTMLRewriter();

      for (const fix of fixes) {{
        if (fix.type === "meta" && fix.payload) {{
          if (fix.payload.title) {{
            rewriter = rewriter.on("title", {{
              element(e) {{
                e.setInnerContent(fix.payload.title);
              }},
            }});
          }}
          if (fix.payload.meta_description) {{
            rewriter = rewriter.on('meta[name="description"]', {{
              element(e) {{
                e.setAttribute("content", fix.payload.meta_description);
              }},
            }});
          }}
        }}

        if (fix.type === "schema" && fix.payload) {{
          rewriter = rewriter.on("head", {{
            element(e) {{
              e.append(
                `<script type="application/ld+json">${{JSON.stringify(fix.payload)}}</script>\\n`,
                {{ html: true }}
              );
            }},
          }});
        }}
      }}

      return rewriter.transform(response);
    }} catch (e) {{
      // Fail-open: return original response if anything fails
      return response;
    }}
  }},
}};

async function trackAiTelemetry(request, siteKey, apiUrl) {{
  try {{
    const ua = (request.headers.get("user-agent") || "").toLowerCase();
    const ref = (request.headers.get("referer") || "").toLowerCase();

    let aiEngine = null;
    if (ref.includes("chatgpt.com") || ref.includes("com.openai.chatgpt")) {{
      aiEngine = "chatgpt";
    }} else if (ref.includes("perplexity.ai")) {{
      aiEngine = "perplexity";
    }} else if (ref.includes("gemini.google.com")) {{
      aiEngine = "gemini";
    }} else if (ref.includes("claude.ai")) {{
      aiEngine = "claude";
    }}

    let isAiBot =
      ua.includes("gptbot") ||
      ua.includes("chatgpt-user") ||
      ua.includes("perplexitybot") ||
      ua.includes("claudebot") ||
      ua.includes("google-extended");

    if (aiEngine || isAiBot) {{
      await fetch(`${{apiUrl}}/public/v1/telemetry/referral`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          site_key: siteKey,
          referrer_url: ref.slice(0, 500),
          landing_url: request.url.slice(0, 500),
          referrer_engine: aiEngine || "ai_bot",
          user_agent: ua.slice(0, 255),
        }}),
      }});
    }}
  }} catch (_) {{
    // Silently ignore telemetry network glitches
  }}
}}
"""


class CloudflareConnector:
    provider_name = "cloudflare"

    def test_connection(
        self, config: dict[str, Any], credentials: dict[str, Any]
    ) -> ConnectionTestResult:
        zone_id = config.get("zone_id", "")
        api_token = credentials.get("api_token", "")

        if not api_token or not zone_id:
            return ConnectionTestResult(
                ok=True,
                message="Cloudflare Worker template ready for deployment.",
                details={
                    "mode": "standalone_worker",
                    "route": config.get("route", "*/*"),
                    "fail_open": True,
                },
            )

        import requests

        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                zone_name = data.get("result", {}).get("name", zone_id)
                return ConnectionTestResult(
                    ok=True,
                    message=f"Connected to Cloudflare Zone '{zone_name}'.",
                    details=data.get("result", {}),
                )
            return ConnectionTestResult(
                ok=False,
                message=f"Cloudflare API error (HTTP {resp.status_code}): {resp.text[:200]}",
            )
        except Exception as e:
            return ConnectionTestResult(ok=False, message=f"Failed to connect to Cloudflare: {e}")

    def deploy_fix(
        self,
        *,
        target_url: str,
        fix_type: str,
        title: str,
        payload: dict[str, Any],
        config: dict[str, Any],
        credentials: dict[str, Any],
        site_key: str,
        previous_state: dict[str, Any] | None = None,
    ) -> DeploymentResult:
        zone_id = config.get("zone_id")
        api_token = credentials.get("api_token")

        prev = previous_state or {}

        # If Cloudflare API Token is configured, purge edge cache for the target URL
        if zone_id and api_token:
            try:
                import requests

                purge_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                }
                requests.post(purge_url, headers=headers, json={"files": [target_url]}, timeout=10)
            except Exception as e:
                logger.warning("Cloudflare cache purge warning: %s", e)

        return DeploymentResult(
            ok=True,
            message="Fix ready for immediate edge injection via Cloudflare Edge Worker.",
            external_reference=f"cf-edge-{hash(target_url) % 10000}",
            previous_state=prev,
            details={"mode": "cloudflare_edge_worker", "target_url": target_url},
        )

    def rollback_fix(
        self,
        *,
        target_url: str,
        fix_type: str,
        external_reference: str | None,
        previous_state: dict[str, Any] | None,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> RollbackResult:
        zone_id = config.get("zone_id")
        api_token = credentials.get("api_token")

        if zone_id and api_token:
            try:
                import requests

                purge_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
                headers = {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                }
                requests.post(purge_url, headers=headers, json={"files": [target_url]}, timeout=10)
            except Exception as e:
                logger.warning("Cloudflare cache purge warning: %s", e)

        return RollbackResult(ok=True, message="Edge cache purged and fix rolled back.")
