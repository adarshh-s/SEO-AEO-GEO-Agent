"""Fix payload sanitization (CLAUDE.md §11).

Every fix payload is cleaned when it is created or edited, and again before it is
served to a live website. Payloads may contain text that came from LLMs or from
competitor pages, so nothing in them is trusted.

- HTML content blocks: allowlist sanitizer (nh3). No scripts, styles, event handlers,
  iframes or javascript: URLs.
- JSON-LD: must be a JSON object (or list of objects) using schema.org; when written into
  an HTML <script> tag it is serialized with `<`, `>` and `&` escaped so it can't break out.
- Text fields (title, meta description, FAQ text): tags and control characters removed,
  length bounded.
- Unknown payload keys are dropped.
"""

from __future__ import annotations

import json
import re
from typing import Any

import nh3

ALLOWED_TAGS = {
    "p",
    "br",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "b",
    "i",
    "a",
    "blockquote",
    "dl",
    "dt",
    "dd",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "section",
    "div",
    "span",
    "details",
    "summary",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}, "*": {"lang", "dir"}}
MAX_JSON_LD_BYTES = 64_000
MAX_HTML_CHARS = 50_000
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class PayloadError(ValueError):
    """A payload that can't be made safe (e.g. invalid JSON-LD)."""


def clean_html(value: Any) -> str:
    if not isinstance(value, str):
        raise PayloadError("html must be a string")
    if len(value) > MAX_HTML_CHARS:
        raise PayloadError("html is too long")
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener nofollow",
        strip_comments=True,
    ).strip()


def clean_text(value: Any, max_len: int) -> str:
    if not isinstance(value, str):
        raise PayloadError("expected text")
    text = nh3.clean(value, tags=set())  # drops all tags, keeps text (entity-escaped)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = _CONTROL.sub("", " ".join(text.split()))
    return text[:max_len]


def clean_json_ld(value: Any) -> dict | list:
    items = value if isinstance(value, list) else [value]
    if not items or not all(isinstance(i, dict) for i in items):
        raise PayloadError("json_ld must be an object or a list of objects")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PayloadError(f"json_ld is not valid JSON: {exc}") from exc
    if len(encoded.encode()) > MAX_JSON_LD_BYTES:
        raise PayloadError("json_ld is too large")
    for item in items:
        context = str(item.get("@context", ""))
        if "schema.org" not in context and "@graph" not in item:
            raise PayloadError("json_ld must use @context https://schema.org")
    return json.loads(encoded)


def json_ld_script_text(value: Any) -> str:
    """Serialize JSON-LD for an HTML <script> element without allowing a break-out."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def sanitize_payload(payload: Any) -> dict[str, Any]:
    """Return a cleaned copy of a fix payload. Unknown keys are dropped."""
    if not isinstance(payload, dict):
        raise PayloadError("payload must be an object")
    out: dict[str, Any] = {}
    if payload.get("json_ld") is not None:
        out["json_ld"] = clean_json_ld(payload["json_ld"])
    if payload.get("title") is not None:
        out["title"] = clean_text(payload["title"], 200)
    if payload.get("meta_description") is not None:
        out["meta_description"] = clean_text(payload["meta_description"], 400)
    if payload.get("html") is not None:
        out["html"] = clean_html(payload["html"])
    if payload.get("faqs") is not None:
        faqs = payload["faqs"]
        if not isinstance(faqs, list):
            raise PayloadError("faqs must be a list")
        out["faqs"] = [
            {
                "question": clean_text(f.get("question", ""), 500),
                "answer": clean_text(f.get("answer", ""), 3000),
            }
            for f in faqs[:50]
            if isinstance(f, dict)
        ]
    # Content blocks only render inside a container the customer places (decision D15),
    # so a payload can't choose where HTML goes.
    return out
