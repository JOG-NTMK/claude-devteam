"""Extracting and checking the JSON result block each agent ends its reply with."""

import json
import re
from collections.abc import Callable

FENCE = re.compile(r"```json[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)
MAX_SCREENSHOTS = 20

Checker = Callable[[object], str | None]


class ResultError(Exception):
    """The reply holds no usable result block."""


def extract_result(reply: str) -> dict:
    """Return the object in the last fenced ``json`` block of ``reply``.

    Raises:
        ResultError: No block, invalid JSON, or not an object.
    """
    blocks = FENCE.findall(reply)
    if not blocks:
        raise ResultError("no ```json block found; end the reply with the result block")
    try:
        data = json.loads(blocks[-1])
    except json.JSONDecodeError as error:
        raise ResultError(f"the last ```json block is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ResultError("the result block must be a JSON object")
    return data


def _one_of(*values: str) -> Checker:
    return lambda value: None if value in values else f"must be one of {', '.join(values)}"


def _string(value: object) -> str | None:
    return None if isinstance(value, str) else "must be a string"


def _text(value: object) -> str | None:
    return None if isinstance(value, str) and value.strip() else "must be a non-empty string"


def _optional_text(value: object) -> str | None:
    return None if value is None else _text(value)


def _decision(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict) and set(value) == {"question"} and not _text(value["question"]):
        return None
    return 'must be null or {"question": "<non-empty>"}'


def _items(check: Callable[[dict], str | None], limit: int | None = None) -> Checker:
    def checker(value: object) -> str | None:
        if not isinstance(value, list):
            return "must be a list"
        if limit is not None and len(value) > limit:
            return f"must have at most {limit} items"
        for index, item in enumerate(value):
            problem = check(item) if isinstance(item, dict) else "must be an object"
            if problem:
                return f"[{index}] {problem}"
        return None

    return checker


def _titled(item: dict) -> str | None:
    if set(item) != {"title", "body"} or _text(item["title"]) or _text(item["body"]):
        return "needs non-empty `title` and `body` only"
    return None


def _captioned(item: dict) -> str | None:
    if set(item) != {"file", "caption"} or _text(item["file"]) or _text(item["caption"]):
        return "needs non-empty `file` and `caption` only"
    return None


def _finding(item: dict) -> str | None:
    if set(item) != {"severity", "file", "line", "text"}:
        return "needs exactly `severity`, `file`, `line`, `text`"
    line_ok = item["line"] is None or (isinstance(item["line"], int) and item["line"] > 0)
    if item["severity"] not in ("blocking", "non_blocking") or _string(item["file"]):
        return "needs `severity` blocking|non_blocking and a string `file`"
    if not line_ok or _text(item["text"]):
        return "needs `line` as a positive integer or null and non-empty `text`"
    return None


CONTRACTS: dict[str, dict[str, Checker]] = {
    "developer": {
        "outcome": _one_of("plan", "done", "needs_decision"),
        "plan": _string,
        "summary": _string,
        "reply": _string,
        "decision": _decision,
        "followups": _items(_titled),
    },
    "reviewer": {
        "verdict": _one_of("approve", "request_changes"),
        "summary": _text,
        "findings": _items(_finding),
        "escalate": _optional_text,
        "decision": _decision,
    },
    "qa": {
        "verdict": _one_of("pass", "fail", "blocked"),
        "summary": _text,
        "report": _text,
        "screenshots": _items(_captioned, MAX_SCREENSHOTS),
        "decision": _decision,
    },
}


def _developer_rules(data: dict) -> list[str]:
    outcome = data["outcome"]
    if outcome == "plan" and not data["plan"].strip():
        return ["`plan` outcome needs a non-empty `plan`"]
    if outcome == "done" and not data["summary"].strip():
        return ["`done` outcome needs a non-empty `summary`"]
    if outcome == "needs_decision" and data["decision"] is None:
        return ["`needs_decision` outcome needs a `decision`"]
    return []


def _reviewer_rules(data: dict) -> list[str]:
    blocking = any(finding["severity"] == "blocking" for finding in data["findings"])
    if data["verdict"] == "approve" and blocking:
        return ["`approve` with blocking findings; use `request_changes`"]
    if data["verdict"] == "request_changes" and not blocking:
        return ["`request_changes` needs at least one blocking finding"]
    return []


RULES: dict[str, Callable[[dict], list[str]]] = {
    "developer": _developer_rules,
    "reviewer": _reviewer_rules,
    "qa": lambda _data: [],
}


def validate_result(role: str, data: dict) -> list[str]:
    """Return every problem with ``data`` as ``role``'s result; empty means valid.

    Raises:
        ValueError: ``role`` is not developer, reviewer or qa.
    """
    if role not in CONTRACTS:
        raise ValueError(f"unknown role {role!r}; expected one of {', '.join(CONTRACTS)}")
    contract = CONTRACTS[role]
    problems = [f"missing key `{key}`" for key in contract if key not in data]
    problems += [f"unexpected key `{key}`" for key in data if key not in contract]
    for key, check in contract.items():
        problem = check(data[key]) if key in data else None
        if problem:
            problems.append(f"`{key}` {problem}")
    return problems or RULES[role](data)
