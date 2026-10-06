"""Jira Cloud as an issue source (read-only, REST v3)."""

from collections.abc import Mapping
from urllib.parse import quote

from devteam_tools.adf import adf_to_text
from devteam_tools.env import require_env
from devteam_tools.http import BasicAuth, request_json
from devteam_tools.model import Comment, Issue

ENV = ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")


def preflight(env: Mapping[str, str]) -> None:
    """Check the Jira variables are set.

    Raises:
        AdapterError: Any is missing.
    """
    require_env(ENV, env, "check Jira settings")


def fetch_issue(key: str, env: Mapping[str, str]) -> Issue:
    """Fetch a Jira issue with its comments.

    Raises:
        AdapterError: Missing settings, or the request fails.
    """
    operation = f"fetch Jira issue {key}"
    base, email, token = require_env(ENV, env, operation)
    base = base.rstrip("/")
    url = f"{base}/rest/api/3/issue/{quote(key)}?fields=summary,description,comment"
    auth = BasicAuth(email, token, ("JIRA_EMAIL", "JIRA_API_TOKEN"))
    data = request_json("GET", url, auth=auth, operation=operation)
    fields = data.get("fields") or {}
    thread = fields.get("comment") or {}
    comments = tuple(
        Comment(
            author=(item.get("author") or {}).get("displayName", "unknown"),
            body=adf_to_text(item.get("body")),
            created=str(item.get("created", "")),
        )
        for item in thread.get("comments") or []
    )
    body = adf_to_text(fields.get("description"))
    total = int(thread.get("total", len(comments)))
    if total > len(comments):
        body += (
            f"\n\n({total} comments exist; {len(comments)} were fetched. Read the rest in Jira.)"
        )
    return Issue(
        id=str(data.get("key", key)),
        title=str(fields.get("summary", "")),
        body=body.strip(),
        url=f"{base}/browse/{key}",
        comments=comments,
    )
