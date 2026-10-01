"""SSRF and URL safety adapter.

Wraps vendor/claude-seo/scripts/url_safety.py with our typed signatures.
"""

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import app_worker.seo_engine._vendor_path  # noqa: F401

try:
    import url_safety as _vendor_safety

    URLSafetyError = _vendor_safety.URLSafetyError
    validate_url = _vendor_safety.validate_url
    validate_url_strict = _vendor_safety.validate_url_strict
    safe_requests_get = _vendor_safety.safe_requests_get
    safe_requests_head = _vendor_safety.safe_requests_head
    safe_requests_session = _vendor_safety.safe_requests_session
    is_safe_ip = _vendor_safety.is_safe_ip
except ImportError:

    class URLSafetyError(ValueError):
        pass

    def is_safe_ip(ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
            return not (
                ip.is_private
                or ip.is_loopback
                or ip.is_reserved
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_unspecified
            )
        except ValueError:
            return False

    def validate_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            host = parsed.hostname
            return bool(host and host not in ("localhost", "127.0.0.1", "::1", "169.254.169.254"))
        except Exception:
            return False

    def validate_url_strict(url: str) -> tuple[str, str]:
        if not validate_url(url):
            raise URLSafetyError(f"Invalid URL: {url}")
        parsed = urlparse(url)
        host = parsed.hostname or ""
        try:
            infos = socket.getaddrinfo(host, parsed.port or 80, socket.AF_INET)
            ips = [info[4][0] for info in infos]
            for ip in ips:
                if not is_safe_ip(ip):
                    raise URLSafetyError(f"Hostname resolves to unsafe IP: {ip}")
            pinned_ip = ips[0] if ips else "127.0.0.1"
            return url, pinned_ip
        except socket.gaierror as e:
            raise URLSafetyError(f"DNS resolution failed: {e}") from e

    def safe_requests_get(url: str, **kwargs: Any) -> Any:
        import requests

        validate_url_strict(url)
        timeout = kwargs.pop("timeout", 15)
        return requests.get(url, timeout=timeout, **kwargs)

    def safe_requests_head(url: str, **kwargs: Any) -> Any:
        import requests

        validate_url_strict(url)
        timeout = kwargs.pop("timeout", 10)
        return requests.head(url, timeout=timeout, **kwargs)

    def safe_requests_session(url: str) -> Any:
        from contextlib import contextmanager

        import requests

        @contextmanager
        def _session():
            validate_url_strict(url)
            s = requests.Session()
            try:
                yield s
            finally:
                s.close()

        return _session()
