"""Parsing git remote URLs into host and repository path."""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from devteam_tools.errors import AdapterError

SCP_STYLE = re.compile(r"^(?:[^@/\s]+@)?(?P<host>[^:/\s]+):(?P<path>.*)$")


@dataclass(frozen=True)
class Remote:
    """Where ``origin`` points: a lower-case host and the repo path without ``.git``."""

    host: str
    path: str


def parse_remote(url: str) -> Remote:
    """Parse an https, ssh:// or scp-style remote URL.

    Raises:
        AdapterError: The URL has no host or no repository path.
    """
    url = url.strip()
    host, path = "", ""
    if "://" in url:
        parts = urlsplit(url)
        host, path = parts.hostname or "", parts.path
    elif match := SCP_STYLE.match(url):
        host, path = match["host"], match["path"]
    path = path.strip("/").removesuffix(".git").strip("/")
    if not host or not path:
        raise AdapterError(
            "read the origin remote",
            f"can't find a host and repository in {url!r}",
            "Point origin at an https or ssh URL: `git remote set-url origin <url>`.",
        )
    return Remote(host.lower(), path)
