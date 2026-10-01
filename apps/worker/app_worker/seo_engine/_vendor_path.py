"""Vendor path setup for claude-seo scripts.

Only files inside apps/worker/app_worker/seo_engine/ should import this.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VENDOR_SCRIPTS = _REPO_ROOT / "vendor" / "claude-seo" / "scripts"

if _VENDOR_SCRIPTS.exists() and str(_VENDOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_VENDOR_SCRIPTS))
