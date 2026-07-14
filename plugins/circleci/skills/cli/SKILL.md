---
name: circleci-cli
description: Day-to-day CircleCI from the terminal with the circleci CLI — authenticate, validate config before you commit, watch the run your push triggered, review pipeline/workflow/job status, read job logs and failed tests, download artifacts, and rerun/cancel/trigger. Use when a developer asks to authenticate CLI access, check their build or pipeline status, watch a run after pushing, see why CI failed, read job output/logs, find failing tests, rerun failed jobs, cancel or re-trigger a run, or validate a config change locally. For first-time project connection / pipeline-definition setup use the onboarding skill; for the diagnose-and-fix methodology on a failing build use circleci-builds.
---

# CircleCI day-to-day developer workflow (CLI)

The everyday loop: change config → commit/push → watch the run → read failures → rerun.
Almost every command **infers the project from the current git remote and the branch from
your checked-out branch**, so from inside a repo you rarely pass `--project`/`--branch`.

Preflight once: `circleci version` and `circleci api api/v2/me` (auto-reads `$CIRCLE_TOKEN`).

## 1. Before you commit — validate locally (fast feedback)

```bash
circleci config validate                       # lint .circleci/config.yml (default path); use -c <path> or - for stdin
circleci config process .circleci/config.yml   # expand orbs/params → the final compiled config
circleci config process .circleci/config.yml --pipeline-parameters params.yml   # process with pipeline params
```
- `validate --org gh/<org>` is needed to resolve **private orbs**.
- `-n/--next` previews upcoming (potentially breaking) config changes.
- Scaffold a starter config for a new repo: `circleci config generate [path]` (won't overwrite).

Handy git hook — block a push when the config is invalid (`.git/hooks/pre-push`):
```bash
#!/bin/sh
circleci config validate || { echo "Fix .circleci/config.yml before pushing"; exit 1; }
```

## 2. Commit, push, and watch the run it triggers

```bash
git push                                        # your trigger fires a run
circleci run watch                              # watch the latest run on the current branch; blocks to completion
circleci run watch --sha "$(git rev-parse HEAD)"  # match the run for THIS commit (polls up to 2m for it to appear)
circleci run watch --failfast                   # bail the moment any job fails
```
`run watch` exit codes make it scriptable: **0** all workflows passed · **1** something
failed · **6** cancelled · **8** timed out (`--timeout`, default 30m). Chain it:
`git push && circleci run watch --sha "$(git rev-parse HEAD)"`.

## 3. Review your pipelines / runs

```bash
circleci run list                    # recent runs for this project (--limit, -b <branch>, -B current branch)
circleci run get                     # latest run on current branch: workflows → jobs, with status
circleci run get <run-id>            # a specific run
circleci my runs                     # YOUR recent runs across every project you can access
circleci run open                    # open the current branch's run in the browser
```
`run get` shows the run → workflow → job tree. Add `--json` to pull IDs for drilling in
(`workflows[].id`, `workflows[].jobs[].id`) — those UUIDs feed the commands below.

## 4. Drill into a failure

```bash
circleci run get --json --jq '.workflows[].jobs[] | select(.current_outcome=="failed") | {name,id}'   # failing jobs + UUIDs
circleci job output list <job-id>              # per-step logs (rendered; --tail N, default last 200 lines/step)
circleci job output get  <job-id> --step-num <N>   # full output of one step (--execution <i> for parallel runs)
circleci job get <job-id>                      # job metadata (status, timing, parallelism)
circleci testresult list <job-id>              # FAILED tests only by default (--all, --filter result=…, --sort, --limit)
circleci job artifact <job-id>                 # list artifacts; -o <dir> to download them
```
Parallel jobs: `job output list --execution <index>` targets one shard.

## 5. Act on a run

```bash
circleci workflow rerun <workflow-id>               # rerun the whole workflow from scratch
circleci workflow rerun <workflow-id> --from-failed # rerun only the failed jobs (workflow IDs come from `run get`)
circleci run cancel <run-number-or-id>              # stop a run (-f to skip the prompt)
circleci run trigger                                # manually trigger a run (current project/branch)
circleci run trigger -b <branch> --parameter deploy=true --parameter tier=2   # trigger with params (repeatable)
circleci workflow cancel <workflow-id>              # cancel a single workflow
```
To debug interactively (SSH into a job), rerun **with SSH** from the web app — there is no
CLI flag for it; `circleci run open` gets you there fast.

## Troubleshooting — where to get each piece of information

| You want to know… | Command |
|---|---|
| Did my push build? Which run? | `circleci run watch --sha "$(git rev-parse HEAD)"` / `circleci run list -B` |
| Overall status of the latest run | `circleci run get` |
| Which workflow/job failed | `circleci run get --json --jq '.workflows[].jobs[] \| select(.current_outcome=="failed")'` |
| Why a step failed (logs) | `circleci job output list <job-id>` → `job output get <job-id> --step-num N` |
| Which tests failed | `circleci testresult list <job-id>` |
| Build outputs / reports | `circleci job artifact <job-id> -o ./artifacts` |
| Config problem before pushing | `circleci config validate` / `circleci config process` |
| Config error in the UI vs local | validate with `--org` to match private-orb resolution |
| Everything I triggered lately | `circleci my runs` |
| Open it in the browser | `circleci run open`, `circleci workflow open`, `circleci job open` |
| CircleCI feature/config syntax question | use the **circleci-config** skill / docs MCP rather than guessing |

## Gotchas
- Commands default to the **git remote's project and your current branch** — `cd` into the
  repo. Override with `--project gh/<org>/<repo>` and `-b <branch>` when outside it (note:
  `run get`/`run open` default the branch to `main` when `--project` is set, not your checkout).
- `run watch --sha` **polls up to 2 minutes** for the run to appear — expected right after a push.
- Logs, tests, and artifacts key off the **job UUID** (from `run get --json` /
  `workflow get`), not the job number.
- `run cancel` takes a run number *or* UUID; pass `--project` when cancelling by number.
- `circleci api <path>` defaults to `/api/v3` — prefix `api/v2/...` explicitly for v2 endpoints.
- Don't confuse `run trigger` (this skill: fire a run on the inferred project/branch) with
  `pipeline run --definition-id …` (definition-targeted; see the onboarding skill).
- Verify a real run + `job output`/`testresult` — a green status alone doesn't prove the
  step did what you intended.

## Guardrails

- **Read before you mutate.** Prefer read-only commands (`run get`/`list`, `job output`,
  `testresult`, `job artifact`) before `rerun`/`trigger`/`cancel`, and confirm the
  organization/project scope before mutating pipeline state.
- **Never print raw secret values** from environment variables or tokens. Pipe secrets from
  `op read`/stdin — never pass them as command-line args (they leak into shell history and logs).
- **Don't invent commands.** Current CLI (≥1.0) exposes `pipeline`, `project`, `trigger`,
  `run`, `job`, `workflow`, `config`, and `api`. Verify with `circleci help` first; if a
  subcommand isn't listed, don't use it. On older builds that lack `api`/`logs`, fall back to
  the `pipeline`/`trigger`/`run` verbs and read cloud job logs from the CircleCI app/UI or
  connected CircleCI MCP tooling.
- **If auth/permissions fail, report the exact scope gap** and safest remediation
  (`circleci auth login`, refresh permissions in User Settings) rather than retrying blindly.

## Report back

When you finish, summarize:

1. Commands run and their purpose.
2. Key outputs — pipeline/workflow/job ids, status, failing step.
3. Actions taken (rerun/trigger/validate) and why.
4. Remaining blockers and the next recommended CLI command.
