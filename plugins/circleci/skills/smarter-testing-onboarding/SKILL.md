---
name: circleci-smarter-testing-onboarding
description: Onboard a project onto CircleCI Smarter Testing — write `.circleci/test-suites.yml`, replace the raw test step (or legacy `circleci tests glob`/`split`/`run`) with `circleci testsuite run`, validate with `circleci testsuite doctor`, make sure the free features work (static test splitting, rerun only failed tests, test uploads), then ask if any credit-charged features should be enabled (test impact analysis, dynamic test splitting, dynamic parallelism, auto rerun failed tests). Use for first-time setup of Smarter Testing, testsuite, test-suites YAML, or migrating a test step. Not for running (circleci-smarter-testing-run) or debugging a suite that is already onboarded.
---

# CircleCI Smarter Testing Onboarding

Testsuite replaces a raw test command with `.circleci/test-suites.yml` + `circleci testsuite run "<suite name>"`. This skill gets a suite onboarded and doctor-clean, checks the free features work, then enables whichever credit-charged features the user asks for. It covers onboarding only, not running or debugging an already onboarded suite.

Always start with:

```shell
circleci testsuite doctor "<suite name>" --json
```

Doctor's `action_items` say exactly what's wrong and how to fix it. Apply the fix, rerun doctor, repeat until `checks` all pass. Never run the project's raw test command or the YAML's `discover`/`run` directly to validate — always go through doctor.

- **No config found** — use doctor's starter `test-suites.yml`, adapted to the project's real test runner. If a test step already exists (raw `npm test`/`pytest`/`go test`, or legacy `circleci tests split`/`circleci tests run`), base `discover`/`run` on it rather than inventing a new one.
- **JUnit atoms not matching results** — usually the reporter isn't emitting a `file` attribute per test case. Fix at the source, e.g. `JEST_JUNIT_ADD_FILE_ATTRIBUTE=true` for jest-junit, or `--override-ini=junit_family=xunit1` for pytest.
- Ignore any `next_steps` about test impact analysis, dynamic test splitting, or auto-rerun until the user has chosen features below.

Once doctor is clean: replace the old test step in `.circleci/config.yml` with `circleci testsuite run "<suite name>"`, and remove now-redundant legacy test-split steps. Test results are uploaded either by a `store_test_results` job step pointed at the directory of `outputs.junit`, or by `options: store-test-results: true` in `test-suites.yml`, which replaces that step. Use one or the other, never both.

## Smarter Testing features

Smarter Testing has free features, which come with onboarding, and credit-charged features, which the user opts into. The full list is in the [Smarter Testing overview](https://circleci.com/docs/guides/test/smarter-testing-overview/).

### Free, with every suite

Make sure these work once doctor is clean, and tell the user they have them:

- **Static test splitting** — with `parallelism` set on the test job, tests are split across the nodes using timing data from previous runs. Needs no option; check the job's `parallelism` is kept when replacing the old test step.
- **Rerun only failed tests** — rerunning a workflow from failed reruns only the tests that failed. Needs nothing beyond `circleci testsuite run`.
- **Test uploads** — uploaded results show on the job's Tests tab and feed Test Insights. Needs `store_test_results` or `options: store-test-results: true`, as above.

### Credit-charged, opt in

Local runs are free. In CI, these count test atoms toward the plan's monthly allowance, with a charge above it of 3,000 credits per 100,000 test atoms:

| Plan        | Test atoms included per month |
|-------------|-------------------------------|
| Free        | 1,000                         |
| Performance | 10,000                        |
| Scale       | 100,000                       |

Each `circleci testsuite run` in a CI job with any of them enabled counts its discovered test atoms once, however many are enabled and whatever the parallelism. Running the suite locally never costs anything, even though test impact analysis and auto-rerun apply to local runs too; dynamic test splitting and dynamic parallelism only apply in CI. Tell the user both before they choose.

Ask the user which of these they want (don't assume any):

- **Test impact analysis** — learns which source files impact which tests from coverage, then runs only the tests impacted by a change. Needs an `analysis` command in the suite.
- **Dynamic test splitting** — distributes tests across parallel nodes from a shared queue as they run, so no node sits idle.
- **Dynamic parallelism** (experimental) — sets the test job's parallelism when the pipeline runs, from the selected tests or a target duration per node.
- **Auto-rerun failed tests** — retries failed tests in the same run until they pass or hit the limit.

For each feature the user wants:

1. Apply the `options:` snippet from doctor's `next_steps` (`test-impact-analysis: true`, `dynamic-test-splitting: true`, `max-auto-rerun: <0-10>`).
2. Rerun doctor — fix whatever it flags (e.g. missing `file-mapper` when atoms aren't files, missing job `parallelism` for splitting) and repeat until clean.
3. For test impact analysis specifically, once clean, seed initial data once — the one legitimate non-doctor use of `testsuite run` during setup:
   ```shell
   circleci testsuite run "<suite name>" --analyze-tests=impacted
   ```

Once test impact analysis is enabled and seeded, recommend the user replace their everyday local test command (`npm test`, `pytest`, `go test`, etc.) with `circleci testsuite run "<suite name>"`, which selects only the tests their changes impact, same as CI. Running the suite from then on, including when to fall back to `--local`, is owned by `circleci-smarter-testing-run`.

## Guardrails

- Only enable the features the user actually asked for — don't turn on test impact analysis, dynamic test splitting, dynamic parallelism, or auto-rerun speculatively.
- `circleci testsuite doctor "<suite name>"` is the only command that executes tests during setup, except the one-time seed step and the dev-loop recommendation above.
- No secrets in `test-suites.yml` — use contexts/env vars. Don't commit local impact data under `.circleci/`.
- Hand off CLI install/auth issues to `circleci-cli`, other config/caching/workspace work to `circleci-config`, and CI failures after a doctor-clean config to `circleci-builds`.

## Output Contract

Remove extraneous files created during setup. Report the free features in place, which credit-charged features were enabled, files changed, the final doctor output, and any blocked prerequisites.
