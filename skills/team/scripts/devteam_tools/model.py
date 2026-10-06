"""Plain data passed between adapters and the CLI."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Comment:
    """One human comment on an issue."""

    author: str
    body: str
    created: str


@dataclass(frozen=True)
class Issue:
    """An issue as the agents read it, whatever tracker it came from."""

    id: str
    title: str
    body: str
    url: str
    comments: tuple[Comment, ...]


@dataclass(frozen=True)
class PullRequest:
    """An opened pull/merge request; both fields are empty for plain git."""

    url: str
    number: str


@dataclass(frozen=True)
class Screenshot:
    """A QA screenshot and what it shows."""

    path: Path
    caption: str


def render_issue(issue: Issue) -> str:
    """Return the issue as the markdown file the agents read."""
    lines = [f"# {issue.title}", ""]
    if issue.url:
        lines += [f"Source: {issue.url}", ""]
    lines += [issue.body.strip() or "(no description)", ""]
    if issue.comments:
        lines += ["## Comments", ""]
        for comment in issue.comments:
            lines += [f"### {comment.author} · {comment.created}", "", comment.body.strip(), ""]
    return "\n".join(lines).rstrip() + "\n"


def slugify(text: str, max_words: int = 5) -> str:
    """Return a branch-safe slug of the first words of ``text``, at most 40 characters."""
    words = re.findall(r"[a-z0-9]+", text.lower())[:max_words]
    return "-".join(words)[:40].strip("-") or "issue"
