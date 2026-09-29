from sqlalchemy import func, select

from app_api.seed import DEMO_EMAIL, seed
from app_core.db import system_session
from app_core.models import AiPrompt, Keyword, Site
from conftest import make_client


def test_seed_is_idempotent_and_demo_can_log_in(app):
    assert seed() is True
    assert seed() is False
    with system_session() as db:
        sites = {s.platform: s for s in db.scalars(select(Site))}
        assert set(sites) == {"wordpress", "nextjs", "salla"}
        assert sites["salla"].additional_languages == ["ar"]
        assert sites["wordpress"].additional_languages == []
        assert (
            db.scalar(select(func.count()).select_from(Keyword).where(Keyword.language == "ar"))
            == 3
        )
        assert db.scalar(select(func.count()).select_from(AiPrompt)) == 14
    client = make_client(app)
    r = client.post("/auth/login", json={"email": DEMO_EMAIL, "password": "demo-password-123"})
    assert r.status_code == 200
    assert r.json()["orgs"][0]["plan_code"] == "business"
