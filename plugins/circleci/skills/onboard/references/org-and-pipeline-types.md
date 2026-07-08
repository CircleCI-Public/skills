# Org types, pipeline types, and setup gotchas (CLI reference)

The main onboarding flow assumes the common path: a GitHub org with the CircleCI
**GitHub App** installed, one repo, config at `.circleci/config.yml`. Read this when
the situation doesn't fit that mold — a Bitbucket org, an OAuth-only org, a standalone
`circleci/<uuid>` org, central config, or when project setup "looks done" but the
Pipelines page is empty.

## Org type vs pipeline type — two separate things

Don't infer either from `vcs_type` alone.

### Org type — fixed, read from the org slug (Organization Settings → Overview)

| Org type | Slug | How it's created | VCS integrations available |
|---|---|---|---|
| `github` | `gh/<org>` (aka `github/<org>`) | Auto-imported on GitHub OAuth login | GitHub OAuth (built-in) **+** GitHub App (add-on) |
| `bitbucket` | `bb/<org>` | Auto-imported on Bitbucket OAuth login | Bitbucket Cloud OAuth (built-in) only |
| `circleci` | `circleci/<orgUUID>` | Created manually (web app / API / CLI) | GitHub App, GitLab (SaaS + self-managed), Bitbucket Data Center — all add-ons |

`gh/` and `bb/` are **OAuth orgs**; `circleci/<orgUUID>` is a **standalone org**.

### Pipeline type — what actually gates pipeline-definition/trigger steps

- **OAuth pipeline** — the classic pipeline. Exactly one per project, auto-created when the
  project is set up; config *must* be `.circleci/config.yml` in the project's own repo;
  checkout = that repo. This is all a `bb/` project or an OAuth-only `gh/` project gets.
  There is **no** CLI pipeline-definition/trigger creation for it — it just runs on push.
- **GitHub App pipeline** (a "standalone" pipeline) — zero/one/many per project, config in
  any repo & path, cross-repo triggers, external repo IDs. **This is what `pipeline create`
  (`--config-provider github_app`) and `project trigger create` build**, and it requires the
  **CircleCI GitHub App to be installed**.

**Key point:** the GitHub App is an add-on that installs *into* a `gh/` OAuth org, so GitHub
App pipelines can coexist with the classic OAuth pipeline in the *same* `gh/` project. A `gh/`
slug does **not** mean "OAuth only." **The slug tells you the org type, not the pipeline type.**

**CLI coverage:** only **GitHub App / GitHub App Server** pipelines are buildable from the CLI
(`--config-provider`/`--checkout-provider github_app`/`github_server`). **GitLab and Bitbucket
Data Center are standalone too but have no CLI provider** — create their pipelines in the web
app. Everything slug-addressable (env vars, contexts, `pipeline run`, `config validate`,
`project get`, `open`) works for every org — just swap the `gh/`/`bb/`/`gl/`/`circleci/` prefix.

## Create ≠ set up (the empty-Pipelines-page trap)

The v2 `project create` endpoint **creates the project entity but does not link the repo, add
a webhook, or add a follower.** CircleCI deliberately skips webhooks for follower-less projects
(to avoid spending credits), so a created-but-unfollowed project shows **"needs to be set up"**
with an **empty Pipelines page** — even though direct pipeline links still work.

- **OAuth orgs (`gh/`, `bb/`):** `project follow` (v1.1) is what creates the webhook and
  completes setup. Always `create` **then** `follow`.
- **Standalone orgs (`circleci/<orgUUID>`):** `create` the project, connect a repo by adding a
  pipeline definition, then `follow` to surface it on the dashboard.

Verify with `circleci project list | grep <repo>` — it returns only **followed** projects, so
it's the check that catches the trap. If a followed project still won't show pipelines, refresh
permissions (User Settings → Account Integrations → Refresh Permissions) and confirm org deploy
keys aren't disabled.

## Trigger event presets and options

`project trigger create --event-preset <preset>` selects which VCS events fire the pipeline
(all-pushes, PR-only, default-branch-only, tag-only, and many more). For the current set of
presets and their semantics, see the CircleCI docs (use the **circleci-config** skill / docs
MCP, or search "trigger event presets").

Trigger notes worth knowing regardless of preset:
- `--provider`: `github_app`, `github_server`, `github_oauth`, `webhook`, or `schedule`
  (defaults to `github_app`). `github_app`/`github_server`/`github_oauth` require `--repo-id`.
- `--config-ref <branch>` — only when the config repo differs from the event source.
- `--checkout-ref` is **rejected** when the checkout repo == the event source (checkout follows
  the pushed ref).
- Multiple triggers on one repo can cross-fire (e.g. two `all-pushes` both run on every push).

## Central config (config in a different repo than checkout)

A pipeline definition sets **where the config comes from** (`config_source`) and **what gets
checked out** (`checkout_source`). For central config, set `--config-repo-id` to the central
repo and `--checkout-repo-id` to the app repo. The config path can be any directory, not just
`.circleci/`.

## URL orbs need an allow-list entry first

URL orbs fail config processing until the org allow-lists them:

```bash
circleci api api/v2/organization/<ORG_UUID>/url-orb-allow-list \
  -d '{"name":"..","prefix":"https://raw.githubusercontent.com/<org>/<repo>/","auth":"none"}'
```

## Teardown: the CLI stands a project up but can't tear it down

There is **no** `project delete`, `unfollow`, or `archive`, and no delete for pipeline
definitions or triggers. The only teardown the CLI offers is `context delete` and
`project envvar delete`. **Delete a project in the web app** (Project Settings → Overview →
Delete Project). Scripted teardown of a project has no supported CLI/API path.

## Verify with real output, not just a green status

Always confirm a real run reached the steps you expected — use the `run`/`workflow`/`job`
verbs (no need to hit `circleci api` directly):

```bash
circleci pipeline run --project <slug> --definition-id <DEF_ID> --branch <branch> --json  # capture the run id
circleci run get <run-id> --json    # run → workflow → job tree; pull workflows[].id / workflows[].jobs[].id
circleci workflow get <workflow-id> # jobs + numbers + status for one workflow
circleci job output list <job-uuid> # step logs — confirm expected behavior
```

Prefer `pipeline run --definition-id` for verification: it's definition-targeted, so it bypasses
triggers and won't cross-fire other definitions. A green "success" status alone doesn't prove the
step did what you intended.
