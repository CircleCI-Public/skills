# Deploy markers

Marker commands are `circleci run release …`, provided by
[task-agent-subcommand-release](https://github.com/circleci/task-agent-subcommand-release)
and compiled into build-agent. Flags below are verified against `cmd/subcommand/plan/plan.go`
and `cmd/subcommand/update/update.go`.

## Command reference

### `circleci run release plan [plan-name]`

`plan-name` is positional and defaults to `default`.

| Flag | Required | Default | Notes |
|------|----------|---------|-------|
| `--target-version` | **yes** | — | The version being released |
| `--environment-name` | no | — | Omittable only if the org has exactly one environment |
| `--component-name` | no | — | Omittable only if the project has exactly one component |
| `--namespace` | no | `default` | Omit the flag entirely when the repo has no namespace |
| `--release-strategy` | no | `deployment` | Omit unless changing it |
| `--rollback` | no | `false` | Marks the release as a rollback; rollback pipelines only |

### `circleci run release update [plan-name]`

| Flag | Required | Notes |
|------|----------|-------|
| `--status` | **yes** | `RUNNING`, `SUCCESS`, `FAILED`, `CANCELED` |
| `--failure-reason` | no | Free text, pairs with `FAILED` |
| `--keep-target-version-live` | no | Keeps the version live despite failure or cancellation |

The plan name passed to `update` must match the one passed to `plan`.

## Step shapes to emit

Match these exactly, so the result is consistent with what the guided setup in the web app
produces for the same repository.

```yaml
- run:
    name: Plan deployment
    command: |
      circleci run release plan ${DEPLOY_NAME} \
        --environment-name="staging" \
        --namespace="my-namespace" \
        --component-name="my-service" \
        --target-version="${APP_VERSION}"
```

Omit the `--namespace` line entirely when there is no namespace; do not pass an empty
string. Flags use the `--flag="value"` form.

```yaml
- run:
    name: Update deployment status to running
    command: circleci run release update ${DEPLOY_NAME} --status=RUNNING
```

**Without validation** — emit both terminal steps after the deploy step:

```yaml
- run:
    name: Update deployment status to success
    command: circleci run release update ${DEPLOY_NAME} --status=SUCCESS
    when: on_success
- run:
    name: Update deployment status to failed
    command: circleci run release update ${DEPLOY_NAME} --status=FAILED
    when: on_fail
```

**With validation** — emit only the failure terminal step on the deploy job. **Do not**
add the `on_success` / `--status=SUCCESS` step. The paired `type: release` job owns
success: CircleCI marks the release `SUCCESS` when the validation window completes
without a failing signal (or when the user promotes it). Marking `SUCCESS` from the
deploy job first leaves the release terminal while validation is still `RUNNING`, and the
deploys UI shows a green check during an active validation window. See
`validation.md`.

```yaml
- run:
    name: Update deployment status to failed
    command: circleci run release update ${DEPLOY_NAME} --status=FAILED
    when: on_fail
```

The `when: on_fail` step is always required on the deploy job — omitting it leaves failed
deploys stuck in `RUNNING` forever.

### Placement

`plan` goes immediately **before** the deploying step, `RUNNING` immediately **after** it,
and the two terminal steps at the end of the job:

```text
plan → <the step that performs the deploy> → RUNNING → SUCCESS / FAILED
```

Markers bracket the step that **performs** the deploy, not the setup steps around it —
`aws-cli/setup`, `kubernetes/install`, and `aws-eks/update_kubeconfig_with_authenticator`
prepare for a deploy, they do not perform one.

`RUNNING` landing after the deploy step reads oddly, and it is deliberate: this is the
order the guided setup in the web app produces, and matching it is the point of this
section. Do not "correct" it to `plan → RUNNING → deploy`.

### Deploy name

For a single deployment in a job, use `"${CIRCLE_JOB}"` (quoted, because of the `${`).
For multiple deployments in one job, give each a unique literal name such as
`api-staging` and `web-staging`.

> **If validation is in scope, do not use `"${CIRCLE_JOB}"`.** The plan name has to be
> repeated verbatim as `plan_name` on a `type: release` job, and a literal is far easier
> to match than an expression resolved at runtime. Pick a stable name like
> `component-release` and use it in both places. See `validation.md`.

## Detection: skip, upgrade, or inject

This classification is what you **report and recommend** in step 1 of
`../SKILL.md`, not a decision to make silently. "Skip" means "recommend keeping as
is" — the user can still ask you to regenerate it, and that is a legitimate request.

Check in this order.

**Skip** when the job is already fully instrumented:

- it contains both `circleci run release plan` and `circleci run release update`, or
- it uses the **`circleci/deploys` orb** — a `deploys/plan` or `deploys/log` step, with the
  orb declared under `orbs:` as `circleci/deploys@…`. The orb emits the marker commands
  for you, so a job carrying these is instrumented even though it contains no literal
  `circleci run release` text. See the warning below, or
- it has `deploy_markers_mode` set to a non-`OFF` value on a supported orb job (see
  `orbs.md`), or
- it is not a deployment job at all: build, test, lint, publish-without-promotion, or
  anything dry-run (job name containing `dry-run` / `dry_run` / `dryrun`, or a command
  with `--dry-run`).

**Upgrade** when instrumentation is present but incomplete. The important case:

> `circleci deploy init` writes a **single** `circleci run release log` step with
> `$CIRCLE_SHA1` hardcoded. That is a deploy record, not a release lifecycle.

Tooling that treats *any* `circleci run release` occurrence as "already instrumented" will
skip such a job, which leaves log-only markers next to a `validation.enabled` config that
can never work — there is no planned release for validation to attach to. **Do not
replicate that behaviour.** Replace the
log-only step with the full plan/RUNNING/terminal-marker lifecycle and tell the user you
upgraded it. Use plan/RUNNING/SUCCESS/FAILED when validation is out of scope; use
plan/RUNNING/FAILED only (no deploy-job `SUCCESS`) when validation is in scope.

Also upgrade when you find a `plan` with no terminal `update` steps, or `deploy_markers_mode`
explicitly set to `OFF`.

**Inject** otherwise, when the job promotes to a live environment. Signals:

- job name contains `deploy`, `deploying`, `release`, or `releasing`
- commands containing `kubectl`, `helm install`, `helm upgrade`, `terraform apply`,
  `pulumi up`, `cloudformation deploy`, `aws deploy`, `./deploy`, or `/deploy`
- a deploy script at any path, even when you cannot read its body

Treat a job whose name contains `build`, `test`, `lint`, or `format-check` as not a
deployment unless it also contains `deploy`.

### Do not inject on top of the `circleci/deploys` orb

A job using `deploys/plan` or `deploys/log` is **already instrumented**. Matching on the
literal string `circleci run release` misses it, so a naive scan classifies the job as
"absent" and injects raw markers alongside the orb's — two plans for one deployment, and
the second orphans the first.

If the repo uses the orb and the instrumentation is incomplete, say so and let the user
choose: extend it in orb form, or replace the orb steps with raw markers. Do not mix the
two in one job.

### Kubernetes: ask before instrumenting

**`kubectl` and `helm` are ambiguous signals.** They mean the job deploys to Kubernetes,
which splits into two setups that need *different* markers:

| Setup | What to emit |
|-------|--------------|
| **CircleCI release agent** (Kubernetes Cluster environment integration) | `plan` **only**, plus a `type: release` job. **No `update` steps at all** |
| **Agentless** (`kubectl apply` / `helm upgrade` with no agent) | The normal full lifecycle: plan, RUNNING, and the terminal steps |

The official guidance is explicit that `circleci run release update` is for deploy markers
only, and that with the release agent you must **not** use the `update` commands — the
agent reports status itself. Emitting them anyway means two writers fighting over one
release's status.

You cannot tell which setup applies by reading the repo: the agent runs in the cluster,
not in the config. So **ask**. Useful hints to offer, none conclusive on their own: a
`circleci.com/version` label on the manifests, Argo Rollouts resources, or an existing
`release-strategy` setting all suggest the agent.

When the agent is in use, the `on_fail` FAILED step is **not** required, which is the one
case where invariant 4 in `verification.md` does not apply.

## Parameter inference

**Read the repository first.** This is the skill's actual advantage over the wizard, and
should be the primary path. Look at deploy scripts, helm charts and values files,
Kubernetes manifests, Terraform variables, Dockerfiles, and existing environment
variables in the config.

Use this ladder only where the repo is genuinely silent.

**`target_version`** — the version identifier only, never a full image tag, and never
`component_name` repeated as a prefix:

1. version-related env vars already used in the job (`APP_VERSION`, `VERSION`, `IMAGE_TAG`,
   `TARGET_VERSION`, `RELEASE_VERSION`)
2. helm chart or release version (`helm upgrade --version`, chart `appVersion`)
3. the version expression inside an image tag — from `myapp-${APP_VERSION}` take
   `${APP_VERSION}`, not the whole string
4. last resort: `"${CIRCLE_TAG}"` when the job deploys from git tags, otherwise
   `"1.0.${CIRCLE_BUILD_NUM}-${CIRCLE_SHA1:0:7}"`

**`namespace`** — omit the field entirely when absent:

1. explicit flags in deploy commands (`helm --namespace`, `kubectl -n`)
2. a job environment variable named `NAMESPACE`, kept as written (`"${NAMESPACE}"`)
3. when several deployments share a job, take each one's namespace from its own steps

**`environment_name`** — from the job or workflow name (`deploy-to-staging` gives
`staging`), the target cluster or account, or branch filters. Falls back to `default`.

**`component_name`** — the service being deployed: the helm release name, the Kubernetes
deployment name, or the image name. Falls back to `"${CIRCLE_PROJECT_REPONAME}"`.

> `component_name` and `environment_name` must match the tags on the monitoring side
> **exactly** — they are exact-match filters. If validation is in scope, settle these
> values now and reuse the same strings in `monitoring.md`.
> Do not let the two sides be typed independently.

## Invariants after editing

Work through `verification.md`, which has the command for each check.
Beyond `circleci config validate` there are six:

1. every original non-marker `run` command is still present
2. there is exactly one `plan` per deployment unit
3. every `update` references a planned deploy name
4. a job with a `plan` has an `on_fail` terminal step; it has an `on_success` /
   `--status=SUCCESS` step only when validation is **not** in scope for that plan name
   (see `validation.md`)
5. a `validation` block has a `type: release` job whose `plan_name` some marker planned
6. when validation is in scope for a plan name, no marker job emits
   `--status=SUCCESS` for that plan — success is delegated to the release job

Every one of these compiles cleanly when broken, which is the point. The first exists
because silently dropping a step while rewriting YAML is the characteristic failure of
generated config, and a passing `circleci config validate` says nothing about it. The last
catches the mismatch that fails a release job at run time with `Planned release not found`.

If the `circleci` CLI is absent you can still run all six — they need only `git` and
`grep`. Say that compilation went unverified rather than reporting a clean pass.
