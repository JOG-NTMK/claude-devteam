import subprocess
from dataclasses import dataclass, field

import pytest


@dataclass
class FakeCommands:
    """Stands in for subprocess.run; answers by the longest matching argv prefix."""

    responses: dict[tuple[str, ...], tuple[int, str, str]] = field(default_factory=dict)
    calls: list[list[str]] = field(default_factory=list)

    def respond(
        self, prefix: tuple[str, ...], stdout: str = "", returncode: int = 0, stderr: str = ""
    ) -> None:
        self.responses[prefix] = (returncode, stdout, stderr)

    def __call__(self, args, **_kwargs):
        self.calls.append(list(args))
        for prefix in sorted(self.responses, key=len, reverse=True):
            if tuple(args[: len(prefix)]) == prefix:
                code, out, err = self.responses[prefix]
                return subprocess.CompletedProcess(args, code, out, err)
        raise AssertionError(f"unexpected command: {args}")


@pytest.fixture
def commands(monkeypatch):
    fake = FakeCommands()
    monkeypatch.setattr("devteam_tools.commands.subprocess.run", fake)
    return fake
