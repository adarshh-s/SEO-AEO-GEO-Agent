from conftest import set_plan


def test_analyze_is_mock_and_never_preselects_arabic(account):
    r = account.client.post("/onboarding/analyze", json={"url": "https://myshop.myshopify.com"})
    body = r.json()
    assert body["source"] == "mock" and body["platform"] == "shopify"
    assert body["domain"] == "myshop.myshopify.com"
    sa = account.client.post("/onboarding/analyze", json={"url": "clinic.com.sa"}).json()
    assert sa["detected_languages"] == ["en", "ar"]  # detected on the site, not tracking languages


def test_suggestions_only_in_enabled_languages(account):
    args = {"brand_name": "Smile", "industry": "dentist", "city": "Riyadh"}
    en = account.client.post("/onboarding/suggestions", json={**args, "languages": ["en"]}).json()
    assert {k["language"] for k in en["keywords"]} == {"en"}
    assert {p["language"] for p in en["prompts"]} == {"en"}
    both = account.client.post(
        "/onboarding/suggestions", json={**args, "languages": ["en", "ar"]}
    ).json()
    assert {p["language"] for p in both["prompts"]} == {"en", "ar"}
    assert any("Riyadh" in k["keyword"] for k in en["keywords"])


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
