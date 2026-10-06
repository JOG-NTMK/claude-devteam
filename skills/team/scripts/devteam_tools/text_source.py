"""Issues given as pasted text or as a file path."""

from pathlib import Path

from devteam_tools.errors import AdapterError
from devteam_tools.model import Issue, slugify


def _read_file(ref: str, cwd: Path) -> Path | None:
    if "\n" in ref:
        return None
    try:
        candidate = cwd / ref
        return candidate if candidate.is_file() else None
    except OSError:
        return None


def fetch_issue(ref: str, cwd: Path) -> Issue:
    """Return an issue from a file at ``ref`` (relative to ``cwd``) or from ``ref`` as text.

    The first line is the title (leading ``#`` removed); the rest is the body.

    Raises:
        AdapterError: There is no text.
    """
    path = _read_file(ref, cwd)
    text = (path.read_text(encoding="utf-8") if path else ref).strip()
    if not text:
        raise AdapterError(
            "read the issue text", "the issue text is empty", "Paste the issue or pass a file."
        )
    first, _, rest = text.partition("\n")
    title = first.lstrip("#").strip()
    return Issue(
        id=slugify(title), title=title, body=rest.strip(), url=str(path or ""), comments=()
    )
