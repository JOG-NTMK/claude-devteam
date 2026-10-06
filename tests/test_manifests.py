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
