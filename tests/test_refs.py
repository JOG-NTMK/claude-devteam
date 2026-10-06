import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.refs import Source, Target, classify_source, classify_target
from devteam_tools.remote import Remote


def never(_host: str) -> bool:
    return False


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        (None, Target.GIT),
        (Remote("github.com", "a/b"), Target.GITHUB),
        (Remote("bitbucket.org", "ws/r"), Target.BITBUCKET),
        (Remote("gitlab.com", "g/r"), Target.GITLAB),
        (Remote("git.internal", "g/r"), Target.GIT),
    ],
)
def test_classify_target_by_host(remote, expected):
    assert classify_target(remote, never) is expected


def test_classify_target_recognises_a_self_hosted_gitlab():
    remote = Remote("gitlab.example.com", "jason/x")
    assert classify_target(remote, lambda host: host == "gitlab.example.com") is Target.GITLAB


@pytest.mark.parametrize(
    ("ref", "target", "expected"),
    [
        ("ABC-123", Target.BITBUCKET, (Source.JIRA, "ABC-123")),
        ("#42", Target.GITHUB, (Source.GITHUB, "42")),
        ("42", Target.GITLAB, (Source.GITLAB, "42")),
        ("Add dark mode\nso it is dark", Target.GIT, (Source.TEXT, "Add dark mode\nso it is dark")),
        ("abc-123", Target.GITHUB, (Source.TEXT, "abc-123")),
    ],
)
def test_classify_source(ref, target, expected):
    assert classify_source(ref, target) == expected


@pytest.mark.parametrize("target", [Target.BITBUCKET, Target.GIT])
def test_issue_number_without_an_issue_forge_is_rejected(target):
    with pytest.raises(AdapterError, match="needs a GitHub or GitLab remote"):
        classify_source("42", target)


def test_empty_ref_is_rejected():
    with pytest.raises(AdapterError, match="empty"):
        classify_source("   ", Target.GITHUB)
