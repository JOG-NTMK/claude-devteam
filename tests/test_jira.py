import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.jira import fetch_issue, preflight

ENV = {
    "JIRA_URL": "https://acme.atlassian.net/",
    "JIRA_EMAIL": "me@acme.test",
    "JIRA_API_TOKEN": "t",
}
URL = "https://acme.atlassian.net/rest/api/3/issue/ABC-12?fields=summary,description,comment"


def adf(value):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": value}]}],
    }


def test_fetch_issue_maps_fields_and_comments(http):
    http.route(
        "GET",
        URL,
        200,
        {
            "key": "ABC-12",
            "fields": {
                "summary": "Export CSV",
                "description": adf("Users export deals."),
                "comment": {
                    "total": 1,
                    "comments": [
                        {
                            "author": {"displayName": "Sam"},
                            "body": adf("Include prices."),
                            "created": "2026-10-01",
                        }
                    ],
                },
            },
        },
    )
    issue = fetch_issue("ABC-12", ENV)
    assert issue.id == "ABC-12"
    assert issue.title == "Export CSV"
    assert issue.body == "Users export deals."
    assert issue.url == "https://acme.atlassian.net/browse/ABC-12"
    assert [(c.author, c.body) for c in issue.comments] == [("Sam", "Include prices.")]


def test_fetch_issue_says_when_comments_were_truncated(http):
    http.route(
        "GET",
        URL,
        200,
        {
            "key": "ABC-12",
            "fields": {
                "summary": "S",
                "description": None,
                "comment": {"total": 3, "comments": []},
            },
        },
    )
    issue = fetch_issue("ABC-12", ENV)
    assert "3 comments exist; 0 were fetched" in issue.body


def test_fetch_issue_missing_credentials_is_reported_before_any_request(http):
    with pytest.raises(AdapterError, match="missing JIRA_EMAIL, JIRA_API_TOKEN"):
        fetch_issue("ABC-12", {"JIRA_URL": "https://acme.atlassian.net"})
    assert http.requests == []


def test_preflight_checks_the_same_variables():
    with pytest.raises(AdapterError, match="missing JIRA_URL"):
        preflight({"JIRA_EMAIL": "e", "JIRA_API_TOKEN": "t"})
