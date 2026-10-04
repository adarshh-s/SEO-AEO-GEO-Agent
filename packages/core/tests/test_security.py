"""Regression tests for the 2026-10-04 security review (sanitization, SSRF, crypto, providers)."""

import socket

import pytest

from app_core.sanitize import (
    PayloadError,
    clean_html,
    json_ld_script_text,
    sanitize_payload,
)

XSS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg/onload=alert(1)>",
    '<a href="javascript:alert(1)">x</a>',
    '<iframe src="https://evil.example"></iframe>',
    '<p style="background:url(javascript:alert(1))">x</p>',
    "<math><mtext><table><mglyph><style><img src=x onerror=alert(1)>",
]


@pytest.mark.parametrize("payload", XSS)
def test_html_sanitizer_removes_script_vectors(payload):
    out = clean_html(payload).lower()
    for bad in ("<script", "onerror", "onload", "javascript:", "<iframe", "style="):
        assert bad not in out


def test_html_sanitizer_keeps_safe_content():
    out = clean_html('<h2>FAQ</h2><p>Visit <a href="https://example.com">us</a></p>')
    assert "<h2>FAQ</h2>" in out and 'href="https://example.com"' in out
    assert 'rel="noopener nofollow"' in out


def test_json_ld_cannot_break_out_of_script_tag():
    text = json_ld_script_text({"name": "</script><script>alert(1)</script>"})
    assert "</script" not in text.lower() and "<" not in text


def test_json_ld_validation():
    ok = {"@context": "https://schema.org", "@type": "Organization", "name": "Acme"}
    assert sanitize_payload({"json_ld": ok})["json_ld"] == ok
    for bad in ("not json-ld", [1, 2], {"@type": "Thing"}, {"@context": "https://evil", "x": 1}):
        with pytest.raises(PayloadError):
            sanitize_payload({"json_ld": bad})


def test_payload_unknown_keys_and_selectors_dropped():
    out = sanitize_payload({"title": "<b>Hi</b>", "container_selector": "body", "evil": 1})
    assert out == {"title": "Hi"}


# --- SSRF guard (API-side) ----------------------------------------------------------------


def _fake_resolver(ip):
    return lambda host, port, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.1.2.3", "169.254.169.254", "192.168.0.1", "100.64.0.1"]
)
def test_safe_request_blocks_hosts_resolving_to_private_ips(monkeypatch, ip):
    from app_core import net

    monkeypatch.setattr(net.socket, "getaddrinfo", _fake_resolver(ip))  # any private IP blocks
    with pytest.raises(net.UnsafeUrlError):
        net.safe_get("https://innocent-looking.example.com/")


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "gopher://x", "http://localhost/", "http://a:b@example.com/"]
)
def test_safe_request_rejects_bad_urls(url):
    from app_core.net import UnsafeUrlError, safe_get

    with pytest.raises(UnsafeUrlError):
        safe_get(url)


# --- encryption at rest ------------------------------------------------------------------


def test_encryption_round_trip_and_not_plaintext():
    from app_core.crypto import decrypt, encrypt

    token = encrypt('{"access_token": "shpat_secret"}')
    assert "shpat_secret" not in token
    assert decrypt(token) == '{"access_token": "shpat_secret"}'


# --- providers never fake data in production --------------------------------------------------


def test_providers_refuse_to_mock_in_production(monkeypatch):
    from app_core.providers import ai_answer, serp
    from app_core.settings import Settings

    prod = Settings(
        env="staging",
        jwt_secret="x" * 40,
        cookie_secure=True,
        app_encryption_key="Wl9kZXZfX2tleV9fZm9yX190ZXN0c19vbmx5X18xMjM0NTY=",
    )
    monkeypatch.setattr(ai_answer, "get_settings", lambda: prod)
    monkeypatch.setattr(serp, "get_settings", lambda: prod)
    with pytest.raises(ai_answer.ProviderNotConfigured):
        ai_answer.get_answer_engine("chatgpt")
    with pytest.raises(ai_answer.ProviderNotConfigured):
        serp.get_serp_provider()


def test_mock_providers_allowed_in_tests():
    from app_core.providers.ai_answer import MockAnswerEngineProvider, get_answer_engine

    assert isinstance(get_answer_engine("gemini"), MockAnswerEngineProvider)


def test_serp_country_codes():
    from app_core.providers.serp import UnsupportedCountry, country_location_code

    assert country_location_code("US") == 2840
    assert country_location_code("sa") == 2682
    assert country_location_code("AE") == 2784
    assert country_location_code("GB") == 2826
    with pytest.raises(UnsupportedCountry):
        country_location_code("ZZ")


def test_shopify_shop_domain_is_restricted():
    from app_core.connectors.shopify import shopify_shop_domain

    assert shopify_shop_domain("my-store") == "my-store.myshopify.com"
    assert shopify_shop_domain("https://My-Store.myshopify.com/admin") == "my-store.myshopify.com"
    for bad in ("169.254.169.254", "evil.com", "my-store.myshopify.com.evil.com", "x.myshopify.co"):
        with pytest.raises(ValueError):
            shopify_shop_domain(bad)


def test_resolve_prefers_ipv4_and_rejects_mixed(monkeypatch):
    from app_core import net

    infos = [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700::1", 443, 0, 0)),
             (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.215.14", 443))]  # fmt: skip
    monkeypatch.setattr(net.socket, "getaddrinfo", lambda *a, **k: infos)
    assert net.resolve_public("x.example", 443) == ["93.184.215.14", "2606:4700::1"]
    mixed = infos + [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]
    monkeypatch.setattr(net.socket, "getaddrinfo", lambda *a, **k: mixed)
    with pytest.raises(net.UnsafeUrlError):
        net.resolve_public("x.example", 443)
