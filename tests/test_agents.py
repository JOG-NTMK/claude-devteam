import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLAYWRIGHT_PREFIX = "mcp__plugin_{plugin}_playwright__"


def frontmatter(name: str) -> dict[str, str]:
    text = (ROOT / "agents" / f"{name}.md").read_text(encoding="utf-8")
    _, block, _body = text.split("---\n", 2)
    fields = {}
    for line in block.strip().splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def tools(name: str) -> list[str]:
    return [tool.strip() for tool in frontmatter(name)["tools"].split(",")]


@pytest.mark.parametrize(
    ("name", "model", "effort"),
    [
        ("developer", "claude-opus-5-5", "medium"),
        ("reviewer", "claude-opus-5-5", "high"),
        ("qa", "claude-sonnet-5-5", "high"),
    ],
)
def test_models_and_effort(name, model, effort):
    fields = frontmatter(name)
    assert (fields["name"], fields["model"], fields["effort"]) == (name, model, effort)


@pytest.mark.parametrize("name", ["developer", "reviewer", "qa"])
def test_no_agent_can_spawn_agents(name):
    assert "Agent" not in tools(name)


@pytest.mark.parametrize("name", ["reviewer", "qa"])
def test_reviewer_and_qa_cannot_edit(name):
    assert not {"Edit", "Write", "NotebookEdit"} & set(tools(name))


def test_only_qa_gets_the_browser_and_names_match_the_server():
    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["name"]
    prefix = PLAYWRIGHT_PREFIX.format(plugin=plugin)
    assert (
        "playwright" in json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    )
    qa_browser = [tool for tool in tools("qa") if tool.startswith("mcp__")]
    assert qa_browser
    assert all(tool.startswith(prefix) for tool in qa_browser)
    assert f"{prefix}browser_take_screenshot" in qa_browser
    for name in ("developer", "reviewer"):
        assert not [tool for tool in tools(name) if tool.startswith("mcp__")]
