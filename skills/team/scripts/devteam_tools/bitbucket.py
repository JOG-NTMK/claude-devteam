"""Bitbucket Cloud as a pull request target (REST 2.0, Atlassian API token)."""

from collections.abc import Mapping
from dataclasses import dataclass

from devteam_tools.env import require_env
from devteam_tools.errors import AdapterError
from devteam_tools.http import BasicAuth, request_json
from devteam_tools.model import PullRequest
from devteam_tools.remote import Remote

ENV = ("BITBUCKET_EMAIL", "BITBUCKET_API_TOKEN")
API = "https://api.bitbucket.org/2.0/repositories"


@dataclass(frozen=True)
class PrRequest:
    """What to open: source branch, destination branch, title and markdown body."""

    branch: str
    base: str
    title: str
    body: str


def _repository_url(remote: Remote, operation: str) -> str:
    if remote.path.count("/") != 1:
        raise AdapterError(
            operation,
            f"origin path {remote.path!r} is not workspace/repository",
            "Point origin at https://bitbucket.org/<workspace>/<repository>.git.",
        )
    return f"{API}/{remote.path}"


def _auth(env: Mapping[str, str], operation: str) -> BasicAuth:
    email, token = require_env(ENV, env, operation)
    return BasicAuth(email, token, ENV)


def preflight(remote: Remote, env: Mapping[str, str]) -> None:
    """Check the credentials can read the repository.

    Raises:
        AdapterError: Missing credentials, a bad remote, or no access.
    """
    operation = "check Bitbucket access"
    url = _repository_url(remote, operation)
    request_json("GET", url, auth=_auth(env, operation), operation=operation)


def open_pr(remote: Remote, request: PrRequest, env: Mapping[str, str]) -> PullRequest:
    """Open a pull request for an already-pushed branch.

    Raises:
        AdapterError: The request fails or the response has no web link.
    """
    operation = f"open a Bitbucket pull request from {request.branch}"
    url = f"{_repository_url(remote, operation)}/pullrequests"
    data = request_json(
        "POST",
        url,
        auth=_auth(env, operation),
        operation=operation,
        body={
            "title": request.title,
            "description": request.body,
            "source": {"branch": {"name": request.branch}},
            "destination": {"branch": {"name": request.base}},
            "close_source_branch": True,
        },
    )
    link = ((data.get("links") or {}).get("html") or {}).get("href")
    if not link:
        raise AdapterError(
            operation,
            "Bitbucket returned no pull request link",
            "Look for the pull request in Bitbucket; record its URL in state.json before retrying.",
        )
    return PullRequest(url=str(link), number=str(data.get("id", "")))


def comment(remote: Remote, number: str, body: str, env: Mapping[str, str]) -> None:
    """Post a markdown comment on a pull request.

    Raises:
        AdapterError: The request fails.
    """
    operation = f"comment on Bitbucket pull request #{number}"
    url = f"{_repository_url(remote, operation)}/pullrequests/{number}/comments"
    request_json(
        "POST",
        url,
        auth=_auth(env, operation),
        operation=operation,
        body={"content": {"raw": body}},
    )
