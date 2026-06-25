---
name: circleci-smarter-testing
description: Onboard onto CircleCI Smarter Testing (testsuite) with `.circleci/test-suites.yml`, config wiring, `circleci run testsuite`, and `--doctor` until checks pass. Use for Smarter Testing, testsuite, test-suites YAML, test impact analysis, dynamic test splitting, auto rerun failed tests, or migrating raw test commands.
---

# CircleCI Smarter Testing

## Overview

**Beta** ([Discuss](https://discuss.circleci.com/t/product-launch-smarter-testing-is-now-in-beta/54497)). Create or adjust `.circleci/test-suites.yml`, wire it into CI, and validate with `--doctor` until checks pass. Let doctor diagnose YAML, command, JUnit, and testsuite errors before adding extra guidance.

## Doctor command (required)

When iterating with `--doctor`, the agent **must always** run this exact command (substitute the suite name only):

```bash
$ circleci run testsuite "<suite name>" --doctor --json
```

Example output:

```json
{
  "checks": [
	{
	  "name": "< check name >",
	  "state": "< success | skipped | failed >"
	}
  ],
  "action_items": [
	{
	  "title": "< what happened >",
	  "content": "< advice on how to fix the problem >"
	}
  ],
  "next_steps": [
	{
	  "title": "< next step >",
	  "content": "< suggestion for the next thing to configure >"
    }
  ]
}
```

Do not modify this command: no pipes, `tail`, redirects, backgrounding, or truncation.

**Scope:** testsuite setup and validation. Primary doc: [Getting started](https://circleci.com/docs/guides/test/getting-started-with-smarter-testing/).

**Lazy references:** read only what the task needs—do not load every reference file up front.

- CI / `store_test_results` → [references/ci-and-junit.md](references/ci-and-junit.md)

## Inputs To Gather

- Runner, test root, existing `.circleci/config.yml`
- Hand off: **`circleci-cli`** (install/auth/plugin) | **`circleci-config`** (JUnit/test results) | **`circleci-builds`** (CI fails after doctor-clean config)

## Workflow

1. **Local vs CI** — Local needs [CLI](https://circleci.com/docs/guides/toolkit/local-cli/) + testsuite plugin (`brew install circleci/tap/circleci-testsuite` on macOS; [binaries](https://circleci.com/docs/guides/test/getting-started-with-smarter-testing/) on Linux/WSL). CI uses `circleci run testsuite` on executors + [ci-and-junit.md](references/ci-and-junit.md).
2. **Inspect** — runner, layout, existing CI; reuse documented test commands; run testsuite from the test root (no `cd` in YAML).
3. **Doctor** — run the exact doctor command above; apply its advice; repeat until pass.
4. **Next steps** — Ask to configure next steps from the doctor command output. Run the doctor command after each.

## Guardrails

- Never skip doctor after editing `test-suites.yml`.
- No secrets in YAML—use contexts/env vars; document variable names only.
- Do not swap a working testsuite for legacy `circleci tests split` / `circleci tests run`.

## Reference map

- [ci-and-junit.md](references/ci-and-junit.md) — full `config.yml`, JUnit directory upload.

## Output Contract

Provide:

1. Runner, working directory, files changed, commands run (`--doctor` and follow-ups).
2. What to commit and open items (beta access, blocked prerequisites).
