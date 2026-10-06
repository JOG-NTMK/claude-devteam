"""Git forge and issue tracker operations for the devteam skill.

Every command prints one JSON object on stdout and exits 0, or prints what failed and how to
fix it on stderr and exits 1.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from devteam_tools import bitbucket, github, gitinfo, gitlab, jira, text_source
from devteam_tools.bitbucket import PrRequest
from devteam_tools.comments import compose_comment, load_screenshots
from devteam_tools.errors import AdapterError
from devteam_tools.model import Issue, PullRequest, render_issue
from devteam_tools.refs import Source, Target, classify_source, classify_target
from devteam_tools.remote import Remote, parse_remote

NODE_HINT = "Install Node.js 18 or newer; QA's browser runs through npx."


def _remote() -> Remote | None:
    url = gitinfo.origin_url(Path.cwd())
    return None if url is None else parse_remote(url)


def _require_remote(target: Target) -> Remote:
    remote = _remote()
    if remote is None:
        raise AdapterError(
            f"use {target.value}", "the repository has no origin remote", "Add an origin remote."
        )
    return remote


def detect(args: argparse.Namespace) -> dict:
    """Classify the issue ref and the PR target, and find the base branch."""
    remote = _remote()
    target = classify_target(remote, gitlab.is_gitlab_host)
    source, ref = classify_source(args.ref, target)
    return {
        "source": source.value,
        "target": target.value,
        "ref": ref,
        "base": gitinfo.base_branch(Path.cwd(), has_remote=remote is not None),
        "remote": None if remote is None else {"host": remote.host, "path": remote.path},
    }


def preflight(args: argparse.Namespace) -> dict:
    """Check every tool and credential the run will need, before any work starts."""
    gitinfo.require_tool("npx", NODE_HINT)
    source, target = Source(args.source), Target(args.target)
    if source is Source.GITHUB or target is Target.GITHUB:
        github.preflight()
    if source is Source.GITLAB or target is Target.GITLAB:
        gitlab.preflight(_require_remote(Target.GITLAB).host)
    if source is Source.JIRA:
        jira.preflight(os.environ)
    if target is Target.BITBUCKET:
        bitbucket.preflight(_require_remote(target), os.environ)
    return {"ok": True}


def _fetch(source: Source, ref: str) -> Issue:
    if source is Source.GITHUB:
        return github.fetch_issue(ref)
    if source is Source.GITLAB:
        return gitlab.fetch_issue(ref)
    if source is Source.JIRA:
        return jira.fetch_issue(ref, os.environ)
    return text_source.fetch_issue(ref, Path.cwd())


def fetch_issue(args: argparse.Namespace) -> dict:
    """Fetch the issue into ``<root>/<id>/issue.md``."""
    issue = _fetch(Source(args.source), args.ref)
    directory = Path(args.root) / issue.id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "issue.md"
    path.write_text(render_issue(issue), encoding="utf-8")
    return {"id": issue.id, "title": issue.title, "url": issue.url, "path": str(path)}


def open_pr(args: argparse.Namespace) -> dict:
    """Open the pull request for a pushed branch; plain git opens nothing."""
    target, body_file = Target(args.target), Path(args.body_file)
    pull = PullRequest(url="", number="")
    if target is Target.GITHUB:
        pull = github.open_pr(args.branch, args.base, args.title, body_file)
    elif target is Target.GITLAB:
        pull = gitlab.open_pr(args.branch, args.base, args.title, body_file)
    elif target is Target.BITBUCKET:
        body = body_file.read_text(encoding="utf-8")
        request = PrRequest(args.branch, args.base, args.title, body)
        pull = bitbucket.open_pr(_require_remote(target), request, os.environ)
    return {"url": pull.url, "number": pull.number}


def comment(args: argparse.Namespace) -> dict:
    """Post the review/QA comment with its screenshots; plain git posts nothing."""
    target = Target(args.target)
    screenshots = []
    if args.screenshots_json:
        screenshots = load_screenshots(Path(args.screenshots_json), Path(args.screenshot_dir))
    body = Path(args.body_file).read_text(encoding="utf-8")
    if target is Target.GIT:
        return {"posted": False}
    if target is Target.GITLAB:
        gitlab.comment(args.pr, compose_comment(body, screenshots, gitlab.upload))
    elif target is Target.GITHUB:
        github.comment(args.pr, compose_comment(body, screenshots, None))
    else:
        text = compose_comment(body, screenshots, None)
        bitbucket.comment(_require_remote(target), args.pr, text, os.environ)
    return {"posted": True}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge.py", description=__doc__)
    commands = parser.add_subparsers(required=True)
    sources = [source.value for source in Source]
    targets = [target.value for target in Target]

    command = commands.add_parser("detect", help="classify the issue ref and target")
    command.add_argument("ref")
    command.set_defaults(handler=detect)

    command = commands.add_parser("preflight", help="check tools and credentials")
    command.add_argument("--source", required=True, choices=sources)
    command.add_argument("--target", required=True, choices=targets)
    command.set_defaults(handler=preflight)

    command = commands.add_parser("fetch-issue", help="write <root>/<id>/issue.md")
    command.add_argument("--source", required=True, choices=sources)
    command.add_argument("--ref", required=True)
    command.add_argument("--root", required=True)
    command.set_defaults(handler=fetch_issue)

    command = commands.add_parser("open-pr", help="open the pull request")
    command.add_argument("--target", required=True, choices=targets)
    for name in ("--branch", "--base", "--title", "--body-file"):
        command.add_argument(name, required=True)
    command.set_defaults(handler=open_pr)

    command = commands.add_parser("comment", help="post the review and QA comment")
    command.add_argument("--target", required=True, choices=targets)
    command.add_argument("--pr", required=True)
    command.add_argument("--body-file", required=True)
    command.add_argument("--screenshots-json")
    command.add_argument("--screenshot-dir", default=".")
    command.set_defaults(handler=comment)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one command; return the process exit code."""
    args = _parser().parse_args(argv)
    try:
        result = args.handler(args)
    except AdapterError as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
