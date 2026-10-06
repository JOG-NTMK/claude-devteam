import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.remote import Remote, parse_remote


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("git@github.com:jason/devteam.git", Remote("github.com", "jason/devteam")),
        ("https://github.com/jason/devteam", Remote("github.com", "jason/devteam")),
        (
            "ssh://git@gitlab.example.com:2222/g/sub/repo.git",
            Remote("gitlab.example.com", "g/sub/repo"),
        ),
        ("https://user@bitbucket.org/ws/repo.git/", Remote("bitbucket.org", "ws/repo")),
        ("git@GitLab.Example.com:g/r.git", Remote("gitlab.example.com", "g/r")),
    ],
)
def test_parse_remote_handles_common_url_shapes(url, expected):
    assert parse_remote(url) == expected


@pytest.mark.parametrize("url", ["", "not a url", "https://github.com/", "git@host:"])
def test_parse_remote_rejects_urls_without_host_or_path(url):
    with pytest.raises(AdapterError, match="read the origin remote"):
        parse_remote(url)
