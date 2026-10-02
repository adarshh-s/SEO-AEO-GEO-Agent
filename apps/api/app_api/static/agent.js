/**
 * OmniRank Universal SEO & AI Optimization Snippet (agent.js)
 * Zero dependencies, fail-safe, cookieless telemetry and fix injection.
 */
(function () {
  "use strict";

  try {
    // Prevent double execution
    if (
      (window.OmniRank && window.OmniRank.loaded) ||
      (window.QuardLink && window.QuardLink.loaded)
    ) {
      return;
    }

    var currentScript =
      document.currentScript ||
      document.querySelector("script[data-site]") ||
      document.querySelector('script[src*="agent.js"]');

    if (!currentScript) {
      return;
    }

    var siteKey =
      currentScript.getAttribute("data-site") ||
      currentScript.getAttribute("data-site-key");
    if (!siteKey) {
      return;
    }

    // Determine API origin from script src or default
    var scriptSrc = currentScript.getAttribute("src") || "";
    var apiOrigin = "";
    if (scriptSrc.indexOf("http") === 0) {
      var a = document.createElement("a");
      a.href = scriptSrc;
      apiOrigin = a.protocol + "//" + a.host;
    }

    window.OmniRank = {
      version: "1.0.0",
      loaded: true,
      siteKey: siteKey,
      appliedFixes: [],
    };
    window.QuardLink = window.OmniRank;

    // 1. Cookieless AI Referral & Bot Traffic Tracking
    var referrer = (document.referrer || "").toLowerCase();
    var aiEngine = null;

    if (
      referrer.indexOf("chatgpt.com") !== -1 ||
      referrer.indexOf("com.openai.chatgpt") !== -1
    ) {
      aiEngine = "chatgpt";
    } else if (referrer.indexOf("perplexity.ai") !== -1) {
      aiEngine = "perplexity";
    } else if (referrer.indexOf("gemini.google.com") !== -1) {
      aiEngine = "gemini";
    } else if (referrer.indexOf("claude.ai") !== -1) {
      aiEngine = "claude";
    } else if (referrer.indexOf("copilot.microsoft.com") !== -1) {
      aiEngine = "copilot";
    }

    if (aiEngine) {
      var pingPayload = JSON.stringify({
        site_key: siteKey,
        url: window.location.href,
        referrer_engine: aiEngine,
      });

      var pingUrl = (apiOrigin || "") + "/public/v1/telemetry/referral";
      if (navigator.sendBeacon) {
        navigator.sendBeacon(pingUrl, pingPayload);
      } else if (window.fetch) {
        fetch(pingUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: pingPayload,
          keepalive: true,
        }).catch(function () {});
      }
    }

    // 2. Fetch and apply approved/deployed fixes
    function applyFixes() {
      var currentUrl = window.location.href.split("#")[0];
      var fixesUrl =
        (apiOrigin || "") +
        "/public/v1/fixes?site_key=" +
        encodeURIComponent(siteKey) +
        "&url=" +
        encodeURIComponent(currentUrl);

      if (!window.fetch) {
        return;
      }

      fetch(fixesUrl)
        .then(function (res) {
          if (!res.ok) {
            return null;
          }
          return res.json();
        })
        .then(function (data) {
          if (!data || !data.fixes || !data.fixes.length) {
            return;
          }

          var fixes = data.fixes;
          for (var i = 0; i < fixes.length; i++) {
            var fix = fixes[i];
            try {
              if (fix.type === "schema" && fix.payload && fix.payload.json_ld) {
                var scriptTag = document.createElement("script");
                scriptTag.type = "application/ld+json";
                scriptTag.setAttribute("data-quardlink-injected", "true");
                scriptTag.setAttribute("data-fix-id", fix.id);
                scriptTag.textContent = JSON.stringify(fix.payload.json_ld);
                document.head.appendChild(scriptTag);
                window.QuardLink.appliedFixes.push(fix.id);
              } else if (fix.type === "meta" && fix.payload) {
                if (fix.payload.title) {
                  document.title = fix.payload.title;
                }
                if (fix.payload.meta_description) {
                  var metaDesc = document.querySelector(
                    'meta[name="description"]',
                  );
                  if (!metaDesc) {
                    metaDesc = document.createElement("meta");
                    metaDesc.setAttribute("name", "description");
                    document.head.appendChild(metaDesc);
                  }
                  metaDesc.setAttribute(
                    "content",
                    fix.payload.meta_description,
                  );
                }
                window.QuardLink.appliedFixes.push(fix.id);
              } else if (
                (fix.type === "faq" || fix.type === "content_block") &&
                fix.payload &&
                fix.payload.html
              ) {
                var containerSelector =
                  fix.payload.container_selector ||
                  (fix.type === "faq"
                    ? "[data-quardlink-faq]"
                    : "[data-quardlink-container]");
                var targetEl = document.querySelector(containerSelector);
                if (targetEl) {
                  var wrapper = document.createElement("div");
                  wrapper.setAttribute("data-quardlink-injected", "true");
                  wrapper.setAttribute("data-fix-id", fix.id);
                  wrapper.innerHTML = fix.payload.html;
                  targetEl.appendChild(wrapper);
                  window.QuardLink.appliedFixes.push(fix.id);
                }
              }
            } catch (err) {
              // Ignore single fix errors
            }
          }

          // Trigger custom event for advanced client integrations
          if (window.CustomEvent) {
            var evt = new CustomEvent("quardlink:fixes-applied", {
              detail: { count: window.QuardLink.appliedFixes.length },
            });
            window.dispatchEvent(evt);
          }
        })
        .catch(function () {});
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", applyFixes);
    } else {
      applyFixes();
    }
  } catch (globalErr) {
    // Fail completely silent
  }
})();
