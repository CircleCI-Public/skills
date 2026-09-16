---
name: onboarding
description: "Agent-driven onboarding guide for CircleCI. Walks a user through the full setup journey: account creation, organization selection or creation, GitHub App connection, project creation, pipeline definition + trigger, and iterating a config file until it passes. Everything is done from the terminal with the circleci CLI — never send the user to the web app for something a command can do. Use this skill whenever a user says \"onboard to CircleCI\", \"set up CircleCI\", \"get started with CircleCI\", \"connect my repo to CircleCI\", \"create a CircleCI project\", or asks for help with any early CircleCI setup step. Also trigger if the user has a new repo and wants CI running on it. For day-to-day work on an already-connected project (watch a run, read failing logs, rerun) use the circleci-cli skill instead."
---

# CircleCI Onboarding

Guide the user through setting up CircleCI from scratch. Work through the
stages below **in order**. At each stage, use `AskUserQuestion` to collect
structured input rather than asking in prose. Run CLI commands to verify state
before asking questions you can answer yourself. Skip stages that are already
complete.

**Do not send the user to the web app for anything a command can do.** Every
stage below resolves its own state through the CLI — the org list, the GitHub
App connection, the repository ID. The only browser steps are the ones that
genuinely need a browser: signup/login, and approving the GitHub App install.
If you catch yourself about to say "go to app.circleci.com and copy X", the
answer is in this file instead.

> This flow assumes the common path: a **GitHub org with the CircleCI GitHub App
> installed**, one repo, config at `.circleci/config.yml`. When the situation
> doesn't fit — a Bitbucket (`bb/`) or OAuth-only org, a standalone
> `circleci/<uuid>` org, central config, or a project that looks set up but shows
> an empty Pipelines page — read `references/org-and-pipeline-types.md`. It
> explains org type vs pipeline type, the `project follow` webhook trap, central
> config, URL-orb allow-listing, and CLI teardown limits.

**`circleci onboard` is the same flow in one command.** It generates a config,
signs the user up, creates and follows the project, and adds a pipeline
definition plus an all-pushes trigger — and it is idempotent, so it is safe on a
re-run. It needs a TTY to ask which org to use, so it only completes
unattended when the account has exactly one org. Two ways to use it:

- The user is at their own terminal: tell them to run `circleci onboard` and
  answer the prompts. That is the best experience available and you should offer
  it.
- You are driving (no TTY): run `circleci onboard --scan` when the account has
  exactly one org (Stage 2 tells you), and work through the stages below
  otherwise. They are the non-interactive equivalent, with you asking the
  questions the CLI would have prompted for.

---

## Stage 0: Check prerequisites

```bash
circleci version
```

Read the version out of the output. Don't reach for `--json` here: the legacy
CLI's `version` command takes no flags, so it would fail on exactly the versions
this check exists to catch, and an "unknown flag" error tells you nothing.

The two formats differ, which is itself the signal: v1 prints
`circleci <version>+<commit> (<source>)`, and the legacy CLI prints
`<version>+<commit> (<source>)` with no name in front.

If the major version is `0` (i.e. below `1.0.0`), stop and tell the user this
flow needs 1.0.0 or later, and how to upgrade for their install:

```
brew upgrade circleci            # macOS / Linux (Homebrew)
winget upgrade --id CircleCI.CLI # Windows
sudo snap refresh circleci       # Snap
```

Other install methods are listed at
https://github.com/CircleCI-Public/circleci-cli#installation. Do not proceed
past this stage if the version check fails.

Then run `circleci auth me` before asking anything. If it returns a user, skip
Stage 1 and note the username.

---

## Stage 1: Account

If not authenticated, ask:

```
AskUserQuestion(
  "Are you new to CircleCI or do you already have an account?",
  header: "Account",
  options: [
    { label: "New — create an account", description: "Open signup in browser via circleci auth signup" },
    { label: "Existing — log in",        description: "Open login in browser via circleci auth login" }
  ]
)
```

Run `circleci auth signup` or `circleci auth login` accordingly. Both open a
browser and then **block for up to 5 minutes waiting for approval**, so:

- Run them in the background, or with a timeout well above your default.
- Tell the user to approve the request in their browser, and pass along the URL
  printed to stderr in case the window never came to the front.

`--no-browser` prints the URL without opening anything. Verify with
`circleci auth me`.

---

## Stage 2: Organization

List the user's orgs yourself — never ask them to go and find a slug:

```bash
circleci api api/v2/me/collaborations --jq '.[] | "\(.slug)\t\(.name)"'
```

This is the one inline source of org **slugs**, which is what `--org` takes.
(`circleci org list` prints org IDs only, so it cannot answer this question.)

- **Exactly one org:** use it and say which one you picked. Don't ask.
- **More than one:** offer them as `AskUserQuestion` options, one per org,
  labelled with the slug and the name — the same choice `circleci onboard`
  would have prompted for.
- **None:** the account belongs to no org yet. Ask whether to create one:

  ```
  AskUserQuestion(
    "You're not in any CircleCI organization yet. Create one?",
    header: "Organization",
    options: [
      { label: "Create a CircleCI org", description: "I'll create it from here and use it for this project" },
      { label: "Wait for an invite",    description: "An admin adds me to an existing org first" }
    ]
  )
  ```

  To create one, ask for a name, then:

  ```bash
  circleci api api/v2/organization -f name="<org-name>" -f vcs_type=circleci --jq .slug
  ```

  That is the same endpoint `circleci onboard` uses, and it returns the new
  org's slug (`circleci/<uuid>`) — a **standalone** org, which is the type that
  supports GitHub App pipelines. Re-run the collaborations call to confirm.

A GitHub org is never created this way: a `gh/<org>` org appears on its own once
you log in with GitHub or install the GitHub App on that GitHub organization. If
the user expected to see one and doesn't, that is a Stage 3 problem, not an org
creation problem.

Note the org slug **and** the org UUID (`.id` from the same call) — Stage 3 and
Stage 5 both need the UUID.

---

## Stage 3: GitHub App connection

Check whether the org is already connected, using the org UUID from Stage 2:

```bash
circleci api 'provider/connections?filter[org_id]=<org-uuid>' --jq '.data[].attributes.provider'
```

If `github_app` is in the output, the app is installed — skip to Stage 4.

If it isn't, ask for a real install URL rather than guessing at an app page.
This mints a one-hour token, so only call it when the user is about to open it:

```bash
circleci api 'provider/connections/setup?filter[org_id]=<org-uuid>' \
  -d '{"type":"vcs","vcs":{"provider":"github_app"},"return_url":"https://app.circleci.com/cli/github-app-installed"}' \
  --jq '.data.attributes.url'
```

Give that URL to the user, tell them to install the CircleCI GitHub App and
grant it access to the repo they're setting up, then re-run the
`provider/connections` check above until `github_app` appears. If
`.data.attributes.next_step` comes back as anything other than `redirect`, the
install cannot be driven from here — hand it to the user with
`circleci onboard` and let its browser flow handle it.

---

## Stage 4: Project

Ask:

```
AskUserQuestion(
  "Which repository do you want to set up CI for?",
  header: "Repository",
  options: [
    { label: "A repo already in CircleCI (follow existing)", description: "circleci project follow" },
    { label: "A new repo (create project)",                  description: "circleci project create" }
  ]
)
```

For a new project, ask the repo name (default to the current directory name if
in a git repo), then create it, link the checkout, and follow it:

```bash
circleci project create <repo-name> --org <org-slug> --json   # capture id and slug
circleci project link                                          # writes .circleci/info.yml
circleci project follow                                        # completes setup, adds the webhook
```

Save the project `slug` and `id` (UUID).

> **`create` is not "set up".** `project create` makes the project entity but
> adds no webhook and no follower, so it shows "needs to be set up" with an
> empty Pipelines page until `project follow` runs. This bites OAuth orgs
> (`gh/`, `bb/`) hardest. `circleci project list` returns **followed** projects
> only, so it's the check that catches it. See
> `references/org-and-pipeline-types.md`.

If `project create` reports the name is already taken, it's likely this repo's
own project from an earlier attempt. Don't create a second one — point the
checkout at the existing project with
`circleci project link --project <org-slug>/<project-id>` (add `--force` if
`.circleci/info.yml` already exists) and carry on.

---

## Stage 5: Pipeline definition + trigger

You need the provider's repository ID. Resolve it through CircleCI — the org's
GitHub App connection already knows it, so `gh` is not required:

```bash
circleci api 'provider/repositories?filter[org_id]=<org-uuid>&filter[provider]=github_app&page[limit]=100' \
  --jq '.data[].attributes | select(.repo_full_name=="<owner>/<repo>") | .repo_id'
```

If that returns nothing: page through with `page[cursor]` from `.page.next` on
orgs with many repos; if the repo still isn't listed, the GitHub App hasn't been
granted access to it (back to Stage 3). Fall back to `gh api /repos/<owner>/<repo> --jq .id`
if `gh` is available, and only then ask the user for the ID.

Ask which trigger preset to use, then create both the definition and the
trigger without any further confirmation:

```
AskUserQuestion(
  "What events should trigger this pipeline?",
  header: "Trigger",
  options: [
    { label: "All pushes + PRs (recommended)", description: "all-pushes preset — runs on every push to any branch and PR events" },
    { label: "Pull requests only",             description: "only-open-prs — runs on PR open/update" },
    { label: "Default branch only",            description: "default-branch-pushes — runs only on pushes to main/master" },
    { label: "Tags only",                      description: "only-tags — runs on tag pushes, e.g. releases" }
  ]
)
```

Map the choice to `--event-preset`: `all-pushes`, `only-open-prs`,
`default-branch-pushes`, `only-tags`. (Many more presets exist — merge-queue,
PR-comment, labeled-PRs. See `references/org-and-pipeline-types.md`.)

Then immediately (no further confirmation needed):

```bash
# Create pipeline definition
circleci pipeline create \
  --project <project-slug> \
  --name "main" \
  --config-provider github_app \
  --config-repo-id <repo-id> \
  --config-file .circleci/config.yml \
  --checkout-provider github_app \
  --checkout-repo-id <repo-id> \
  --json

# Create trigger
circleci project trigger create \
  --project <project-slug> \
  --pipeline-definition-id <definition-id> \
  --repo-id <repo-id> \
  --event-preset <chosen-preset> \
  --json
```

Save the pipeline definition `id`. Both commands are safe to re-run only after
checking for what already exists — `circleci pipeline list` and
`circleci project trigger list --pipeline-definition-id <id>` — otherwise you
get duplicates that cross-fire on every push. Proceed to Stage 6.

> Pipeline definitions and triggers are **GitHub App only**. In an OAuth-only
> `gh/` org or a `bb/` org, this stage does not apply: the project's single
> classic pipeline runs on push once the project is followed, and Stage 4 was
> the last setup step. Skip to Stage 6 and just push.

---

## Stage 6: Config — create and iterate until green

### 6a — Config file

Check if `.circleci/config.yml` already exists. If not, generate it without
asking — do not prompt the user for a config strategy:

```bash
circleci config generate   # detects the stack; never overwrites an existing config
```

Then always validate:

```bash
circleci config validate
```

Fix any validation errors before proceeding.

**Important:** before using `npm test` as a build step, check `package.json`
for a `"test"` script. If it's missing, use `npm run build` instead (common
for Next.js and other frontend-only projects with no test suite).

### 6b — Commit, push, and watch

Do all of this automatically without waiting for user confirmation. Commit the
whole `.circleci/` directory: `info.yml` records the project's ID, and nothing
can recover that ID from the project's name later.

```bash
git add .circleci/
git commit -m "Add CircleCI config"
git push
circleci run watch --sha "$(git rev-parse HEAD)" --failfast
```

`run watch --sha` polls up to 2 minutes for the trigger to create the run,
which is exactly the post-push case. If no run ever appears, the trigger didn't
fire — check Stage 5, then start one directly by definition:

```bash
circleci pipeline run --project <project-slug> --definition-id <definition-id> \
  --branch "$(git rev-parse --abbrev-ref HEAD)" --json   # capture .id as <run-id>
circleci run watch <run-id> --project <project-slug> --failfast
```

Watch exit codes:

- `0` → passed, go to **Wrap-up**
- `1` → a job failed, go to 6c
- `6` → cancelled (ask the user what happened)
- `7` → the config was rejected, including a dynamic-config continuation — fix
  the config and go back to 6b
- `8` → timed out (check whether jobs are stuck)

### 6c — Diagnose and fix (loop)

```bash
circleci run get --failure-report
```

That prints condensed output for every failed step and is built for this — it
is the first thing to run on a red run. Drill further when you need more:

```bash
circleci run get --json --jq '.workflows[].jobs[] | select(.current_outcome=="failed") | {name,id}'
circleci job output list <job-id>                      # per-step logs
circleci job output get <job-id> --step-num <n>         # one step in full
circleci testresult list <job-id>                       # failed tests only
```

Read the failure, identify the root cause, edit `.circleci/config.yml`,
explain the change briefly, then loop back to 6b. Common fixes:

| Symptom | Fix |
|---|---|
| `Missing script: "test"` | Replace `npm test` with `npm run build` |
| Command not found | Add install step or use a different Docker image |
| Test failures | Verify test command matches repo's actual test runner |
| Permission denied | `chmod +x` the script, or switch to a non-root image |
| Config schema error | Fix YAML per `circleci config validate` output |
| Missing env var | Add it with `circleci envvar set <NAME> <value>` |

Repeat 6b–6c until exit `0`.

---

## Wrap-up

```bash
circleci run open <run-id>   # open the passing run in the browser (UUID, not a run number)
```

Tell the user:

- The trigger from Stage 5 means **future pushes fire automatically** — no
  manual `pipeline run` needed.
- Day-to-day operation from here (watch a run, read failing logs and tests,
  rerun) is the **circleci-cli** skill.
- Suggested next steps (offer as a question):

```
AskUserQuestion(
  "What would you like to set up next?",
  header: "Next steps",
  multiSelect: true,
  options: [
    { label: "Secrets / env vars",  description: "Store API keys safely with circleci envvar or contexts" },
    { label: "Test parallelism",    description: "Split tests across multiple containers to go faster" },
    { label: "Dependency caching",  description: "Cache node_modules / pip / gradle to speed up builds" },
    { label: "Orbs",                description: "Reusable config packages for common tools (AWS, Docker, etc.)" }
  ]
)
```

Then help with whatever they select.

---

## General guidance

- **Run CLI checks before asking.** If you can determine the answer yourself
  (auth status, org list, project list, file existence), do it — don't ask the
  user, and never ask them to look something up in the web app.
- **Keep state.** Track org slug, org UUID, project slug, project UUID,
  pipeline definition ID, and repository ID once discovered.
- **Use `--json`/`--jq`** on commands that return IDs so values are easy to
  extract. `circleci api` supports `--jq` too.
- **Don't invent commands or URLs.** Check `circleci <group> --help` before
  using a subcommand or flag you haven't verified. There is no `circleci logs`,
  no `project delete`, and no org-setup page to link to.
- **`circleci api <path>`** resolves relative to `/api/v3`; a path starting with
  `api` is sent as given (which is why the v2 calls above are spelled out in
  full). Reach for it only where no command covers what you need — as in Stages
  2, 3 and 5 here.
- **On failure**, surface the raw error, diagnose it, and propose a fix before
  retrying. Auth errors → `circleci auth login`. 404s → check the project slug.
- **For Bitbucket/OAuth-only/standalone orgs, central config, URL orbs, or
  teardown**, consult `references/org-and-pipeline-types.md`.
