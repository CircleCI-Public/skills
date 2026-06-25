# Test Results Reference

Use this reference when configuring test metadata.

Sources:
- [Collect test data](https://circleci.com/docs/collect-test-data/)

## Goals

- Upload valid JUnit XML so CircleCI can power the Tests tab, flaky test detection, timing-based splitting, and other testing capabilities.
- Make test parallelism measurable before increasing it.

## Baseline Requirements

- Use `store_test_results` to upload XML test results.
- Ensure the generated JUnit XML includes `file`, `classname`, or `name` attributes.
- Keep a copy of the raw XML as an artifact when debugging test metadata issues.

## Failure Modes To Check

- `store_test_results` points at the wrong path or directory.
- The XML uploads, but lacks `file`, `classname`, or `name`, so testing features behave unexpectedly.
- Parallel reruns leave some nodes with no tests; create required directories before persistence so downstream steps do not fail on empty reruns.
- Teams rely on artifacts only and never enable `store_test_results`, which blocks Test Insights and testing features.

## Common Fixes To Suggest

- Add or fix `store_test_results`.
- Upload the same XML with `store_artifacts` while debugging metadata issues.
- Add `--verbose` to `circleci run testsuite` when debugging.
