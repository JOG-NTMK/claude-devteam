import io
import json
import subprocess
from dataclasses import dataclass, field
from email.message import Message
from urllib.error import HTTPError

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


@dataclass
class FakeHttp:
    """Stands in for urlopen; answers by (method, full URL)."""

    routes: dict[tuple[str, str], tuple[int, object]] = field(default_factory=dict)
    requests: list = field(default_factory=list)

    def route(self, method: str, url: str, status: int = 200, payload: object = None) -> None:
        self.routes[(method, url)] = (status, payload if payload is not None else {})

    def __call__(self, request, timeout):
        self.requests.append(request)
        key = (request.get_method(), request.full_url)
        if key not in self.routes:
            raise AssertionError(f"unexpected request: {key}")
        status, payload = self.routes[key]
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        if status >= 400:
            raise HTTPError(request.full_url, status, "error", Message(), io.BytesIO(body))
        return io.BytesIO(body)


@pytest.fixture
def http(monkeypatch):
    fake = FakeHttp()
    monkeypatch.setattr("devteam_tools.http.urlopen", fake)
    return fake
