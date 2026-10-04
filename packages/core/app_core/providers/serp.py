"""SERP ranking provider interface and implementations (DataForSEO + Mock)."""

import hashlib
import urllib.parse
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Any, Protocol

from app_core.logging import get_logger
from app_core.providers.ai_answer import ProviderNotConfigured
from app_core.settings import get_settings

log = get_logger(__name__)

# ISO 3166-1 numeric codes. Google Ads / DataForSEO country location codes are 2000 + this.
_ISO_NUMERIC = {
    "SA": 682,
    "AE": 784,
    "KW": 414,
    "QA": 634,
    "BH": 48,
    "OM": 512,
    "EG": 818,
    "JO": 400,
    "US": 840,
    "GB": 826,
    "CA": 124,
    "AU": 36,
    "IN": 356,
    "PK": 586,
    "TR": 792,
    "DE": 276,
    "FR": 250,
    "ES": 724,
    "IT": 380,
    "NL": 528,
    "IE": 372,
    "NZ": 554,
    "SG": 702,
    "MY": 458,
}


class UnsupportedCountry(ValueError):
    pass


def country_location_code(country: str) -> int:
    try:
        return 2000 + _ISO_NUMERIC[country.upper()]
    except KeyError:
        raise UnsupportedCountry(
            f"No DataForSEO location mapping for country '{country}'"
        ) from None


@dataclass
class SerpResult:
    position: int | None
    url_ranked: str | None
    serp_features: list[str]
    ai_overview_present: bool
    ai_overview_cites_site: bool
    cost_usd: Decimal
    raw_response: dict[str, Any] = field(default_factory=dict)


class SerpProvider(Protocol):
    def check_ranking(
        self,
        *,
        keyword: str,
        domain: str,
        country: str,
        language: str,
        device: str = "desktop",
        city: str | None = None,
    ) -> SerpResult: ...


@lru_cache(maxsize=64)
def _city_codes(login: str, password: str, country: str) -> dict[str, int]:
    """{city name (casefolded): location_code} for a country, from DataForSEO's free
    locations endpoint. Cached per worker process; on failure the country code is used."""
    import requests
    from requests.auth import HTTPBasicAuth

    try:
        resp = requests.get(
            f"https://api.dataforseo.com/v3/serp/google/locations/{country.lower()}",
            auth=HTTPBasicAuth(login, password),
            timeout=30,
        )
        resp.raise_for_status()
        results = (resp.json().get("tasks") or [{}])[0].get("result") or []
    except Exception as exc:  # network/API error: fall back to country-level tracking
        log.warning("serp.locations_failed", country=country, error=str(exc)[:200])
        _city_codes.cache_clear()
        return {}
    codes: dict[str, int] = {}
    for loc in results:
        if loc.get("location_type") == "City" and loc.get("location_name"):
            name = loc["location_name"].split(",")[0].strip().casefold()
            codes.setdefault(name, loc["location_code"])  # first (most prominent) wins
    return codes


class DataForSeoSerpProvider:
    """Live Google SERP check via DataForSEO REST API."""

    def __init__(self, login: str | None = None, password: str | None = None) -> None:
        s = get_settings()
        self.login = login or s.dataforseo_login
        self.password = password or s.dataforseo_password
        self.base_url = "https://api.dataforseo.com/v3"

    def location_code(self, country: str, city: str | None) -> int:
        """City-level location when DataForSEO knows the city, else the country."""
        if city:
            code = _city_codes(self.login, self.password, country.upper()).get(city.casefold())
            if code:
                return code
        return country_location_code(country)

    def check_ranking(
        self,
        *,
        keyword: str,
        domain: str,
        country: str,
        language: str,
        device: str = "desktop",
        city: str | None = None,
    ) -> SerpResult:
        if not self.login or not self.password:
            raise ProviderNotConfigured("DataForSEO: set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD")

        import requests
        from requests.auth import HTTPBasicAuth

        payload = [
            {
                "keyword": keyword,
                "location_code": self.location_code(country, city),
                "language_code": language,
                "device": device,
                "depth": 100,
            }
        ]

        endpoint = f"{self.base_url}/serp/google/organic/live/advanced"
        resp = requests.post(
            endpoint,
            auth=HTTPBasicAuth(self.login, self.password),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # Parse tasks
        tasks = data.get("tasks", [])
        if not tasks or not tasks[0].get("result"):
            return SerpResult(
                position=None,
                url_ranked=None,
                serp_features=[],
                ai_overview_present=False,
                ai_overview_cites_site=False,
                cost_usd=Decimal("0.0020"),
                raw_response=data,
            )

        result_item = tasks[0]["result"][0]
        items = result_item.get("items", [])
        cost = Decimal(str(tasks[0].get("cost", 0.0020)))

        position: int | None = None
        url_ranked: str | None = None
        serp_features: set[str] = set()
        ai_overview_present = False
        ai_overview_cites = False

        normalized_domain = domain.lower().replace("www.", "")

        for item in items:
            item_type = item.get("type")
            if item_type:
                serp_features.add(item_type)

            if item_type == "ai_overview":
                ai_overview_present = True
                for ref in item.get("references", []):
                    ref_url = ref.get("url", "").lower()
                    if normalized_domain in ref_url:
                        ai_overview_cites = True

            if item_type == "organic":
                item_url = item.get("url", "").lower()
                parsed = urllib.parse.urlparse(item_url)
                item_domain = parsed.hostname or ""
                if normalized_domain in item_domain and position is None:
                    position = item.get("rank_group") or item.get("rank_absolute")
                    url_ranked = item.get("url")

        return SerpResult(
            position=position,
            url_ranked=url_ranked,
            serp_features=sorted(serp_features),
            ai_overview_present=ai_overview_present,
            ai_overview_cites_site=ai_overview_cites,
            cost_usd=cost,
            raw_response={"item_count": len(items)},
        )


class MockSerpProvider:
    """Deterministic mock for testing and offline development."""

    def check_ranking(
        self,
        *,
        keyword: str,
        domain: str,
        country: str,
        language: str,
        device: str = "desktop",
        city: str | None = None,
    ) -> SerpResult:
        normalized_domain = domain.lower().replace("www.", "")
        kw_lower = keyword.lower()

        # Seed hash from inputs
        seed = int(hashlib.sha256(f"{domain}:{keyword}:{country}".encode()).hexdigest(), 16)

        # Brand keywords rank higher
        is_brand = any(part in kw_lower for part in normalized_domain.split(".") if len(part) > 3)

        if is_brand:
            position = (seed % 3) + 1  # 1 to 3
        elif (seed % 10) < 7:  # 70% chance of ranking somewhere in top 40
            position = (seed % 35) + 4  # 4 to 38
        else:
            position = None

        url_ranked = f"https://{domain}/" if position else None
        has_ai_overview = (seed % 3) == 0
        cites_site = has_ai_overview and (position is not None and position <= 10)

        features = ["organic"]
        if (seed % 2) == 0:
            features.append("people_also_ask")
        if (seed % 4) == 0:
            features.append("featured_snippet")
        if has_ai_overview:
            features.append("ai_overview")

        return SerpResult(
            position=position,
            url_ranked=url_ranked,
            serp_features=features,
            ai_overview_present=has_ai_overview,
            ai_overview_cites_site=cites_site,
            cost_usd=Decimal("0.0000"),
            raw_response={"mock": True},
        )


def get_serp_provider() -> "DataForSeoSerpProvider | MockSerpProvider":
    """Real DataForSEO provider, or the mock where allowed (local/test only)."""
    s = get_settings()
    if s.dataforseo_login and s.dataforseo_password:
        return DataForSeoSerpProvider()
    if s.mock_providers_allowed:
        return MockSerpProvider()
    raise ProviderNotConfigured("DataForSEO: set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD")
