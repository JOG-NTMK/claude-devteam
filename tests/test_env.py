import pytest

from devteam_tools.env import require_env
from devteam_tools.errors import AdapterError


def test_require_env_returns_stripped_values_in_order():
    env = {"A": " a ", "B": "b"}
    assert require_env(("A", "B"), env, "op") == ("a", "b")


def test_require_env_names_every_missing_or_blank_variable():
    with pytest.raises(AdapterError) as caught:
        require_env(("A", "B", "C"), {"B": "  "}, "fetch Jira issue")
    assert "missing A, B, C" in str(caught.value)
    assert "Fix: Export A, B, C" in str(caught.value)
