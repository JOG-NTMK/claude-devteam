"""The subprocess boundary: every git, gh and glab call goes through here."""

import json
import subprocess
from pathlib import Path

from devteam_tools.errors import AdapterError


def run(args: list[str], *, operation: str, hint: str, cwd: Path | None = None) -> str:
    """Run a command and return its stdout.

    Raises:
        AdapterError: The program is missing or exits non-zero.
    """
    try:
        completed = subprocess.run(args, capture_output=True, text=True, check=False, cwd=cwd)
    except FileNotFoundError as error:
        raise AdapterError(operation, f"{args[0]} is not installed", hint) from error
    if completed.returncode != 0:
        output = (completed.stderr or completed.stdout or "").strip()[-800:]
        detail = f"`{' '.join(args)}` exited {completed.returncode}: {output}"
        raise AdapterError(operation, detail, hint)
    return completed.stdout


def run_json(args: list[str], *, operation: str, hint: str, cwd: Path | None = None) -> dict:
    """Run a command whose stdout is a JSON object and return it parsed.

    Raises:
        AdapterError: The command fails or prints something other than a JSON object.
    """
    output = run(args, operation=operation, hint=hint, cwd=cwd)
    try:
        data = json.loads(output)
    except json.JSONDecodeError as error:
        raise AdapterError(operation, f"`{' '.join(args)}` did not return JSON", hint) from error
    if not isinstance(data, dict):
        raise AdapterError(operation, f"`{' '.join(args)}` did not return a JSON object", hint)
    return data
