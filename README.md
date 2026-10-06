# devteam

A Claude Code plugin that takes one issue to a reviewed, QA-tested pull request. A developer
agent plans and implements the change, a reviewer agent reads it, and a QA agent tests the running
app in a headless browser. The `/devteam:team` skill runs the loop in your session. It stops for
you to approve the plan and to confirm before anything is pushed.

## Install

```
/plugin marketplace add git@github.com:<you>/claude-devteam.git
/plugin install devteam@devteam
```

## Use

```
/devteam:team 42                 # GitHub or GitLab issue, from the repo's origin
/devteam:team ABC-123            # Jira issue
/devteam:team docs/ticket.md     # issue text in a file
/devteam:team "Add CSV export…"  # pasted issue text
```

Run state lives in `.devteam/<id>/` (git-ignored through `.git/info/exclude`). Running the same
command again resumes an interrupted run.

## What the project needs

The agents learn the project only from its `CLAUDE.md`, `AGENTS.md` and `README.md`. Make sure
those say:
- how to run the tests and every other check (lint, format, types);
- how to start the app locally, its URL, any logins, and the seeders or fixtures QA may use;
- any spec or requirement convention, and anything that always needs a human to look at it.

When the docs don't say, the agents ask (or QA reports `blocked`).

## Prerequisites

| Where the issue or PR lives | Needs |
|---|---|
| everything | `git`, `python3` ≥ 3.11, Node.js ≥ 18 (`npx`, for the QA browser) |
| GitHub | `gh` logged in (`gh auth login`) |
| GitLab | `glab` logged in for the host (`glab auth login --hostname <host>`) |
| Jira | `JIRA_URL` (e.g. `https://acme.atlassian.net`), `JIRA_EMAIL`, `JIRA_API_TOKEN` |
| Bitbucket Cloud | `BITBUCKET_EMAIL`, `BITBUCKET_API_TOKEN` |
| any other remote, or none | nothing: you get the branch and a PR description to paste |

Atlassian tokens: create them at id.atlassian.com → Security → API tokens. Use a token with
scopes. Jira needs `read:jira-work`. Bitbucket needs `read:repository:bitbucket`,
`read:pullrequest:bitbucket` and `write:pullrequest:bitbucket`. Bitbucket app passwords no longer
work.

Screenshots are embedded in the PR comment on GitLab. On GitHub and Bitbucket they stay in
`.devteam/<id>/screenshots/`, and the comment lists their paths.

## Develop

```
uv sync
uv run pytest && uv run ruff check . && uv run ty check
claude plugin validate . --strict
claude --plugin-dir .          # try the plugin without installing it
```
