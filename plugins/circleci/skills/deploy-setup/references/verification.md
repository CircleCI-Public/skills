# Verifying generated config

Run every check here before showing the diff. **None of them are optional**, and the
reason is the same for all of them: each one describes a config that compiles cleanly
while being broken. `circleci config validate` passing tells you nothing about any of them.

Work through them in order and report the result of each. Do not summarise as "validated"
— say which checks you ran and what they found, so the user can see what was and was not
covered.

## 0. Compilation

```bash
circleci config validate .circleci/config.yml
```

Repeat for `deploy.yml` and `rollback.yml` if you generated them.

If the CLI is not installed, **say so explicitly and continue with the rest** — the
invariants below need nothing but `git` and `grep`, and they are the checks that matter
most. Do not report a pass; report that compilation went unverified and that CI will be the
first thing to compile the config. Offer the [local CLI](https://circleci.com/docs/local-cli/).

## 1. No original `run` command was dropped

Silently losing a step while rewriting YAML is *the* characteristic failure of generated
config, and it is invisible to compilation. This is the single most important check.

Read the diff and account for every removed line:

```bash
git diff -- .circleci/config.yml
```

Every `-` line must be either a marker command you deliberately replaced, or a line you can
explain. A removed `run` step that you cannot explain means you dropped it — restore it.

Reading the diff is more reliable than pattern-matching here, because you can tell intent.
As a mechanical cross-check on a large diff, compare the non-marker commands before and
after:

```bash
extract() {
  grep -E '^[[:space:]]*command:' \
    | sed -E 's/^[[:space:]]*command:[[:space:]]*//' \
    | grep -vE 'circleci[[:space:]]+run[[:space:]]+release[[:space:]]+(plan|update|log)' \
    | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | grep -v '^$' | sort -u
}
comm -23 <(git show HEAD:.circleci/config.yml | extract) <(extract < .circleci/config.yml)
```

Any output is a command present before your edit and missing now.

**Empty output is not proof.** `extract` reads only what follows `command:` on the same
line, so a step written as `command: |` reduces to the single token `|` and its body is
invisible. Delete a block-form `helm upgrade` and this check still comes back clean. Treat
it as a cheap scan of inline commands, and let the diff you just read be the real
evidence.

## 2. Exactly one `plan` per deployment unit

Two `plan` commands for the same deploy name create two releases, and the second orphans
the first.

```bash
grep -oE 'circleci run release plan[[:space:]]+[^ \\]+' .circleci/*.yml \
  | sed -E 's/:circleci run release plan[[:space:]]+/ /' | tr -d '"' | sort | uniq -c
grep -nE 'deploys/(plan|log)' .circleci/*.yml
```

The second command catches the `circleci/deploys` orb, whose steps carry a plan without
containing the literal text the first command looks for. **A job with both an orb step and
a raw `plan` is the duplicate this check exists to find**, and the first command alone
cannot see it.

Output is one line per file and plan name, so **every count must be 1**. The filename is
kept deliberately: the same plan name in `config.yml` and in `deploy.yml` is legitimate,
because those are separate pipelines. Counting names alone would report that pair as a
duplicate. A count above 1 means one file plans the same name twice, which is the fault.

## 3. Every `update` references a planned name

An `update` naming a plan that was never created leaves the release stuck, and compiles fine.

```bash
grep -ohE 'circleci run release (plan|update)[[:space:]]+[^ \\]+' .circleci/*.yml \
  | sed -E 's/circleci run release //' | tr -d '"' | sort -u
```

Read the output: every name appearing after `update` must also appear after `plan`. A
typo'd name is the usual cause.

## 4. Terminal steps, conditional on validation

Without an `on_fail` step, a failed deploy sits in `RUNNING` forever.

```bash
grep -nE 'when:[[:space:]]*(on_fail|on_success)' .circleci/*.yml
```

- **Every job with a `plan` needs a `when: on_fail` step** marking `FAILED`. The single
  exception is a Kubernetes job using the CircleCI release agent, which must carry no
  `update` steps at all — see `markers.md`.
- **`on_success` marking `SUCCESS` is required only when validation is *not* in scope** for
  that plan name. See check 6.

## 5. A `validation` block has a release job that matches

This one fails loudly at run time with `Planned release not found`, unlike the others — but
only after a real deploy, so catch it here.

```bash
grep -nE '^[[:space:]]*(validation:|type:[[:space:]]*release|plan_name:)' .circleci/*.yml
```

When a `validation:` block is present, confirm all three:

1. there is a `type: release` job to carry it
2. its `plan_name` exactly matches a name passed to `circleci run release plan`
3. `plan_name` is a **literal**, not an expression — `"${CIRCLE_JOB}"` cannot be matched

Both jobs must also be in the same workflow, with the release job requiring the deploy job.
See `validation.md`.

## 6. No `SUCCESS` marker when validation owns the plan

The subtle one. If the deploy job marks `SUCCESS`, the release completes before validation
can evaluate it, so the validation result never affects anything.

```bash
grep -nE -- '--status=SUCCESS' .circleci/*.yml
```

**Match the flag on its own, not `update … --status=SUCCESS` on one line.** Marker
commands are routinely written across a line continuation — it is the shape the templates
in `pipelines.md` emit — and a line-oriented pattern spanning both words silently misses
them:

```yaml
command: |
  circleci run release update my-deploy \
    --status=SUCCESS
```

A premature `SUCCESS` is the most damaging mistake this file checks for, so prefer the
looser pattern and inspect the hits. Matching the flag alone can also flag a comment or a
rollback job, which the per-hit check below sorts out.

One limit to state rather than paper over: checks 2, 3 and 6 assume a **literal** plan
name. Where the config uses a variable such as `${DEPLOY_NAME}`, they can compare only the
variable and not the value it resolves to — report that instead of claiming all six
invariants passed.

For each hit, check whether that plan name is carried by a `type: release` job with
`validation.enabled: true`. If it is, **remove the `SUCCESS` step** — success is delegated
to the release job. The `on_fail`/`FAILED` step still stays.

## Reporting

State plainly what you checked and what you could not:

> Ran `circleci config validate` on all three files (pass). Checked the six invariants:
> no dropped commands, one plan per unit, all update names planned, `on_fail` present,
> release job `plan_name` matches, no premature `SUCCESS`. Compilation of `rollback.yml`
> unverified — no `circleci` CLI on PATH.

If any check fails, fix it and re-run that check before showing the diff. Never present a
diff for approval with a known failing invariant.
