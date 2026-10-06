"""Building the review/QA comment, with screenshots embedded or listed."""

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from devteam_tools.errors import AdapterError
from devteam_tools.model import Screenshot

OPERATION = "prepare QA screenshots"


def load_screenshots(listing: Path, directory: Path) -> list[Screenshot]:
    """Read QA's ``[{"file", "caption"}]`` list, with files relative to ``directory``.

    Raises:
        AdapterError: The listing is malformed, or a file is missing or outside ``directory``.
    """
    try:
        items = json.loads(listing.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdapterError(OPERATION, f"can't read {listing}: {error}", "Re-run QA.") from error
    if not isinstance(items, list):
        raise AdapterError(OPERATION, f"{listing} is not a JSON list", "Re-run QA.")
    root = directory.resolve()
    screenshots = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            raise AdapterError(OPERATION, f"bad entry in {listing}: {item!r}", "Re-run QA.")
        path = (root / item["file"]).resolve()
        if not path.is_relative_to(root):
            raise AdapterError(OPERATION, f"{item['file']} is outside {root}", "Re-run QA.")
        if not path.is_file():
            raise AdapterError(OPERATION, f"{item['file']} is not in {root}", "Re-run QA.")
        screenshots.append(Screenshot(path, str(item.get("caption", path.name))))
    return screenshots


def compose_comment(
    body: str, screenshots: Sequence[Screenshot], upload: Callable[[Path], str] | None
) -> str:
    """Append screenshots: embedded via ``upload`` when given, else listed as local paths."""
    if not screenshots:
        return body
    heading = "### Screenshots" if upload else "### Screenshots (saved locally)"
    lines = [body.rstrip(), "", heading, ""]
    for shot in screenshots:
        if upload is None:
            lines.append(f"- {shot.caption}: `{shot.path}`")
        else:
            lines += [f"**{shot.caption}**", "", upload(shot.path), ""]
    return "\n".join(lines).rstrip() + "\n"
