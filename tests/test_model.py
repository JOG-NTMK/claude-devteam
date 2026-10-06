from devteam_tools.model import Comment, Issue, render_issue, slugify


def test_render_issue_includes_title_source_body_and_comments():
    issue = Issue(
        id="42",
        title="Show leave days",
        body="Cards show leave days.",
        url="https://example.test/issues/42",
        comments=(Comment(author="sam", body="Also on mobile.", created="2026-10-01"),),
    )
    assert render_issue(issue) == (
        "# Show leave days\n\n"
        "Source: https://example.test/issues/42\n\n"
        "Cards show leave days.\n\n"
        "## Comments\n\n"
        "### sam · 2026-10-01\n\n"
        "Also on mobile.\n"
    )


def test_render_issue_marks_an_empty_description():
    issue = Issue(id="x", title="T", body="  ", url="", comments=())
    assert render_issue(issue) == "# T\n\n(no description)\n"


def test_slugify_keeps_five_lowercase_words():
    assert slugify("Show LEAVE days on the deal cards!") == "show-leave-days-on-the"


def test_slugify_falls_back_when_nothing_is_left():
    assert slugify("!!! ???") == "issue"


def test_slugify_caps_length_without_trailing_hyphen():
    slug = slugify("a" * 30 + " " + "b" * 30)
    assert len(slug) <= 40
    assert not slug.endswith("-")
