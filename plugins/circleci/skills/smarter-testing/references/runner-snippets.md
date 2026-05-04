# Smarter Testing — reference snippets

All commands execute **relative to the directory where** `circleci run testsuite` **is run**. Avoid `cd` / `--directory` inside YAML command strings.

## CI jobs and JUnit output directory

- **Executor image:** the **`circleci run testsuite`** command is already available on CircleCI executors (convenience and other documented images). Install the testsuite plugin locally only for development and doctor runs.
- **JUnit parent directory:** if the test runner does not create the directory for `outputs.junit` (for example `test-reports/`), add **`mkdir -p`** (or equivalent) **before** `circleci run testsuite` so `store_test_results` is not empty.
- **Classic vs testsuite:** JUnit quality, `circleci tests run`, and timings-only splits **without** `test-suites.yml` are covered in the config skill reference [test-results-and-splitting.md](../../config/references/test-results-and-splitting.md).

## Example `.circleci/config.yml`

```yaml
version: 2.1

jobs:
  test:
    docker:
      - image: cimg/node:22.0
    steps:
      - checkout
      - run:
          name: Install dependencies
          command: npm ci
      - run: mkdir -p test-reports
      - run:
          name: Run testsuite
          command: circleci run testsuite "ci tests"
      - store_test_results:
          path: test-reports

workflows:
  version: 2
  ci-tests:
    jobs:
      - test
```

Skip `mkdir -p test-reports` if your `run` command in `test-suites.yml` already creates that folder. For `store_test_results`, use the **parent directory** from `outputs.junit` (for example `test-reports`), not the path to one XML file. A testsuite run may produce **several** JUnit files; upload the whole directory so CircleCI receives all of them.

For **dynamic test splitting**, add `parallelism` on the job and `options.dynamic-test-splitting: true` in `test-suites.yml`; the same `circleci run testsuite "ci tests"` step runs on each parallel node.

## Getting started — runner starters (from CircleCI docs)

**Vitest**

```yaml
---
name: ci tests
discover: vitest list --filesOnly
run: vitest run --reporter=junit --outputFile="<< outputs.junit >>" --bail 0 << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

**Jest**

Requires the **[jest-junit](https://www.npmjs.com/package/jest-junit)** reporter as a **devDependency** (`npm install --save-dev jest-junit` or your package manager equivalent). Add `default` to `--reporters` if you still want console output during development.

```yaml
---
name: ci tests
discover: jest --listTests
run: JEST_JUNIT_OUTPUT_FILE="<< outputs.junit >>" jest --runInBand --reporters=default --reporters=jest-junit --bail << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

**pytest**

```yaml
---
name: ci tests
discover: find ./tests -type f -name 'test*.py'
run: pytest --disable-pytest-warnings --no-header --quiet --tb=short --junit-xml="<< outputs.junit >>" << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

**Go (gotestsum)**

```yaml
---
name: ci tests
discover: go list -f '{{ if or (len .TestGoFiles) (len .XTestGoFiles) }} {{ .ImportPath }} {{end}}' ./...
run: go tool gotestsum --junitfile="<< outputs.junit >>" -- -race -count=1 << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

**RSpec** (requires `rspec_junit_formatter` gem)

```yaml
---
name: ci tests
discover: find spec -type f -name '*_spec.rb'
run: bundle exec rspec --format RspecJunitFormatter --out "<< outputs.junit >>" << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

**Mocha**

```yaml
---
name: ci tests
discover: find ./tests -type f -name '*_test.js'
run: mocha --reporter xunit --reporter-options output="<< outputs.junit >>",showRelativePaths << test.atoms >>
outputs:
  junit: test-reports/tests.xml
```

## Test impact analysis — add `analysis` + option

Official page: [Set up test impact analysis](https://circleci.com/docs/guides/test/set-up-test-impact-analysis/).

Add dev dependencies / plugins per runner:

- Vitest: [vitest-circleci-coverage](https://github.com/circleci/vitest-circleci-coverage)
- Jest: [jest-circleci-coverage](https://github.com/circleci/jest-circleci-coverage)
- Mocha: [mocha-circleci-coverage](https://github.com/circleci/mocha-circleci-coverage)
- pytest: [pytest-circleci-coverage](https://github.com/circleci/pytest-circleci-coverage)
- RSpec: [rspec-circleci-coverage](https://github.com/circleci/rspec-circleci-coverage)

Example additions (Vitest):

```yaml
analysis: CIRCLECI_COVERAGE=<< outputs.circleci-coverage >> vitest run --silent --bail 0 << test.atoms >>
options:
  test-impact-analysis: true
```

Go example (includes `file-mapper`):

```yaml
file-mapper: go list -json="Dir,ImportPath,TestGoFiles,XTestGoFiles" ./... > << outputs.go-list-json >>
analysis: go tool gotestsum -- -coverprofile="<< outputs.go-coverage >>" -cover -coverpkg ./... << test.atoms >>
options:
  test-impact-analysis: true
```

**Selection tuning** (optional): `full-test-run-paths`, `test-selection-rules` — see [options in config reference](https://circleci.com/docs/guides/test/testsuite-configuration-reference/#options).

## Dynamic test splitting

```yaml
options:
  dynamic-test-splitting: true
```

Requires job `parallelism` greater than 1. [Doc](https://circleci.com/docs/guides/test/use-dynamic-test-splitting/).

## Auto rerun failed tests

```yaml
options:
  max-auto-rerun: 3
  # optional: auto-rerun-duration: 5m   # or 1h, 20%, etc.
```

[Doc](https://circleci.com/docs/guides/test/auto-rerun-failed-tests/). `max-auto-rerun` is 0–10; with `auto-rerun-duration`, whichever limit is hit first stops reruns.

## Doctor command

```bash
circleci run testsuite "ci tests" --doctor
```

Use the **exact** suite name from `name:` in `test-suites.yml`.
