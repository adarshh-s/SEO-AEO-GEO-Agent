"""Customer URL input validation. Network-level SSRF checks happen in the worker (url_safety)."""

import ipaddress
from urllib.parse import urlsplit

from app_api.errors import ApiError

_BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}


def _invalid(message: str = "Enter a valid public website address, like example.com.") -> ApiError:
    return ApiError(422, "invalid_url", message)


def normalize_site_url(raw: str) -> tuple[str, str]:
    """Return (homepage_url, domain) for user input like 'Example.com/path' or 'https://x.com'."""
    value = raw.strip()
    if not value:
        raise _invalid()
    if "://" not in value:
        value = f"https://{value}"
    parts = urlsplit(value)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise _invalid()
    host = parts.hostname.rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise _invalid() from None
    try:
        ipaddress.ip_address(host)
        raise _invalid("Use the website's domain name, not an IP address.")
    except ValueError:
        pass
    if host in _BLOCKED_HOSTS or "." not in host or host.endswith((".local", ".internal")):
        raise _invalid()
    port = f":{parts.port}" if parts.port and parts.port not in (80, 443) else ""
    domain = host[4:] if host.startswith("www.") else host
    return f"{parts.scheme}://{host}{port}/", domain


def normalize_domain(raw: str) -> str:
    return normalize_site_url(raw)[1]
