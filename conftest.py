"""Root test config: tests never read a developer's .env (see app_core.settings)."""

import os

os.environ.setdefault("APP_ENV_FILE", "")
os.environ.setdefault("ENV", "test")
