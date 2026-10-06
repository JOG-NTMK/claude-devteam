"""Facts about the local repository."""

import shutil
from pathlib import Path

from devteam_tools.commands import run
from devteam_tools.errors import AdapterError

IN_A_REPO = "Run /devteam:team from inside a git repository."


def origin_url(cwd: Path) -> str | None:
    """Return the ``origin`` remote URL, or None when there is no origin."""
    remotes = run(["git", "remote"], operation="list git remotes", hint=IN_A_REPO, cwd=cwd)
    if "origin" not in remotes.split():
        return None
    url = run(
        ["git", "remote", "get-url", "origin"],
        operation="read the origin remote",
        hint=IN_A_REPO,
        cwd=cwd,
    )
    return url.strip()


def base_branch(cwd: Path, *, has_remote: bool) -> str:
    """Return the branch work starts from: origin's default branch, else the current branch.

    Raises:
        AdapterError: origin's HEAD is unknown, or HEAD is detached in a repo without a remote.
    """
    if has_remote:
        ref = run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            operation="find origin's default branch",
            hint="Run `git remote set-head origin --auto`, then retry.",
            cwd=cwd,
        )
        return ref.strip().removeprefix("origin/")
    branch = run(
        ["git", "branch", "--show-current"],
        operation="find the current branch",
        hint=IN_A_REPO,
        cwd=cwd,
    ).strip()
    if not branch:
        raise AdapterError(
            "find the current branch", "HEAD is detached", "Check out the base branch first."
        )
    return branch


def require_tool(name: str, hint: str) -> None:
    """Raise unless ``name`` is on PATH.

    Raises:
        AdapterError: The program can't be found.
    """
    if shutil.which(name) is None:
        raise AdapterError(f"find {name}", f"{name} is not on PATH", hint)
