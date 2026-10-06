"""The one error type every adapter raises."""


class AdapterError(Exception):
    """An operation against git, a forge or a tracker failed.

    Args:
        operation: What was being attempted, e.g. "fetch Jira issue ABC-1".
        detail: What went wrong, including the command or HTTP status.
        hint: The action that should fix it.
    """

    def __init__(self, operation: str, detail: str, hint: str) -> None:
        super().__init__(operation, detail, hint)
        self.operation = operation
        self.detail = detail
        self.hint = hint

    def __str__(self) -> str:
        return f"{self.operation} failed: {self.detail}\nFix: {self.hint}"
