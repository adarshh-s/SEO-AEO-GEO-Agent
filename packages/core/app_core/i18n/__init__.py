"""Server-side translations (emails, reports, notifications).

English is the source; other locales may be incomplete and fall back to English per key.
Add a language by adding `<code>.json` here (and to SUPPORTED_UI_LANGUAGES).
`{product}` is always available and filled from brand.json.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app_core.brand import PRODUCT_NAME
from app_core.languages import DEFAULT_LANGUAGE

_DIR = Path(__file__).parent


@lru_cache
def _catalog(lang: str) -> dict[str, str]:
    path = _DIR / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def t(lang: str | None, key: str, **params: Any) -> str:
    text = _catalog(lang or DEFAULT_LANGUAGE).get(key) or _catalog(DEFAULT_LANGUAGE).get(key) or key
    return text.format(product=PRODUCT_NAME, **params)
