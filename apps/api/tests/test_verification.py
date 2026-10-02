"""Tests for site ownership verification via HTML meta tag and DNS TXT record."""

import uuid
from unittest.mock import MagicMock, patch

from app_core.brand import BRAND
from app_core.db import system_session
from app_core.models import AuditLogEntry, Site
from conftest import SITE, signup


def test_get_verification_status(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    res = owner.client.get(f"/sites/{site_id}/verification")
    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is False
    assert data["domain"] == "example.com"
    assert "token" in data
    assert (
        f'<meta name="{BRAND["verification_meta_name"]}" content="{data["token"]}">'
        in data["meta_tag"]
    )
    assert f"{BRAND['dns_txt_prefix']}{data['token']}" in data["dns_txt_record"]


def test_verify_via_meta_tag(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    status = owner.client.get(f"/sites/{site_id}/verification").json()
    token = status["token"]
    html_page = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <title>Test Page</title>
        <meta name="{BRAND["verification_meta_name"]}" content="{token}">
      </head>
      <body><h1>Welcome</h1></body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_page

    with patch("requests.get", return_value=mock_resp):
        res = owner.client.post(f"/sites/{site_id}/verify")
        assert res.status_code == 200
        data = res.json()
        assert data["verified"] is True
        assert data["method"] == "meta_tag"

    # Verify site in DB is marked verified
    with system_session() as db:
        s = db.get(Site, uuid.UUID(site_id))
        assert s.verified_at is not None
        assert s.verification_method == "meta_tag"

        logs = db.query(AuditLogEntry).filter_by(action="site.verified").all()
        assert len(logs) == 1


def test_verify_via_dns_txt(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    status = owner.client.get(f"/sites/{site_id}/verification").json()
    token = status["token"]

    # Meta tag check fails
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head></head><body>No meta tag here</body></html>"

    # DNS mock record
    mock_txt_item = MagicMock()
    mock_txt_item.strings = [f"{BRAND['dns_txt_prefix']}{token}".encode()]

    with (
        patch("requests.get", return_value=mock_resp),
        patch("dns.resolver.resolve", return_value=[mock_txt_item]),
    ):
        res = owner.client.post(f"/sites/{site_id}/verify")
        assert res.status_code == 200
        data = res.json()
        assert data["verified"] is True
        assert data["method"] == "dns_txt"


def test_verification_failed_when_both_missing(app):
    owner = signup(app)
    site = owner.client.post("/sites", json=SITE).json()
    site_id = site["id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head></head><body>Nothing</body></html>"

    with (
        patch("requests.get", return_value=mock_resp),
        patch("dns.resolver.resolve", side_effect=Exception("No TXT records")),
    ):
        res = owner.client.post(f"/sites/{site_id}/verify")
        assert res.status_code == 400
        assert res.json()["detail"]["code"] == "verification_failed"
