# API and CLI layer

Registration can be automated. **Prefer the `circleci` CLI over raw HTTP** — it reads the
stored token itself, so no command you compose ever contains a credential, and it infers
the project from the git remote, so you skip UUID resolution entirely.

What the CLI cannot do is **designate** a definition as the project's deploy or rollback
pipeline, or mint a webhook secret. Hand both to the user with instructions from
`ui-steps.md`. Do not attempt undocumented internal endpoints or browser automation.

**Pipeline creation is optional.** Without a token, give the user the `circleci pipeline
create` commands to run themselves. Never block the config work on API access — the repo
changes are the valuable part and they work regardless.

## Read the official CLI skill first

`CircleCI-Public/circleci-cli` ships a maintained skill at `skills/circleci` covering
invocation patterns for the CLI: authentication, structured output, project targeting, and
which command covers each v3 endpoint. **Load it rather than relying on this file for CLI
mechanics** — it is maintained alongside the binary and this file is not. What follows is
only the deploy-specific subset.

## Check the CLI first

```bash
circleci version
circleci pipeline --help   # absent on older builds
```

Commands below were read from `CircleCI-Public/circleci-cli` on `main`. `circleci pipeline`
and `circleci api` are recent additions, so a user on an older build may have the binary
but not these subcommands. Check before planning around them rather than discovering it
mid-sequence, and fall back to raw HTTP or the UI.

### Authentication

```bash
circleci auth me      # fails with "No CircleCI API token found" when unauthenticated
circleci auth login   # OAuth browser flow
```

**Never ask the user for an API token.** `circleci auth login` uses an OAuth flow that
needs no secret from them, which is both safer and less work than pasting a token.

Two practical notes. It **blocks until the user approves, for up to 5 minutes** — run it in
the background or with a generous timeout, not a foreground call that gives up after a
minute. And with no TTY it opens the browser and prints the URL to stderr, so pass that URL
along and tell the user to go approve it; they are watching you, not your tool output.

### Output and targeting

Human output is markdown. Add `--json` for structured data and `--jq '<expr>'` to filter
without a separate `jq`. The project comes from the cwd's git remotes; `--org <vcs>/<org>`
overrides it, where vcs is `gh`, `bb`, or `circleci`.

In non-TTY contexts the CLI already skips the pager, strips color, and fails fast with a
useful message instead of prompting. No defensive flags needed.

## Commands that map to the steps

| Need | Command |
|------|---------|
| Resolve the project | Implicit: every command below defaults to the git remote |
| List existing definitions | `circleci pipeline list --json` |
| Create a definition | `circleci pipeline create …` |
| Read deploy settings | `circleci deploy settings --json` |
| Anything without a command | `circleci api <path>` |

### Creating the definitions

```bash
circleci pipeline create \
  --name deploy \
  --description "Deploy pipeline" \
  --config-provider github_app \
  --config-repo-id "$REPO_ID" \
  --config-file .circleci/deploy.yml \
  --checkout-provider github_app \
  --checkout-repo-id "$REPO_ID" \
  --json
```

Repeat with `--name rollback` and `--config-file .circleci/rollback.yml`. Capture the `id`
from the JSON so you can confirm designation later.

**Get `REPO_ID` from the project's existing definition rather than the VCS.** The project
already has a definition for `.circleci/config.yml`, and it carries the same external ID:

```bash
REPO_ID=$(circleci pipeline list --json \
  --jq '.[0].config_source.repo.external_id')
```

That avoids a second credential entirely. `gh api repos/{owner}/{repo} --jq .id` is the
fallback when the project has no definition yet.

### What the integration supports — check this before promising anything

Two separate limits apply, and confusing them produces bad advice:

1. **Whether deploy/rollback pipelines exist as a feature** for that integration. Where
   they do not, there is no UI fallback either — the capability is absent, not merely
   un-automated.
2. **Whether `circleci pipeline create` can make the definition.**
   `checkout_source.provider` accepts `github_app`, `github_server`, and `bitbucket_dc`.
   Anything else is rejected as an unknown provider.

| Integration | Deploy markers | Deploy + rollback pipelines | Definition via CLI/API |
|-------------|----------------|------------------------------|------------------------|
| GitHub App | yes | yes | yes |
| GitHub Enterprise Server | yes | yes | yes |
| GitHub **OAuth**, no App installed | yes | needs the GitHub App | no — install the App |
| GitLab, GitLab self-managed | yes | **not supported** | no |
| Bitbucket Cloud | yes | **not supported** | no |
| Bitbucket Data Center | **not supported** | **not supported** | accepted, but moot |
| Cursor Origin (beta) | yes | **not supported** | no |

So the failure modes are genuinely different, and the thing to say differs with them:

- **GitHub OAuth without the App** — fixable. Recommend installing it, see below.
- **GitLab, Bitbucket Cloud, Cursor Origin** — markers and validation work; deploy and
  rollback pipelines are **unavailable on this integration**. Drop them from the scope and
  say why. Do not send the user to the UI to create something the UI cannot create either.
- **Auto-rollback** needs a registered rollback pipeline, so it is unavailable wherever
  rollback pipelines are. Say this when it removes an option the user asked for.

**Tell the user at the point it applies, not at the end.** Say what you cannot do and why.
Never let a skipped or failed creation read as success: the committed config does nothing
until the pipelines are registered, and someone who thinks setup finished discovers
otherwise at their next deploy.

Detecting the integration locally is imperfect. The usable signal is the project's existing
definitions:

```bash
circleci pipeline list --json --jq '.[].config_source.provider'
```

If the project has no definitions yet, you cannot tell in advance — attempt the create and
read the error rather than guessing, then fall back.

`origin` *is* a valid public-API provider value, but only for
`GET /api/v3/provider/repositories`, which lists reachable repos. It is not a valid
config or checkout source, so it does not help here.

### GitHub OAuth org: recommend installing the GitHub App

An org on the legacy GitHub OAuth app can still run pipelines — `github_oauth` is a valid
**event source** — but it is not a valid config or checkout source, so no pipeline
definition can be created for it. Deploy and rollback pipelines need the GitHub App.

This is not a dead end, and it is worth stating plainly: **every org can now install the
CircleCI GitHub App, including orgs already on the OAuth app.** The two coexist; installing
the App does not migrate or disturb the existing OAuth integration, and it is what unlocks
pipeline definitions along with the rest of the newer functionality.

Point them at the org's GitHub integration settings, note that it is an org-level action
they may need an admin for, and offer to continue with the config work meanwhile — steps 3
through 8 do not depend on it at all.

### Idempotency

Check before creating, or you get a second definition with the same name:

```bash
circleci pipeline list --json --jq '.[] | select(.name == "deploy")'
```

## Careful: "run" means a pipeline execution

`circleci pipeline` manages pipeline **definitions** — which repo to check out and where
the config lives. One **execution** of a pipeline is a **run**, so recent pipeline runs come
from `circleci run list`, not `circleci pipeline list`.

The v2 API called an execution a pipeline, which is where the collision comes from. It
matters at step 12: to find the deploy you just triggered, use `circleci run list --branch
<branch>`, then `circleci job output list <job-id>` to read the marker steps.

Note also that `circleci run release plan` (the marker command, from
`markers.md`) is unrelated to `circleci run list`. Same word, different things.

## `circleci api` for the rest

A generic authenticated passthrough. Paths are relative to `/api/v3`; a path starting with
`api` is sent as given, so prefix `api/v2/` for v2 routes. The `Authorization` header comes
from the stored token, and the exit code is 0 for 2xx, 4 for 4xx/5xx.

```bash
circleci api api/v2/deploy/projects/{project_id}/releases --jq '.items[0]'
```

A literal `{project-id}` placeholder is substituted for you when run from a repo with
detected remotes, so `circleci api 'projects/{project-id}'` works as written. Pass the real
UUID when you want determinism.

This is how you close the verification loop at step 12 without composing a `curl` that
carries a token.

> **It cannot reach internal `/private/*` routes.** The path resolver prefixes anything
> not starting with `api` with `api/v3`, so a `private/…` path becomes `/api/v3/private/…`
> and 404s. Designation is a user step — see `ui-steps.md`. Do not work around this with
> raw HTTP.

## Public read routes

| Call | Use |
|------|-----|
| `GET /api/v2/project/{provider}/{org}/{project}` | Resolve `id` and `organization_id` from a slug. `provider` is `gh`, `github`, `bb`, or `circleci` |
| `POST /api/v2/projects/{project_id}/pipeline-definitions` | What `circleci pipeline create` wraps. Body needs `name`, `config_source`, `checkout_source` |
| `GET /api/v2/projects/{project_id}/pipeline-definitions` | Existing definitions, for idempotency |
| `GET /api/v2/deploy/projects/{project_id}/settings` | Confirm designation landed |
| `GET /api/v2/deploy/projects/{project_id}/releases` | Verify the smoke-test deploy produced a release |

Use the deploy-settings read to verify designation after the user completes the UI step.

## User-handoff steps (no agent automation)

Two actions exist only in the UI today. Give the user instructions from
`ui-steps.md` and verify what you can through public reads afterward.

| Action | Agent does | User does |
|--------|------------|-----------|
| Designate deploy/rollback pipelines | Create definitions via CLI; verify settings after | Select definitions in project deploy settings |
| Mint webhook secret | Write monitoring instructions | Generate secret in org deploy settings, paste into provider |

Do not PATCH internal endpoints, compose `curl` against undocumented routes, or drive a
browser for either step.

## Sequencing

Commit and push before registering. Registration references a config file path, so a
definition created against a file that is not yet on the branch points at nothing.

**On a PR flow, creating the definition is fine while the PR is open** — it is created
against a path, and the path resolves once the branch merges. What you must not do is imply
the pipeline is ready to trigger. Say that it becomes live on merge. Same for the smoke
test, which needs a real deploy from the default branch.

1. list existing definitions for idempotency — `circleci pipeline list --json`
2. create the `deploy` definition, then `rollback` — `circleci pipeline create`
3. give the user designation instructions — `ui-steps.md`
4. when they confirm, read deploy settings and check both definition ids are set
