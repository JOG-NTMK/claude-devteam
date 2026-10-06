import base64
import json
import re
from urllib.error import URLError

import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.http import BasicAuth, request_json

AUTH = BasicAuth("me@x.test", "tok", ("X_EMAIL", "X_TOKEN"))
URL = "https://api.test/thing"


def test_sends_basic_auth_and_json_body(http):
    http.route("POST", URL, 201, {"id": 7})
    assert request_json("POST", URL, auth=AUTH, operation="op", body={"a": 1}) == {"id": 7}
    sent = http.requests[0]
    expected = base64.b64encode(b"me@x.test:tok").decode()
    assert sent.get_header("Authorization") == f"Basic {expected}"
    assert sent.get_header("Content-type") == "application/json"
    assert json.loads(sent.data) == {"a": 1}


@pytest.mark.parametrize(
    ("status", "payload", "hint"),
    [
        (401, b"<html>nope</html>", "Check X_EMAIL and X_TOKEN"),
        (403, {"error": {"message": "scope"}}, "scope"),
        (404, {"errorMessages": ["Issue does not exist"]}, "exists"),
        (500, {}, "Retry"),
    ],
)
def test_http_errors_carry_status_detail_and_hint(http, status, payload, hint):
    http.route("GET", URL, status, payload)
    with pytest.raises(AdapterError) as caught:
        request_json("GET", URL, auth=AUTH, operation="fetch thing")
    message = str(caught.value)
    assert f"HTTP {status} from GET {URL}" in message
    assert hint in message


def test_a_string_error_field_is_reported(http):
    http.route("GET", URL, 400, {"error": "bad request"})
    with pytest.raises(AdapterError, match="bad request"):
        request_json("GET", URL, auth=AUTH, operation="fetch thing")


def test_404_includes_the_server_message(http):
    http.route("GET", URL, 404, {"errorMessages": ["Issue does not exist"]})
    with pytest.raises(AdapterError, match="Issue does not exist"):
        request_json("GET", URL, auth=AUTH, operation="fetch thing")


def test_network_failure_names_the_url(monkeypatch):
    def offline(_request, timeout):
        raise URLError("no route")

    monkeypatch.setattr("devteam_tools.http.urlopen", offline)
    with pytest.raises(AdapterError, match=re.escape(f"could not reach {URL}")):
        request_json("GET", URL, auth=AUTH, operation="fetch thing")


def test_non_json_success_is_an_error(http):
    http.route("GET", URL, 200, b"<html/>")
    with pytest.raises(AdapterError, match="non-JSON"):
        request_json("GET", URL, auth=AUTH, operation="fetch thing")
