"""Tests for Saudi platform connectors (Salla and Zid)."""

from app_core.connectors import get_connector
from app_core.connectors.salla import (
    SallaConnector,
    generate_salla_instructions,
    generate_salla_snippet_code,
)
from app_core.connectors.zid import (
    ZidConnector,
    generate_zid_instructions,
    generate_zid_snippet_code,
)


def test_salla_connector_snippet_mode():
    conn = get_connector("salla")
    assert isinstance(conn, SallaConnector)

    # Snippet mode test connection
    res = conn.test_connection(config={"mode": "snippet"}, credentials={})
    assert res.ok is True
    assert "Manual Snippet" in res.message

    # Deploy fix in snippet mode
    deploy_res = conn.deploy_fix(
        target_url="https://salla.sa/store/product-1",
        fix_type="meta",
        title="Optimized Title",
        payload={"title": "Optimized Title"},
        config={"mode": "snippet"},
        credentials={},
        site_key="salla_site_key_123",
    )
    assert deploy_res.ok is True
    assert "CDN snippet" in deploy_res.message
    assert deploy_res.external_reference is not None

    # Rollback fix
    rb_res = conn.rollback_fix(
        target_url="https://salla.sa/store/product-1",
        fix_type="meta",
        external_reference=deploy_res.external_reference,
        previous_state=deploy_res.previous_state,
        config={"mode": "snippet"},
        credentials={},
    )
    assert rb_res.ok is True


def test_salla_connector_partner_api_mock():
    conn = SallaConnector()
    # Test connection with mock token
    res = conn.test_connection(
        config={"mode": "partner_api", "app_id": "app-test-1"},
        credentials={"access_token": "mock-token-salla"},
    )
    assert res.ok is True
    assert "Connected successfully" in res.message

    # Deploy fix
    deploy_res = conn.deploy_fix(
        target_url="https://salla.sa/store/product-1",
        fix_type="meta",
        title="API Meta Title",
        payload={"title": "API Meta Title"},
        config={"mode": "partner_api"},
        credentials={"access_token": "mock-token-salla"},
        site_key="salla_site_key_123",
    )
    assert deploy_res.ok is True
    assert "salla-api-" in deploy_res.external_reference


def test_salla_bilingual_instructions():
    instr = generate_salla_instructions("site_key_abc")
    assert "سلة" in instr["ar"]
    assert "Twilight" in instr["en"] or "Header Scripts" in instr["en"]

    code = generate_salla_snippet_code("site_key_abc")
    assert 'data-platform="salla"' in code
    assert "site_key_abc" in code


def test_zid_connector_snippet_mode():
    conn = get_connector("zid")
    assert isinstance(conn, ZidConnector)

    res = conn.test_connection(config={"mode": "snippet"}, credentials={})
    assert res.ok is True
    assert "Manual Snippet" in res.message

    deploy_res = conn.deploy_fix(
        target_url="https://zid.store/item-1",
        fix_type="meta",
        title="Zid Optimized Title",
        payload={"title": "Zid Optimized Title"},
        config={"mode": "snippet"},
        credentials={},
        site_key="zid_site_key_456",
    )
    assert deploy_res.ok is True
    assert "CDN snippet" in deploy_res.message

    rb_res = conn.rollback_fix(
        target_url="https://zid.store/item-1",
        fix_type="meta",
        external_reference=deploy_res.external_reference,
        previous_state=deploy_res.previous_state,
        config={"mode": "snippet"},
        credentials={},
    )
    assert rb_res.ok is True


def test_zid_connector_partner_api_mock():
    conn = ZidConnector()
    res = conn.test_connection(
        config={"mode": "partner_api", "store_id": "zid-store-99"},
        credentials={"access_token": "test-token-zid"},
    )
    assert res.ok is True
    assert "Connected successfully" in res.message

    deploy_res = conn.deploy_fix(
        target_url="https://zid.store/item-1",
        fix_type="content_block",
        title="Zid FAQ Block",
        payload={"content": "<p>FAQ</p>"},
        config={"mode": "partner_api"},
        credentials={"access_token": "test-token-zid"},
        site_key="zid_site_key_456",
    )
    assert deploy_res.ok is True
    assert "zid-api-" in deploy_res.external_reference


def test_zid_bilingual_instructions():
    instr = generate_zid_instructions("site_key_xyz")
    assert "زد" in instr["ar"]
    assert "Zid Integration Guide" in instr["en"]

    code = generate_zid_snippet_code("site_key_xyz")
    assert 'data-platform="zid"' in code
    assert "site_key_xyz" in code
