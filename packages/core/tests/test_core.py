import json
from pathlib import Path

from app_core.brand import BRAND, PRODUCT_NAME, crawler_user_agent
from app_core.i18n import t
from app_core.languages import is_rtl

ROOT = Path(__file__).resolve().parents[3]


def test_brand_generated_matches_config():
    config = {
        k: v
        for k, v in json.loads((ROOT / "config/brand.json").read_text()).items()
        if not k.startswith("_")
    }
    assert config == BRAND
    assert config["product_name"] == PRODUCT_NAME


def test_crawler_user_agent_uses_brand_and_never_upstream_name():
    ua = crawler_user_agent("https://example.com/bot")
    assert BRAND["crawler_user_agent_token"] in ua
    assert "ClaudeSEO" not in ua


def test_rtl_detection():
    assert is_rtl("ar") and is_rtl("ar-SA")
    assert not is_rtl("en")


def test_i18n_falls_back_to_english_and_fills_product(tmp_path, monkeypatch):
    assert PRODUCT_NAME in t("en", "email.verify.subject")
    assert t("ar", "email.verify.subject") != t("en", "email.verify.subject")
    assert t("fr", "email.verify.subject") == t("en", "email.verify.subject")  # missing locale
    assert t("ar", "no.such.key") == "no.such.key"


def test_production_refuses_dev_secrets():
    import pytest
    from pydantic import ValidationError

    from app_core.settings import DEV_JWT_SECRET, Settings

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(env="production", cookie_secure=True, jwt_secret=DEV_JWT_SECRET)
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(env="production", jwt_secret="x" * 40, cookie_secure=False)
    assert Settings(env="production", jwt_secret="x" * 40, cookie_secure=True).is_production
