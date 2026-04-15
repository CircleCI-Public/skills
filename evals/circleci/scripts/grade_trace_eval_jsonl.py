#!/usr/bin/env python3
"""Grade captured JSONL traces for CircleCI skill evals."""

from __future__ import annotations

import argparse
import json
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
        if not line:
            continue
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade codex JSONL captures")
    parser.add_argument(
        "--summary",
        default="evals/circleci/artifacts/latest/summary.json",
        help="Capture summary path",
    )
    parser.add_argument(
        "--report",
        default="evals/circleci/artifacts/latest/report.json",
        help="Where to write machine-readable grading report",
    )
    parser.add_argument(
        "--min-json-events",
        type=int,
        default=3,
        help="Minimum parsed JSON objects required for a healthy run",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Return zero even when grading fails",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed grading diagnostics for failing checks",
    )
    args = parser.parse_args()

    summary_path = Path(args.summary).resolve()
    report_path = Path(args.report).resolve()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    results = summary.get("results", [])
    preflight = summary.get("preflight", {})

    graded_cases: list[dict[str, Any]] = []
    failures = 0

    preflight_ok = bool(preflight.get("ok", True))
    preflight_reason = preflight.get("reason", "")
    preflight_code = preflight.get("returncode")
    if not preflight_ok:
        failures += 1

    for item in results:
        case_id = item.get("id")
        expected_skill = item.get("expected_skill")
        returncode = item.get("returncode")
        stdout_path = Path(item.get("stdout", ""))
        stderr_path = Path(item.get("stderr", ""))

        events = read_json_lines(stdout_path)
        event_count = len(events)

        text_blob = "\n".join(flatten_strings(events)).lower()
        mentions_expected_skill = bool(expected_skill) and str(expected_skill).lower() in text_blob

        checks = {
            "process_exit_zero": returncode == 0,
            "minimum_json_events": event_count >= args.min_json_events,
            "mentions_expected_skill": True if expected_skill is None else mentions_expected_skill,
        }
        passed = all(checks.values())
        if not passed:
            failures += 1
            if args.verbose:
                print(f"Case '{case_id}' failed checks: {checks}")
                print(f"- expected_skill: {expected_skill}")
                print(f"- returncode: {returncode}")
                print(f"- stdout: {stdout_path}")
                print(f"- stderr: {stderr_path}")

        stderr_preview = ""
        if stderr_path.exists():
            stderr_preview = "\n".join(
                stderr_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:20]
            )

        graded_cases.append(
            {
                "id": case_id,
                "expected_skill": expected_skill,
                "returncode": returncode,
                "json_event_count": event_count,
                "checks": checks,
                "passed": passed,
                "stderr_preview": stderr_preview,
            }
        )

    report = {
        "summary_path": str(summary_path),
        "preflight": {
            "ok": preflight_ok,
            "reason": preflight_reason,
            "returncode": preflight_code,
        },
        "min_json_events": args.min_json_events,
        "total_cases": len(graded_cases),
        "failed_cases": failures,
        "passed_cases": max(0, len(graded_cases) - failures),
        "cases": graded_cases,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote grading report: {report_path}")
    if not preflight_ok:
        print(f"Preflight: FAILED ({preflight_reason}, exit {preflight_code})")
        if args.verbose:
            print("Preflight failed before case grading. See summary/report for captured preflight details.")
    print(f"Passed: {report['passed_cases']}/{report['total_cases']}")

    if failures and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
