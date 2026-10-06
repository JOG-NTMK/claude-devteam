---
name: team
description: Take one issue to a reviewed, QA-tested pull request with the devteam developer, reviewer and QA agents. Use when the user runs /devteam:team with an issue number, a Jira key, a file path or pasted issue text.
argument-hint: <issue number | JIRA-123 | file path | issue text>
disable-model-invocation: true
---

# devteam: issue → pull request

You orchestrate three agents on one issue: `devteam:developer`, `devteam:reviewer` and
`devteam:qa`. You run the loop, keep state, and do every git push and forge write yourself, only
after the user confirms. The agents never write to a forge.

The issue reference is: `$ARGUMENTS`

Throughout:
- `FORGE` means `python3 "${CLAUDE_SKILL_DIR}/scripts/forge.py"` and `RESULT` means
  `python3 "${CLAUDE_SKILL_DIR}/scripts/result.py"`. Both print JSON on success; on failure they
  exit non-zero with what failed and a `Fix:` line. Show that to the user and stop. Never work
  around a failed check.
- `RUN` is the absolute path `<repo root>/.devteam/<id>`; `WT` is `RUN/wt`.
- After every step, rewrite `RUN/state.json` (schema below) before starting the next.
- Agents get absolute paths only.

## 0. Resume or start

If `$ARGUMENTS` names an existing `.devteam/<id>/` directory, or any `.devteam/*/state.json` has
`"ref"` equal to `$ARGUMENTS`, read that state and continue at its `step`. Say which step you're
resuming. Otherwise start at 1.

`state.json`:
```json
{
  "ref": "<as given>", "id": "<id>", "source": "...", "target": "...", "base": "main",
  "branch": "feat/42-slug", "worktree": "<abs WT>", "step": "plan | implement | review | qa | ship | done",
  "rounds_used": 0, "review_round": 0, "qa_round": 0,
  "pushed": false, "pr_url": "", "pr_number": "", "comment_posted": false
}
```

## 1. Preflight and fetch

1. `cd "$(git rev-parse --show-toplevel)"`. If `git status --porcelain` prints anything, stop:
   the user must commit or stash first.
2. Exclude run state from git: add `.devteam/` to `$(git rev-parse --git-common-dir)/info/exclude`
   unless it's already there.
3. `FORGE detect "$ARGUMENTS"` gives `source`, `target`, `ref`, `base`. Then
   `FORGE preflight --source <source> --target <target>`.
4. `FORGE fetch-issue --source <source> --ref "<ref>" --root .devteam` gives `id`, `title`,
   `path`. Read `issue.md` and show the user its title and URL.

## 2. Branch and worktree

1. Branch type: `fix` if the issue describes a defect, otherwise `feat` (or `docs`, `test`,
   `chore`, `refactor`, `perf` when the issue is clearly that). The name is
   `<type>/<id>-<slug of the title, ≤ 5 words>`, e.g. `feat/ABC-123-export-deals-csv`.
2. If there is a remote: `git fetch origin <base>` then
   `git worktree add -b <branch> "<WT>" origin/<base>`. Without a remote:
   `git worktree add -b <branch> "<WT>" <base>`. If the branch already exists, stop and ask the
   user whether to resume on it or pick a new name.
3. Write `state.json` with `step: "plan"`.

## 3. Calling an agent

For every agent call:
1. Call the Agent tool with `subagent_type` set to the agent and a task message that starts with
   the fields below, one per line, followed by any step-specific line:
   ```
   mode: <plan | implement | fix>        (developer only)
   run dir: <RUN>
   worktree: <WT>
   base: <base>
   round: <n>                            (reviewer and qa)
   base worktree: <RUN/base>             (qa only)
   ```
2. Save the reply verbatim to `RUN/replies/<step>-<n>.md` with the Write tool.
3. `RESULT <role> RUN/replies/<step>-<n>.md`. If it fails, send the agent one follow-up (use
   SendMessage to the same agent if available, otherwise call it again with the same task) saying:
   "Your result block was invalid: <the problems>. Reply with only the corrected ```json block."
   Validate again. If it still fails, stop and show the user the raw reply.
4. If the result has a `decision`, stop the loop and ask the user that question (AskUserQuestion
   when it has clear options, otherwise plain text). Save the answer to `RUN/decisions.md`
   (append, with the step) and repeat the same call with this line added to the task message:
   `user's answer: <answer>; earlier answers in RUN/decisions.md`.

## 4. Plan ⏸

1. Developer, `mode: plan`.
2. Write the plan to `RUN/plan.md`. Show it to the user and ask: approve, or what to change.
3. If they change it, append their corrections under `## User corrections` in `plan.md`. Update
   state: `step: "implement"`.

## 5. Implement

Developer, `mode: implement`. Save its `summary` to `RUN/summary.md` and its `followups` to
`RUN/followups.json`. Check that `git -C "<WT>" log <base>..HEAD --oneline` shows commits. If it
doesn't, treat that as a failed result (step 3.3). Update `step: "review"`.

## 6. Review and QA loop

Keep `rounds_used` (fix runs) at most 3 across review and QA.

**Review:** increment `review_round`. Call the reviewer with `round: <review_round>`, and save the
result's findings and summary to `RUN/review-<review_round>.md` (as markdown: summary, then each
finding with severity, file:line and text). If `request_changes`, go to **Fix**. Otherwise set
`step: "qa"` and go to **QA**.

**QA:** increment `qa_round`. On the first QA round, create the base worktree at the commit
the branch started from: `git worktree add --detach "<RUN>/base" "$(git -C "<WT>" merge-base HEAD <B>)"`,
where `<B>` is `origin/<base>` when there is a remote and `<base>` otherwise.
Call QA with `round: <qa_round>`. Save `report` to `RUN/qa-<qa_round>.md` and `screenshots` to
`RUN/screenshots.json`. Then remove the base worktree (`git worktree remove --force "<RUN>/base"`).
- `pass`: set `step: "ship"` and go to **Ship**.
- `fail`: go to **Fix**, and after it a fresh review, then QA again.
- `blocked`: stop and show the user the report. QA can't run the app as documented, so the user
  either fixes the docs/environment and resumes, or tells you to ship without QA (say so in the
  PR body's QA section).

**Fix:** if `rounds_used` is already 3, stop and ask the user: one more round, ship with the open
findings listed, or abandon. Otherwise increment `rounds_used` and call the developer,
`mode: fix`, adding the line `findings: <RUN/review-n.md and/or RUN/qa-n.md>`. Append its `reply`
to `RUN/replies.md`. Then return to **Review**.

## 7. Ship ⏸

1. Show the user: the developer's summary; the review verdict, any `escalate` reason (prominently)
   and non-blocking findings left open; the QA table; `git -C "<WT>" diff --stat <base>...HEAD`;
   the follow-ups. Ask: ship, or stop here.
2. Build the PR body from `${CLAUDE_SKILL_DIR}/references/pr-body.md` (fill rules are in that
   file) into `RUN/pr-body.md`. The title is the issue title, prefixed with `<KEY>: ` for Jira.
3. Build the comment into `RUN/comment.md`: `## Review` (summary and every finding, including
   non-blocking, with each round's verdict), then `## QA` (the latest `qa-<n>.md`).
4. Do only the writes `state.json` hasn't recorded yet, recording each as soon as it succeeds:
   - Push (if there is a remote): `git -C "<WT>" push -u origin <branch>`, then `pushed: true`.
     Never force-push.
   - `FORGE open-pr --target <target> --branch <branch> --base <base> --title "<title>" --body-file RUN/pr-body.md`,
     then record `pr_url` and `pr_number`. On plain git (empty URL), print the title and the body
     for the user to paste, and the branch name.
   - `FORGE comment --target <target> --pr <pr_number> --body-file RUN/comment.md --screenshots-json RUN/screenshots.json --screenshot-dir RUN/screenshots`
     (omit both screenshot flags when there are none), then `comment_posted: true`.
5. Remove the worktree: `git worktree remove "<WT>"`. Keep `RUN/` as the record of the run. Set
   `step: "done"`.
6. Tell the user the PR URL (or the branch), the rounds used, the follow-ups to file, and where
   the screenshots are if they weren't embedded.

## Rules

- Stop only at: the plan, an agent decision, the round cap, a `blocked` QA, a failed command, and
  Ship. Everything else runs without asking.
- Never edit code in the worktree yourself, and never fix an agent's result block yourself:
  agents do the work, and you only run the loop.
- Never push, open a PR or post a comment before the user confirms at Ship.
- If the user interrupts, the state on disk is enough to resume with `/devteam:team <id>`.
