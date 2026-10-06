"""GitLab through the glab CLI."""

import re
import subprocess
from pathlib import Path

from devteam_tools.commands import run, run_json
from devteam_tools.errors import AdapterError
from devteam_tools.model import Comment, Issue, PullRequest

LOGIN_HINT = "Run `glab auth login --hostname <host>`."
MR_URL = re.compile(r"https://\S+/-/merge_requests/(\d+)")


def is_gitlab_host(host: str) -> bool:
    """Return True when glab is installed and logged in to ``host``."""
    try:
        completed = subprocess.run(
            ["glab", "auth", "status", "--hostname", host],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return completed.returncode == 0


def preflight(host: str) -> None:
    """Check glab is logged in to ``host``.

    Raises:
        AdapterError: It isn't.
    """
    run(
        ["glab", "auth", "status", "--hostname", host],
        operation=f"check GitLab login for {host}",
        hint=LOGIN_HINT.replace("<host>", host),
    )


def fetch_issue(number: str) -> Issue:
    """Fetch an issue and its human comments (system notes are dropped).

    Raises:
        AdapterError: glab fails or returns unexpected output.
    """
    data = run_json(
        ["glab", "issue", "view", number, "-F", "json", "-c"],
        operation=f"fetch GitLab issue #{number}",
        hint=f"Check issue #{number} exists in this project. {LOGIN_HINT}",
    )
    comments = tuple(
        Comment(
            author=(note.get("author") or {}).get("username", "unknown"),
            body=str(note.get("body", "")),
            created=str(note.get("created_at", "")),
        )
        for note in data.get("Notes") or []
        if not note.get("system")
    )
    return Issue(
        id=str(data["iid"]),
        title=str(data.get("title", "")),
        body=str(data.get("description") or ""),
        url=str(data.get("web_url", "")),
        comments=comments,
    )


def open_pr(branch: str, base: str, title: str, body_file: Path) -> PullRequest:
    """Open a merge request for an already-pushed branch.

    Raises:
        AdapterError: glab fails, or its output holds no merge request URL.
    """
    operation = f"open a GitLab merge request from {branch}"
    output = run(
        [
            "glab",
            "mr",
            "create",
            "--source-branch",
            branch,
            "--target-branch",
            base,
            "--title",
            title,
            "--description-file",
            str(body_file),
            "--yes",
        ],
        operation=operation,
        hint=f"Check {branch} is pushed and has no open merge request. {LOGIN_HINT}",
    )
    match = MR_URL.search(output)
    if match is None:
        raise AdapterError(
            operation,
            f"glab printed no merge request URL: {output.strip()[:300]}",
            "Look for the merge request in GitLab; record its URL in state.json before retrying.",
        )
    return PullRequest(url=match[0], number=match[1])


def upload(path: Path) -> str:
    """Upload a file to the project and return the markdown that embeds it.

    Raises:
        AdapterError: The upload fails or returns no markdown.
    """
    operation = f"upload {path.name} to GitLab"
    data = run_json(
        ["glab", "api", "projects/:fullpath/uploads", "--form", f"file=@{path}"],
        operation=operation,
        hint=LOGIN_HINT,
    )
    markdown = data.get("markdown")
    if not isinstance(markdown, str) or not markdown:
        raise AdapterError(operation, "GitLab returned no markdown for the upload", LOGIN_HINT)
    return markdown


def comment(number: str, body: str) -> None:
    """Post a note on a merge request.

    Raises:
        AdapterError: glab fails.
    """
    run(
        ["glab", "mr", "note", "create", number, "-m", body],
        operation=f"comment on GitLab merge request !{number}",
        hint=LOGIN_HINT,
    )
