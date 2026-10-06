import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.remote import Remote, is_local_remote, parse_remote


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


@pytest.mark.parametrize(
    "url", ["/srv/git/r.git", "file:///srv/r.git", "../r.git", "./r", "C:/repos/r"]
)
def test_local_path_remotes_are_recognised(url):
    assert is_local_remote(url)


@pytest.mark.parametrize(
    "url", ["git@github.com:a/b.git", "https://github.com/a/b", "ssh://git@h:22/a/b"]
)
def test_network_remotes_are_not_local(url):
    assert not is_local_remote(url)
