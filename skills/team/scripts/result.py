"""Validate an agent reply's result block: result.py <developer|reviewer|qa> <reply-file>."""

import argparse
import json
import sys
from pathlib import Path

from devteam_tools.results import CONTRACTS, ResultError, extract_result, validate_result


def main(argv: list[str] | None = None) -> int:
    """Print the result JSON (exit 0) or the problems with it (exit 1)."""
    parser = argparse.ArgumentParser(prog="result.py", description=__doc__)
    parser.add_argument("role", choices=list(CONTRACTS))
    parser.add_argument("reply_file", type=Path)
    args = parser.parse_args(argv)
    try:
        data = extract_result(args.reply_file.read_text(encoding="utf-8"))
    except (OSError, ResultError) as error:
        print(f"Invalid {args.role} result:\n- {error}", file=sys.stderr)
        return 1
    problems = validate_result(args.role, data)
    if problems:
        print(
            f"Invalid {args.role} result:", *(f"- {p}" for p in problems), sep="\n", file=sys.stderr
        )
        return 1
    print(json.dumps(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
