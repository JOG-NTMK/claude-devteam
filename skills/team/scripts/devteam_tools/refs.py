"""Deciding where the issue comes from and where the pull request goes."""

import re
from collections.abc import Callable
from enum import StrEnum

from devteam_tools.errors import AdapterError
from devteam_tools.remote import Remote

JIRA_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
ISSUE_NUMBER = re.compile(r"^#?(\d+)$")


class Source(StrEnum):
    """Where the issue text comes from."""

    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    TEXT = "text"


class Target(StrEnum):
    """Where the pull request is opened."""

    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    GIT = "git"


def classify_target(remote: Remote | None, is_gitlab_host: Callable[[str], bool]) -> Target:
    """Return the PR target for ``origin``; unknown hosts and no remote mean plain git."""
    if remote is None:
        return Target.GIT
    if remote.host == "github.com":
        return Target.GITHUB
    if remote.host == "bitbucket.org":
        return Target.BITBUCKET
    if remote.host == "gitlab.com" or is_gitlab_host(remote.host):
        return Target.GITLAB
    return Target.GIT


def classify_source(ref: str, target: Target) -> tuple[Source, str]:
    """Return the issue source for ``ref`` and the ref normalised for that source.

    Raises:
        AdapterError: The ref is empty, or is an issue number on a forge without issues here.
    """
    ref = ref.strip()
    if not ref:
        raise AdapterError(
            "read the issue reference",
            "the issue reference is empty",
            "Pass an issue number, a Jira key, a file path or the issue text.",
        )
    if JIRA_KEY.match(ref):
        return Source.JIRA, ref
    number = ISSUE_NUMBER.match(ref)
    if number is None:
        return Source.TEXT, ref
    if target is Target.GITHUB:
        return Source.GITHUB, number[1]
    if target is Target.GITLAB:
        return Source.GITLAB, number[1]
    raise AdapterError(
        "read the issue reference",
        f"issue #{number[1]} needs a GitHub or GitLab remote, but origin is {target.value}",
        "Pass a Jira key, a file path, or paste the issue text.",
    )
