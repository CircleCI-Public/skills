# Test Results Reference

Use this reference when configuring test metadata. Tests run with `circleci testsuite run`; to set that up or migrate a raw or legacy test step, hand off to `circleci-smarter-testing-onboarding`.

Sources:
- [Getting started with Smarter Testing](https://circleci.com/docs/guides/test/getting-started-with-smarter-testing/)
- [Testsuite configuration reference](https://circleci.com/docs/guides/test/testsuite-configuration-reference/)

## Goals

- Upload valid JUnit XML so CircleCI can power the Tests tab, flaky test detection, timing-based splitting, and other testing capabilities.
- Make test parallelism measurable before increasing it.

## Baseline Requirements

- Run tests with `circleci testsuite run`. Its default and generated suites upload results with `options: store-test-results: true`; use a `store_test_results` step only for a suite that doesn't set it, never both.
- Ensure the JUnit XML the suite writes to `outputs.junit` includes `file`, `classname`, or `name` attributes.
- Keep a copy of the raw XML as an artifact when debugging test metadata issues.

## Failure Modes To Check

- The test job runs a raw test command (`npm test`, `pytest`, `go test`) or the legacy `circleci tests glob`/`split`/`run` instead of `circleci testsuite run`.
- Results upload twice, from both `store-test-results: true` and a `store_test_results` step.
- A suite without `store-test-results: true` has no `store_test_results` step, or the step points somewhere other than the directory of `outputs.junit`.
- The XML uploads, but lacks `file`, `classname`, or `name`, so testing features behave unexpectedly.
- Parallel reruns leave some nodes with no tests; create required directories before persistence so downstream steps do not fail on empty reruns.

## Common Fixes To Suggest

- Replace the test step with `circleci testsuite run "<suite name>"` via `circleci-smarter-testing-onboarding`.
- Keep one upload: `options: store-test-results: true` in the suite, or a `store_test_results` step pointed at the directory of `outputs.junit`.
- Fix missing attributes at the reporter, e.g. `JEST_JUNIT_ADD_FILE_ATTRIBUTE=true` for jest-junit, then rerun `circleci testsuite doctor "<suite name>"`.
- Upload the same XML with `store_artifacts` while debugging metadata issues.
- Add `--verbose` to `circleci testsuite run` when debugging.
