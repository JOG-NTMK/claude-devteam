"""Converting Atlassian Document Format (Jira v3 descriptions and comments) to text."""

import re
from collections.abc import Callable

Node = dict
Renderer = Callable[[Node, str], str]


def adf_to_text(document: object) -> str:
    """Return markdown-ish text for an ADF document; unknown nodes keep their children."""
    if isinstance(document, str):
        return document.strip()
    if not isinstance(document, dict):
        return ""
    return re.sub(r"\n{3,}", "\n\n", _render(document, "")).strip()


def _render(node: Node, indent: str) -> str:
    renderer = RENDERERS.get(str(node.get("type", "")), _children_joined)
    return renderer(node, indent)


def _children(node: Node) -> list[Node]:
    return [child for child in node.get("content") or [] if isinstance(child, dict)]


def _attrs(node: Node) -> dict:
    attrs = node.get("attrs")
    return attrs if isinstance(attrs, dict) else {}


def _children_joined(node: Node, indent: str) -> str:
    return "".join(_render(child, indent) for child in _children(node))


def _inline(node: Node) -> str:
    return "".join(_render(child, "") for child in _children(node))


def _text(node: Node, _indent: str) -> str:
    value = str(node.get("text", ""))
    for mark in node.get("marks") or []:
        kind = mark.get("type")
        if kind == "code":
            value = f"`{value}`"
        elif kind == "strong":
            value = f"**{value}**"
        elif kind == "em":
            value = f"*{value}*"
        elif kind == "link":
            value = f"[{value}]({_attrs(mark).get('href', '')})"
    return value


def _paragraph(node: Node, _indent: str) -> str:
    return _inline(node) + "\n\n"


def _heading(node: Node, _indent: str) -> str:
    level = int(_attrs(node).get("level", 1))
    return "#" * level + " " + _inline(node) + "\n\n"


def _list(node: Node, indent: str, *, ordered: bool) -> str:
    lines = []
    for number, item in enumerate(_children(node), start=1):
        marker = f"{number}." if ordered else "-"
        body = "".join(_render(child, indent + "  ") for child in _children(item))
        body = re.sub(r"\n{2,}", "\n", body).strip("\n")
        lines.append(f"{indent}{marker} {body}")
    return "\n".join(lines) + "\n\n"


def _code_block(node: Node, _indent: str) -> str:
    language = _attrs(node).get("language", "")
    return f"```{language}\n{_inline(node)}\n```\n\n"


def _blockquote(node: Node, indent: str) -> str:
    inner = _children_joined(node, indent).strip()
    return "\n".join(f"> {line}" if line else ">" for line in inner.splitlines()) + "\n\n"


def _table(node: Node, _indent: str) -> str:
    rows = []
    for row in _children(node):
        cells = [_children_joined(cell, "").strip().replace("\n", " ") for cell in _children(row)]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows) + "\n\n"


RENDERERS: dict[str, Renderer] = {
    "text": _text,
    "paragraph": _paragraph,
    "heading": _heading,
    "bulletList": lambda node, indent: _list(node, indent, ordered=False),
    "orderedList": lambda node, indent: _list(node, indent, ordered=True),
    "codeBlock": _code_block,
    "blockquote": _blockquote,
    "table": _table,
    "rule": lambda _node, _indent: "---\n\n",
    "hardBreak": lambda _node, _indent: "\n",
    "mention": lambda node, _indent: str(_attrs(node).get("text", "@someone")),
    "emoji": lambda node, _indent: str(
        _attrs(node).get("text") or _attrs(node).get("shortName", "")
    ),
    "inlineCard": lambda node, _indent: str(_attrs(node).get("url", "")),
    "media": lambda _node, _indent: "[attachment]",
    "mediaSingle": lambda node, indent: _children_joined(node, indent) + "\n\n",
}
