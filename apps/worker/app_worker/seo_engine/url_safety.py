"""SSRF protection for every outbound fetch of a customer-supplied URL (CLAUDE.md §9, §11).

Thin re-export of vendor/claude-seo/scripts/url_safety.py (DNS-pinned requests, redirect
re-validation, private/reserved/metadata IP blocking). There is deliberately no fallback:
if the vendored module is missing, importing this module fails, so a worker can never run
with weaker protection. The worker image must include vendor/claude-seo.

The vendored module patches DNS resolution process-wide, so only call it from Celery
prefork workers (one task per process), never from threads or the API.
"""

import app_worker.seo_engine._vendor_path  # noqa: F401  (puts vendor scripts on sys.path)

try:
    import url_safety as _vendor_safety
except ImportError as exc:  # pragma: no cover - deployment error, not a runtime branch
    raise ImportError(
        "vendor/claude-seo is missing (run `git submodule update --init`); refusing to fetch "
        "customer URLs without SSRF protection"
    ) from exc

URLSafetyError = _vendor_safety.URLSafetyError
is_safe_ip = _vendor_safety.is_safe_ip
validate_url = _vendor_safety.validate_url
validate_url_strict = _vendor_safety.validate_url_strict
safe_requests_get = _vendor_safety.safe_requests_get
safe_requests_head = _vendor_safety.safe_requests_head
safe_requests_session = _vendor_safety.safe_requests_session
make_safe_playwright_route_handler = _vendor_safety.make_safe_playwright_route_handler

__all__ = [
    "URLSafetyError",
    "is_safe_ip",
    "make_safe_playwright_route_handler",
    "safe_requests_get",
    "safe_requests_head",
    "safe_requests_session",
    "validate_url",
    "validate_url_strict",
]
