import json
import re

import pytest

from devteam_tools.comments import compose_comment, load_screenshots
from devteam_tools.errors import AdapterError
from devteam_tools.model import Screenshot


def write_listing(tmp_path, items):
    listing = tmp_path / "screenshots.json"
    listing.write_text(json.dumps(items), encoding="utf-8")
    return listing


def test_load_screenshots_resolves_paths(tmp_path):
    (tmp_path / "after").mkdir()
    (tmp_path / "after" / "home.png").write_bytes(b"x")
    listing = write_listing(tmp_path, [{"file": "after/home.png", "caption": "Home after"}])
    assert load_screenshots(listing, tmp_path) == [
        Screenshot(tmp_path / "after" / "home.png", "Home after")
    ]


def test_a_missing_screenshot_fails_before_anything_is_posted(tmp_path):
    listing = write_listing(tmp_path, [{"file": "after/gone.png", "caption": "Gone"}])
    with pytest.raises(AdapterError, match=re.escape("after/gone.png")):
        load_screenshots(listing, tmp_path)


@pytest.mark.parametrize("items", [{"file": "a.png"}, [{"caption": "no file"}], ["a.png"]])
def test_a_malformed_listing_is_rejected(tmp_path, items):
    with pytest.raises(AdapterError, match="prepare QA screenshots"):
        load_screenshots(write_listing(tmp_path, items), tmp_path)


def test_a_screenshot_outside_the_directory_is_rejected(tmp_path):
    listing = write_listing(tmp_path, [{"file": "../secret.png", "caption": "x"}])
    with pytest.raises(AdapterError, match="outside"):
        load_screenshots(listing, tmp_path / "shots")


def test_compose_embeds_uploads_with_captions(tmp_path):
    shot = Screenshot(tmp_path / "a.png", "Deal card")
    body = compose_comment("Report", [shot], lambda path: f"![{path.name}](/uploads/{path.name})")
    assert body == "Report\n\n### Screenshots\n\n**Deal card**\n\n![a.png](/uploads/a.png)\n"


def test_compose_lists_local_paths_without_an_uploader(tmp_path):
    shot = Screenshot(tmp_path / "a.png", "Deal card")
    body = compose_comment("Report", [shot], None)
    assert (
        body
        == f"Report\n\n### Screenshots (saved locally)\n\n- Deal card: `{tmp_path / 'a.png'}`\n"
    )


def test_compose_without_screenshots_is_the_body():
    assert compose_comment("Report\n", [], None) == "Report\n"
