"""Site crawling, platform detection, and AI crawler audit tasks (crawl queue)."""

import uuid
from datetime import UTC, datetime

import structlog

from app_core.db import system_session
from app_core.models import CrawlSnapshot, Site
from app_worker.celery_app import app
from app_worker.seo_engine import (
    check_ai_robots,
    detect_platform,
    fetch_page,
    render_page,
)

logger = structlog.get_logger(__name__)


@app.task(name="app_worker.tasks.crawl.crawl_site")
def crawl_site(site_id_str: str) -> dict:
    """Crawl site homepage, diff raw vs rendered DOM, detect platform, check robots.txt."""
    site_id = uuid.UUID(site_id_str)
    with system_session() as db:
        site = db.get(Site, site_id)
        if not site:
            logger.error("site_not_found_for_crawl", site_id=site_id_str)
            return {"error": "Site not found"}

        logger.info("starting_site_crawl", site_id=site_id_str, url=site.homepage_url)
        try:
            fetch_res = fetch_page(site.homepage_url)
            render_res = render_page(fetch_res)
            platform_facts = detect_platform(fetch_res, render_res)
            robots_status = check_ai_robots(site.homepage_url)

            # Update site platform/rendering if not manually confirmed
            if not site.platform_confirmed:
                site.platform = platform_facts.platform.value
            site.rendering = platform_facts.rendering.value

            snapshot = CrawlSnapshot(
                org_id=site.org_id,
                site_id=site.id,
                url=site.homepage_url,
                http_status=fetch_res.status_code,
                raw_html_hash=fetch_res.raw_html_hash,
                rendered_html_hash=render_res.rendered_html_hash,
                js_only_content_detected=render_res.js_only_content_detected,
                js_only_text=render_res.js_only_text,
                raw_text=fetch_res.raw_text[:50000] if fetch_res.raw_text else None,
                rendered_text=render_res.rendered_text[:50000]
                if render_res.rendered_text
                else None,
                meta_title=fetch_res.meta_title,
                meta_description=fetch_res.meta_description,
                ai_robots_allowed=robots_status,
                fetched_at=datetime.now(UTC),
            )
            db.add(snapshot)
            db.commit()

            return {
                "site_id": site_id_str,
                "platform": site.platform,
                "rendering": site.rendering,
                "js_only_content_detected": render_res.js_only_content_detected,
                "ai_robots_allowed": robots_status,
            }
        except Exception as e:
            logger.exception("crawl_site_failed", site_id=site_id_str, error=str(e))
            db.rollback()
            return {"error": str(e)}
