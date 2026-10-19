# CircleCI skills

CircleCI-managed plugins for AI agents. Two plugins live here: **circleci**, the
skills for building, debugging and optimizing pipelines, and **chunk**, the
skills for CircleCI Chunk.

## Install

### Claude Code

Adding the marketplace registers the catalog. Installing the plugin is a
separate step, and skipping it is why `/reload-plugins` would report no skills:

```
/plugin marketplace add CircleCI-Public/skills
/plugin install circleci@circleci-public-skills
```

Add `chunk@circleci-public-skills` as well for the Chunk skills. The same two
steps work from a shell with `claude plugin marketplace add` and
`claude plugin install`.

The circleci plugin also runs the
[CircleCI YAML language server](https://github.com/CircleCI-Public/circleci-yaml-language-server),
so Claude sees config errors after each edit and can look up jobs, commands and
orbs by name. It downloads the server the first time it edits a YAML file, and
checks once a day for a newer release. That needs `curl` or `wget` on macOS and
Linux, and PowerShell on Windows, which every supported Windows has. To pin a
version, set `CIRCLECI_YAML_LSP_VERSION`.

### Codex

```
codex plugin marketplace add CircleCI-Public/skills
codex plugin add circleci@circleci-skills
```

### Any agent that reads SKILL.md

The skills are plain markdown under `plugins/<plugin>/skills/<skill>/SKILL.md`,
with no plugin runtime required. Point your agent at that directory, or copy the
ones you want into wherever it looks for skills.

Most of these drive the [circleci CLI](https://github.com/CircleCI-Public/circleci-cli),
so install that too and run `circleci auth login` once.

## Updating

Each plugin's `CHANGELOG.md` lists what changed in each version. To hear about
new versions, watch this repository on GitHub for releases.

### Claude Code

Claude Code doesn't update plugins from this marketplace unless you turn on
auto-update, which is off by default for marketplaces outside Anthropic's own.
Until then you keep the version you installed.

To turn on auto-update, run `/plugin`, open the **Marketplaces** tab, select
`circleci-public-skills`, and choose **Enable auto-update**. Claude Code then
updates the plugins when a session starts, and the new versions load in the
next session or after `/reload-plugins`.

To update now, choose **Update marketplace** in the same place, or from a shell:

```
claude plugin marketplace update circleci-public-skills
claude plugin update circleci@circleci-public-skills
```

### Codex

Codex keeps the version you installed. Refresh the marketplace, then add the
plugin again to install the new version, and start a new session to load it:

```
codex plugin marketplace upgrade circleci-skills
codex plugin add circleci@circleci-skills
```

`codex plugin list` shows the installed version.

## Organization

There's a toplevel codex compatible marketplace meant to facilitate local testing in codex.

The actual plugin in `plugins/circleci` is compatible with existing codex marketplaces.

## Releasing

Installed plugins only update when the `version` in their manifest changes, so
every change under `plugins/<plugin>/` needs a new version:

1. Bump `version` in `plugins/<plugin>/.claude-plugin/plugin.json`, and in
   `.codex-plugin/plugin.json` too if the plugin has one. The two stay equal.
2. Add a `## <version> - <date>` entry to `plugins/<plugin>/CHANGELOG.md`.

The `plugin-versions` job checks both, and fails a branch that changes a plugin
without them. Run `scripts/check_plugin_versions.sh` to check locally.

After it merges, tag and release it:

```bash
scripts/tag_release.sh circleci
```

It reads the version from the manifest on `main`, pushes
`<plugin>-v<version>`, and creates a GitHub release with the changelog entry as
its notes. It stops if that version was already released, or if the changelog
has no entry for it.

To see what has landed since the last release:

```bash
git log "$(git describe --tags --abbrev=0 --match 'circleci-v*' origin/main)"..origin/main -- plugins/circleci
```

## Publishing the Codex directory listing

The listing in the Codex plugin directory is a zip uploaded to the portal by
hand. Installing with `codex plugin marketplace add CircleCI-Public/skills`
reads this repository directly and doesn't go through these steps.

A `circleci-v<version>` tag from `scripts/tag_release.sh` starts the
`codex-bundle` job, which builds `circleci-<version>.zip` and stores it as an
artifact. Upload that zip to the Codex portal and publish it.

`scripts/build_codex_bundle.sh` builds the same zip from `HEAD` into `dist/`
if you want to look at it first.

## Coverage

**circleci**

| Skill | What it covers |
| --- | --- |
| `cli` | The day-to-day loop: validate, push, `run watch`, read failing logs and tests, rerun |
| `builds` | Diagnosing failing builds and flaky pipelines down to a root cause |
| `debug-ci-failures` | Working through a red pipeline, test results and flaky tests |
| `config` | Writing and optimizing `.circleci/config.yml` for speed, cost and reliability |
| `onboard` | Connecting a new repo end to end, including org and pipeline types |
| `deploy-setup` | Deploy markers, deploy and rollback pipelines, release validation, monitoring webhooks |
| `smarter-testing-onboarding` | Onboarding onto Smarter Testing: `.circleci/test-suites.yml`, `circleci testsuite run`, and choosing which credit-charged capabilities to enable |
| `smarter-testing-run` | Running tests locally through Smarter Testing with `circleci testsuite run`, narrowed with `--test-atom-pattern` |
| `smarter-testing-debugging` | Explaining test selection and test runs with `circleci testsuite impact` and `circleci testsuite result` |

**chunk**

| Skill | What it covers |
| --- | --- |
| `chunk` | Installing and driving the `chunk` CLI, including cloud mode |
| `chunk-sidecar-setup` | Standing up a local sidecar |
| `chunk-sidecar` | Operating it once it is running |
| `chunk-review` | Reviewing a diff before it lands |
| `chunk-testing-gaps` | Finding the gaps in a project's test coverage |

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
- `circleci-smarter-testing-onboarding` cases: ensure testsuite, `test-suites.yml`, legacy test-command migration, Smarter Testing, test impact analysis, and dynamic test splitting prompts route to `circleci-smarter-testing-onboarding` (explicit + implicit).
- `circleci-smarter-testing-run` cases: ensure prompts to run tests locally, or a subset of them by test atom pattern, route to `circleci-smarter-testing-run` (explicit + implicit).
- `circleci-smarter-testing-debugging` cases: ensure impact data, test selection, and skipped-test prompts route to `circleci-smarter-testing-debugging` (explicit + implicit).
- `circleci-deploy-setup` cases: ensure deploy-marker, deploy/rollback pipeline, and release-validation prompts route to `circleci-deploy-setup` (explicit + implicit).
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
- `testsuite-explicit-smoke` / `smarter-testing-explicit-smoke`: validate explicit `$circleci-smarter-testing-onboarding` prompts for testsuite setup and capability setup select `circleci-smarter-testing-onboarding`.
- `smarter-testing-run-explicit-smoke`: validate explicit `$circleci-smarter-testing-run` prompt selects `circleci-smarter-testing-run`.
- `negative-control-smoke`: validate unrelated prompt reports `none`.

### 3) Trace evals (full codex `--json` capture + grading, optional)

```bash
evals/circleci/scripts/run_trace_capture_evals_local.sh
```

Trace case purpose (`evals/circleci/cases/trace-cases.json`):
- validate codex capture preflight and JSONL artifact generation for explicit and implicit prompts.
- validate grading behavior for expected skill mention and negative controls.
- `testsuite-explicit` / `testsuite-implicit` / `smarter-testing-implicit`: validate `$circleci-smarter-testing-onboarding`, legacy test-command migration, and Smarter Testing capability prompts route to `circleci-smarter-testing-onboarding`.

If codex preflight fails with a network error, verify that `codex exec` can reach OpenAI endpoints from your environment.
