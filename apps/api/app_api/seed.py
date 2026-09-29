"""Demo data (SEED_DEMO=true): `python -m app_api.seed`. Idempotent.

Creates a demo org on the Business plan with three sites so the UI can be demoed
without API keys: a no-code WordPress site (English), a coded Next.js site (English),
and a Salla store with Arabic enabled. Also a platform admin account.
All domains use the reserved `.example` TLD.
"""

import secrets

from sqlalchemy import select

from app_api.security import hash_password, now
from app_api.services.sites import new_site_key
from app_core.db import system_session
from app_core.logging import configure_logging, get_logger
from app_core.models import AiPrompt, Keyword, Membership, Organization, Plan, Site, User
from app_core.settings import get_settings

log = get_logger(__name__)

DEMO_EMAIL = "demo@example.com"
VIEWER_EMAIL = "viewer@example.com"
ADMIN_EMAIL = "admin@example.com"

SITES = [
    {
        "name": "Bright Smile Dental",
        "domain": "brightsmile-dental.example",
        "platform": "wordpress",
        "rendering": "server",
        "languages": ("en", []),
        "country": "US",
        "city": "Austin",
        "industry": "Dental clinic",
        "brand_names": {"en": ["Bright Smile Dental", "Bright Smile"]},
        "competitors": ["austinfamilydentist.example", "lonestarsmiles.example"],
        "keywords": [
            ("dentist austin", "en"),
            ("emergency dentist austin", "en"),
            ("teeth whitening austin", "en"),
            ("invisalign austin", "en"),
            ("bright smile dental reviews", "en"),
            ("pediatric dentist near me", "en"),
        ],
        "prompts": [
            ("What is the best dentist in Austin?", "en", "local"),
            ("Which Austin dentist is good for kids?", "en", "local"),
            ("How much does teeth whitening cost in Austin?", "en", "informational"),
            ("Is Bright Smile Dental a good choice?", "en", "navigational"),
            ("Compare emergency dentists in Austin.", "en", "comparison"),
        ],
    },
    {
        "name": "Tasklane",
        "domain": "tasklane.example",
        "platform": "nextjs",
        "rendering": "hybrid",
        "languages": ("en", []),
        "country": "US",
        "city": None,
        "industry": "Project management software",
        "brand_names": {"en": ["Tasklane"]},
        "competitors": ["trelloish.example", "asanalike.example", "mondayish.example"],
        "keywords": [
            ("project management software for small teams", "en"),
            ("kanban app", "en"),
            ("tasklane pricing", "en"),
            ("asana alternative", "en"),
            ("best task tracker for startups", "en"),
        ],
        "prompts": [
            (
                "What is the best project management tool for a 10-person startup?",
                "en",
                "commercial",
            ),
            ("What are good alternatives to Asana?", "en", "comparison"),
            ("Which kanban app has the best free plan?", "en", "commercial"),
            ("Is Tasklane good for agencies?", "en", "navigational"),
        ],
    },
    {
        "name": "Riyadh Oud House",
        "domain": "oud-house.example",
        "platform": "salla",
        "rendering": "server",
        "languages": ("en", ["ar"]),
        "country": "SA",
        "city": "Riyadh",
        "industry": "Perfume and oud store",
        "brand_names": {
            "en": ["Riyadh Oud House", "Oud House"],
            "ar": ["بيت العود الرياض", "بيت العود"],
        },
        "competitors": ["arabianoud.example", "abdulsamadqurashi.example"],
        "keywords": [
            ("oud perfume riyadh", "en"),
            ("best oud online saudi", "en"),
            ("عطور عود الرياض", "ar"),
            ("أفضل دهن عود", "ar"),
            ("متجر عطور أونلاين", "ar"),
        ],
        "prompts": [
            ("Where can I buy authentic oud in Riyadh?", "en", "local"),
            ("What are the best Saudi oud perfume brands?", "en", "commercial"),
            ("ما هو أفضل متجر لشراء دهن العود في الرياض؟", "ar", "local"),
            ("ما هي أفضل ماركات العود السعودية؟", "ar", "commercial"),
            ("هل بيت العود متجر موثوق؟", "ar", "navigational"),
        ],
    },
]


def _user(db, email: str, name: str, password: str, *, admin: bool = False) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name=name,
            password_hash=hash_password(password),
            email_verified_at=now(),
            is_platform_admin=admin,
        )
        db.add(user)
        db.flush()
    return user


def seed() -> bool:
    s = get_settings()
    with system_session() as db:
        if db.scalar(select(User.id).where(User.email == DEMO_EMAIL)):
            log.info("seed.skip", reason="demo data already present")
            return False
        business = db.scalar(select(Plan).where(Plan.code == "business"))
        owner = _user(db, DEMO_EMAIL, "Demo Owner", s.demo_user_password)
        viewer = _user(db, VIEWER_EMAIL, "Demo Viewer", s.demo_user_password)
        _user(db, ADMIN_EMAIL, "Platform Admin", s.demo_user_password, admin=True)

        org = Organization(
            name="Demo Company",
            slug="demo-company",
            plan_id=business.id,
            plan_assigned_at=now(),
            addons={"arabic": True},
        )
        db.add(org)
        db.flush()
        db.add_all(
            [
                Membership(org_id=org.id, user_id=owner.id, role="owner"),
                Membership(org_id=org.id, user_id=viewer.id, role="viewer"),
            ]
        )

        for spec in SITES:
            primary, extra = spec["languages"]
            site = Site(
                org_id=org.id,
                domain=spec["domain"],
                homepage_url=f"https://{spec['domain']}/",
                name=spec["name"],
                platform=spec["platform"],
                platform_confirmed=True,
                rendering=spec["rendering"],
                primary_language=primary,
                additional_languages=extra,
                default_country=spec["country"],
                default_city=spec["city"],
                industry=spec["industry"],
                brand_names=spec["brand_names"],
                competitor_domains=spec["competitors"],
                site_key=new_site_key(),
                verification_token=secrets.token_hex(16),
                created_by=owner.id,
            )
            db.add(site)
            db.flush()
            db.add_all(
                Keyword(
                    org_id=org.id,
                    site_id=site.id,
                    keyword=k,
                    language=lang,
                    country=spec["country"],
                    city=spec["city"],
                    device="mobile" if i % 3 == 2 else "desktop",
                )
                for i, (k, lang) in enumerate(spec["keywords"])
            )
            db.add_all(
                AiPrompt(
                    org_id=org.id,
                    site_id=site.id,
                    prompt_text=p,
                    language=lang,
                    country=spec["country"],
                    intent=intent,
                )
                for p, lang, intent in spec["prompts"]
            )
    log.info("seed.done", owner=DEMO_EMAIL, admin=ADMIN_EMAIL)
    return True


def main() -> None:
    s = get_settings()
    configure_logging(s.log_level, s.log_json)
    if not s.seed_demo:
        log.info("seed.skip", reason="SEED_DEMO is not true")
        return
    if s.is_production:
        log.warning("seed.skip", reason="refusing to seed demo data in production")
        return
    seed()


if __name__ == "__main__":
    main()
