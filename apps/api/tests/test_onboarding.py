from conftest import set_plan

SHOP_HTML = """<html lang="en"><head><title>Oud House | Luxury Oud</title>
<meta property="og:site_name" content="Riyadh Oud House">
<link rel="stylesheet" href="https://cdn.shopify.com/s/files/theme.css">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Store",
"name":"Riyadh Oud House","address":{"addressLocality":"Riyadh","addressCountry":"SA"}}</script>
</head><body><h1>Authentic oud</h1><p>Hand-picked oud oils. عطور العود الفاخرة</p></body></html>"""


def _fake_site(monkeypatch, html=SHOP_HTML):
    from app_api.services import onboarding

    monkeypatch.setattr(
        onboarding, "fetch_homepage", lambda url: (html, {"content-type": "text/html"}, url)
    )


def test_analyze_reads_the_real_page_without_ai(account, monkeypatch):
    _fake_site(monkeypatch)
    body = account.client.post("/onboarding/analyze", json={"url": "oudhouse.com"}).json()
    assert body["source"] == "live" and body["notice"] == "ai_unavailable"
    assert body["platform"] == "shopify"  # fingerprinted from the HTML, not the hostname
    assert body["brand_name"] == "Riyadh Oud House"
    assert body["city"] == "Riyadh" and body["country"] == "SA"
    # Arabic text found on the site is reported, but tracking languages are chosen by the user.
    assert body["detected_languages"] == ["en", "ar"]


def test_analyze_with_ai_fills_profile_and_logs_cost(account, monkeypatch):
    from decimal import Decimal

    from app_api.services import onboarding
    from app_core import llm

    _fake_site(monkeypatch)
    profile = onboarding.SiteProfile(
        brand_name="Riyadh Oud House",
        industry="luxury oud perfume store",
        city="Riyadh",
        country_code="sa",
        business_type="ecommerce",
        summary="Sells oud oils in Riyadh.",
        competitor_domains=["www.Arabianoud.com", "ajmal.com"],
    )
    monkeypatch.setattr(
        llm, "parse", lambda **kw: llm.LlmResult(profile, "claude-haiku-4-5", Decimal("0.0021"))
    )
    body = account.client.post("/onboarding/analyze", json={"url": "oudhouse.com"}).json()
    assert body["source"] == "live+ai" and body["notice"] is None
    assert body["industry"] == "luxury oud perfume store" and body["country"] == "SA"
    assert body["competitors"] == ["arabianoud.com", "ajmal.com"]
    assert body["summary"].startswith("Sells oud")

    from sqlalchemy import select

    from app_core.db import system_session
    from app_core.models import UsageCounter

    with system_session() as db:
        row = db.scalar(select(UsageCounter).where(UsageCounter.org_id == account.org_id))
        assert row.category == "llm" and row.cost_usd == Decimal("0.0021")


def test_analyze_unreachable_site_still_returns_something(account, monkeypatch):
    from app_api.services import onboarding

    def boom(url):
        raise ConnectionError("timeout")

    monkeypatch.setattr(onboarding, "fetch_homepage", boom)
    body = account.client.post(
        "/onboarding/analyze", json={"url": "https://myshop.myshopify.com"}
    ).json()
    assert body["source"] == "unreachable" and body["platform"] == "shopify"


def test_suggestions_templates_without_ai_only_in_enabled_languages(account):
    args = {"brand_name": "Smile", "industry": "dentist", "city": "Riyadh"}
    en = account.client.post("/onboarding/suggestions", json={**args, "languages": ["en"]}).json()
    assert en["source"] == "template"
    assert {k["language"] for k in en["keywords"]} == {"en"}
    assert {p["language"] for p in en["prompts"]} == {"en"}
    both = account.client.post(
        "/onboarding/suggestions", json={**args, "languages": ["en", "ar"]}
    ).json()
    assert {p["language"] for p in both["prompts"]} == {"en", "ar"}


def test_ai_suggestions_drop_languages_that_were_not_requested(account, monkeypatch):
    from decimal import Decimal

    from app_api.services import onboarding as ob
    from app_core import llm

    out = ob.SuggestionSet(
        keywords=[ob.KeywordSuggestion(keyword="oud riyadh", language="en"),
                  ob.KeywordSuggestion(keyword="عود", language="ar"),
                  ob.KeywordSuggestion(keyword="Oud Riyadh", language="en")],
        prompts=[ob.PromptSuggestion(prompt_text="Where to buy oud?", language="en",
                                     intent="local")],
    )  # fmt: skip
    monkeypatch.setattr(
        llm, "parse", lambda **kw: llm.LlmResult(out, "claude-haiku-4-5", Decimal("0.01"))
    )
    body = account.client.post(
        "/onboarding/suggestions",
        json={"brand_name": "Oud", "industry": "perfume", "languages": ["en"],
              "site_summary": "Sells oud."},
    ).json()  # fmt: skip
    assert body["source"] == "ai"
    assert [k["keyword"] for k in body["keywords"]] == ["oud riyadh"]  # ar dropped, dup removed
    assert body["prompts"][0]["intent"] == "local"


def test_complete_creates_site_keywords_prompts_atomically(account):
    set_plan(account.org_id, "starter", addons={"arabic": True})
    payload = {
        "site": {
            "homepage_url": "smile.sa",
            "name": "Smile",
            "primary_language": "en",
            "additional_languages": ["ar"],
            "default_country": "SA",
            "default_city": "Riyadh",
            "industry": "dentist",
            "platform": "wordpress",
            "platform_confirmed": True,
            "brand_names": {"en": ["Smile"], "ar": ["سمايل"]},
        },
        "keywords": [
            {"keyword": "dentist riyadh", "language": "en"},
            {"keyword": "طبيب أسنان الرياض", "language": "ar"},
        ],
        "prompts": [
            {"prompt_text": "Best dentist in Riyadh?", "language": "en", "intent": "local"}
        ],
    }
    r = account.client.post("/onboarding/complete", json=payload)
    assert r.status_code == 201, r.text
    assert account.client.get("/org").json()["usage"] == {"sites": 1, "keywords": 2, "prompts": 1}

    # A failing part (too many prompts for the plan) rolls back the whole thing.
    payload["site"]["homepage_url"] = "other.sa"
    set_plan(account.org_id, "growth")
    payload["prompts"] = [
        {"prompt_text": f"prompt number {i}", "language": "en"} for i in range(150)
    ]
    assert account.client.post("/onboarding/complete", json=payload).status_code == 402
    assert account.client.get("/org").json()["usage"]["sites"] == 1
