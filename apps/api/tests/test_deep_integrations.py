"""Unit tests for Phase 4 deep integrations and platform connectors."""

import io
import uuid
import zipfile

import pytest

from app_core.connectors import (
    CloudflareConnector,
    GithubConnector,
    GoogleSearchConsoleConnector,
    ShopifyConnector,
    WebflowConnector,
    WixConnector,
    WordpressConnector,
    generate_cloudflare_worker_js,
    generate_wordpress_plugin_php,
    generate_wordpress_plugin_zip,
)
from app_core.models import Fix
from conftest import SITE, set_plan, signup


@pytest.fixture
def site_setup(app):
    acct = signup(app, email="integrator@example.com", org_name="Integration Corp")
    set_plan(acct.org_id, "growth")
    site = acct.client.post("/sites", json={**SITE, "homepage_url": "https://example.com"}).json()
    return acct, site


def test_wordpress_connector_and_generator():
    wp = WordpressConnector()
    res = wp.test_connection({"site_url": "https://example.com"}, {})
    assert res.ok
    assert "plugin_sync" in res.details["mode"]

    # Plugin php & zip generation
    php = generate_wordpress_plugin_php("test_site_key_123", "https://api.example.com")
    assert "QuardLink_SEO" in php
    assert "test_site_key_123" in php
    assert "wpseo_schema_graph" in php
    assert "rank_math/json_ld" in php
    assert "gptbot" in php

    zip_bytes = generate_wordpress_plugin_zip("test_key", "https://api.example.com")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "quardlink-seo/quardlink-seo.php" in names
        assert "quardlink-seo/readme.txt" in names

    # Deploy meta fix
    meta_deploy = wp.deploy_fix(
        target_url="https://example.com/about",
        fix_type="meta",
        title="About Us Updated Title",
        payload={"title": "About Us Updated Title", "meta_description": "Meta description content"},
        config={"site_url": "https://example.com"},
        credentials={},
        site_key="test_key",
    )
    assert meta_deploy.ok
    assert meta_deploy.external_reference is not None

    # Deploy content fix (must be draft, never publish)
    content_deploy = wp.deploy_fix(
        target_url="https://example.com/faq",
        fix_type="faq",
        title="Frequently Asked Questions",
        payload={"html": "<p>FAQ Content</p>"},
        config={"site_url": "https://example.com"},
        credentials={},
        site_key="test_key",
    )
    assert content_deploy.ok
    assert content_deploy.details["status"] == "draft"

    # Rollback
    rollback_res = wp.rollback_fix(
        target_url="https://example.com/about",
        fix_type="meta",
        external_reference=meta_deploy.external_reference,
        previous_state=meta_deploy.previous_state,
        config={"site_url": "https://example.com"},
        credentials={},
    )
    assert rollback_res.ok


def test_shopify_connector():
    shopify = ShopifyConnector()
    test_conn = shopify.test_connection({"shop_domain": "myshop.myshopify.com"}, {})
    assert test_conn.ok

    # Meta fix
    meta_res = shopify.deploy_fix(
        target_url="https://example.com/products/headphones",
        fix_type="meta",
        title="Wireless Headphones Pro",
        payload={"title": "Wireless Headphones Pro", "meta_description": "Best noise cancelling"},
        config={"shop_domain": "myshop.myshopify.com"},
        credentials={},
        site_key="test_key",
    )
    assert meta_res.ok
    assert meta_res.external_reference is not None

    # Schema fix (app metafield)
    schema_res = shopify.deploy_fix(
        target_url="https://example.com/products/headphones",
        fix_type="schema",
        title="Product Schema",
        payload={"@context": "https://schema.org", "@type": "Product", "name": "Headphones"},
        config={"shop_domain": "myshop.myshopify.com"},
        credentials={},
        site_key="test_key",
    )
    assert schema_res.ok
    assert "quardlink" in schema_res.details["namespace"]

    # Draft blog article for content fix
    blog_res = shopify.deploy_fix(
        target_url="https://example.com/blogs/news/guide",
        fix_type="content_block",
        title="SEO Guide 2026",
        payload={"html": "<p>Content</p>"},
        config={"shop_domain": "myshop.myshopify.com"},
        credentials={},
        site_key="test_key",
    )
    assert blog_res.ok
    assert blog_res.details["isPublished"] is False


def test_github_connector():
    gh = GithubConnector()
    conn_res = gh.test_connection({"repo_owner": "acme", "repo_name": "web"}, {})
    assert conn_res.ok

    deploy_res = gh.deploy_fix(
        target_url="https://example.com/about",
        fix_type="meta",
        title="Updated Page Title",
        payload={"title": "Updated Page Title", "meta_description": "Updated Description"},
        config={"repo_owner": "acme", "repo_name": "web", "base_branch": "main"},
        credentials={},
        site_key="test_key",
    )
    assert deploy_res.ok
    assert "https://github.com/acme/web/pull/" in deploy_res.external_reference
    assert deploy_res.details["branch"].startswith("quardlink/fix-")

    rollback_res = gh.rollback_fix(
        target_url="https://example.com/about",
        fix_type="meta",
        external_reference=deploy_res.external_reference,
        previous_state=deploy_res.previous_state,
        config={"repo_owner": "acme", "repo_name": "web"},
        credentials={},
    )
    assert rollback_res.ok


def test_cloudflare_connector_and_script():
    cf = CloudflareConnector()
    conn = cf.test_connection({"zone_id": "zone123"}, {})
    assert conn.ok

    js_code = generate_cloudflare_worker_js("cf_site_key", "https://api.example.com")
    assert "HTMLRewriter" in js_code
    assert "cf_site_key" in js_code
    assert "ctx.waitUntil" in js_code
    assert "trackAiTelemetry" in js_code

    deploy = cf.deploy_fix(
        target_url="https://example.com",
        fix_type="meta",
        title="Edge Title",
        payload={"title": "Edge Title"},
        config={"zone_id": "zone123"},
        credentials={},
        site_key="cf_site_key",
    )
    assert deploy.ok
    assert "cf-edge-" in deploy.external_reference


def test_google_search_console_connector():
    gsc = GoogleSearchConsoleConnector()
    auth_url = gsc.get_auth_url("client123", "https://app.example.com/oauth", "state123")
    assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert "webmasters.readonly" in auth_url

    tokens = gsc.exchange_code("", "", "auth_code_123", "https://app.example.com/oauth")
    assert tokens["access_token"].startswith("gsc_mock_access_")

    sites = gsc.list_sites(tokens["access_token"])
    assert len(sites) >= 1
    assert sites[0]["permissionLevel"] == "siteOwner"

    analytics = gsc.query_search_analytics(tokens["access_token"], "https://example.com/")
    assert len(analytics) >= 1
    assert "clicks" in analytics[0]
    assert "impressions" in analytics[0]


def test_webflow_and_wix_connectors():
    wf = WebflowConnector()
    wf_conn = wf.test_connection({"site_id": "wf_123"}, {})
    assert wf_conn.ok
    wf_deploy = wf.deploy_fix(
        target_url="https://example.com/services",
        fix_type="meta",
        title="Webflow Services",
        payload={"title": "Webflow Services", "meta_description": "Services desc"},
        config={"site_id": "wf_123"},
        credentials={},
        site_key="key",
    )
    assert wf_deploy.ok

    wix = WixConnector()
    wix_conn = wix.test_connection({"site_id": "wix_123"}, {})
    assert wix_conn.ok
    wix_deploy = wix.deploy_fix(
        target_url="https://example.com/contact",
        fix_type="meta",
        title="Contact Wix Title",
        payload={"title": "Contact Wix Title", "meta_description": "Contact desc"},
        config={"site_id": "wix_123"},
        credentials={},
        site_key="key",
    )
    assert wix_deploy.ok


def test_site_integrations_api_crud_and_downloads(app, site_setup):
    acct, site = site_setup
    client = acct.client
    site_id = site["id"]

    # 1. List initially empty
    resp = client.get(f"/sites/{site_id}/integrations")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Connect WordPress
    create_resp = client.post(
        f"/sites/{site_id}/integrations",
        json={"provider": "wordpress", "config": {"site_url": "https://example.com"}},
    )
    assert create_resp.status_code == 201
    wp_integ = create_resp.json()
    assert wp_integ["provider"] == "wordpress"
    assert wp_integ["status"] == "active"
    integ_id = wp_integ["id"]

    # 3. Test connection
    test_resp = client.post(f"/sites/{site_id}/integrations/{integ_id}/test")
    assert test_resp.status_code == 200
    assert test_resp.json()["ok"] is True

    # 4. Patch config
    patch_resp = client.patch(
        f"/sites/{site_id}/integrations/{integ_id}",
        json={"config": {"site_url": "https://example.com", "yoast_active": True}},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["config"]["yoast_active"] is True

    # 5. Download WordPress Plugin Zip
    dl_resp = client.get(f"/sites/{site_id}/integrations/wordpress/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/zip"
    assert len(dl_resp.content) > 500

    # 6. Get Cloudflare Worker JS
    cf_resp = client.get(f"/sites/{site_id}/integrations/cloudflare/worker.js")
    assert cf_resp.status_code == 200
    assert "HTMLRewriter" in cf_resp.text
    assert site["site_key"] in cf_resp.text

    # 7. Google Search Console OAuth endpoints
    auth_resp = client.get(
        f"/sites/{site_id}/integrations/google-search-console/auth-url?redirect_uri=https://app.example.com/oauth"
    )
    assert auth_resp.status_code == 200
    assert "accounts.google.com" in auth_resp.json()["auth_url"]

    # Connect GSC
    connect_resp = client.post(
        f"/sites/{site_id}/integrations/google-search-console/connect",
        json={
            "code": "sample_auth_code",
            "property_url": "https://example.com/",
            "redirect_uri": "https://app.example.com/oauth",
        },
    )
    assert connect_resp.status_code == 200
    assert connect_resp.json()["provider"] == "google_search_console"

    # Site ownership verified via GSC
    site_after = client.get(f"/sites/{site_id}").json()
    assert site_after["verified_at"] is not None
    assert site_after["verification_method"] == "google_search_console"

    # Query GSC performance
    perf_resp = client.get(f"/sites/{site_id}/integrations/google-search-console/performance")
    assert perf_resp.status_code == 200
    assert len(perf_resp.json()["rows"]) >= 1

    # 8. Delete integration
    del_resp = client.delete(f"/sites/{site_id}/integrations/{integ_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True


def test_fix_deployment_and_rollback_via_deep_integration(app, site_setup):
    acct, site = site_setup
    client = acct.client
    site_id = site["id"]

    # Connect GitHub integration
    client.post(
        f"/sites/{site_id}/integrations",
        json={
            "provider": "github",
            "config": {"repo_owner": "org", "repo_name": "repo", "base_branch": "main"},
        },
    )

    # Create a fix
    from app_core.db import system_session

    fix_id = uuid.uuid4()
    with system_session() as session:
        session.add(
            Fix(
                id=fix_id,
                org_id=acct.org_id,
                site_id=uuid.UUID(site_id),
                type="meta",
                status="approved",
                language="en",
                target_url="https://example.com/pricing",
                title="Best Pricing Plans",
                payload={"title": "Best Pricing Plans", "meta_description": "Affordable plans"},
            )
        )
        session.commit()

    # Deploy via GitHub
    deploy_resp = client.post(
        f"/sites/{site_id}/fixes/{fix_id}/deploy",
        json={"deployed_via": "github"},
    )
    assert deploy_resp.status_code == 200
    fix_data = deploy_resp.json()
    assert fix_data["status"] == "deployed"
    assert fix_data["deployed_via"] == "github"
    assert "https://github.com/org/repo/pull/" in fix_data["external_reference"]

    # Rollback fix
    rollback_resp = client.post(f"/sites/{site_id}/fixes/{fix_id}/rollback")
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["status"] == "rolled_back"
