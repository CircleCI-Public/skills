# Which command covers each API endpoint

Check here before reaching for `circleci api`. Every command below takes `--json` and
`--jq`, so output shape is never a reason to use the raw API, and each one infers the
project or organization from the git remote.

Paths are relative to `/api/v3`, which is what `circleci api` assumes when a path has no
prefix. An execution of a pipeline is a **run** (`/runs`); `/pipelines` holds pipeline
*definitions*, the checkout source and config location a run executes.

## Runs, workflows and jobs

| What you want | Command | Endpoint |
|---|---|---|
| Recent runs for a project | `circleci run list [--branch <b>] [--project gh/org/repo]` | `POST /runs/search` |
| Your own recent runs, every project | `circleci my runs` | `GET /runs?filter[user_id]=me` |
| One run and its workflows | `circleci run get <run-id>` | `GET /runs/{id}` |
| Workflows of a run | `circleci workflow list <run-id>` | `GET /workflows` |
| One workflow and its jobs | `circleci workflow get <workflow-id>` (`--json`: `jobs[]`) | `GET /workflows/{id}`, `GET /jobs?filter[workflow_id]=` |
| Rerun or cancel a workflow | `circleci workflow rerun <workflow-id>`, `circleci workflow cancel <workflow-id>` | `POST /workflows/{id}/rerun`, `POST /workflows/{id}/cancel` |
| One job | `circleci job get <job-id>` | `GET /jobs/{id}` |
| Step output | `circleci job output list <job-id>`, `circleci job output get <job-id> --step-num <n>` | `GET /jobs/{id}/stdout` |
| Artifacts | `circleci job artifact <job-id>` | `GET /jobs/{id}/artifacts` |
| Test results | `circleci testresult list <job-id>` | `GET /jobs/{id}/tests` |
| CPU and memory use | `circleci job resource-usage get <job-id>` | `GET /jobs/{id}/resource-usage` |

Run ids accept a UUID or a run number. Workflow and job ids are UUIDs, printed by
`circleci run get --json` and `circleci workflow get --json`.

## Projects, organizations and settings

| What you want | Command | Endpoint |
|---|---|---|
| Who am I | `circleci auth me` | `GET /users` |
| Organizations you belong to | `circleci org list` | `GET /orgs` |
| Organization settings | `circleci org setting list` | `GET /orgs/{id}/settings` |
| Projects | `circleci project list`, `circleci project get` | `GET /projects`, `GET /projects/{id}` |
| Project settings | `circleci project setting list` | `GET /projects/{id}/settings` |
| Pipeline definitions | `circleci pipeline list` | `GET /pipelines` |
| Triggers on a definition | `circleci project trigger list --pipeline-definition-id <id>` (ids from `pipeline list`) | `GET /triggers` |
| Project env vars | `circleci envvar list` | v2 `GET /api/v2/project/{slug}/envvar` |
| Contexts and their secrets | `circleci context list`, `circleci context secret list <context>` | `GET /contexts`, `GET /contexts/{id}/env-vars` |
| Deploys | `circleci deploy list` | `GET /deploy/deployments` |
| Deploy components and environments | `circleci deploy component list`, `circleci deploy environment list` | `GET /deploy/components`, `GET /deploy/environments` |

## What still needs `circleci api`

No command covers `usage/exports`, `analysis/*` and `metric/*` (usage, credit, job and test
analytics), `notification/*` or `audit/*`, nor the `provider/*` endpoints beyond what
`circleci onboard` does with them.

`{project-id}` and `{org-id}` in a path are filled in from the git remote, so
`circleci api 'orgs/{org-id}/…'` works from inside a checkout. Outside one, pass the ids
literally.
