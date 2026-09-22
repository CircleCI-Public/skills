# Orb-native deploy markers

Five AWS orb jobs accept deploy-marker parameters natively. When a repo deploys through
one of them, prefer the orb parameters over hand-written `circleci run release` steps.

Re-check the versions below before trusting them; orbs ship independently of this skill.

## Supported jobs

| Orb | Job | Minimum marker-capable versions | Latest | `namespace` param |
|-----|-----|----------------------------------|--------|-------------------|
| `circleci/aws-eks` | `update_container_image` | 3.1.0, 4.1.1 | 4.1.1 | yes |
| `circleci/aws-ecs` | `deploy_service_update` | 3.3.0, 4.2.0, 6.1.0, 7.3.0, 8.1.2 | 8.1.2 | no |
| `circleci/aws-code-deploy` | `deploy` | 3.0.2 | 3.0.2 | no |
| `circleci/aws-elastic-beanstalk` | `deploy` | 3.0.1 | 3.0.1 | yes |
| `circleci/aws-lambda` | `update_lambda_function` | 1.0.1 | 1.0.1 | no |

Only `aws-eks` and `aws-elastic-beanstalk` declare `deploy_markers_namespace`. Passing it
to the other three fails compilation with `Unexpected argument(s)`.

The minimums are per-major, and several are patch-level because the first release of a
major lacked `component_name` / `environment_name`. Notable cases: `aws-eks` 3.1.0 is a
backport of 4.1.0; `aws-ecs` 5.x has no backport at all; `aws-code-deploy` 3.0.0 has no
markers and 3.0.1 has only `mode` / `deploy_name` / `target_version`.

## Two hard constraints

**Orb-native markers are declared on orb jobs, so they only work at the workflow level.**
A `- aws-eks/update_container_image:` entry appearing as a *step inside a job body* cannot
carry marker parameters. If the repo invokes the orb that way, fall back to raw
`circleci run release` steps from `markers.md`.

**Never use orb-native marker parameters in a rollback job.** Rollback jobs are ordinary
jobs, not orb job invocations. Use raw marker commands there.

## Parameter naming: one kebab-case exception

Every marker-capable orb version uses snake_case parameters, except **`aws-ecs` major 3**,
which uses kebab-case for both the job name and the parameters:

- `aws-ecs` 3.x: job `deploy-service-update`, parameter `deploy-markers-mode`
- everything else: job `deploy_service_update`, parameter `deploy_markers_mode`

CircleCI switched to snake_case from `aws-ecs` major 4 onward. When *matching* an existing
step, fold `-` and `_` so either spelling matches. When *emitting*, keep the author's
original spelling of the job name and use the convention that matches the declared version.

## What to emit

Set the mode at the workflow level:

```yaml
workflows:
  deploy:
    jobs:
      - aws-eks/update_container_image:
          deploy_markers_mode: PLAN_AND_UPDATE
          deploy_markers_target_version: "${APP_VERSION}"
          deploy_markers_component_name: my-service
          deploy_markers_environment_name: staging
```

`PLAN_AND_UPDATE` is the default mode (`DefaultOrbNativeMarkerMode`). A bare job name in
the workflow list becomes a mapping when you add the parameter.

Skip a job that already has the mode set to a non-empty, non-`OFF` value. Overwrite it
when the value is `OFF`.

Leave the entry alone when its parameter node is a YAML alias or any other non-mapping
node — overwriting would discard real parameters.

## Version upgrades

When the declared version is below the minimum, upgrade within the same major if that
major has a backport (`aws-eks@3.0.0` becomes `3.1.0`), otherwise to `LatestVersion`.

Two guards, both worth preserving:

- **Do not upgrade if the config already contains raw `circleci run release` markers.** The
  orb's `PLAN_AND_UPDATE` default would double up with them, producing two plans for one
  deployment.
- **Do not upgrade an orb whose marker-capable job the config never invokes.** Bumping
  across majors for an unused feature can break unrelated parameters.

Scope the rewrite to the declaration's own line. A full YAML round-trip reformats the
whole document, and a document-wide string replace also rewrites the version inside
`run:` commands, comments, and parameter defaults.
