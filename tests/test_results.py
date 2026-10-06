import json

import pytest

import result as result_cli
from devteam_tools.results import ResultError, extract_result, validate_result

DEVELOPER_DONE = {
    "outcome": "done",
    "plan": "",
    "summary": "Added X.",
    "reply": "",
    "decision": None,
    "followups": [],
}
REVIEW_APPROVE = {
    "verdict": "approve",
    "summary": "Fine.",
    "findings": [],
    "escalate": None,
    "decision": None,
}
QA_PASS = {
    "verdict": "pass",
    "summary": "3 of 3 pass",
    "report": "| a |",
    "screenshots": [],
    "decision": None,
}


def fenced(data):
    return f"```json\n{json.dumps(data)}\n```"


def test_extract_uses_the_last_json_block_and_ignores_trailing_text():
    reply = f"Example:\n{fenced({'example': 1})}\nDone.\n{fenced(DEVELOPER_DONE)}\nThanks!"
    assert extract_result(reply) == DEVELOPER_DONE


def test_extract_without_a_block_explains_the_format():
    with pytest.raises(ResultError, match="no ```json block"):
        extract_result("All done, looks good.")


def test_extract_rejects_invalid_json_and_non_objects():
    with pytest.raises(ResultError, match="not valid JSON"):
        extract_result("```json\n{oops}\n```")
    with pytest.raises(ResultError, match="must be a JSON object"):
        extract_result("```json\n[1]\n```")


@pytest.mark.parametrize(
    ("role", "data"), [("developer", DEVELOPER_DONE), ("reviewer", REVIEW_APPROVE), ("qa", QA_PASS)]
)
def test_valid_results_have_no_problems(role, data):
    assert validate_result(role, data) == []


def test_missing_unexpected_and_mistyped_keys_are_all_reported():
    data = {**DEVELOPER_DONE, "outcome": "shipped", "extra": 1}
    del data["followups"]
    problems = validate_result("developer", data)
    assert "missing key `followups`" in problems
    assert "unexpected key `extra`" in problems
    assert any(p.startswith("`outcome` must be one of") for p in problems)


def test_developer_cross_checks():
    assert "`plan` outcome needs a non-empty `plan`" in validate_result(
        "developer", {**DEVELOPER_DONE, "outcome": "plan"}
    )
    assert "`needs_decision` outcome needs a `decision`" in validate_result(
        "developer", {**DEVELOPER_DONE, "outcome": "needs_decision"}
    )


def test_reviewer_verdict_must_match_blocking_findings():
    blocking = {"severity": "blocking", "file": "a.py", "line": 3, "text": "Bug."}
    assert (
        "`approve` with blocking findings"
        in validate_result("reviewer", {**REVIEW_APPROVE, "findings": [blocking]})[0]
    )
    problems = validate_result("reviewer", {**REVIEW_APPROVE, "verdict": "request_changes"})
    assert "`request_changes` needs at least one blocking finding" in problems


def test_reviewer_finding_shape():
    bad = {"severity": "major", "file": "a.py", "line": "3", "text": ""}
    problems = validate_result("reviewer", {**REVIEW_APPROVE, "findings": [bad]})
    assert any("`findings` [0]" in p for p in problems)


def test_qa_screenshot_cap():
    shots = [{"file": f"after/{n}.png", "caption": "c"} for n in range(21)]
    assert any("at most 20" in p for p in validate_result("qa", {**QA_PASS, "screenshots": shots}))


def test_decision_must_have_a_question():
    assert any(
        "`decision`" in p for p in validate_result("qa", {**QA_PASS, "decision": {"question": ""}})
    )


def test_unknown_role():
    with pytest.raises(ValueError, match="unknown role"):
        validate_result("planner", {})


def test_cli_prints_result_or_problems(tmp_path, capsys):
    good = tmp_path / "good.md"
    good.write_text(fenced(QA_PASS), encoding="utf-8")
    assert result_cli.main(["qa", str(good)]) == 0
    assert json.loads(capsys.readouterr().out) == QA_PASS

    bad = tmp_path / "bad.md"
    bad.write_text(fenced({**QA_PASS, "verdict": "ok"}), encoding="utf-8")
    assert result_cli.main(["qa", str(bad)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("Invalid qa result:")
    assert "`verdict` must be one of" in err
