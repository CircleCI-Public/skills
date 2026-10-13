---
name: circleci-smarter-testing-debugging
description: Debug CircleCI Smarter Testing on a project that is already onboarded, using `circleci testsuite impact` to explore impact data (which files impact a test, which tests a file impacts) and `circleci testsuite result` to show how a job's test atoms were selected and how they ran. Use when asking why a test was selected or skipped, why a change didn't run the expected tests, why too many tests run, or how a test atom ran in a job. For first-time setup use circleci-smarter-testing-onboarding.
---

# CircleCI Smarter Testing Debugging

Explains test selection and test runs on a suite that is already onboarded. If `.circleci/test-suites.yml` doesn't exist, use `circleci-smarter-testing-onboarding` first.

Both commands are experimental — check `circleci testsuite impact --help` and `circleci testsuite result --help` if a flag below is rejected.

Run them from the project directory where tests are run. `impact` reads impact data from CircleCI, which needs `circleci auth login`; pass `--local` to read the impact data stored locally by `--local` runs instead.

## Which command

| Question                                                    | Command                                            |
|-------------------------------------------------------------|----------------------------------------------------|
| How were a job's test atoms selected, and how did they run? | `circleci testsuite result <job-id>`               |
| Why did this test atom run or get skipped in that job?      | `circleci testsuite result <job-id> --test <atom>` |
| Which test atoms were slowest in that job?                  | `circleci testsuite result <job-id> --sort time`   |
| Which files impact this test atom?                          | `circleci testsuite impact --test <atom>`          |
| Which test atoms does this file impact?                     | `circleci testsuite impact --file <path>`          |
| Which files trigger the most tests?                         | `circleci testsuite impact --sort impact`          |

- `--key <key>` when the suite sets `options: impact-key`; otherwise the default key is read.
- `--version <N>` reads an older version of the impact data, e.g. from before selection changed.
- Get the job ID from the job URL, or hand off to `circleci-cli` to find it from the pipeline.

Start with `result` for a specific job, then use `impact` to explain what it shows.

## Common findings

- **A test didn't run after a file changed** — `impact --file <path>` doesn't list it, so coverage doesn't link them. If the link is real but coverage can't see it (migrations, fixtures, non-source files), suggest a `test-selection-rules` entry for the atom, or `full-test-run-paths` if the file should run everything.
- **A file isn't in impact data at all** — it has never been analyzed. Check that analysis runs on the default branch (default `--analyze-tests`, or a separate analysis job) and that the file is covered by the `analysis` command.
- **Too many tests run** — `impact --sort impact` shows the files connected to the most atoms. A change to a shared helper or config file near the top selects most of the suite; that's expected, not a bug.
- **A test runs on every branch** — `result --test` shows the reason; a test that failed on the previous run for the branch, or a new test, is always selected.

## Guardrails

- `impact` and `result` only read data. Don't run the suite or rerun jobs to debug selection.
- Suggest changes to `test-suites.yml` and let the user decide; after any change, rerun `circleci testsuite doctor "<suite name>"` until clean.
- Don't enable credit-charged options (test impact analysis, dynamic test splitting, dynamic parallelism, auto-rerun) while debugging — that's onboarding, owned by `circleci-smarter-testing-onboarding`.
- Hand off CLI install/auth issues to `circleci-cli`, and failing tests or builds unrelated to selection to `circleci-builds`.

## Output Contract

Report the commands run, what they showed for the test atoms or files in question, the cause, and any suggested `test-suites.yml` change.
