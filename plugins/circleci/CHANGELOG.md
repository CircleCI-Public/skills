# Changelog

Each version here is the `version` in `.claude-plugin/plugin.json` and
`.codex-plugin/plugin.json`. Claude Code and Codex only update an installed
plugin when that version changes.

Before 1.3.0 the Codex manifest was versioned on its own. Its 1.1.0 was
released from the same commit as Claude Code's 1.2.1, without the language
server. From 1.3.0 both manifests carry the same version.

## 1.4.0 - 2026-10-19

- Added `smarter-testing-run`, which runs a project's tests locally through
  `circleci testsuite run` instead of the test runner, selecting from
  CircleCI's impact data, or local data when not signed in, and narrows them
  to a subset with `--test-atom-pattern`. On a CircleCI project without
  Smarter Testing it runs the project's own tests, then says once what Smarter
  Testing would add and offers to set it up.
- `smarter-testing-onboarding` covers the free features too: static test
  splitting, rerunning only failed tests and test uploads, alongside the
  credit-charged ones and each plan's test atom allowance.

## 1.3.0 - 2026-10-16

- Merged the `testsuite` and `smarter-testing` skills into one
  `smarter-testing-onboarding` skill, matching the docs, where Smarter Testing
  names the whole tool, free and paid.
- Added `smarter-testing-debugging`, which explains test selection and test runs
  with `circleci testsuite impact` and `circleci testsuite result`.

## 1.2.1 - 2026-09-30

- The language server checks each edit to a config at once, so diagnostics
  arrive on the same step as the edit. Claude Code only.

## 1.2.0 - 2026-09-30

- Runs the CircleCI YAML language server, so Claude sees config errors after
  each edit and can look up jobs, commands and orbs by name. Claude Code only.

## 1.1.0 - 2026-09-23

Everything since the first release, which landed without a version change until
this one:

- Added `smarter-testing`, `onboard`, `testsuite`, `debug-ci-failures` and
  `deploy-setup`.
- Moved the `chunk` skill out to the chunk plugin.
- Rewrote `onboard` around the commands that exist, including org and pipeline
  types and GitHub App setup.
- `cli` points at commands instead of the raw API, covers signing in, and maps
  API endpoints to commands.
- The plugin has one description everywhere it's listed.

## 1.0.0 - 2026-04-15

- First release: `cli`, `builds`, `config` and `chunk`.
