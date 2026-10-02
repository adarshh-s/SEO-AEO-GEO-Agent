from app_core.brand import BRAND
from conftest import SITE, set_plan


def test_create_site_normalizes_url_and_generates_keys(account):
    r = account.client.post("/sites", json=SITE)
    assert r.status_code == 201, r.text
    site = r.json()
    assert site["domain"] == "example.com"
    assert site["homepage_url"] == "https://www.example.com/"
    assert site["primary_language"] == "en" and site["additional_languages"] == []
    assert site["site_key"].startswith(f"{BRAND['site_key_prefix']}_")
    assert site["platform"] == "unknown" and site["verified_at"] is None


def test_invalid_and_private_urls_rejected(account):
    for bad in [
        "localhost:8000",
        "http://127.0.0.1",
        "ftp://example.com",
        "https://intranet",
        "http://10.0.0.5/admin",
        "https://user:pw@example.com",
    ]:
        r = account.client.post("/sites", json={**SITE, "homepage_url": bad})
        assert r.status_code == 422, bad


def test_duplicate_site_and_trial_site_limit(account):
    set_plan(account.org_id, "growth")
    assert account.client.post("/sites", json=SITE).status_code == 201
    assert account.client.post("/sites", json=SITE).json()["detail"]["code"] == "site_exists"
    set_plan(account.org_id, "trial")
    r = account.client.post("/sites", json={**SITE, "homepage_url": "other.com"})
    assert r.status_code == 402 and r.json()["detail"]["code"] == "plan_limit_reached"


def test_arabic_is_opt_in_and_needs_addon_on_small_plans(account):
    body = {**SITE, "additional_languages": ["ar"]}
    r = account.client.post("/sites", json=body)
    assert r.status_code == 402  # trial: 1 language unless the Arabic add-on is granted
    set_plan(account.org_id, "starter", addons={"arabic": True})
    r = account.client.post("/sites", json=body)
    assert r.status_code == 201 and r.json()["additional_languages"] == ["ar"]


def test_update_site_languages_and_brand_names(account):
    set_plan(account.org_id, "growth")
    site = account.client.post("/sites", json=SITE).json()
    r = account.client.patch(
        f"/sites/{site['id']}",
        json={
            "additional_languages": ["ar"],
            "brand_names": {"en": ["Example", " "], "ar": ["إكزامبل"]},
            "competitor_domains": ["https://rival.com", "example.com", "rival.com", "not a domain"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["additional_languages"] == ["ar"]
    assert body["brand_names"] == {"en": ["Example"], "ar": ["إكزامبل"]}
    assert body["competitor_domains"] == ["rival.com"]
    assert (
        account.client.patch(f"/sites/{site['id']}", json={"primary_language": "xx"}).status_code
        == 422
    )


def test_keywords_bulk_dedupe_language_and_limits(account):
    site = account.client.post("/sites", json=SITE).json()
    url = f"/sites/{site['id']}/keywords"
    r = account.client.post(
        url,
        json={
            "items": [
                {"keyword": "dentist  riyadh", "language": "en"},
                {"keyword": "Dentist Riyadh", "language": "en"},
                {"keyword": "dentist riyadh", "language": "en", "device": "mobile"},
            ]
        },
    )
    assert r.json() == {"created": 2, "skipped_duplicates": 1}
    kws = account.client.get(url).json()
    assert {k["country"] for k in kws} == {"SA"}  # defaults to the site's country
    r = account.client.post(url, json={"items": [{"keyword": "طبيب أسنان", "language": "ar"}]})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "language_not_enabled"
    r = account.client.post(
        url, json={"items": [{"keyword": f"k{i}", "language": "en"} for i in range(30)]}
    )
    assert r.status_code == 402  # trial allows 25 keywords


def test_keyword_status_and_delete(account):
    site = account.client.post("/sites", json=SITE).json()
    url = f"/sites/{site['id']}/keywords"
    account.client.post(url, json={"items": [{"keyword": "a", "language": "en"}]})
    kw = account.client.get(url).json()[0]
    assert (
        account.client.patch(f"{url}/{kw['id']}", json={"status": "paused"}).json()["status"]
        == "paused"
    )
    assert account.client.delete(f"{url}/{kw['id']}").status_code == 200
    assert account.client.get(url).json() == []


def test_prompts(account):
    site = account.client.post("/sites", json=SITE).json()
    url = f"/sites/{site['id']}/prompts"
    r = account.client.post(
        url,
        json={
            "items": [
                {"prompt_text": "Best dentist in Riyadh?", "language": "en", "intent": "local"},
                {"prompt_text": "best dentist in riyadh?", "language": "en"},
            ]
        },
    )
    assert r.json() == {"created": 1, "skipped_duplicates": 1}
    assert account.client.get(url).json()[0]["intent"] == "local"


def test_deleting_site_cascades(account):
    site = account.client.post("/sites", json=SITE).json()
    account.client.post(
        f"/sites/{site['id']}/keywords", json={"items": [{"keyword": "a", "language": "en"}]}
    )
    assert account.client.delete(f"/sites/{site['id']}").status_code == 200
    assert account.client.get("/org").json()["usage"] == {"sites": 0, "keywords": 0, "prompts": 0}
