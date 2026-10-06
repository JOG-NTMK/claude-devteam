import json

import pytest

from devteam_tools import bitbucket
from devteam_tools.bitbucket import PrRequest
from devteam_tools.errors import AdapterError
from devteam_tools.remote import Remote

ENV = {"BITBUCKET_EMAIL": "me@acme.test", "BITBUCKET_API_TOKEN": "t"}
REMOTE = Remote("bitbucket.org", "acme/shop")
API = "https://api.bitbucket.org/2.0/repositories/acme/shop"


def test_open_pr_posts_branches_and_returns_the_web_url(http):
    http.route(
        "POST",
        f"{API}/pullrequests",
        201,
        {"id": 9, "links": {"html": {"href": "https://bitbucket.org/acme/shop/pull-requests/9"}}},
    )
    pr = bitbucket.open_pr(
        REMOTE, PrRequest("feat/ABC-12-csv", "main", "ABC-12: Export CSV", "Body"), ENV
    )
    assert (pr.url, pr.number) == ("https://bitbucket.org/acme/shop/pull-requests/9", "9")
    assert json.loads(http.requests[0].data) == {
        "title": "ABC-12: Export CSV",
        "description": "Body",
        "source": {"branch": {"name": "feat/ABC-12-csv"}},
        "destination": {"branch": {"name": "main"}},
        "close_source_branch": True,
    }


def test_open_pr_without_a_link_fails(http):
    http.route("POST", f"{API}/pullrequests", 201, {"id": 9})
    with pytest.raises(AdapterError, match="no pull request link"):
        bitbucket.open_pr(REMOTE, PrRequest("b", "main", "T", "B"), ENV)


def test_comment_posts_raw_markdown(http):
    http.route("POST", f"{API}/pullrequests/9/comments", 201, {"id": 1})
    bitbucket.comment(REMOTE, "9", "**QA** pass", ENV)
    assert json.loads(http.requests[0].data) == {"content": {"raw": "**QA** pass"}}


def test_preflight_reads_the_repository(http):
    http.route("GET", API, 200, {"full_name": "acme/shop"})
    bitbucket.preflight(REMOTE, ENV)
    assert http.requests[0].get_method() == "GET"


def test_preflight_names_missing_credentials(http):
    with pytest.raises(AdapterError, match="missing BITBUCKET_EMAIL, BITBUCKET_API_TOKEN"):
        bitbucket.preflight(REMOTE, {})


def test_a_remote_that_is_not_workspace_slash_repo_is_rejected():
    with pytest.raises(AdapterError, match="workspace/repository"):
        bitbucket.preflight(Remote("bitbucket.org", "acme"), ENV)
