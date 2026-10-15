---
name: team
description: Take one issue to reviewed, QA-tested commits with the devteam developer, reviewer and QA agents, on a new branch or the current one, then optionally push and open a pull request. Use when the user runs /devteam:team, or asks to implement, work on or ship an issue end to end, given an issue number, a Jira key, a file path or pasted issue text. Pass that reference as the argument, followed by --no-worktree when the work must happen in the current checkout.
argument-hint: <issue number | JIRA-123 | file path | issue text> [--no-worktree]
---

# devteam: issue → reviewed commits

You orchestrate three agents on one issue: `devteam:developer`, `devteam:reviewer` and
`devteam:qa`. You run the loop, keep state, and do every git push and forge write yourself, only
when the user chooses it at Ship. Doing neither is a fine outcome. The agents never write to a
forge.

The arguments are: `$ARGUMENTS`

If the arguments start or end with `--no-worktree` as a separate word, remove that word and work
in the current checkout instead of a new worktree (`use_worktree: false`). Use this when the app
can only run from the main checkout. Otherwise `use_worktree: true`. What remains is the issue
reference, called REF below.

Throughout:
- `FORGE` means `python3 "${CLAUDE_SKILL_DIR}/scripts/forge.py"` and `RESULT` means
  `python3 "${CLAUDE_SKILL_DIR}/scripts/result.py"`. Both print JSON on success; on failure they
  exit non-zero with what failed and a `Fix:` line. Show that to the user and stop. Never work
  around a failed check.
- `RUN` is the absolute path `<repo root>/.devteam/<id>`. `WT` is `RUN/wt`, or the repo root
  when `use_worktree` is false.
- **Untrusted text never goes on a command line.** Issue text, titles and agent output can hold
  backticks or `$(…)`. Write such text to a file with the Write tool and pass the file's path.
  Only values these instructions build from safe parts (ids, branch names, numbers, paths) appear
  in commands.
- After every step, rewrite `RUN/state.json` (schema below) before starting the next.
- Agents get absolute paths only.

## 0. Resume or start

If REF names an existing `.devteam/<id>/` directory, or any `.devteam/*/state.json` has `"ref"`
equal to REF, read that state and continue at its `step`, keeping its `use_worktree`. Say which
step you're resuming. When `use_worktree` is false and `git branch --show-current` isn't the
state's `branch`: if `git status --porcelain` prints nothing, `git switch <branch>`; otherwise
stop and ask the user to commit or stash first. Otherwise start at 1.

`state.json`:
```json
{
  "ref": "<REF>", "id": "<id>", "source": "...", "target": "...", "base": "main",
  "branch": "feat/42-slug", "new_branch": true, "start": "<commit sha>",
  "worktree": "<abs WT>", "use_worktree": true, "return_branch": "",
  "step": "plan | implement | review | fix | qa | ship | done",
  "fixing": [], "rounds_used": 0, "review_round": 0, "qa_round": 0,
  "ship_notes": [], "ship_action": "", "pushed": false, "pr_url": "", "pr_number": "",
  "comment_posted": false
}
```

`fixing` lists the findings files the current fix works through. `ship_notes` records anything
the PR must admit, such as "shipped without QA" or "shipped with open findings".
`base` is the branch a pull request would target. `start` is the commit this run's work starts
from: every diff, the QA before shots and the developer's baseline use it, so earlier commits on
a reused branch aren't reviewed again. `new_branch` is false when the run continues on the branch
the checkout was already on. `return_branch` is the branch the checkout was on before the run,
set only when the run switched away from it. `ship_action` is the user's choice at Ship: `pr`,
`push` or `none`.

## 1. Preflight and fetch

1. `cd "$(git rev-parse --show-toplevel)"`. If `git status --porcelain` prints anything, stop:
   the user must commit or stash first.
2. Exclude run state from git: add `.devteam/` to `$(git rev-parse --git-common-dir)/info/exclude`
   unless it's already there.
3. Write REF to `.devteam/incoming-ref.txt` with the Write tool.
   `FORGE detect --ref-file .devteam/incoming-ref.txt` gives `source`, `target`, `ref`, `base`.
   Then `FORGE preflight --source <source> --target <target>`.
4. `FORGE fetch-issue --source <source> --ref-file .devteam/incoming-ref.txt --root .devteam`
   gives `id`, `title`, `path`. Delete `.devteam/incoming-ref.txt`. Write the title to
   `RUN/title.txt` (prefixed with `<KEY>: ` for Jira). Read `issue.md` and show the user its title
   and URL.

## 2. Branch and worktree

Let `<current>` be `git branch --show-current`. If it's non-empty and isn't `base`, ask the user
(AskUserQuestion): continue on `<current>`, or a new branch from `base`.
- **Continue:** `branch` is `<current>`, `new_branch: false`, `start` is `git rev-parse HEAD`.
  The branch is checked out here, so set `use_worktree: false` and leave `return_branch` empty.
  If the user passed no `--no-worktree`, say the run uses the current checkout. Skip to step 3
  below.
- **New branch:** carry on with step 1 below.

On `base` or a detached HEAD, carry on with step 1 below without asking.

1. Branch type: `fix` if the issue describes a defect, otherwise `feat` (or `docs`, `test`,
   `chore`, `refactor`, `perf` when the issue is clearly that). The name is
   `<type>/<id>-<slug>`, where the slug is up to 5 lowercase words of the title using only
   `a-z`, `0-9` and `-`. For example: `feat/ABC-123-export-deals-csv`.
2. If the branch already exists, stop and ask the user whether to resume on it or pick a new
   name. Let `<from>` be `origin/<base>` after `git fetch origin <base>` when there is a remote,
   and `<base>` otherwise. Set `new_branch: true` and `start` to `git rev-parse <from>`.
   - `use_worktree` true: `git worktree add -b <branch> "<WT>" <start>`.
   - `use_worktree` false: save `<current>` as `return_branch`, then
     `git switch -c <branch> <start>`.
3. Write `state.json` with `step: "plan"`.

## 3. Calling an agent

For every agent call:
1. Call the Agent tool with `subagent_type` set to the agent and a task message that starts with
   the fields below, one per line, followed by any step-specific line:
   ```
   mode: <plan | implement | fix>        (developer only)
   run dir: <RUN>
   worktree: <WT>
   start: <start>
   round: <n>                            (reviewer and qa)
   base worktree: <RUN/base>             (qa only)
   ```
2. Save the reply verbatim to a new file `RUN/replies/<step>-<n>-<attempt>.md` with the Write
   tool. `<attempt>` starts at 1 and goes up with each reply in that step, so no reply is
   overwritten.
3. Run `RESULT <role>` on that file. If it fails, send the same agent one follow-up with
   SendMessage: "Your result block was invalid: <the problems>. Reply with only the corrected
   ```json block." Save and validate that reply as the next attempt. If it still fails, or
   SendMessage isn't available, stop and show the user the raw reply.
4. If the result has a `decision`, stop the loop and ask the user that question (AskUserQuestion
   when it has clear options, otherwise plain text). Save the answer to `RUN/decisions.md`
   (append, with the step). Then call the agent again with this line added to the task message:
   `user's answer: <answer>; earlier answers in RUN/decisions.md`.
5. After every developer call, run `git -C "<WT>" status --porcelain --untracked-files=no`. If it
   prints anything, the developer left tracked changes uncommitted. Send it one SendMessage to
   commit or revert them, then check again. If they're still there, stop and tell the user.

## 4. Plan ⏸

1. Developer, `mode: plan`.
2. Write the plan to `RUN/plan.md`. Show it to the user and ask: approve, or what to change.
3. If they change it, append their corrections under `## User corrections` in `plan.md`. Update
   state: `step: "implement"`.

## 5. Implement

Developer, `mode: implement`. Save its `summary` to `RUN/summary.md` and its `followups` to
`RUN/followups.json`. Check that `git -C "<WT>" log <start>..HEAD --oneline` shows commits. If it
doesn't, treat that as a failed result (step 3.3). Update `step: "review"`.

## 6. Review and QA loop

`rounds_used` counts fix runs, and review and QA share a cap of 3.

**Review:** set `step: "review"` and increment `review_round`. Call the reviewer with
`round: <review_round>` and the line `developer replies: <RUN>/replies.md` (if that file exists).
Save the result's findings and summary to `RUN/review-<review_round>.md`, as markdown: the
summary, then each finding with its severity, file:line and text. If `request_changes`, go to
**Fix** with `fixing: ["review-<review_round>.md"]`. Otherwise set `step: "qa"` and go to
**QA**.

**QA:** increment `qa_round`. Make a fresh base worktree at `start`:
- if `<RUN>/base` exists, `git worktree remove --force "<RUN>/base"` first;
- then `git worktree add --detach "<RUN>/base" <start>`.

Call QA with `round: <qa_round>`. Save `report` to `RUN/qa-<qa_round>.md` and `screenshots` to
`RUN/screenshots.json`. Then remove the base worktree
(`git worktree remove --force "<RUN>/base"`), also when QA stopped with a decision.
- `pass`: set `step: "ship"` and go to **Ship**.
- `fail`: go to **Fix** with `fixing: ["qa-<qa_round>.md"]`. Fix leads to a fresh review, and
  then QA again.
- `blocked`: stop and show the user the report. QA can't run the app as documented. The user
  either fixes the docs or environment and resumes, or tells you to ship without QA. In that
  case add "shipped without QA: <reason>" to `ship_notes` and go to **Ship**.

**Fix:** if `rounds_used` is already 3, stop and ask the user: one more round, ship with the open
findings listed, or abandon.
- Ship: add "shipped with open findings: <files>" to `ship_notes`.
- Abandon: remove the worktrees that exist with `--force` (`RUN/base`, and `WT` when
  `use_worktree` is true). When `return_branch` is set, `git switch <return_branch>`. Tell the
  user the branch name and `RUN/` are kept, and stop. When `new_branch` is false, also tell them
  the run's commits are on `<branch>` after `<start>`; never reset them yourself.

Otherwise set `step: "fix"`, save `fixing`, increment `rounds_used`, and call the developer with
`mode: fix` and the line `findings: <the files in fixing, as absolute paths>`. Append its `reply`
to `RUN/replies.md` under a `## Round <rounds_used>` heading. Then clear `fixing` and go to
**Review**. When resuming at `step: "fix"`, call the developer again with the same `fixing`
files.

## 7. Ship ⏸

1. Show the user:
   - the developer's summary;
   - the review verdict, with any `escalate` reason shown prominently, and the non-blocking
     findings still open;
   - the QA table and the `ship_notes`;
   - `git -C "<WT>" diff --stat <start>..HEAD`;
   - the follow-ups.

   Ask (AskUserQuestion), and save the answer as `ship_action`:
   - `pr`: push and open a pull request against `base`, with the review and QA comment. On plain
     git this prints a description to paste instead. When the branch already has a pull request,
     suggest `push`.
   - `push`: push the branch only. Offer it only when there is a remote.
   - `none`: leave the commits on the local branch. Go straight to step 5.
2. For `pr` only, build `RUN/pr-body.md` from `${CLAUDE_SKILL_DIR}/references/pr-body.md`,
   replacing each `{{…}}`:
   - `closes_line`: `Closes #<id>` for a GitHub or GitLab issue; the Jira key for Jira; nothing
     for text.
   - `developer_summary`: `RUN/summary.md`.
   - `qa_summary` and `qa_report`: the latest QA result's `summary` and `report`. Without a QA
     pass, write "Not run: <the ship_notes entry>" and leave the report empty.
   - `review_summary`: the last review's summary and verdict.
   - `escalation_line`: `**Needs a human look:** <escalate>`, or nothing.
   - `ship_notes`: each note as a bullet, or nothing.
   - `followups`: each follow-up's title as a bullet with its body indented below, or `None.`
   - `rounds_used`: the number.

   Delete lines left empty, so no `{{` remains.
3. For `pr` only, build `RUN/comment.md`. Under `## Review`, put every round's verdict and
   summary, then every finding, including non-blocking ones. Under `## Developer replies`, put
   `RUN/replies.md` if it exists. Under `## QA`, put the latest `qa-<n>.md`.
4. Do only the writes `ship_action` asks for that `state.json` hasn't recorded yet, and record
   each one as soon as it succeeds:
   - Push (`pr` and `push`, if there is a remote): `git -C "<WT>" push -u origin <branch>`, then
     `pushed: true`. Never force-push. If the push is rejected, show the error and stop.
   - `pr` only: `FORGE open-pr --target <target> --branch <branch> --base <base> --title-file RUN/title.txt --body-file RUN/pr-body.md`,
     then record `pr_url` and `pr_number`. On plain git, where the URL is empty, print the title,
     the body and the branch name for the user to paste.
   - `pr` only: `FORGE comment --target <target> --pr <pr_number> --body-file RUN/comment.md --screenshots-json RUN/screenshots.json --screenshot-dir RUN/screenshots`,
     leaving out both screenshot flags when there are none. Then record `comment_posted: true`.
5. Leave the branch. The tracked files are clean (step 3.5), so only untracked build output such
   as dependencies remains. When `use_worktree` is true, `git worktree remove --force "<WT>"`.
   When `return_branch` is set, `git switch <return_branch>`. Keep `RUN/` as the record of the
   run, and set `step: "done"`.
6. Tell the user the branch, the PR URL if one was opened, whether it was pushed, the rounds
   used, the follow-ups to file, and where the screenshots are if they weren't embedded.

## Rules

- Stop only at: the branch question, the plan, an agent decision, the round cap, a `blocked` QA,
  a failed command, and Ship. Everything else runs without asking.
- Never edit code in `WT` yourself, and never fix an agent's result block yourself:
  agents do the work, and you only run the loop.
- Never push, open a PR or post a comment unless the user chose it at Ship.
- When `use_worktree` is false, the agents work in the user's checkout: tell the user at step 2
  not to edit it or switch branches until the run stops.
- If the user interrupts, the state on disk is enough to resume with `/devteam:team <id>`.
