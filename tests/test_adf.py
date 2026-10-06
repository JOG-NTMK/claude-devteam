from devteam_tools.adf import adf_to_text


def doc(*content):
    return {"type": "doc", "version": 1, "content": list(content)}


def para(*content):
    return {"type": "paragraph", "content": list(content)}


def text(value, *marks):
    node = {"type": "text", "text": value}
    if marks:
        node["marks"] = list(marks)
    return node


def test_none_and_strings():
    assert adf_to_text(None) == ""
    assert adf_to_text("  plain  ") == "plain"


def test_paragraphs_with_marks_and_links():
    document = doc(
        para(
            text("Use "),
            text("cfg", {"type": "code"}),
            text(" and "),
            text("bold", {"type": "strong"}),
            text(" see "),
            text("docs", {"type": "link", "attrs": {"href": "https://d.test"}}),
        ),
        para(text("Second")),
    )
    assert adf_to_text(document) == "Use `cfg` and **bold** see [docs](https://d.test)\n\nSecond"


def test_heading_lists_and_nesting():
    item = lambda *c: {"type": "listItem", "content": list(c)}  # noqa: E731
    document = doc(
        {"type": "heading", "attrs": {"level": 2}, "content": [text("Criteria")]},
        {
            "type": "orderedList",
            "content": [
                item(
                    para(text("First")),
                    {"type": "bulletList", "content": [item(para(text("sub")))]},
                ),
                item(para(text("Second"))),
            ],
        },
    )
    assert adf_to_text(document) == "## Criteria\n\n1. First\n  - sub\n2. Second"


def test_code_block_quote_rule_and_inline_nodes():
    document = doc(
        {"type": "codeBlock", "attrs": {"language": "php"}, "content": [text("echo 1;")]},
        {"type": "blockquote", "content": [para(text("quoted"))]},
        {"type": "rule"},
        para(
            {"type": "mention", "attrs": {"text": "@sam"}},
            text(" "),
            {"type": "emoji", "attrs": {"shortName": ":tada:"}},
            {"type": "hardBreak"},
            {"type": "inlineCard", "attrs": {"url": "https://x.test"}},
        ),
        {"type": "mediaSingle", "content": [{"type": "media", "attrs": {}}]},
    )
    assert adf_to_text(document) == (
        "```php\necho 1;\n```\n\n> quoted\n\n---\n\n@sam :tada:\nhttps://x.test\n\n[attachment]"
    )


def test_tables_render_as_pipe_rows():
    cell = lambda v: {"type": "tableCell", "content": [para(text(v))]}  # noqa: E731
    document = doc(
        {
            "type": "table",
            "content": [
                {"type": "tableRow", "content": [cell("a"), cell("b")]},
                {"type": "tableRow", "content": [cell("1"), cell("2")]},
            ],
        }
    )
    assert adf_to_text(document) == "| a | b |\n| 1 | 2 |"


def test_unknown_nodes_keep_their_children():
    document = doc({"type": "panel", "content": [para(text("inside"))]}, {"type": "mystery"})
    assert adf_to_text(document) == "inside"
