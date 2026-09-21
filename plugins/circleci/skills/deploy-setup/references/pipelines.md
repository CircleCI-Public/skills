# Deploy and rollback pipelines

Two extra config files, each registered as its own pipeline definition on the project:

- `.circleci/deploy.yml` — triggered from the Deploys UI to deploy a chosen version
- `.circleci/rollback.yml` — triggered on rollback, manually or by auto-rollback

Both are derived from the deploy jobs already in `.circleci/config.yml`.

## The one thing that is easy to get wrong

Values selected in the Deploys UI arrive under the **`pipeline.deploy`** namespace:

```yaml
environment:
  COMPONENT_NAME: "<< pipeline.deploy.component_name >>"
  ENVIRONMENT_NAME: "<< pipeline.deploy.environment_name >>"
  NAMESPACE: "<< pipeline.deploy.namespace >>"
  TARGET_VERSION: "<< pipeline.deploy.target_version >>"
```

Two more exist and are easy to miss, both aimed at rollback:

| Value | Meaning |
|-------|---------|
| `pipeline.deploy.current_version` | The version being rolled back **from** |
| `pipeline.deploy.reason` | The free-text reason entered in the rollback dialog |

Neither is required, but a rollback job that logs `reason` and reports `current_version`
gives a much more readable audit trail than one that only knows its target.

There is no `pipeline.parameters.component_name`. Writing that fails compilation with
`Unknown variable(s)`. Always quote the expressions.

A job's own `parameters:` block is unrelated — keep any `<< parameters.x >>` references
exactly as written.

## Rollback job shape

One rollback job per deploy job, named `{deploy-job-name}-rollback`.

```yaml
deploy-staging-rollback:
  docker:
    - image: cimg/base:stable
  environment:
    COMPONENT_NAME: "<< pipeline.deploy.component_name >>"
    ENVIRONMENT_NAME: "<< pipeline.deploy.environment_name >>"
    NAMESPACE: "<< pipeline.deploy.namespace >>"
    TARGET_VERSION: "<< pipeline.deploy.target_version >>"
  steps:
    - checkout
    - run:
        name: Plan rollback
        command: |
          circleci run release plan deploy-staging-rollback \
            --environment-name="${ENVIRONMENT_NAME}" \
            --namespace="${NAMESPACE}" \
            --component-name="${COMPONENT_NAME}" \
            --target-version="${TARGET_VERSION}" \
            --rollback
    - run:
        name: Perform rollback
        command: |
          helm upgrade myapp ./chart --set image.tag=${TARGET_VERSION}
    - run:
        name: Update deployment status to running
        command: circleci run release update deploy-staging-rollback --status=RUNNING
    - run:
        name: Update deployment status to success
        command: circleci run release update deploy-staging-rollback --status=SUCCESS
        when: on_success
    - run:
        name: Update deployment status to failed
        command: circleci run release update deploy-staging-rollback --status=FAILED
        when: on_fail
```

Rules that matter:

- **Always pass an explicit plan name.** Use the rollback job name. Never `"${CIRCLE_JOB}"`
  and never omit it.
- **`--rollback` goes on the plan command.**
- **Never use orb-native marker parameters here.** Those work only on orb jobs; see
  `orbs.md`.
- **Preserve executors, orb steps, and custom commands** from the source deploy job. If the
  deploy job uses `executor: <name>`, keep the reference and carry the executor definition
  into the assembled file. Copy setup steps such as `aws-cli/setup`,
  `helm/install_helm_client`, or a custom `load-version` verbatim — do not reimplement orb
  functionality as plain `run` steps, because the assembler only copies orbs and commands
  that the generated job actually references as steps.
- **Do not carry over branch filters.** "Preserve the source job" means executors, orbs and
  steps — not the source workflow's `filters:` / `branches:` block. These pipelines are
  triggered on demand from the Deploys UI, which runs them against the project's default
  branch unless the caller names another one. A `branches: only: main` filter therefore
  looks harmless and then silently yields a workflow with no jobs the first time someone
  deploys from a different branch. Leave the deploy and rollback jobs unfiltered.

### Rolling back means redeploying a version, not "undo"

The rollback step must restore **the version chosen in the Deploys UI**. Replace every
version expression from the deploy job — `${CIRCLE_TAG}`, `${CIRCLE_BUILD_NUM}`,
`${APP_VERSION}` — with `${TARGET_VERSION}`, and re-run the same deployment mechanism
pointed at it.

Prefer `helm upgrade --set image.tag=${TARGET_VERSION}` over implicit "previous revision"
commands like a bare `helm rollback`, unless the deploy job itself uses that pattern. An
implicit rollback ignores the selected version, which is rarely what the user asked for.

When the inverse is genuinely unclear, emit:

```yaml
    - run:
        name: Perform rollback
        command: |
          # TODO: add rollback logic using ${TARGET_VERSION}
```

and tell the user. Never invent a `./rollback.sh` that does not exist.

## Cancel jobs

Each pipeline pairs every deploy or rollback job with a cancel job, so a canceled run does
not leave the release stuck in `RUNNING`:

```yaml
  cancel-deploy-staging-rollback:
    docker:
      - image: cimg/base:stable
    steps:
      - run:
          name: Update planned release to CANCELED
          command: |
            circleci run release update deploy-staging-rollback \
              --status=CANCELED
```

Wired through the `canceled` status of the job it shadows:

```yaml
workflows:
  rollback:
    jobs:
      - deploy-staging-rollback
      - cancel-deploy-staging-rollback:
          requires:
            - deploy-staging-rollback:
              - canceled
```

Naming follows `RollbackJobName` (`<deploy-job>-rollback`) and the `cancel-` prefix.

## Assembly

Each file is standalone: `version`, then `jobs:`, then a single workflow (`deploy` or
`rollback`).

Carry over any `orbs:`, `executors:`, and `commands:` that the generated jobs reference —
a rollback job referencing `executor: my-executor` fails to compile if the definition
stays behind in `config.yml`.

Attach the source job's workflow filters to the primary job in `deploy.yml` so branch and
tag gating is preserved. The cancel job needs no filters; it only waits on cancellation.

### Validation in these pipelines

Each file is its own pipeline with its own workflows, so a `type: release` job in
`config.yml` does **not** cover deploys triggered from the Deploys UI. If the user wants
validation on those too, `deploy.yml` needs its own `type: release` job, with a
`plan_name` matching the plan created by that file's deploy job. See
`validation.md`.

When validation is in scope for a deploy pipeline, apply the same marker rule as in
`markers.md`: the deploy job in `deploy.yml` gets plan/RUNNING/FAILED only —
**no** `--status=SUCCESS` step on the deploy job. Success is delegated to the
`type: release` job. Rollback pipelines are unchanged; they still use SUCCESS/FAILED on the
rollback job itself.

**Do not add validation to `rollback.yml`.** Validating a rollback means a failing signal
can roll back the rollback, which is rarely what anyone wants and is confusing to unpick
during an incident. Leave it out unless the user asks for it explicitly and says why.

## After generating

Validate both files, not just `config.yml`:

```bash
circleci config validate .circleci/deploy.yml
circleci config validate .circleci/rollback.yml
```

Then commit and push **before** registering them. Registration references a config file
path, so a pipeline registered against a file that is not yet on the branch will fail when
triggered. See `api.md`.

These files go through the same review path as the marker changes — a branch and a PR by
default, direct to the default branch only if the user asked. They are production deploy
and rollback definitions, so they are the last thing to push unreviewed. See
`../SKILL.md`.
