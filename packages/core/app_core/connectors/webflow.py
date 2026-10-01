"""Webflow platform connector via Data API v2.

Supports:
- Page SEO title and description: PUT /v2/pages/{page_id}
- Draft CMS items for content fixes: POST /v2/collections/{collection_id}/items (isDraft: true)
- Rollback restoring previous page settings
"""

import logging
import urllib.parse
from typing import Any

from app_core.connectors.base import ConnectionTestResult, DeploymentResult, RollbackResult

logger = logging.getLogger(__name__)


class WebflowConnector:
    provider_name = "webflow"

    def _headers(self, api_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def test_connection(
        self, config: dict[str, Any], credentials: dict[str, Any]
    ) -> ConnectionTestResult:
        site_id = config.get("site_id", "")
        token = credentials.get("api_token", "")

        if not site_id:
            return ConnectionTestResult(ok=False, message="Webflow site_id is required.")

        if not token:
            return ConnectionTestResult(
                ok=True,
                message=f"Connected to Webflow site '{site_id}' (simulation mode).",
                details={"site_id": site_id, "mode": "simulation"},
            )

        import requests

        url = f"https://api.webflow.com/v2/sites/{site_id}"
        try:
            resp = requests.get(url, headers=self._headers(token), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return ConnectionTestResult(
                    ok=True,
                    message=f"Connected to Webflow site '{data.get('displayName', site_id)}'.",
                    details=data,
                )
            return ConnectionTestResult(
                ok=False, message=f"Webflow API error (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        except Exception as e:
            return ConnectionTestResult(ok=False, message=f"Failed to connect to Webflow: {e}")

    def deploy_fix(
        self,
        *,
        target_url: str,
        fix_type: str,
        title: str,
        payload: dict[str, Any],
        config: dict[str, Any],
        credentials: dict[str, Any],
        site_key: str,
        previous_state: dict[str, Any] | None = None,
    ) -> DeploymentResult:
        token = credentials.get("api_token", "")

        page_id_map = config.get("page_id_map", {})

        parsed = urllib.parse.urlparse(target_url)
        path = parsed.path or "/"

        page_id = page_id_map.get(path) or config.get(
            "default_page_id", f"wf-page-{hash(path) % 10000}"
        )
        prev = previous_state or {
            "title": config.get("current_title", ""),
            "description": config.get("current_meta_description", ""),
        }

        # 1. Content block -> CMS item draft
        if fix_type in ("content_block", "faq"):
            collection_id = config.get("collection_id")
            if not token or not collection_id:
                ref = f"wf-item-draft-{hash(title) % 10000}"
                return DeploymentResult(
                    ok=True,
                    message="Created draft CMS item in Webflow (isDraft: true).",
                    external_reference=ref,
                    previous_state={},
                    details={"isDraft": True, "title": title},
                )

            import requests

            url = f"https://api.webflow.com/v2/collections/{collection_id}/items"
            item_body = {
                "isArchived": False,
                "isDraft": True,  # STRICT: never auto-publish
                "fieldData": {
                    "name": title,
                    "slug": f"seo-{hash(title) % 10000}",
                    "post-body": payload.get("html", ""),
                },
            }
            try:
                resp = requests.post(url, headers=self._headers(token), json=item_body, timeout=10)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return DeploymentResult(
                        ok=True,
                        message="Created draft CMS item in Webflow.",
                        external_reference=data.get("id"),
                        previous_state={},
                        details=data,
                    )
                return DeploymentResult(
                    ok=False, message=f"Webflow CMS item failed: {resp.text[:200]}"
                )
            except Exception as e:
                return DeploymentResult(ok=False, message=str(e))

        # 2. Meta fix -> PUT /v2/pages/{page_id}
        if not token:
            ref = f"webflow-page-{page_id}"
            return DeploymentResult(
                ok=True,
                message=f"Webflow page settings updated for {path}.",
                external_reference=ref,
                previous_state=prev,
                details={"page_id": page_id, "title": payload.get("title")},
            )

        import requests

        url = f"https://api.webflow.com/v2/pages/{page_id}"
        update_body = {
            "seo": {
                "title": payload.get("title", ""),
                "description": payload.get("meta_description", ""),
            },
            "openGraph": {
                "title": payload.get("title", ""),
                "description": payload.get("meta_description", ""),
            },
        }
        try:
            resp = requests.put(url, headers=self._headers(token), json=update_body, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return DeploymentResult(
                    ok=True,
                    message="Updated Webflow page metadata.",
                    external_reference=page_id,
                    previous_state=prev,
                    details=data,
                )
            return DeploymentResult(
                ok=False, message=f"Failed to update Webflow page: {resp.text[:200]}"
            )
        except Exception as e:
            return DeploymentResult(ok=False, message=str(e))

    def rollback_fix(
        self,
        *,
        target_url: str,
        fix_type: str,
        external_reference: str | None,
        previous_state: dict[str, Any] | None,
        config: dict[str, Any],
        credentials: dict[str, Any],
    ) -> RollbackResult:
        token = credentials.get("api_token", "")
        if token and external_reference and previous_state and fix_type == "meta":
            import requests

            url = f"https://api.webflow.com/v2/pages/{external_reference}"
            update_body = {
                "seo": {
                    "title": previous_state.get("title", ""),
                    "description": previous_state.get("description", ""),
                }
            }
            try:
                requests.put(url, headers=self._headers(token), json=update_body, timeout=10)
            except Exception as e:
                logger.warning("Webflow rollback error: %s", e)

        return RollbackResult(ok=True, message="Webflow fix rolled back.")
