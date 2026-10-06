import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.gitinfo import base_branch, origin_url, require_tool


def test_origin_url_is_none_without_an_origin_remote(commands, tmp_path):
    commands.respond(("git", "remote"), stdout="upstream\n")
    assert origin_url(tmp_path) is None


def test_origin_url_returns_the_url(commands, tmp_path):
    commands.respond(("git", "remote"), stdout="origin\n")
    commands.respond(("git", "remote", "get-url", "origin"), stdout="git@github.com:a/b.git\n")
    assert origin_url(tmp_path) == "git@github.com:a/b.git"


def test_base_branch_reads_origin_head(commands, tmp_path):
    commands.respond(("git", "symbolic-ref"), stdout="origin/main\n")
    assert base_branch(tmp_path, has_remote=True) == "main"


def test_base_branch_without_origin_head_says_how_to_set_it(commands, tmp_path):
    commands.respond(("git", "symbolic-ref"), returncode=128, stderr="not a symbolic ref")
    with pytest.raises(AdapterError, match="git remote set-head origin --auto"):
        base_branch(tmp_path, has_remote=True)


def test_base_branch_without_remote_is_the_current_branch(commands, tmp_path):
    commands.respond(("git", "branch", "--show-current"), stdout="trunk\n")
    assert base_branch(tmp_path, has_remote=False) == "trunk"


def test_base_branch_without_remote_rejects_detached_head(commands, tmp_path):
    commands.respond(("git", "branch", "--show-current"), stdout="\n")
    with pytest.raises(AdapterError, match="detached"):
        base_branch(tmp_path, has_remote=False)


def test_require_tool_names_the_missing_program(monkeypatch):
    monkeypatch.setattr("devteam_tools.gitinfo.shutil.which", lambda _name: None)
    with pytest.raises(AdapterError, match="npx is not on PATH"):
        require_tool("npx", "Install Node.js.")
