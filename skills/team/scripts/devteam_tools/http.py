"""The HTTP boundary for Jira and Bitbucket: JSON over Basic auth, errors with hints."""

import base64
import json
from dataclasses import dataclass
from http import HTTPStatus
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from devteam_tools.errors import AdapterError

TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class BasicAuth:
    """Credentials and the env var names they came from, for error hints."""

    user: str
    token: str
    env_names: tuple[str, str]


def request_json(
    method: str, url: str, *, auth: BasicAuth, operation: str, body: dict | None = None
) -> dict:
    """Send a JSON request and return the JSON object response.

    Raises:
        AdapterError: HTTP error status, network failure, or a non-JSON response.
    """
    data = None if body is None else json.dumps(body).encode()
    request = Request(url, data=data, method=method)
    credentials = base64.b64encode(f"{auth.user}:{auth.token}".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read()
    except HTTPError as error:
        detail = f"HTTP {error.code} from {method} {url}: {_server_message(error)}"
        raise AdapterError(operation, detail, _hint(error.code, auth)) from error
    except URLError as error:
        raise AdapterError(
            operation, f"could not reach {url}: {error.reason}", "Check the network and base URL."
        ) from error
    return _parse(payload, method, url, operation)


def _parse(payload: bytes, method: str, url: str, operation: str) -> dict:
    try:
        data = json.loads(payload or b"{}")
    except json.JSONDecodeError as error:
        raise AdapterError(
            operation, f"{method} {url} returned non-JSON", "Check the base URL."
        ) from error
    if not isinstance(data, dict):
        raise AdapterError(operation, f"{method} {url} returned non-JSON object", "Report this.")
    return data


def _server_message(error: HTTPError) -> str:
    raw = error.read()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return raw.decode(errors="replace")[:300]
    if not isinstance(data, dict):
        return str(data)[:300]
    error_field = data.get("error")
    nested = error_field.get("message") if isinstance(error_field, dict) else error_field
    messages = data.get("errorMessages") or [nested]
    return "; ".join(str(message) for message in messages if message)[:300]


def _hint(status: int, auth: BasicAuth) -> str:
    email_var, token_var = auth.env_names
    hints = {
        HTTPStatus.UNAUTHORIZED: f"Check {email_var} and {token_var}; it may be expired.",
        HTTPStatus.FORBIDDEN: "The token lacks a scope this call needs; see the README.",
        HTTPStatus.NOT_FOUND: "Check that it exists and that this account can see it.",
    }
    return hints.get(status, "Retry later; if it persists, check the service status page.")
