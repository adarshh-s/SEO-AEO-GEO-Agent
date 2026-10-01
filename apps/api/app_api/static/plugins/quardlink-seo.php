<?php
/**
 * Plugin Name: QuardLink SEO & AEO
 * Plugin URI: https://quardlink.com
 * Description: Automatic SEO & AI search optimization for WordPress. Seamlessly integrates with Yoast SEO and Rank Math.
 * Version: 1.0.0
 * Author: QuardLink
 * Author URI: https://quardlink.com
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: quardlink-seo
 */

if (!defined('ABSPATH')) {
    exit;
}

define('QUARDLINK_VERSION', '1.0.0');

class QuardLink_SEO {
    private static $instance = null;
    private $site_key;
    private $api_url;

    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $this->site_key = get_option('quardlink_site_key', '');
        $this->api_url = rtrim(get_option('quardlink_api_url', 'https://api.quardlink.com'), '/');

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
    }

    public function track_ai_visits() {
        if (is_admin() || wp_doing_ajax() || wp_doing_cron()) {
            return;
        }

        $ua = isset($_SERVER['HTTP_USER_AGENT']) ? strtolower($_SERVER['HTTP_USER_AGENT']) : '';
        $ref = isset($_SERVER['HTTP_REFERER']) ? strtolower($_SERVER['HTTP_REFERER']) : '';

        $ai_engine = null;
        if (strpos($ref, 'chatgpt.com') !== false) {
            $ai_engine = 'chatgpt';
        } elseif (strpos($ref, 'perplexity.ai') !== false) {
            $ai_engine = 'perplexity';
        } elseif (strpos($ref, 'gemini.google.com') !== false) {
            $ai_engine = 'gemini';
        } elseif (strpos($ref, 'claude.ai') !== false) {
            $ai_engine = 'claude';
        }

        $bot_name = null;
        if (strpos($ua, 'gptbot') !== false) {
            $bot_name = 'gptbot';
        } elseif (strpos($ua, 'chatgpt-user') !== false) {
            $bot_name = 'chatgpt-user';
        } elseif (strpos($ua, 'perplexitybot') !== false) {
            $bot_name = 'perplexitybot';
        } elseif (strpos($ua, 'claudebot') !== false) {
            $bot_name = 'claudebot';
        } elseif (strpos($ua, 'google-extended') !== false) {
            $bot_name = 'google-extended';
        }

        if ($ai_engine || $bot_name) {
            wp_remote_post($this->api_url . '/public/v1/telemetry/referral', array(
                'blocking' => false,
                'headers' => array('Content-Type' => 'application/json'),
                'body' => wp_json_encode(array(
                    'site_key' => $this->site_key,
                    'referrer_url' => substr($ref, 0, 500),
                    'landing_url' => substr((is_ssl() ? 'https://' : 'http://') . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'], 0, 500),
                    'referrer_engine' => $ai_engine ? $ai_engine : 'ai_bot',
                    'user_agent' => substr($ua, 0, 255),
                )),
                'timeout' => 2,
            ));
        }
    }

    private function get_current_fixes() {
        static $fixes = null;
        if ($fixes !== null) {
            return $fixes;
        }

        if (empty($this->site_key)) {
            $fixes = array();
            return $fixes;
        }

        $current_url = (is_ssl() ? 'https://' : 'http://') . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
        $cache_key = 'quardlink_fixes_' . md5($current_url);
        $cached = get_transient($cache_key);
        if ($cached !== false) {
            $fixes = $cached;
            return $fixes;
        }

        $api_endpoint = add_query_arg(array(
            'site_key' => $this->site_key,
            'url' => $current_url,
        ), $this->api_url . '/public/v1/fixes');

        $response = wp_remote_get($api_endpoint, array('timeout' => 3));
        if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200) {
            $fixes = array();
            return $fixes;
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        $fixes = isset($data['fixes']) ? $data['fixes'] : array();
        set_transient($cache_key, $fixes, 15 * MINUTE_IN_SECONDS);
        return $fixes;
    }

    public function render_head_fixes() {
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {
            if ($fix['type'] === 'schema' && !empty($fix['payload'])) {
                echo '<script type="application/ld+json">' . wp_json_encode($fix['payload']) . '</script>' . "\n";
            }
            if ($fix['type'] === 'meta' && !empty($fix['payload']['meta_description'])) {
                if (!defined('WPSEO_VERSION') && !defined('RANK_MATH_VERSION')) {
                    echo '<meta name="description" content="' . esc_attr($fix['payload']['meta_description']) . '">' . "\n";
                }
            }
        }
    }

    public function filter_title_parts($parts) {
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {
            if ($fix['type'] === 'meta' && !empty($fix['payload']['title'])) {
                $parts['title'] = $fix['payload']['title'];
                break;
            }
        }
        return $parts;
    }

    public function filter_yoast_title($title) {
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {
            if ($fix['type'] === 'meta' && !empty($fix['payload']['title'])) {
                return $fix['payload']['title'];
            }
        }
        return $title;
    }

    public function filter_yoast_metadesc($desc) {
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {
            if ($fix['type'] === 'meta' && !empty($fix['payload']['meta_description'])) {
                return $fix['payload']['meta_description'];
            }
        }
        return $desc;
    }

    public function filter_yoast_schema($graph) {
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {
            if ($fix['type'] === 'schema' && !empty($fix['payload'])) {
                $graph[] = $fix['payload'];
            }
        }
        return $graph;
    }

    public function filter_rankmath_title($title) {
        return $this->filter_yoast_title($title);
    }

    public function filter_rankmath_description($desc) {
        return $this->filter_yoast_metadesc($desc);
    }

    public function filter_rankmath_schema($data) {
        $fixes = $this->get_current_fixes();
        foreach ($fixes as $fix) {
            if ($fix['type'] === 'schema' && !empty($fix['payload'])) {
                $data['quardlink_schema'] = $fix['payload'];
            }
        }
        return $data;
    }

    public function register_admin_menu() {
        add_options_page('QuardLink SEO', 'QuardLink SEO', 'manage_options', 'quardlink-seo', array($this, 'admin_page_html'));
    }

    public function register_settings() {
        register_setting('quardlink_settings', 'quardlink_site_key');
        register_setting('quardlink_settings', 'quardlink_api_url');
    }

    public function admin_page_html() {
        if (!current_user_can('manage_options')) {
            return;
        }
        ?>
        <div class="wrap">
            <h1>QuardLink SEO & AEO Settings</h1>
            <p>Connect your WordPress site to QuardLink for automated search and AI visibility optimization.</p>
            <form action="options.php" method="post">
                <?php settings_fields('quardlink_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th scope="row">Site Key</th>
                        <td><input type="text" name="quardlink_site_key" value="<?php echo esc_attr(get_option('quardlink_site_key', $this->site_key)); ?>" class="regular-text" /></td>
                    </tr>
                    <tr>
                        <th scope="row">API URL</th>
                        <td><input type="url" name="quardlink_api_url" value="<?php echo esc_attr(get_option('quardlink_api_url', $this->api_url)); ?>" class="regular-text" /></td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }
}

add_action('plugins_loaded', array('QuardLink_SEO', 'get_instance'));
