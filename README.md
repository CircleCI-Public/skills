# skills
CircleCI managed plugins for AI Agents

# Organization

There's a toplevel codex compatible marketplace meant to facilitate local testing in codex.

The actual plugin in `plugins/circleci` is compatible with existing codex marketplaces.

## Coverage

Skills include:
- general CircleCI build debugging
- usage of the chunk cli and cloud based modes
- the circleci CLI day-to-day developer workflow — validate, push, `run watch`, read failing logs/tests, rerun
- circleci config management and optimization
- CircleCI Smarter Testing (testsuite) onboarding and `test-suites.yml` setup
- guided onboarding of a new project to CircleCI (incl. org/pipeline types, `project follow`, central config)

## Manual eval runs

Run from the repository root:

### 1) CI-safe routing evals (frontmatter + static routing)

```bash
evals/circleci/scripts/run_routing_evals_ci.sh
```

This runs:
- SKILL frontmatter checks for `plugins/circleci/skills/*/SKILL.md`
- `quick_validate.py` checks (when available)
- routing eval cases from `evals/circleci/cases/skill-routing-cases.json`

Routing case purpose (`evals/circleci/cases/skill-routing-cases.json`):
- `circleci-builds` cases: ensure failed-build, flaky, and root-cause prompts route to `circleci-builds` (explicit + implicit).
- `circleci-cli` cases: ensure CLI/auth/rerun/command-line prompts route to `circleci-cli` (explicit + implicit).
- `circleci-config` cases: ensure `.circleci/config.yml`, caching, workspace, and runtime optimization prompts route to `circleci-config` (explicit + implicit).
- `chunk` cases: ensure Chunk setup and `chunk-cli` prompts route to `chunk` (explicit + implicit).
- `circleci-testsuite` cases: ensure testsuite, `test-suites.yml`, and legacy test-command migration prompts route to `circleci-testsuite` (explicit + implicit).
- `circleci-smarter-testing` cases: ensure Smarter Testing, test impact analysis, and dynamic test splitting prompts route to `circleci-smarter-testing` (explicit + implicit).
- negative-control cases: ensure non-CircleCI prompts route to `null`.

### 2) Local invocation smoke (codex `--json`, not in CI)

```bash
evals/circleci/scripts/run_invocation_smoke_evals_local.sh
```

Default local mode is non-strict and still writes artifacts even if preflight or a case fails.

Strict mode (non-zero exit on failures, local-only):

```bash
STRICT=1 evals/circleci/scripts/run_invocation_smoke_evals_local.sh
```

Artifacts are written to:
- `evals/circleci/artifacts/invocation-smoke/latest/report.json`
- per-case JSONL/stderr files under `evals/circleci/artifacts/invocation-smoke/latest/<case-id>/`

Invocation smoke case purpose (`evals/circleci/cases/skill-invocation-smoke-cases.json`):
- `builds-explicit-smoke`: validate explicit `$circleci-builds` prompt selects `circleci-builds`.
- `chunk-explicit-smoke`: validate explicit `$chunk` prompt selects `chunk`.
- `cli-implicit-smoke`: validate CLI intent prompt selects `circleci-cli` without explicit skill mention.
- `testsuite-explicit-smoke`: validate explicit `$circleci-testsuite` prompt selects `circleci-testsuite`.
- `smarter-testing-explicit-smoke`: validate explicit `$circleci-smarter-testing` prompt selects `circleci-smarter-testing`.
- `negative-control-smoke`: validate unrelated prompt reports `none`.

### 3) Trace evals (full codex `--json` capture + grading, optional)

```bash
evals/circleci/scripts/run_trace_capture_evals_local.sh
```

Trace case purpose (`evals/circleci/cases/trace-cases.json`):
- validate codex capture preflight and JSONL artifact generation for explicit and implicit prompts.
- validate grading behavior for expected skill mention and negative controls.
- `testsuite-explicit` / `testsuite-implicit`: validate `$circleci-testsuite` and legacy test-command migration prompts.
- `smarter-testing-implicit`: validate CircleCI Smarter Testing (test impact analysis, dynamic test splitting) prompts route to `circleci-smarter-testing`.

If codex preflight fails with a network error, verify that `codex exec` can reach OpenAI endpoints from your environment.
