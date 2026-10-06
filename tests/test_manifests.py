import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_marketplace_lists_the_plugin_by_its_manifest_name():
    plugin = load(".claude-plugin/plugin.json")
    marketplace = load(".claude-plugin/marketplace.json")
    entry = marketplace["plugins"][0]
    assert entry["name"] == plugin["name"] == "devteam"
    assert entry["source"] == "./"
    assert entry["version"] == plugin["version"]


def test_playwright_server_is_pinned_and_headless():
    args = load(".mcp.json")["mcpServers"]["playwright"]["args"]
    package = next(arg for arg in args if arg.startswith("@playwright/mcp@"))
    assert package.split("@")[-1][0].isdigit(), "pin an exact version, never @latest"
    assert "--headless" in args
    assert "--isolated" in args


def test_skill_is_user_invoked_and_references_existing_scripts():
    text = (ROOT / "skills/team/SKILL.md").read_text(encoding="utf-8")
    _, block, body = text.split("---\n", 2)
    assert "name: team" in block
    assert "disable-model-invocation: true" in block
    for script in ("scripts/forge.py", "scripts/result.py", "references/pr-body.md"):
        assert script in body
        assert (ROOT / "skills/team" / script).is_file()
    for agent in ("devteam:developer", "devteam:reviewer", "devteam:qa"):
        assert agent in body


def test_skill_never_puts_untrusted_text_on_a_command_line():
    commands = [
        line
        for line in (ROOT / "skills/team/SKILL.md").read_text(encoding="utf-8").splitlines()
        if "FORGE " in line and "`FORGE" in line
    ]
    assert commands
    for line in commands:
        assert "$ARGUMENTS" not in line
        assert "<title>" not in line
        assert '--ref "' not in line
