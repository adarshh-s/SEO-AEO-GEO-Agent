"""Tests for Integrations: universal snippet info, API key management, and Webhooks."""

from conftest import SITE, signup


def test_snippet_info(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    res = owner.client.get(f"/sites/{site_id}/integrations/snippet")
    assert res.status_code == 200
    data = res.json()
    assert data["site_key"].startswith("qls_")
    assert "/public/v1/agent.js" in data["script_url"]
    assert f'data-site="{data["site_key"]}"' in data["snippet_tag"]
    assert "wordpress" in data["instructions"]
    assert "shopify" in data["instructions"]
    assert "nextjs" in data["instructions"]


def test_api_keys_lifecycle(app):
    owner = signup(app)

    # 1. Create API key
    create_res = owner.client.post(
        "/org/api-keys",
        json={"name": "Production Key", "scopes": ["fixes:read", "fixes:deploy"]},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == "Production Key"
    assert created["scopes"] == ["fixes:read", "fixes:deploy"]
    assert "raw_key" in created
    assert created["raw_key"].startswith("ql_live_")
    key_id = created["id"]

    # 2. List API keys (raw_key should NOT be present)
    list_res = owner.client.get("/org/api-keys")
    assert list_res.status_code == 200
    keys = list_res.json()
    assert len(keys) == 1
    assert keys[0]["id"] == key_id
    assert keys[0]["name"] == "Production Key"
    assert "raw_key" not in keys[0]
    assert "hashed_key" not in keys[0]
    assert keys[0]["prefix"].startswith("ql_live_")

    # 3. Delete API key
    del_res = owner.client.delete(f"/org/api-keys/{key_id}")
    assert del_res.status_code == 200

    list_after = owner.client.get("/org/api-keys").json()
    assert len(list_after) == 0


def test_webhooks_lifecycle(app):
    owner = signup(app)

    # 1. Create Webhook
    create_res = owner.client.post(
        "/org/webhooks",
        json={
            "url": "https://api.myclient.com/webhook",
            "events": ["fix.created", "fix.approved", "fix.deployed"],
        },
    )
    assert create_res.status_code == 201
    wh = create_res.json()
    assert wh["url"] == "https://api.myclient.com/webhook"
    assert wh["status"] == "active"
    assert "secret" in wh
    webhook_id = wh["id"]

    # 2. List Webhooks
    list_res = owner.client.get("/org/webhooks")
    assert list_res.status_code == 200
    whs = list_res.json()
    assert len(whs) == 1
    assert whs[0]["id"] == webhook_id

    # 3. Delete Webhook
    del_res = owner.client.delete(f"/org/webhooks/{webhook_id}")
    assert del_res.status_code == 200

    list_after = owner.client.get("/org/webhooks").json()
    assert len(list_after) == 0
