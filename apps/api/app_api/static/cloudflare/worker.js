/**
 * QuardLink Cloudflare Edge Worker Template
 * Real-time SEO & AEO HTMLRewriter for edge proxy sites
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    let response;
    try {
      response = await fetch(request);
    } catch (err) {
      return new Response("Origin Unreachable", { status: 502 });
    }

    const contentType = response.headers.get("content-type") || "";
    if (response.status !== 200 || !contentType.includes("text/html")) {
      return response;
    }

    const siteKey = env.QUARDLINK_SITE_KEY || "YOUR_SITE_KEY_HERE";
    const apiUrl = (env.QUARDLINK_API_URL || "https://api.quardlink.com").replace(/\/+$/, "");

    // 1. Asynchronous AI crawler and referral logging
    ctx.waitUntil(trackAiTelemetry(request, siteKey, apiUrl));

    // 2. Fetch approved page fixes (fail-open)
    try {
      const cache = caches.default;
      const cacheKey = new Request(
        `${apiUrl}/public/v1/fixes?site_key=${encodeURIComponent(siteKey)}&url=${encodeURIComponent(request.url)}`,
        { method: "GET" }
      );

      let fixesResponse = await cache.match(cacheKey);
      if (!fixesResponse) {
        fixesResponse = await fetch(cacheKey.url, {
          headers: { "User-Agent": "QuardLink-Cloudflare-Worker/1.0" },
          cf: { cacheTtl: 300, cacheEverything: true },
        });
        if (fixesResponse.ok) {
          ctx.waitUntil(cache.put(cacheKey, fixesResponse.clone()));
        }
      }

      if (!fixesResponse.ok) {
        return response; // Fail-open
      }

      const data = await fixesResponse.json();
      const fixes = data.fixes || [];
      if (fixes.length === 0) {
        return response;
      }

      // 3. Inject fixes into HTML stream
      let rewriter = new HTMLRewriter();

      for (const fix of fixes) {
        if (fix.type === "meta" && fix.payload) {
          if (fix.payload.title) {
            rewriter = rewriter.on("title", {
              element(e) {
                e.setInnerContent(fix.payload.title);
              },
            });
          }
          if (fix.payload.meta_description) {
            rewriter = rewriter.on('meta[name="description"]', {
              element(e) {
                e.setAttribute("content", fix.payload.meta_description);
              },
            });
          }
        }

        if (fix.type === "schema" && fix.payload) {
          rewriter = rewriter.on("head", {
            element(e) {
              e.append(
                `<script type="application/ld+json">${JSON.stringify(fix.payload)}</script>\n`,
                { html: true }
              );
            },
          });
        }
      }

      return rewriter.transform(response);
    } catch (_e) {
      return response; // Fail-open
    }
  },
};

async function trackAiTelemetry(request, siteKey, apiUrl) {
  try {
    const ua = (request.headers.get("user-agent") || "").toLowerCase();
    const ref = (request.headers.get("referer") || "").toLowerCase();

    let aiEngine = null;
    if (ref.includes("chatgpt.com") || ref.includes("com.openai.chatgpt")) {
      aiEngine = "chatgpt";
    } else if (ref.includes("perplexity.ai")) {
      aiEngine = "perplexity";
    } else if (ref.includes("gemini.google.com")) {
      aiEngine = "gemini";
    } else if (ref.includes("claude.ai")) {
      aiEngine = "claude";
    }

    let isAiBot =
      ua.includes("gptbot") ||
      ua.includes("chatgpt-user") ||
      ua.includes("perplexitybot") ||
      ua.includes("claudebot") ||
      ua.includes("google-extended");

    if (aiEngine || isAiBot) {
      await fetch(`${apiUrl}/public/v1/telemetry/referral`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_key: siteKey,
          referrer_url: ref.slice(0, 500),
          landing_url: request.url.slice(0, 500),
          referrer_engine: aiEngine || "ai_bot",
          user_agent: ua.slice(0, 255),
        }),
      });
    }
  } catch (_) {
    // Fail-silent
  }
}
