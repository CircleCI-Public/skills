# `test-suites.yml` by runner

Read **only** the section that matches the detected runner. Other stacks: [Getting started](https://circleci.com/docs/guides/test/getting-started-with-smarter-testing/) and [config reference](https://circleci.com/docs/guides/test/testsuite-configuration-reference/).

## Template

```yaml
---
name: ci tests
discover: <command; one test atom per line on stdout>
run: <command; write JUnit to "<< outputs.junit >>"; include << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

## Vitest

```yaml
---
name: ci tests
discover: vitest list --filesOnly
run: vitest run --reporter=junit --outputFile="<< outputs.junit >>" --bail 0 << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

## pytest

```yaml
---
name: ci tests
discover: find ./tests -type f -name 'test*.py'
run: pytest --disable-pytest-warnings --no-header --quiet --tb=short --junit-xml="<< outputs.junit >>" << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

## Other runners (official starters)

| Runner | Notes |
|--------|--------|
| Jest | [jest-junit](https://www.npmjs.com/package/jest-junit) devDependency; `--reporters=default --reporters=jest-junit` |
| Go | `gotestsum` + `go list` discover; TIA needs `file-mapper` — see [optional-features.md](optional-features.md) |
| RSpec | `rspec_junit_formatter` gem |
| Mocha | xunit reporter to `<< outputs.junit >>` |

Copy full YAML from the getting-started guide; then run `circleci run testsuite "ci tests" --doctor`.
