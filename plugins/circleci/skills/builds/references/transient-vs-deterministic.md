# Transient Vs Deterministic Failures Reference

Use this reference when deciding whether a failing CircleCI job should be fixed at the source, rerun automatically, rerun manually, or reported as an external/transient issue.

Sources:
- [Automatic reruns](https://circleci.com/docs/guides/orchestrate/automatic-reruns/)
- [Rerun failed tests](https://circleci.com/docs/guides/test/rerun-failed-tests/)

## Classification Goal

- Treat retries as a targeted mitigation for temporary failure modes.
- Treat deterministic failures as defects to fix in code, config, environment setup, or test data.
- Make the classification explicit before suggesting reruns, flaky-test workflows, or automatic retry behavior.

## Likely Transient Signals

- Network timeouts to external package registries or APIs.
- Temporary infrastructure instability.
- Spot/interruption-style executor loss.
- Flaky tests with a history of passing unchanged on rerun. `circleci testresult flaky`
  lists the project's known flakes, so check a failing test's name against it.
- A rerun on the same commit succeeds without any code or config change.

## Likely Deterministic Signals

- Config validation errors or missing keys.
- Repeatable dependency install failures caused by bad versions, paths, or credentials.
- Consistent test assertion failures on the same commit.
- Missing files, wrong working directories, or broken environment assumptions.
- Cache or workspace path mismatches that fail the same way every time.

## Stopped By The Plan

Neither transient nor a defect: the job never ran. CircleCI refused to start it,
so it has no logs, no test results and no resource usage. Its only step is a
cancelled placeholder named `Error: Task information unavailable`, and the
reason is in the job's errors (`circleci job get <job-id>`, under `## Errors`).

| Error code | Means | Tell the user |
| --- | --- | --- |
| `free-plan-no-credits-available` | The org's plan has no credits left. | Quote the message. The job runs once the org upgrades its plan or its credits refill; nothing in the code or config is wrong. The CLI cannot say when a refill is due, so do not guess a date. |
| `resource-class-not-in-plan` | The job asks for a resource class the plan does not include, or one that does not exist. The message names the class and image. | Check the class name in the config first: a typo gets the same error. If the name is right, either choose a class the plan includes or upgrade. This one can be fixed in the config. |
| `execution-authorization-unknown` | The check that decides whether the job may run did not reach an answer. It is not documented, so go by its message rather than its code. | Quote the message. Do not say the org is out of credits or needs an upgrade on the strength of this code alone. |

- Report the reason and stop. Do not rerun: the job is stopped the same way until
  the plan changes. If the user asked for a rerun, say so before doing it.
- Changing the plan is for whoever manages the org's billing. Do not attempt it.
- Jobs downstream of a stopped job never ran either, and `circleci job get` on
  them fails. They are not separate failures.
- Mention an upgrade only when a job's errors say so. A job that ran its steps
  and failed is never a plan problem, however quickly it failed.

## Rerun Guidance

- Prefer manual investigation first when the first occurrence is ambiguous.
- Recommend automatic step reruns only for steps with a well-understood transient failure pattern.
- Recommend automatic workflow reruns only when rerunning failed jobs is materially cheaper than re-executing the entire workflow and the failure mode is plausibly temporary.
- For flaky tests, prefer `circleci testsuite run` plus rerun workflow from failed or auto rerun failed tests over rerunning entire workflows.

## Guardrails

- Do not use retries to mask deterministic test or deploy failures.
- Do not introduce blanket reruns across a whole workflow without evidence that the dominant failures are transient.
- Keep retry counts low and explain what symptom they are targeting.
- If the same commit fails repeatedly after reruns, stop escalating retries and fix the root cause.

## Diagnostic Workflow

1. Check whether the failure reproduces on the same commit.
2. Identify whether the first failing step points to config, environment, dependency, test, or external service instability.
3. If tests are involved, check whether rerun-failed-tests prerequisites are configured before recommending that feature.
4. If proposing auto-reruns, scope them to the smallest failing unit that matches the observed transient pattern.

## Common Fixes To Suggest

- Add low-count step reruns for a flaky external dependency fetch step.
- Use rerun workflow from failed or auto rerun failed tests for known flaky test suites once JUnit metadata and `circleci testsuite run` are configured.
- Remove retries and fix environment parity when failures are deterministic.
- Report external outages clearly when the pipeline itself is healthy but a dependency is not.
