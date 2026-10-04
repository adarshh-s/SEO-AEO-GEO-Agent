"""Thread-safe SSRF-protected HTTP for customer-controlled URLs outside the crawl workers.

The workers use claude-seo's url_safety, which patches DNS resolution process-wide and is
not thread-safe, so it can't run inside the API. This module does the same job per call:

1. resolve the hostname once and require every address to be public;
2. connect to that pinned IP (TLS still verifies the real hostname via SNI), so DNS
   rebinding can't swap in a private address between the check and the connection;
3. never follow redirects automatically: each Location is re-validated the same way.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter

_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


class UnsafeUrlError(ValueError):
    """The URL points somewhere we must not connect to (private network, metadata, …)."""


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def resolve_public(host: str, port: int) -> list[str]:
    """All of host's addresses (IPv4 first), or raise if any of them isn't public."""
    host = host.rstrip(".").lower()
    if host in _BLOCKED_HOSTS or host.endswith((".local", ".internal", ".localhost")):
        raise UnsafeUrlError(f"blocked host: {host}")
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"cannot resolve {host}") from exc
    ips = sorted({info[4][0] for info in infos}, key=lambda ip: (":" in ip, ip))
    if not ips or not all(_is_public(ip) for ip in ips):
        raise UnsafeUrlError(f"{host} resolves to a non-public address")
    return ips


class _PinnedAdapter(HTTPAdapter):
    """Connects to a pre-validated IP while presenting/verifying the real hostname for TLS."""

    def __init__(self, hostname: str, **kwargs: Any) -> None:
        self._hostname = hostname
        super().__init__(**kwargs)

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs["server_hostname"] = self._hostname
        kwargs["assert_hostname"] = self._hostname
        super().init_poolmanager(*args, **kwargs)


def safe_request(
    method: str,
    url: str,
    *,
    timeout: float = 10,
    max_redirects: int = 3,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> requests.Response:
    """requests.request() for untrusted URLs. Raises UnsafeUrlError for unsafe targets."""
    for _ in range(max_redirects + 1):
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise UnsafeUrlError("only http(s) URLs with a hostname are allowed")
        if parts.username or parts.password:
            raise UnsafeUrlError("credentials in URLs are not allowed")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        ips = resolve_public(parts.hostname, port)
        resp = None
        for i, ip in enumerate(ips[:4]):  # IPv4 first; next address if one is unreachable
            ip_host = f"[{ip}]" if ":" in ip else ip
            netloc = f"{ip_host}:{port}"
            pinned = urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))
            try:
                with requests.Session() as session:
                    session.mount(f"{parts.scheme}://", _PinnedAdapter(parts.hostname))
                    req_headers = {**(headers or {}), "Host": parts.netloc.rsplit("@", 1)[-1]}
                    resp = session.request(
                        method,
                        pinned,
                        headers=req_headers,
                        timeout=timeout,
                        allow_redirects=False,
                        **kwargs,
                    )
                break
            except requests.ConnectionError:
                if i == len(ips[:4]) - 1:
                    raise
        assert resp is not None
        if resp.is_redirect and resp.headers.get("location"):
            url = urljoin(url, resp.headers["location"])
            method = "GET" if resp.status_code in (301, 302, 303) else method
            kwargs.pop("data", None)
            kwargs.pop("json", None)
            continue
        resp.url = url
        return resp
    raise UnsafeUrlError("too many redirects")


def safe_get(url: str, **kwargs: Any) -> requests.Response:
    return safe_request("GET", url, **kwargs)


def safe_post(url: str, **kwargs: Any) -> requests.Response:
    return safe_request("POST", url, **kwargs)
