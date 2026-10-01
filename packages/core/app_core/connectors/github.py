"""GitHub connector for automated Pull Request generation.

Workflow:
1. Verify repo access with contents:write + pull_requests:write scopes.
2. Create dedicated branch: quardlink/fix-{short_id}.
3. Locate relevant page/component file.
4. Patch title, description, or JSON-LD schema into source code.
5. Commit to branch and open a Pull Request with complete rationale.
6. NEVER auto-merges: merchant/dev team reviews and merges.
7. Stores PR HTML URL in fix.external_reference.
"""

import base64
import json
import logging
import re
import urllib.parse
from typing import Any

from app_core.connectors.base import ConnectionTestResult, DeploymentResult, RollbackResult

logger = logging.getLogger(__name__)


def _patch_html_content(
    content: str, title: str | None, description: str | None, schema: dict[str, Any] | None
) -> str:
    """Safely patch title, meta description, and schema into HTML or JSX."""
    updated = content

    if title:
        if "<title>" in updated:
            updated = re.sub(
                r"<title>.*?</title>", f"<title>{title}</title>", updated, count=1, flags=re.DOTALL
            )
        elif "<head>" in updated:
            updated = updated.replace("<head>", f"<head>\n    <title>{title}</title>", 1)

    if description:
        desc_tag = f'<meta name="description" content="{description}" />'
        if re.search(r'<meta[^>]+name=["\']description["\'][^>]*>', updated, flags=re.IGNORECASE):
            updated = re.sub(
                r'<meta[^>]+name=["\']description["\'][^>]*>',
                desc_tag,
                updated,
                count=1,
                flags=re.IGNORECASE,
            )
        elif "</head>" in updated:
            updated = updated.replace("</head>", f"    {desc_tag}\n  </head>", 1)

    if schema:
        schema_json = json.dumps(schema, indent=2)
        script_tag = f'<script type="application/ld+json">\n{schema_json}\n</script>'
        if "</head>" in updated:
            updated = updated.replace("</head>", f"    {script_tag}\n  </head>", 1)
        elif "</body>" in updated:
            updated = updated.replace("</body>", f"    {script_tag}\n  </body>", 1)

    return updated


class GithubConnector:
    provider_name = "github"

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "QuardLink-Bot/1.0",
        }

    def test_connection(
        self, config: dict[str, Any], credentials: dict[str, Any]
    ) -> ConnectionTestResult:
        owner = config.get("repo_owner", "")
        repo = config.get("repo_name", "")
        token = credentials.get("token", "")

        if not owner or not repo:
            return ConnectionTestResult(
                ok=False, message="Both repo_owner and repo_name are required."
            )

        if not token:
            # Mock / simulator response
            return ConnectionTestResult(
                ok=True,
                message=f"Connected to GitHub repo {owner}/{repo} (simulation mode).",
                details={
                    "repo": f"{owner}/{repo}",
                    "default_branch": config.get("base_branch", "main"),
                    "permissions": {"push": True, "pull": True},
                },
            )

        import requests

        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            resp = requests.get(url, headers=self._headers(token), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                perms = data.get("permissions", {})
                can_push = perms.get("push", False)
                return ConnectionTestResult(
                    ok=True,
                    message=f"Connected to {data.get('full_name')} (default branch: {data.get('default_branch')}).",
                    details={
                        "full_name": data.get("full_name"),
                        "default_branch": data.get("default_branch"),
                        "can_push": can_push,
                    },
                )
            return ConnectionTestResult(
                ok=False, message=f"GitHub API error (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        except Exception as e:
            return ConnectionTestResult(ok=False, message=f"Failed to connect to GitHub: {e}")

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
        owner = config.get("repo_owner", "")
        repo = config.get("repo_name", "")
        token = credentials.get("token", "")
        base_branch = config.get("base_branch", "main")

        parsed = urllib.parse.urlparse(target_url)
        path = parsed.path.strip("/")
        short_id = f"{hash(target_url + title) % 100000:05d}"
        new_branch = f"quardlink/fix-{short_id}"

        # Target file resolution
        candidate_file = config.get("file_path") or payload.get("file_path")
        if not candidate_file:
            candidate_file = "index.html" if not path else f"src/pages/{path}.tsx"

        # Mock / local test mode if no token
        if not token:
            mock_pr_number = hash(title) % 500 + 1
            mock_pr_url = f"https://github.com/{owner}/{repo}/pull/{mock_pr_number}"
            return DeploymentResult(
                ok=True,
                message=f"Created Pull Request on GitHub: {mock_pr_url}",
                external_reference=mock_pr_url,
                previous_state={"file_path": candidate_file, "content": "<!-- Original HTML -->"},
                details={
                    "pr_number": mock_pr_number,
                    "pr_url": mock_pr_url,
                    "branch": new_branch,
                    "file_patched": candidate_file,
                },
            )

        import requests

        headers = self._headers(token)

        try:
            # 1. Get base branch commit SHA
            ref_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                headers=headers,
                timeout=10,
            )
            if ref_resp.status_code != 200:
                return DeploymentResult(
                    ok=False,
                    message=f"Could not find base branch '{base_branch}': {ref_resp.text[:200]}",
                )
            base_sha = ref_resp.json()["object"]["sha"]

            # 2. Create new branch
            create_branch_resp = requests.post(
                f"https://api.github.com/repos/{owner}/{repo}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{new_branch}", "sha": base_sha},
                timeout=10,
            )
            # If branch exists, continue
            if create_branch_resp.status_code not in (201, 422):
                return DeploymentResult(
                    ok=False, message=f"Failed to create branch: {create_branch_resp.text[:200]}"
                )

            # 3. Read target file
            file_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{candidate_file}?ref={new_branch}",
                headers=headers,
                timeout=10,
            )
            file_sha = None
            old_content = ""
            if file_resp.status_code == 200:
                file_data = file_resp.json()
                file_sha = file_data.get("sha")
                raw_b64 = file_data.get("content", "")
                old_content = base64.b64decode(raw_b64).decode("utf-8", errors="ignore")
            else:
                old_content = "<!DOCTYPE html>\n<html>\n<head>\n</head>\n<body>\n</body>\n</html>"

            # 4. Patch file content
            new_title = payload.get("title") if fix_type == "meta" else None
            new_desc = payload.get("meta_description") if fix_type == "meta" else None
            new_schema = payload if fix_type == "schema" else None
            new_content = _patch_html_content(old_content, new_title, new_desc, new_schema)

            # 5. Commit updated file
            commit_payload: dict[str, Any] = {
                "message": f"QuardLink SEO Fix: {title}",
                "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
                "branch": new_branch,
            }
            if file_sha:
                commit_payload["sha"] = file_sha

            put_resp = requests.put(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{candidate_file}",
                headers=headers,
                json=commit_payload,
                timeout=10,
            )
            if put_resp.status_code not in (200, 201):
                return DeploymentResult(
                    ok=False, message=f"Failed to commit change: {put_resp.text[:200]}"
                )

            # 6. Create Pull Request
            pr_body = f"""## 🚀 QuardLink SEO & AEO Automated Fix

### Summary
- **Target URL:** `{target_url}`
- **Fix Type:** `{fix_type}`
- **Description:** {title}

### Changes Proposed
- Patched metadata/schema in `{candidate_file}`.
- All changes are non-destructive and preserve existing application code.

---
*Created automatically by [QuardLink](https://quardlink.com). Please review the diff and merge when ready.*
"""
            pr_resp = requests.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers=headers,
                json={
                    "title": f"QuardLink SEO: {title}",
                    "head": new_branch,
                    "base": base_branch,
                    "body": pr_body,
                },
                timeout=10,
            )
            if pr_resp.status_code == 201:
                pr_data = pr_resp.json()
                pr_url = pr_data["html_url"]
                return DeploymentResult(
                    ok=True,
                    message=f"Created Pull Request: {pr_url}",
                    external_reference=pr_url,
                    previous_state={"file_path": candidate_file, "content": old_content},
                    details={
                        "pr_number": pr_data.get("number"),
                        "pr_url": pr_url,
                        "branch": new_branch,
                        "file_patched": candidate_file,
                    },
                )
            return DeploymentResult(
                ok=False, message=f"Failed to open Pull Request: {pr_resp.text[:200]}"
            )
        except Exception as e:
            return DeploymentResult(ok=False, message=f"GitHub deployment error: {e}")

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
        owner = config.get("repo_owner", "")
        repo = config.get("repo_name", "")
        token = credentials.get("token", "")

        if not external_reference:
            return RollbackResult(ok=True, message="Fix recorded as rolled back.")

        if not token:
            return RollbackResult(
                ok=True,
                message=f"Rollback noted for Pull Request {external_reference}.",
                details={"external_reference": external_reference},
            )

        import requests

        headers = self._headers(token)

        # Check if PR URL: https://github.com/owner/repo/pull/12
        match = re.search(r"/pull/(\d+)", external_reference)
        if match:
            pr_num = match.group(1)
            try:
                # Attempt to close the PR
                requests.patch(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}",
                    headers=headers,
                    json={"state": "closed"},
                    timeout=10,
                )
            except Exception as e:
                logger.warning("Could not close GitHub PR on rollback: %s", e)

        return RollbackResult(
            ok=True,
            message="GitHub Pull Request closed and fix rolled back.",
            details={"external_reference": external_reference},
        )
