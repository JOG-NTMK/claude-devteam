"""GitHub through the gh CLI."""

import re
from pathlib import Path

from devteam_tools.commands import run, run_json
from devteam_tools.errors import AdapterError
from devteam_tools.model import Comment, Issue, PullRequest

LOGIN_HINT = "Run `gh auth login` for this host."
PR_URL = re.compile(r"https://\S+/pull/(\d+)")


def preflight() -> None:
    """Check gh is installed and logged in.

    Raises:
        AdapterError: It isn't.
    """
    run(["gh", "auth", "status"], operation="check GitHub login", hint=LOGIN_HINT)


def fetch_issue(number: str) -> Issue:
    """Fetch an issue and its comments.

    Raises:
        AdapterError: gh fails or returns unexpected output.
    """
    data = run_json(
        ["gh", "issue", "view", number, "--json", "number,title,body,url,comments"],
        operation=f"fetch GitHub issue #{number}",
        hint=f"Check issue #{number} exists in this repository. {LOGIN_HINT}",
    )
    comments = tuple(
        Comment(
            author=(item.get("author") or {}).get("login", "unknown"),
            body=str(item.get("body", "")),
            created=str(item.get("createdAt", "")),
        )
        for item in data.get("comments") or []
    )
    return Issue(
        id=str(data["number"]),
        title=str(data.get("title", "")),
        body=str(data.get("body") or ""),
        url=str(data.get("url", "")),
        comments=comments,
    )


def open_pr(branch: str, base: str, title: str, body_file: Path) -> PullRequest:
    """Open a pull request for an already-pushed branch.

    Raises:
        AdapterError: gh fails, or its output holds no pull request URL.
    """
    operation = f"open a GitHub pull request from {branch}"
    output = run(
        [
            "gh",
            "pr",
            "create",
            "--head",
            branch,
            "--base",
            base,
            "--title",
            title,
            "--body-file",
            str(body_file),
        ],
        operation=operation,
        hint=f"Check {branch} is pushed and has no open pull request. {LOGIN_HINT}",
    )
    match = PR_URL.search(output)
    if match is None:
        raise AdapterError(
            operation,
            f"gh printed no pull request URL: {output.strip()[:300]}",
            "Look for the pull request on GitHub; record its URL in state.json before retrying.",
        )
    return PullRequest(url=match[0], number=match[1])


def comment(number: str, body: str) -> None:
    """Post a comment on a pull request.

    Raises:
        AdapterError: gh fails.
    """
    run(
        ["gh", "pr", "comment", number, "--body", body],
        operation=f"comment on GitHub pull request #{number}",
        hint=LOGIN_HINT,
    )
