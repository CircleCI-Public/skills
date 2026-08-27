---
name: circleci-smarter-testing
description: Enable CircleCI Smarter Testing features (test impact analysis, dynamic test splitting, auto-rerun failed tests) on top of an existing testsuite, driven by `circleci testsuite doctor`. Use for test impact analysis, dynamic test splitting, auto-rerun, or "smarter testing". Requires `.circleci/test-suites.yml` to already exist — if it doesn't, use the circleci-testsuite skill first.
---

# CircleCI Smarter Testing

These features may require a paid plan or be in beta — verify current availability and pricing before promising them to the user.

Builds on top of testsuite. Ask the user which of these they want (don't assume all three):

- **Test impact analysis** — run only the tests affected by a change.
- **Dynamic test splitting** — evenly distribute tests across parallel nodes.
- **Auto-rerun failed tests** — automatically retry failures in the same step.

Start with:

```shell
circleci testsuite doctor "<suite name>" --json
```

If `.circleci/test-suites.yml` doesn't exist, or `checks` don't all pass, stop and send the user to `circleci-testsuite` first — never enable these options against a suite that isn't doctor-clean.

**Set `options: store-test-results: true`** alongside whichever features the user enables, if it isn't already set — it's a separate recommended setting, required for some feature to work. It replaces any classic `store_test_results` job step. Rerun doctor to confirm.

For each feature the user wants:

1. Apply the `options:` snippet from doctor's `next_steps` (`test-impact-analysis: true`, `dynamic-test-splitting: true`, `max-auto-rerun: <0-10>`).
2. Rerun doctor — fix whatever it flags (e.g. missing `file-mapper` when atoms aren't files, missing job `parallelism` for splitting) and repeat until clean.
3. For test impact analysis specifically, once clean, seed initial data once — the one legitimate non-doctor use of `testsuite run` during setup:
   ```shell
   circleci testsuite run "<suite name>" --analyze-tests=impacted
   ```

Once test impact analysis is enabled and seeded, recommend the user replace their everyday local test command (`npm test`, `pytest`, `go test`, etc.) with `circleci testsuite run "<suite name>" --local` — it uses locally stored impact data, so local runs select only the tests impacted by uncommitted changes, same as CI.

## Guardrails

- Only enable the features the user actually asked for — don't turn on test impact analysis, dynamic test splitting, or auto-rerun speculatively.
- `circleci testsuite doctor "<suite name>"` is the only command that executes tests during setup, except the one-time seed step and the `--local` dev-loop recommendation above.
- No secrets in `test-suites.yml` — use contexts/env vars. Don't commit local impact data under `.circleci/`.
- Hand off CLI install/auth issues to `circleci-cli`, other config/caching/workspace work to `circleci-config`, and CI failures after a doctor-clean config to `circleci-builds`.

## Output Contract

Remove extraneous files created during setup. Report which features were enabled, files changed, the final doctor output, and any blocked prerequisites.
