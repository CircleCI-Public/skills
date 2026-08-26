---
name: circleci-smarter-testing
description: Onboard onto CircleCI Smarter Testing (testsuite) with `.circleci/test-suites.yml`, driven entirely by `circleci testsuite doctor`. Use for Smarter Testing, testsuite, test-suites YAML, test impact analysis, dynamic test splitting, auto rerun failed tests, or migrating raw test commands.
---

# CircleCI Smarter Testing

Run this first, before anything else, even if `.circleci/test-suites.yml` doesn't exist yet:

```shell
circleci testsuite doctor "<suite name>"
```

Doctor is self-documenting. Its `action_items` tell you exactly what's wrong and how to fix it (including YAML snippets), and its `next_steps` tell you what to do next once everything passes. Read its output and follow it:

1. **No config found** — doctor's action item includes a starter `test-suites.yml` example. Create `.circleci/test-suites.yml` using it, adapted to the project's real test runner and commands.
2. **A check fails** (invalid config, `discover` or `run` command errors, JUnit atoms not matching, missing `file-mapper`, etc.) — apply exactly what the action item's `content` says, then run doctor again.
   - "JUnit output is missing results for some test atoms" often means the reporter isn't emitting a `file` (or otherwise matchable) attribute per test case, so doctor can't line up atoms to results. Check the runner's JUnit reporter options for a flag to include the file path. For example, Jest's `jest-junit` needs `JEST_JUNIT_ADD_FILE_ATTRIBUTE=true`; pytest needs `--override-ini=junit_family=xunit1` (or a `file="..."` attribute is otherwise absent from `--junit-xml` output).
3. **All checks pass, `action_items` is empty** — doctor's `next_steps` lists optional features (test impact analysis, dynamic test splitting, auto rerun, wiring into CI config) each with its own YAML snippet. Apply only the ones the user asked for, then run doctor again to confirm.
4. Repeat until doctor is green and, if requested, the optional features are in place.

## Guardrails

- `circleci testsuite doctor "<suite name>"` is the only command that executes tests during setup and iteration. Never run the project's raw test command (`npm test`, `pytest`, `go test`, `rspec`, etc.) or the YAML's `discover`/`run` commands directly to validate — always go through doctor.
- The only exception is `circleci testsuite run "<suite name>" --analyze-tests=impacted`, and only when a doctor `next_steps` item explicitly asks for it to seed initial test impact analysis data.
- No secrets in `test-suites.yml` — use contexts/env vars. Don't commit local impact data under `.circleci/`.
- Don't replace a working testsuite with legacy `circleci tests split`/`circleci tests run` unless asked to migrate.
- Hand off CLI install/auth issues to `circleci-cli`, legacy JUnit/timings-split work to `circleci-config`, and CI failures after a doctor-clean config to `circleci-builds`.

## Output Contract

Remove extraneous files created during setup. Report the runner, files changed, the final doctor output, and any blocked prerequisites.
