#!/usr/bin/env python3
"""Run lightweight Codex skill invocation smoke checks (local/manual)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any


def flatten_strings(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            out.extend(flatten_strings(value))
    elif isinstance(obj, list):
        for value in obj:
            out.extend(flatten_strings(value))
    return out


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def load_cases(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"No cases found in {path}")
    return cases


def run_preflight(workdir: Path, model: str) -> dict[str, Any]:
    cmd = [
        "codex",
        "exec",
        "--json",
        "--cd",
        str(workdir),
        "-m",
        model,
        "Reply with exactly: ok",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "command": cmd,
        "stderr_preview": "\n".join((proc.stderr or "").splitlines()[:30]),
        "stdout_preview": "\n".join((proc.stdout or "").splitlines()[:30]),
    }


SELECTED_SKILL_RE = re.compile(r"SELECTED_SKILL=([a-z0-9-]+|none)")


def find_selected_skill(events: list[dict[str, Any]]) -> str | None:
    blob = "\n".join(flatten_strings(events))
    matches = SELECTED_SKILL_RE.findall(blob.lower())
    if not matches:
        return None
    return matches[-1]


def grade_case(events: list[dict[str, Any]], expected_skill: str | None) -> tuple[bool, dict[str, bool], str | None]:
    selected_skill = find_selected_skill(events)
    expected_normalized = "none" if expected_skill is None else str(expected_skill).lower()
    checks = {
        "minimum_json_events": len(events) >= 3,
        "selected_skill_reported": selected_skill is not None,
        "selected_skill_matches_expected": selected_skill == expected_normalized,
    }
    return all(checks.values()), checks, selected_skill


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Codex skill invocation smoke evals")
    parser.add_argument(
        "--cases",
        default="evals/circleci/cases/skill-invocation-smoke-cases.json",
        help="Path to invocation smoke cases JSON",
    )
    parser.add_argument(
        "--out-dir",
        default="evals/circleci/artifacts/invocation-smoke/latest",
        help="Directory to write JSONL and report artifacts",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Working directory passed to codex exec --cd",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.3-codex",
        help="Model passed to codex exec",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Return zero even when one or more checks fail",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-case diagnostics",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases).resolve()
    out_dir = Path(args.out_dir).resolve()
    workdir = Path(args.workspace_root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = load_cases(cases_path)
    failures = 0

    summary: dict[str, Any] = {
        "generated_at": int(time.time()),
        "cases_file": str(cases_path),
        "workdir": str(workdir),
        "model": args.model,
        "preflight": {},
        "cases": [],
    }

    preflight = run_preflight(workdir, args.model)
    summary["preflight"] = preflight
    if not preflight.get("ok"):
        failures += 1
        report_path = out_dir / "report.json"
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Preflight failed (exit {preflight.get('returncode')}). Wrote {report_path}")
        return 0 if args.allow_failures else 1

    for case in cases:
        case_id = str(case.get("id", "")).strip()
        prompt = str(case.get("prompt", "")).strip()
        expected_skill = case.get("expected_skill")
        purpose = str(case.get("purpose", "")).strip()

        eval_instruction = (
            "For eval output, first line must be exactly "
            "SELECTED_SKILL={ACTUAL_SKILL_OR_NONE}. "
            "Then provide one sentence reasoning."
        )
        full_prompt = f"{prompt}\n\n{eval_instruction}"

        case_dir = out_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        events_path = case_dir / "events.jsonl"
        stderr_path = case_dir / "stderr.log"

        cmd = [
            "codex",
            "exec",
            "--json",
            "--cd",
            str(workdir),
            "-m",
            args.model,
            full_prompt,
        ]

        with events_path.open("w", encoding="utf-8") as out_f, stderr_path.open("w", encoding="utf-8") as err_f:
            proc = subprocess.run(cmd, check=False, stdout=out_f, stderr=err_f, text=True)

        events = read_json_lines(events_path)
        passed, checks, selected_skill = grade_case(
            events,
            expected_skill if isinstance(expected_skill, str) else None,
        )
        if proc.returncode != 0:
            passed = False
            checks["process_exit_zero"] = False
        else:
            checks["process_exit_zero"] = True

        if not passed:
            failures += 1

        case_result = {
            "id": case_id,
            "purpose": purpose,
            "expected_skill": expected_skill,
            "selected_skill": selected_skill,
            "returncode": proc.returncode,
            "json_event_count": len(events),
            "checks": checks,
            "passed": passed,
            "events": str(events_path),
            "stderr": str(stderr_path),
        }
        summary["cases"].append(case_result)

        if args.verbose:
            print(f"{case_id}: {'PASS' if passed else 'FAIL'} {checks}")

    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote invocation smoke report: {report_path}")
    print(f"Cases: {len(summary['cases'])}, Failures: {failures}")

    if failures and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
