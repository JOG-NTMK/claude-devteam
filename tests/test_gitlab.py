import json
from pathlib import Path

import pytest

from devteam_tools import gitlab
from devteam_tools.errors import AdapterError


def test_is_gitlab_host_asks_glab(commands):
    commands.respond(("glab", "auth", "status", "--hostname", "gitlab.example.com"))
    commands.respond(("glab", "auth", "status", "--hostname", "git.other"), returncode=1)
    assert gitlab.is_gitlab_host("gitlab.example.com") is True
    assert gitlab.is_gitlab_host("git.other") is False


def test_is_gitlab_host_is_false_without_glab(monkeypatch):
    def missing(*_a, **_k):
        raise FileNotFoundError("glab")

    monkeypatch.setattr("devteam_tools.commands.subprocess.run", missing)
    assert gitlab.is_gitlab_host("gitlab.example.com") is False


def test_fetch_issue_skips_system_notes(commands):
    commands.respond(
        ("glab", "issue", "view"),
        stdout=json.dumps(
            {
                "iid": 26,
                "title": "Pin window",
                "description": "Six weeks.",
                "web_url": "https://gl.test/x/-/issues/26",
                "Notes": [
                    {
                        "author": {"username": "jason"},
                        "body": "Yes",
                        "created_at": "2026-09-30",
                        "system": False,
                    },
                    {
                        "author": {"username": "jason"},
                        "body": "added label",
                        "created_at": "2026-09-30",
                        "system": True,
                    },
                ],
            }
        ),
    )
    issue = gitlab.fetch_issue("26")
    assert commands.calls[0] == ["glab", "issue", "view", "26", "-F", "json", "-c"]
    assert issue.id == "26"
    assert [c.body for c in issue.comments] == ["Yes"]


def test_open_pr_parses_the_mr_url(commands):
    commands.respond(
        ("glab", "mr", "create"),
        stdout="Creating merge request for feat/26-x into main\n!83 Pin window\nhttps://gl.test/x/-/merge_requests/83\n",
    )
    pr = gitlab.open_pr("feat/26-x", "main", "Pin window", Path("/tmp/b.md"))
    assert (pr.url, pr.number) == ("https://gl.test/x/-/merge_requests/83", "83")
    assert commands.calls[0] == [
        "glab",
        "mr",
        "create",
        "--source-branch",
        "feat/26-x",
        "--target-branch",
        "main",
        "--title",
        "Pin window",
        "--description-file",
        "/tmp/b.md",
        "--yes",
    ]


def test_open_pr_without_a_url_fails(commands):
    commands.respond(("glab", "mr", "create"), stdout="done\n")
    with pytest.raises(AdapterError, match="no merge request URL"):
        gitlab.open_pr("b", "main", "T", Path("/tmp/b.md"))


def test_upload_returns_markdown(commands, tmp_path):
    shot = tmp_path / "home.png"
    shot.write_bytes(b"png")
    commands.respond(
        ("glab", "api", "projects/:fullpath/uploads"),
        stdout=json.dumps({"markdown": "![home](/uploads/abc/home.png)"}),
    )
    assert gitlab.upload(shot) == "![home](/uploads/abc/home.png)"
    assert commands.calls[0] == [
        "glab",
        "api",
        "projects/:fullpath/uploads",
        "--form",
        f"file=@{shot}",
    ]


def test_comment_posts_a_note(commands):
    commands.respond(("glab", "mr", "note", "create"))
    gitlab.comment("83", "hello")
    assert commands.calls[0] == ["glab", "mr", "note", "create", "83", "-m", "hello"]
