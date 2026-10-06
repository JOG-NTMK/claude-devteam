import pytest

from devteam_tools.commands import run, run_json
from devteam_tools.errors import AdapterError


def test_run_returns_stdout(commands):
    commands.respond(("git", "remote"), stdout="origin\n")
    assert run(["git", "remote"], operation="list remotes", hint="h") == "origin\n"


def test_run_raises_with_command_exit_code_and_stderr(commands):
    commands.respond(("gh", "auth"), returncode=1, stderr="not logged in")
    with pytest.raises(AdapterError) as caught:
        run(["gh", "auth", "status"], operation="check GitHub login", hint="Run `gh auth login`.")
    message = str(caught.value)
    assert message.startswith("check GitHub login failed:")
    assert "exited 1" in message
    assert "not logged in" in message
    assert message.endswith("Fix: Run `gh auth login`.")


def test_run_reports_a_missing_program(monkeypatch):
    def missing(*_args, **_kwargs):
        raise FileNotFoundError("glab")

    monkeypatch.setattr("devteam_tools.commands.subprocess.run", missing)
    with pytest.raises(AdapterError, match="glab is not installed"):
        run(["glab", "auth", "status"], operation="check GitLab login", hint="Install glab.")


def test_run_json_rejects_non_json(commands):
    commands.respond(("gh",), stdout="not json")
    with pytest.raises(AdapterError, match="did not return JSON"):
        run_json(["gh", "issue", "view"], operation="fetch issue", hint="h")
