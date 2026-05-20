# CI wiring and JUnit upload

Commands in `test-suites.yml` are **relative to the directory where** `circleci run testsuite` **runs**. Do not use `cd` or `--directory` inside YAML command strings.

- **Executors:** `circleci run testsuite` is already on CircleCI executors; install the testsuite plugin **locally** only for doctor runs.
- **JUnit folder:** `mkdir -p` the parent of `outputs.junit` before testsuite if the runner does not create it.
- **Classic path:** JUnit / `circleci tests run` / timings splits without testsuite → [test-results-and-splitting.md](../../config/references/test-results-and-splitting.md).

## Example `.circleci/config.yml`

Assumes `.circleci/test-suites.yml` with `name: ci tests` and `outputs.junit` under `test-reports/`. Adjust image and install for your stack.

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

Skip `mkdir -p test-reports` if `run` in `test-suites.yml` already creates that folder. Point `store_test_results` at the **directory** from `outputs.junit` (for example `test-reports`), not one XML file—testsuite may write **multiple** JUnit files and CircleCI needs the whole directory.

**Dynamic splitting:** job `parallelism` greater than 1 plus `options.dynamic-test-splitting: true` in `test-suites.yml`; same `circleci run testsuite "ci tests"` on each node. Details: [optional-features.md](optional-features.md).
