import json
from pathlib import Path

import pytest

from devteam_tools import github
from devteam_tools.errors import AdapterError


def test_fetch_issue_maps_gh_json(commands):
    commands.respond(
        ("gh", "issue", "view"),
        stdout=json.dumps(
            {
                "number": 42,
                "title": "Leave days",
                "body": "Show them.",
                "url": "https://github.com/a/b/issues/42",
                "comments": [
                    {
                        "author": {"login": "sam"},
                        "body": "Mobile too.",
                        "createdAt": "2026-10-01T10:00:00Z",
                    },
                    {"author": None, "body": "ghost", "createdAt": "2026-10-02T10:00:00Z"},
                ],
            }
        ),
    )
    issue = github.fetch_issue("42")
    assert commands.calls[0] == [
        "gh",
        "issue",
        "view",
        "42",
        "--json",
        "number,title,body,url,comments",
    ]
    assert (issue.id, issue.title, issue.body) == ("42", "Leave days", "Show them.")
    assert [c.author for c in issue.comments] == ["sam", "unknown"]


def test_open_pr_returns_url_and_number(commands):
    commands.respond(("gh", "pr", "create"), stdout="https://github.com/a/b/pull/7\n")
    pr = github.open_pr("feat/42-x", "main", "Leave days", Path("/tmp/body.md"))
    assert (pr.url, pr.number) == ("https://github.com/a/b/pull/7", "7")
    assert commands.calls[0] == [
        "gh",
        "pr",
        "create",
        "--head",
        "feat/42-x",
        "--base",
        "main",
        "--title",
        "Leave days",
        "--body-file",
        "/tmp/body.md",
    ]


def test_open_pr_without_a_url_in_the_output_fails(commands):
    commands.respond(("gh", "pr", "create"), stdout="Created!\n")
    with pytest.raises(AdapterError, match="no pull request URL"):
        github.open_pr("feat/42-x", "main", "T", Path("/tmp/body.md"))


def test_comment_posts_the_body(commands):
    commands.respond(("gh", "pr", "comment"))
    github.comment("7", "Review: approve")
    assert commands.calls[0] == ["gh", "pr", "comment", "7", "--body", "Review: approve"]


def test_preflight_explains_how_to_log_in(commands):
    commands.respond(("gh", "auth", "status"), returncode=1, stderr="You are not logged in")
    with pytest.raises(AdapterError, match="gh auth login"):
        github.preflight()
