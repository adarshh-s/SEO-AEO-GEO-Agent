#!/usr/bin/env python3
"""Write the API's OpenAPI schema to openapi.json (source for the web app's generated types)."""

import json
import os
from pathlib import Path

os.environ.setdefault("ENV", "local")

from app_api.main import app  # noqa: E402

out = Path(__file__).resolve().parent.parent / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {out.name}")
