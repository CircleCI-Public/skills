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

## Read the circleci-cli skill first

The **circleci-cli** skill in this plugin covers CLI mechanics: signing in, structured
output, and project targeting, and
[`references/api-coverage.md`](../../cli/references/api-coverage.md) there maps each v3
endpoint to its command. **Load it rather than relying on this file for CLI mechanics.**
What follows is only the deploy-specific subset.

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

### The token needs write access

The consent screen offers **Read**, **Write**, and **Admin**. Read covers the whole of
step 1 — versions, definitions, settings — and then fails at step 9, because creating a
pipeline definition is a write. **Write is the minimum this skill needs**; Admin is not
required.

Say this when you recommend logging in. A user picking the most conservative option is
behaving sensibly, and they have no way to know it breaks a later step unless you tell
them.

**You cannot read the granted scope back.** `circleci auth me` returns identity only, so
there is no probe to run — state the requirement up front and treat a failed create as
the signal.

Two other things cap what the token can do:

- **the user's org role.** The scope is a ceiling, not a grant: a **Viewer** gets a
  read-only token whatever they pick on the consent screen. If re-authorizing with Write
  does not help, the role is why, and only an org admin can change it.
- **`CIRCLE_TOKEN`.** It takes precedence over stored credentials, so a read-only token
  left in the environment silently overrides a freshly authorized CLI. Rule it out before
  concluding the re-auth failed.

A token cannot be re-scoped after it is issued, so the fix is always to authorize again:

```bash
circleci auth logout
circleci auth login    # choose Write on the consent screen
```

Tokens created by hand on the Personal API Tokens page carry the user's full permissions
instead, so scope is not the problem for those — though they do expire on whatever date
was set when they were created.

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
2. **Whether `circleci pipeline create` can make the definition.** The two provider lists
   differ, and neither accepts Bitbucket:

   - `config_source.provider` — `github_app`, `github_server`, `circleci`, `origin`
   - `checkout_source.provider` — `github_app`, `github_server`, `origin`

   Anything else is rejected as an unknown provider.

| Integration | Deploy markers | Deploy + rollback pipelines | Definition via CLI/API |
|-------------|----------------|------------------------------|------------------------|
| GitHub App | yes | yes | yes |
| GitHub Enterprise Server | yes | yes | yes |
| GitHub **OAuth**, no App connected | yes | needs the GitHub App | no — connect the App first |
| GitLab, GitLab self-managed | yes | **not supported** | no |
| Bitbucket Cloud | yes | **not supported** | no |
| Bitbucket Data Center | **not supported** | **not supported** | no |
| Cursor Origin (beta) | yes | **not supported** | yes — see below |

**Origin needs the repo's full name, not just an id.** It exposes no lookup by id, so
`circleci pipeline create` requires `--config-repo-full-name` and
`--checkout-repo-full-name` in `owner/name` form alongside the usual flags. Omitting them
fails even though the provider is accepted.

Note the Origin row is deliberately split: definitions **can** be created, while deploy
and rollback pipelines are still unavailable there. Creating a definition is not the same
as the deploys feature working.

So the failure modes are genuinely different, and the thing to say differs with them:

- **GitHub OAuth with no connected App** — fixable, and the fix has a specific starting
  point that people miss. See below.
- **GitLab, Bitbucket Cloud, Cursor Origin** — markers and validation work; deploy and
  rollback pipelines are **unavailable on this integration**. Drop them from the scope and
  say why. Do not send the user to the UI to create something the UI cannot create either.
- **Auto-rollback** needs a registered rollback pipeline, so it is unavailable wherever
  rollback pipelines are. Say this when it removes an option the user asked for.

**Tell the user at the point it applies, not at the end.** Say what you cannot do and why.
Never let a skipped or failed creation read as success: the committed config does nothing
until the pipelines are registered, and someone who thinks setup finished discovers
otherwise at their next deploy.

### Two checks, not one

The project's existing definitions tell you what it uses **today**:

```bash
circleci pipeline list --json --jq '.[].config_source.provider'
```

That is not sufficient on its own. A `github_oauth` project in an org that has the GitHub
App properly connected **can** take new `github_app` definitions, and one in an org without
it cannot — and the command above returns `github_oauth` either way. So check the
connection separately before promising anything:

```bash
circleci api 'api/v3/provider/repositories?filter[org_id]={org-id}&filter[provider]=github_app'
```

`{org-id}` is resolved from the git remote, so there is no separate lookup. **Keep the
single quotes** — they stop the shell expanding the `[` and `]` in the query string.

A populated list means the App is connected to **this CircleCI org** and shows which repos
it can reach — so it also settles repo scoping, which is the other thing that can block a
create. An error or an empty list means treat it as **not connected**, and go to the
section below.

Do not report the exact failure shape as if you knew it; the useful distinction is
populated versus not. If the project has no definitions at all and you cannot run this
probe, attempt the create and read the error rather than guessing.

`origin` is also the provider value for `GET /api/v3/provider/repositories`, which lists
reachable repos and is how you resolve the `owner/name` the create flags need.

### GitHub OAuth org: connecting the GitHub App

An org on the legacy GitHub OAuth app can still run pipelines — `github_oauth` is a valid
**event source** — but it is not a valid config or checkout source. Deploy and rollback
pipelines need the GitHub App.

This is not a dead end: **every org can now add the CircleCI GitHub App, including orgs
already on the OAuth app.** The two coexist; adding the App does not migrate or disturb the
existing OAuth integration, and App pipelines can live alongside OAuth ones in the same
org.

> **Tell them to start from CircleCI, not from GitHub.** This is the step people get wrong,
> and getting it wrong looks like success.
>
> **Org → VCS Connections → GitHub App**, then follow the install and authorize prompts.

Installing the App from GitHub's side — the marketplace page, or the org's GitHub settings
— installs it on GitHub **without connecting it to the CircleCI org**. CircleCI records the
installation only when the install is initiated from CircleCI, because it hands GitHub a
signed state value it validates on the way back. Skip that and GitHub reports the App as
installed on all repositories while CircleCI still has no installation for the org, so
every `github_app` definition create fails.

It is an org-level action they may need an admin for. Offer to continue with the config
work meanwhile — steps 3 through 8 do not depend on it at all.

### When a create fails

**Read the error before acting.** The two common failures have unrelated causes, and
treating one as the other sends the user somewhere useless.

| Error | Cause | Where to go |
|-------|-------|-------------|
| **404** | The token lacks write access — **check this first** | Below |
| `pipeline_definition.create_failed` | The org has no connected GitHub App | Further below |

#### 404 on create: suspect the token scope first

A 404 reads as "project not found" and almost never is. An authorization failure on a
write comes back as 404 rather than 403, so a read-scoped token trying to create a
definition looks exactly like a project that does not exist.

The cleanest confirmation is the contrast between reads and writes: **if
`circleci pipeline list` succeeds against the same project and only the create 404s, the
token is read-scoped.** A genuinely missing project would fail both.

So do not send the user hunting for a missing project, and do not retry — the result will
not change. Work through this instead:

1. Is `CIRCLE_TOKEN` set in the environment? It overrides the stored credential, and a
   read-only value there survives any amount of re-authorizing.
2. Re-authorize — `circleci auth logout`, then `circleci auth login`, choosing **Write**
   on the consent screen. See the scope notes above.
3. Still failing? The user's org role is capping the scope. A Viewer cannot hold a write
   token, and only an org admin can change that.

Tell the user which of these you are asking them to check and why, rather than just
asking them to log in again.

#### `pipeline_definition.create_failed`: the App connection

This one is opaque and has one overwhelmingly likely cause: **the org has no connected
GitHub App installation.** Creating a `github_app` config source resolves the org's
installation first, and that lookup failing is what you are seeing.

Check, in this order, and stop at the first that explains it:

| Check | How | If this is it |
|-------|-----|---------------|
| App connected to this CircleCI org | the `provider/repositories` probe above | Have them connect it from Org → VCS Connections. **This is the usual answer** |
| App can reach this repo | same probe — is the repo in the list? | Have them widen the installation's repository access on GitHub |
| Right App | an org can also have the legacy **`circleci-checks`** app, which only does status checks | `circleci-checks` alone is not enough; they need the main CircleCI GitHub App |

**Do not conclude the project needs a "reconnect" or "migrate" step.** There is no such
project-level action, and sending the user to look for one wastes their time. The thing
that is missing is an org-level connection.

If they installed the App from GitHub before you told them not to, connecting it from
CircleCI may require **removing the installation on GitHub first**, then redoing it from
Org → VCS Connections. Offer that as the next thing to try, not as a certainty.

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

**Exactly two placeholders are substituted: `{project-id}` and `{org-id}`.** Both are
resolved from the git remote, so `circleci api 'projects/{project-id}'` works as written,
and either one may appear in a query string as well as in the path. Pass the real UUID when
you want determinism.

Nothing else is expanded. A path like `api/v2/project/{provider}/{org}/{project}` is sent
literally and returns 404 — and because the 404 body is not a UUID, piping it into the next
command produces a misleading 400 rather than an obvious failure. If you need a value the
placeholders do not cover, fetch it in its own command and check it before reusing it.

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
