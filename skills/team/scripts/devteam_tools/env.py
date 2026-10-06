"""Reading credentials from the environment."""

from collections.abc import Mapping

from devteam_tools.errors import AdapterError


def require_env(names: tuple[str, ...], env: Mapping[str, str], operation: str) -> tuple[str, ...]:
    """Return the stripped values of ``names``, in order.

    Raises:
        AdapterError: Any of them is unset or blank; all missing names are listed.
    """
    missing = [name for name in names if not env.get(name, "").strip()]
    if missing:
        listed = ", ".join(missing)
        raise AdapterError(
            operation, f"missing {listed}", f"Export {listed} (see the README's setup section)."
        )
    return tuple(env[name].strip() for name in names)
