"""Check robots.txt access rules for AI crawlers."""

from urllib.parse import urljoin, urlparse

from app_worker.seo_engine.fetch import USER_AGENT
from app_worker.seo_engine.url_safety import safe_requests_get

AI_BOTS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "PerplexityBot",
    "Google-Extended",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
]


def check_ai_robots(base_url: str, *, timeout: int = 10) -> dict[str, bool]:
    """Fetch /robots.txt and determine if each known AI crawler is allowed."""
    parsed = urlparse(base_url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

    try:
        resp = safe_requests_get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code == 404 or resp.status_code >= 400:
            # 404 means no restrictions: all bots allowed
            return {bot: True for bot in AI_BOTS}
        text = resp.text
    except Exception:
        # If fetch fails, default to allowed
        return {bot: True for bot in AI_BOTS}

    return parse_ai_robots(text)


def parse_ai_robots(content: str) -> dict[str, bool]:
    """Parse robots.txt lines for AI bots following standard user-agent matching."""
    lines = content.splitlines()
    current_agents: list[str] = []
    in_rules = False
    # rules per agent: list of (path, allow_bool)
    agent_rules: dict[str, list[tuple[str, bool]]] = {}

    for line in lines:
        line = line.split("#")[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue

        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            if in_rules:
                current_agents = []
                in_rules = False
            agent = value.lower()
            current_agents.append(agent)
            if agent not in agent_rules:
                agent_rules[agent] = []
        elif field in ("disallow", "allow"):
            in_rules = True
            is_allow = field == "allow"
            for agent in current_agents:
                agent_rules[agent].append((value, is_allow))

    results: dict[str, bool] = {}
    wildcard_rules = agent_rules.get("*", [])

    for bot in AI_BOTS:
        bot_lower = bot.lower()
        rules = agent_rules.get(bot_lower, wildcard_rules)
        # Check root access '/'
        allowed = True
        for path, is_allow in rules:
            if path == "/" or path == "":
                if not is_allow and path == "/":
                    allowed = False
                elif is_allow:
                    allowed = True
        results[bot] = allowed

    return results
