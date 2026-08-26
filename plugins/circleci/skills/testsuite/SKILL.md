---
name: circleci-testsuite
description: Onboard a project onto CircleCI's testsuite (`.circleci/test-suites.yml` + `circleci testsuite run`), or migrate off legacy `circleci tests split`/raw test commands onto it. Initial setup for smarter testing features. Driven entirely by `circleci testsuite doctor`. Use for testsuite, test-suites YAML, discover/run commands, JUnit wiring, or migrating an existing test step. For test impact analysis, dynamic test splitting, or auto-rerun, use the circleci-smarter-testing skill instead once testsuite is set up.
---

# CircleCI Testsuite

Testsuite replaces a raw test command with `.circleci/test-suites.yml` + `circleci testsuite run "<suite name>"`. This skill only gets a suite onboarded and doctor-clean — it does not enable Smarter Testing's paid features (test impact analysis, dynamic test splitting). Hand those to `circleci-smarter-testing` once this finishes.

Always start with:

```shell
circleci testsuite doctor "<suite name>" --json
```

Doctor's `action_items` say exactly what's wrong and how to fix it. Apply the fix, rerun doctor, repeat until `checks` all pass. Never run the project's raw test command or the YAML's `discover`/`run` directly to validate — always go through doctor.

- **No config found** — use doctor's starter `test-suites.yml`, adapted to the project's real test runner. If a test step already exists (raw `npm test`/`pytest`/`go test`, or legacy `circleci tests split`/`circleci tests run`), base `discover`/`run` on it rather than inventing a new one.
- **JUnit atoms not matching results** — usually the reporter isn't emitting a `file` attribute per test case. Fix at the source, e.g. `JEST_JUNIT_ADD_FILE_ATTRIBUTE=true` for jest-junit, or `--override-ini=junit_family=xunit1` for pytest.
- Ignore any `next_steps` about test impact analysis, dynamic test splitting, auto-rerun, or `store-test-results` — paid features, out of scope here, owned by `circleci-smarter-testing`.

Once doctor is clean: replace the old test step in `.circleci/config.yml` with `circleci testsuite run "<suite name>"`, and remove now-redundant legacy test-split steps. Leave any existing `store_test_results` job step as-is — `circleci-smarter-testing` replaces it later with `options: store-test-results: true`. Tell the user testsuite is onboarded and that `circleci-smarter-testing` can add test impact analysis, dynamic test splitting, or auto-rerun on top.

## Guardrails

- Do not add any `options:` (`store-test-results`, `test-impact-analysis`, `dynamic-test-splitting`, `max-auto-rerun`) — all Smarter Testing features, paid and free, are out of scope for this skill.
- No secrets in `test-suites.yml` — use contexts/env vars.
- Hand off CLI install/auth issues to `circleci-cli`, other config/caching/workspace work to `circleci-config`, and CI failures after a doctor-clean config to `circleci-builds`.

## Output Contract

Remove extraneous files created during setup. Report the runner, files changed, the final doctor output, and any blocked prerequisites.
