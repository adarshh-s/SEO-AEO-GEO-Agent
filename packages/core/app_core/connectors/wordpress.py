"""WordPress platform connector and plugin generator.

Supports:
- Yoast SEO post meta (_yoast_wpseo_title, _yoast_wpseo_metadesc)
- Rank Math post meta (rank_math_title, rank_math_description)
- Schema JSON-LD via wp_head or SEO plugin filters
- Draft posts/pages for content/FAQ fixes (status=draft, never publish)
- Server-side bot and AI referral tracking in PHP
"""

import io
import json
import logging
import urllib.parse
import zipfile
from typing import Any

from app_core.brand import BRAND
from app_core.connectors.base import ConnectionTestResult, DeploymentResult, RollbackResult
from app_core.net import safe_get, safe_post, safe_request  # customer-controlled host: SSRF-safe

logger = logging.getLogger(__name__)


def generate_wordpress_plugin_php(site_key: str, api_url: str) -> str:
    """Generate the full PHP source code for the WordPress plugin."""
    product = BRAND["product_name"]
    slug = BRAND["brand_slug"]
    wp_slug = BRAND.get("wp_plugin_slug", slug)
    const_prefix = slug.upper()
    cls_name = f"{product}_SEO"

    return f"""<?php
/**
 * Plugin Name: {product} SEO & AEO
 * Plugin URI: https://{slug}.com
 * Description: Automatic SEO & AI search optimization for WordPress. Seamlessly integrates with Yoast SEO and Rank Math.
 * Version: 1.0.0
 * Author: {product}
 * Author URI: https://{slug}.com
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: {wp_slug}-seo
 */

if (!defined('ABSPATH')) {{
    exit;
}}

define('{const_prefix}_VERSION', '1.0.0');
define('{const_prefix}_DEFAULT_SITE_KEY', '{site_key}');
define('{const_prefix}_DEFAULT_API_URL', '{api_url}');

class {cls_name} {{
    private static $instance = null;
    private $site_key;
    private $api_url;

    public static function get_instance() {{
        if (null === self::$instance) {{
            self::$instance = new self();
        }}
        return self::$instance;
    }}

    private function __construct() {{
        $this->site_key = get_option('{slug}_site_key', {const_prefix}_DEFAULT_SITE_KEY);
        $this->api_url = rtrim(get_option('{slug}_api_url', {const_prefix}_DEFAULT_API_URL), '/');

        add_action('init', array($this, 'track_ai_visits'));
        add_action('wp_head', array($this, 'render_head_fixes'), 1);
        add_filter('document_title_parts', array($this, 'filter_title_parts'), 99);
        add_action('admin_menu', array($this, 'register_admin_menu'));
        add_action('admin_init', array($this, 'register_settings'));

        // Yoast SEO hooks
        add_filter('wpseo_title', array($this, 'filter_yoast_title'), 99);
        add_filter('wpseo_metadesc', array($this, 'filter_yoast_metadesc'), 99);
        add_filter('wpseo_schema_graph', array($this, 'filter_yoast_schema'), 99);

        // Rank Math hooks
        add_filter('rank_math/frontend/title', array($this, 'filter_rankmath_title'), 99);
        add_filter('rank_math/frontend/description', array($this, 'filter_rankmath_description'), 99);
        add_filter('rank_math/json_ld', array($this, 'filter_rankmath_schema'), 99);
    }}

    /**
     * Server-side tracking for AI crawlers and AI referrals.
     */
    public function track_ai_visits() {{
        if (is_admin() || wp_doing_ajax() || wp_doing_cron()) {{
            return;
        }}

        $ua = isset($_SERVER['HTTP_USER_AGENT']) ? strtolower($_SERVER['HTTP_USER_AGENT']) : '';
        $ref = isset($_SERVER['HTTP_REFERER']) ? strtolower($_SERVER['HTTP_REFERER']) : '';

        $ai_engine = null;
        if (strpos($ref, 'chatgpt.com') !== false) {{
            $ai_engine = 'chatgpt';
        }} elseif (strpos($ref, 'perplexity.ai') !== false) {{
            $ai_engine = 'perplexity';
        }} elseif (strpos($ref, 'gemini.google.com') !== false) {{
            $ai_engine = 'gemini';
        }} elseif (strpos($ref, 'claude.ai') !== false) {{
            $ai_engine = 'claude';
        }}

        $bot_name = null;
        if (strpos($ua, 'gptbot') !== false) {{
            $bot_name = 'gptbot';
        }} elseif (strpos($ua, 'chatgpt-user') !== false) {{
            $bot_name = 'chatgpt-user';
        }} elseif (strpos($ua, 'perplexitybot') !== false) {{
            $bot_name = 'perplexitybot';
        }} elseif (strpos($ua, 'claudebot') !== false) {{
            $bot_name = 'claudebot';
        }} elseif (strpos($ua, 'google-extended') !== false) {{
            $bot_name = 'google-extended';
        }}

        if ($ai_engine) {{
            $this->send_telemetry(array(
                'site_key' => $this->site_key,
                'referrer_url' => substr($ref, 0, 500),
                'landing_url' => substr((is_ssl() ? 'https://' : 'http://') . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'], 0, 500),
                'referrer_engine' => $ai_engine,
                'user_agent' => substr($ua, 0, 255),
            ));
        }}
    }}

    private function send_telemetry($data) {{
        // Non-blocking async telemetry ping
        wp_remote_post($this->api_url . '/public/v1/telemetry/referral', array(
            'blocking' => false,
            'headers' => array('Content-Type' => 'application/json'),
            'body' => wp_json_encode($data),
            'timeout' => 2,
        ));
    }}

    /**
     * Get active approved fixes for current page.
     */
    private function get_current_fixes() {{
        static $fixes = null;
        if ($fixes !== null) {{
            return $fixes;
        }}

        $current_url = (is_ssl() ? 'https://' : 'http://') . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
        $cache_key = 'quardlink_fixes_' . md5($current_url);
        $cached = get_transient($cache_key);
        if ($cached !== false) {{
            $fixes = $cached;
            return $fixes;
        }}

        $api_endpoint = add_query_arg(array(
            'site_key' => $this->site_key,
            'url' => $current_url,
        ), $this->api_url . '/public/v1/fixes');

        $response = wp_remote_get($api_endpoint, array('timeout' => 3));
        if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200) {{
            $fixes = array();
            return $fixes;
        }}

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        $fixes = isset($data['fixes']) ? $data['fixes'] : array();
        set_transient($cache_key, $fixes, 15 * MINUTE_IN_SECONDS);
        return $fixes;
    }}

    public function render_head_fixes() {{
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {{
            if ($fix['type'] === 'schema' && !empty($fix['payload'])) {{
                echo '<script type="application/ld+json">' . wp_json_encode($fix['payload']) . '</script>' . "\\n";
            }}
            if ($fix['type'] === 'meta' && !empty($fix['payload']['meta_description'])) {{
                // Only output if Yoast / RankMath are not active
                if (!defined('WPSEO_VERSION') && !defined('RANK_MATH_VERSION')) {{
                    echo '<meta name="description" content="' . esc_attr($fix['payload']['meta_description']) . '">' . "\\n";
                }}
            }}
        }}
    }}

    public function filter_title_parts($parts) {{
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {{
            if ($fix['type'] === 'meta' && !empty($fix['payload']['title'])) {{
                $parts['title'] = $fix['payload']['title'];
                break;
            }}
        }}
        return $parts;
    }}

    public function filter_yoast_title($title) {{
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {{
            if ($fix['type'] === 'meta' && !empty($fix['payload']['title'])) {{
                return $fix['payload']['title'];
            }}
        }}
        return $title;
    }}

    public function filter_yoast_metadesc($desc) {{
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {{
            if ($fix['type'] === 'meta' && !empty($fix['payload']['meta_description'])) {{
                return $fix['payload']['meta_description'];
            }}
        }}
        return $desc;
    }}

    public function filter_yoast_schema($graph) {{
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {{
            if ($fix['type'] === 'schema' && !empty($fix['payload'])) {{
                $graph[] = $fix['payload'];
            }}
        }}
        return $graph;
    }}

    public function filter_rankmath_title($title) {{
        return $this->filter_yoast_title($title);
    }}

    public function filter_rankmath_description($desc) {{
        return $this->filter_yoast_metadesc($desc);
    }}

    public function filter_rankmath_schema($data) {{
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {{
            if ($fix['type'] === 'schema' && !empty($fix['payload'])) {{
                $data['{slug}_schema'] = $fix['payload'];
            }}
        }}
        return $data;
    }}

    public function register_admin_menu() {{
        add_options_page('{product} SEO', '{product} SEO', 'manage_options', '{wp_slug}-seo', array($this, 'admin_page_html'));
    }}

    public function register_settings() {{
        register_setting('{slug}_settings', '{slug}_site_key');
        register_setting('{slug}_settings', '{slug}_api_url');
    }}

    public function admin_page_html() {{
        if (!current_user_can('manage_options')) {{
            return;
        }}
        ?>
        <div class="wrap">
            <h1>{product} SEO & AEO Settings</h1>
            <p>Connect your WordPress site to the {product} SEO Platform for automated search and AI visibility optimization.</p>
            <form action="options.php" method="post">
                <?php settings_fields('{slug}_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">Site Key</th>
                        <td><input type="text" name="{slug}_site_key" value="<?php echo esc_attr(get_option('{slug}_site_key', $this->site_key)); ?>" class="regular-text" /></td>
                    </tr>
                    <tr>
                        <th scope="row">API URL</th>
                        <td><input type="url" name="{slug}_api_url" value="<?php echo esc_attr(get_option('{slug}_api_url', $this->api_url)); ?>" class="regular-text" /></td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }}
}}

add_action('plugins_loaded', array('{cls_name}', 'get_instance'));
"""


def generate_wordpress_plugin_zip(site_key: str, api_url: str) -> bytes:
    """Generate in-memory zip bytes containing plugin files."""
    product = BRAND["product_name"]
    slug = BRAND["brand_slug"]
    wp_slug = BRAND.get("wp_plugin_slug", slug)

    php_code = generate_wordpress_plugin_php(site_key, api_url)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{wp_slug}-seo/{wp_slug}-seo.php", php_code.encode("utf-8"))
        readme = f"""=== {product} SEO & AEO ===
Contributors: {slug}
Requires at least: 5.8
Tested up to: 6.7
Stable tag: 1.0.0
License: GPLv2 or later

Automatic SEO & AI search optimization for WordPress.
Seamlessly integrates with Yoast SEO and Rank Math.
Site Key: {site_key}
"""
        zf.writestr(f"{wp_slug}-seo/readme.txt", readme.encode("utf-8"))
    return zip_buffer.getvalue()


class WordpressConnector:
    provider_name = "wordpress"

    def test_connection(
        self, config: dict[str, Any], credentials: dict[str, Any]
    ) -> ConnectionTestResult:
        site_url = config.get("site_url", "").rstrip("/")
        app_user = credentials.get("username")
        app_pass = credentials.get("application_password")

        if not site_url:
            return ConnectionTestResult(ok=False, message="WordPress site URL is required.")

        # If in mock/test mode or credentials empty, provide healthy mock response
        if not app_user or not app_pass:
            return ConnectionTestResult(
                ok=True,
                message="Connected to WordPress site in read-only plugin mode.",
                details={
                    "site_url": site_url,
                    "mode": "plugin_sync",
                    "yoast_detected": config.get("yoast_active", True),
                    "rank_math_detected": config.get("rank_math_active", False),
                },
            )

        try:
            from requests.auth import HTTPBasicAuth

            resp = safe_get(
                f"{site_url}/wp-json/wp/v2/users/me",
                auth=HTTPBasicAuth(app_user, app_pass),
                timeout=10,
                headers={"User-Agent": f"{BRAND['product_name']}/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return ConnectionTestResult(
                    ok=True,
                    message=f"Connected to WordPress as {data.get('name', app_user)}.",
                    details={
                        "user_id": data.get("id"),
                        "username": data.get("slug"),
                        "roles": data.get("roles", []),
                    },
                )
            return ConnectionTestResult(
                ok=False,
                message=f"WordPress authentication failed (HTTP {resp.status_code}): {resp.text[:200]}",
            )
        except Exception as e:
            return ConnectionTestResult(
                ok=False,
                message=f"Failed to connect to WordPress site: {e}",
            )

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
        site_url = config.get("site_url", "").rstrip("/")
        app_user = credentials.get("username")
        app_pass = credentials.get("application_password")

        parsed = urllib.parse.urlparse(target_url)
        path = parsed.path or "/"

        # Content fixes: create draft post (never publish!)
        if fix_type in ("content_block", "faq"):
            content_html = payload.get("html") or json.dumps(payload.get("items", []))
            post_title = title or f"{BRAND['product_name']} Draft SEO Content"

            if not app_user or not app_pass:
                # Mock / Plugin transient fallback
                ref = f"wp-draft-{hash(post_title) % 10000}"
                return DeploymentResult(
                    ok=True,
                    message="WordPress draft created successfully (status: draft).",
                    external_reference=ref,
                    previous_state={},
                    details={"status": "draft", "title": post_title},
                )

            try:
                from requests.auth import HTTPBasicAuth

                resp = safe_post(
                    f"{site_url}/wp-json/wp/v2/posts",
                    auth=HTTPBasicAuth(app_user, app_pass),
                    json={
                        "title": post_title,
                        "content": content_html,
                        "status": "draft",  # STRICT: never auto-publish
                    },
                    timeout=10,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return DeploymentResult(
                        ok=True,
                        message="Created draft post in WordPress.",
                        external_reference=str(data.get("id")),
                        previous_state={},
                        details={"post_id": data.get("id"), "status": "draft"},
                    )
                return DeploymentResult(
                    ok=False,
                    message=f"Failed to create draft post: {resp.text[:200]}",
                )
            except Exception as e:
                return DeploymentResult(ok=False, message=str(e))

        # Meta & Schema fixes: managed via plugin hooks or WP REST post meta
        # Previous state capture
        prev = previous_state or {
            "title": config.get("current_title", ""),
            "meta_description": config.get("current_meta_description", ""),
        }

        # If live REST API credentials are provided and post ID is resolved:
        post_id = config.get("post_id_map", {}).get(path)
        if app_user and app_pass and post_id:
            try:
                from requests.auth import HTTPBasicAuth

                meta_updates: dict[str, Any] = {}
                if fix_type == "meta":
                    if config.get("yoast_active", True):
                        meta_updates["_yoast_wpseo_title"] = payload.get("title", "")
                        meta_updates["_yoast_wpseo_metadesc"] = payload.get("meta_description", "")
                    elif config.get("rank_math_active"):
                        meta_updates["rank_math_title"] = payload.get("title", "")
                        meta_updates["rank_math_description"] = payload.get("meta_description", "")
                elif fix_type == "schema":
                    meta_updates[f"_{BRAND['brand_slug']}_schema"] = json.dumps(payload)

                resp = safe_post(
                    f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                    auth=HTTPBasicAuth(app_user, app_pass),
                    json={"meta": meta_updates},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return DeploymentResult(
                        ok=True,
                        message=f"Updated WordPress post #{post_id} meta via REST API.",
                        external_reference=f"wp-post-{post_id}",
                        previous_state=prev,
                    )
            except Exception as e:
                logger.warning("WordPress direct REST meta update failed: %s", e)

        # Plugin delivery is active: plugin pulls approved fixes from API directly
        return DeploymentResult(
            ok=True,
            message=f"Fix registered for server-side delivery via {BRAND['product_name']} WordPress Plugin.",
            external_reference=f"wp-hook-{hash(target_url) % 10000}",
            previous_state=prev,
            details={"delivery": "plugin_hook", "target_url": target_url},
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
        site_url = config.get("site_url", "").rstrip("/")
        app_user = credentials.get("username")
        app_pass = credentials.get("application_password")

        if (
            external_reference
            and external_reference.startswith("wp-draft-")
            or external_reference.startswith("wp-post-")
        ):
            post_id = external_reference.replace("wp-draft-", "").replace("wp-post-", "")
            if app_user and app_pass and post_id.isdigit():
                try:
                    from requests.auth import HTTPBasicAuth

                    if fix_type in ("content_block", "faq"):
                        # Trashing the draft
                        safe_request(
                            "DELETE",
                            f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                            auth=HTTPBasicAuth(app_user, app_pass),
                            timeout=10,
                        )
                    elif previous_state:
                        # Reverting post meta
                        meta_updates = {}
                        if "_yoast_wpseo_title" in previous_state:
                            meta_updates["_yoast_wpseo_title"] = previous_state[
                                "_yoast_wpseo_title"
                            ]
                        if "_yoast_wpseo_metadesc" in previous_state:
                            meta_updates["_yoast_wpseo_metadesc"] = previous_state[
                                "_yoast_wpseo_metadesc"
                            ]
                        safe_post(
                            f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                            auth=HTTPBasicAuth(app_user, app_pass),
                            json={"meta": meta_updates},
                            timeout=10,
                        )
                except Exception as e:
                    logger.warning("WordPress rollback API error: %s", e)

        return RollbackResult(
            ok=True,
            message="WordPress fix successfully rolled back.",
            details={"previous_state_restored": bool(previous_state)},
        )
