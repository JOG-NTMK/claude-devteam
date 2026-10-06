import pytest

from devteam_tools.errors import AdapterError
from devteam_tools.text_source import fetch_issue


def test_pasted_text_first_line_is_the_title(tmp_path):
    issue = fetch_issue("# Add dark mode\n\nUsers want it.\n", tmp_path)
    assert issue.title == "Add dark mode"
    assert issue.body == "Users want it."
    assert issue.id == "add-dark-mode"
    assert issue.url == ""


def test_a_file_path_is_read(tmp_path):
    (tmp_path / "ticket.md").write_text("Fix login\nIt 500s.", encoding="utf-8")
    issue = fetch_issue("ticket.md", tmp_path)
    assert issue.title == "Fix login"
    assert issue.url == str(tmp_path / "ticket.md")


def test_long_or_path_like_text_is_treated_as_text(tmp_path):
    text = "Support /deals/<id>/share links " + "x" * 5000
    issue = fetch_issue(text, tmp_path)
    assert issue.title.startswith("Support /deals/<id>/share links")


def test_blank_text_is_rejected(tmp_path):
    with pytest.raises(AdapterError, match="empty"):
        fetch_issue("\n\n", tmp_path)
