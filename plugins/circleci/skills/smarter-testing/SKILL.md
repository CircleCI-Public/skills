---
name: circleci-smarter-testing
description: Onboard a repository onto CircleCI Smarter Testing (testsuite). Create or update `.circleci/test-suites.yml`, wire `.circleci/config.yml`, and validate with `circleci run testsuite` plus `--doctor` until checks pass. Use for Smarter Testing, testsuite, test-suites YAML, test impact analysis, testsuite dynamic splitting, auto rerun failed tests, or migrating from raw test commands. Prefer circleci-config when the goal is only JUnit, store_test_results, or circleci tests run timings without testsuite.
---

# CircleCI Smarter Testing

## Overview

Smarter Testing is a **beta** product ([Discuss](https://discuss.circleci.com/t/product-launch-smarter-testing-is-now-in-beta/54497)). Use this skill to produce a complete, runnable Smarter Testing setup for the current workspace with discover, run, and JUnit outputs, optional features the user requests, and CI wiring. Always drive validation with the **doctor** command in a loop until all checks pass.

**Scope:** This skill owns **`test-suites.yml`**, **`circleci run testsuite`**, testsuite **options** (TIA, dynamic splitting, auto rerun), and the **doctor** loop. It does **not** replace the legacy path of tuning **`circleci tests run`**, timings-only parallelism, or JUnit quality without testsuite—that belongs under **`circleci-config`**. For JUnit shape, `store_test_results`, split inputs, and rerun-failed-tests via the classic CLI flow, read [test-results-and-splitting.md](../config/references/test-results-and-splitting.md) in the config skill.

Official guides:

- [Getting started](https://circleci.com/docs/guides/test/getting-started-with-smarter-testing/)
- [Test impact analysis](https://circleci.com/docs/guides/test/set-up-test-impact-analysis/)
- [Dynamic test splitting](https://circleci.com/docs/guides/test/use-dynamic-test-splitting/)
- [Auto rerun failed tests](https://circleci.com/docs/guides/test/auto-rerun-failed-tests/)
- [Test suite config reference](https://circleci.com/docs/guides/test/testsuite-configuration-reference/)

Copy-paste YAML and plugin links live in [references/runner-snippets.md](references/runner-snippets.md).

## Inputs To Gather

- Test runner (Vitest, Jest, pytest, Go, RSpec, Mocha, or other) and documented test commands
- Monorepo layout and directory where tests should run
- Existing `.circleci/config.yml` and any reusable config
- Optional goals: test impact analysis, dynamic splitting, auto rerun limits
- **Hand off when appropriate:** **`circleci-cli`** for install, version, plugin install, auth, and generic CLI troubleshooting; **`circleci-config`** when the user only wants JUnit, `store_test_results`, or `circleci tests run` / timings splits without adopting testsuite; **`circleci-builds`** when testsuite and config are doctor-clean but CI still fails on environment, image, secrets, or unrelated build steps (log-led triage).

## Workflow

1. **Inspect the repo first**: detect runner, layout, existing CircleCI config, and where tests should run from.
2. **Reuse project patterns**: match existing scripts, package manager, and paths; do not invent a parallel test command if the project already documents one.
3. **Working directory**: `circleci run testsuite` must run from the directory where tests live (usually repo root; monorepos may use a subpackage). The CLI walks up to find `.circleci/test-suites.yml`. In `discover`, `run`, and `analysis` commands, do not use `cd` or `--directory` flags inside YAML—paths must work relative to that working directory.
4. **Baseline (required)** — create or update `.circleci/test-suites.yml` with:
   - `name`: stable identifier (for example `ci tests`) used on the CLI
   - `discover`: command that lists test atoms (one line each)
   - `run`: command that runs tests with JUnit XML written to the path referenced by `outputs.junit` placeholders per docs
   - `outputs.junit`: relative path under a directory you pass to `store_test_results` (for example `test-reports/tests.xml`)
5. **Doctor-driven loop** (mandatory after creating or editing `test-suites.yml`):

   ```bash
   circleci run testsuite "<suite name>" --doctor
   ```

   Read the output, apply fixes (discover list, JUnit path, reporters, env vars, plugins), re-run `--doctor` until all checks pass. Only then suggest running without `--doctor` for a full run or flaky-rerun verification.

6. **Prerequisites** — verify or document:
   - [CircleCI CLI](https://circleci.com/docs/guides/toolkit/local-cli/) installed
   - **testsuite plugin** locally: on macOS, `brew install circleci/tap/circleci-testsuite`; on **Linux or WSL**, use [binary installs](https://circleci.com/docs/guides/test/getting-started-with-smarter-testing/) from the same getting-started guide (do not assume Homebrew). If install, PATH, or auth is the blocker, use the **`circleci-cli`** skill.
   - **CI jobs:** **`circleci run testsuite`** is already available on CircleCI executors; jobs only need that invocation plus correct `store_test_results` wiring. The testsuite plugin install above applies to **local** doctor and validation runs.
7. **CI alignment** — `store_test_results` path must be the **directory** containing the JUnit file declared in `outputs.junit` (often `test-reports`). Ensure that directory exists before the test run if the runner does not create it (for example `mkdir -p test-reports` in a prior step). Replace the prior raw test command with `circleci run testsuite "<suite name>"` (same invocation as local, plus flags only when branch-specific behavior is required per docs).
8. **Optional features** (only if the user asks) — enable in `options:` and add `analysis` / `file-mapper` when required. Re-run `--doctor` after each change.

| Feature | Config | Notes |
|--------|--------|--------|
| Test impact analysis | `options.test-impact-analysis: true` plus `analysis:` (and CircleCI coverage plugin or Go file-mapper per runner) | See TIA guide; add `full-test-run-paths` / `test-selection-rules` if manifests or non-source files should force runs |
| Dynamic splitting | `options.dynamic-test-splitting: true` | Job needs `parallelism` greater than 1; document tradeoff if runner startup dominates |
| Auto rerun | `options.max-auto-rerun` (0–10) and/or `options.auto-rerun-duration` | Requires correct JUnit failures in output |

**Branch defaults (CI)** are documented in the TIA guide (`--select-tests`, `--analyze-tests`). Do not commit local impact artifacts (for example `.circleci/` impact JSON named per suite).

9. **Verify locally** (after doctor passes):
   - Full run: `circleci run testsuite "<suite name>"`
   - TIA spot-check (optional): per [TIA local flags](https://circleci.com/docs/guides/test/set-up-test-impact-analysis/)
   - Auto rerun: temporarily fail a test, run without `--doctor`, confirm reruns in logs

## Guardrails

- Treat Smarter Testing as beta unless the user confirms otherwise.
- Do not skip the doctor loop after editing `test-suites.yml`.
- Do not commit local-only impact JSON under `.circleci/`.
- Prefer the smallest config change that satisfies doctor and the user’s stated goals.
- **Secrets:** never paste real tokens, API keys, or bearer credentials into `test-suites.yml` or logs. Use **CircleCI contexts** or **project/org environment variables** and document only the **variable names** the suite expects.
- Do not replace a working **testsuite** setup with legacy **`circleci tests split` / `circleci tests run`**-only flows unless the user explicitly asks to migrate away from Smarter Testing.

## Reference map

- [references/runner-snippets.md](references/runner-snippets.md): copy-paste `test-suites.yml` starters, `config.yml` `store_test_results` wiring, TIA snippets, splitting and auto-rerun YAML, doctor examples.
- [../config/references/test-results-and-splitting.md](../config/references/test-results-and-splitting.md): classic JUnit quality, `store_test_results` pitfalls, `circleci tests run`, timings-based splitting, and rerun-failed-tests **without** testsuite.
- Official Smarter Testing links: see **Overview** list above.

## Output Contract

Provide:

1. Summary of detected runner and working directory for testsuite commands.
2. List of created or updated files (`.circleci/test-suites.yml`, `.circleci/config.yml`, and any runner deps).
3. Exact validation commands run (`--doctor` and any follow-up).
4. What the user should commit and how to compare the Tests tab versus a non-testsuite run if migrating.
5. Remaining manual steps (tokens, org beta access, or blocked prerequisites).
