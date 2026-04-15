#!/usr/bin/env python3
"""Capture JSONL traces for CircleCI skill eval prompts using codex exec --json."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

PANIC_SIGNATURES = [
    "system-configuration-0.6.1/src/dynamic_store.rs",
    "Attempted to create a NULL object.",
]
NETWORK_SIGNATURES = [
    "failed to lookup address information",
    "Could not resolve hostname",
    "error sending request for url (https://api.openai.com/v1/responses)",
    "stream disconnected before completion: error sending request for url",
]


def load_cases(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"No cases found in {path}")
    return cases


def _first_lines(text: str, max_lines: int = 30) -> str:
    if not text:
        return ""
    return "\n".join(text.splitlines()[:max_lines])


def _tail_lines(path: Path, max_lines: int = 30) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max_lines:])


def run_preflight(workdir: Path, model: str) -> dict:
    """Run a tiny codex exec to verify JSONL capture is healthy."""
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
    stderr = proc.stderr or ""
    reason = ""
    if proc.returncode == 0:
        reason = ""
    if any(sig in stderr for sig in PANIC_SIGNATURES):
        reason = "codex_exec_runtime_panic"
    elif any(sig in stderr for sig in NETWORK_SIGNATURES):
        reason = "codex_exec_network_error"
    elif proc.returncode != 0:
        reason = "codex_exec_failed"

    return {
        "ok": proc.returncode == 0,
        "reason": reason,
        "returncode": proc.returncode,
        "command": cmd,
        "stderr_preview": _first_lines(proc.stderr or ""),
        "stdout_preview": _first_lines(proc.stdout or ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture codex --json traces for eval cases")
    parser.add_argument(
        "--cases",
        default="evals/circleci/cases/trace-cases.json",
        help="Path to trace cases JSON",
    )
    parser.add_argument(
        "--out-dir",
        default="evals/circleci/artifacts/latest",
        help="Directory to write artifacts",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Working directory to run codex from",
    )
    parser.add_argument("--model", default="gpt-5.3-codex", help="Model passed to codex")
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Continue and return zero even when one or more cases fail",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose diagnostics for preflight and case failures",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases).resolve()
    out_dir = Path(args.out_dir).resolve()
    workdir = Path(args.workspace_root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = load_cases(cases_path)
    summary: dict = {
        "generated_at": int(time.time()),
        "cases_file": str(cases_path),
        "workdir": str(workdir),
        "model": args.model,
        "preflight": {},
        "results": [],
    }

    if args.verbose:
        print("Capture configuration:")
        print(f"- cases: {cases_path}")
        print(f"- out_dir: {out_dir}")
        print(f"- workdir: {workdir}")
        print(f"- model: {args.model}")

    failures = 0
    preflight = run_preflight(workdir, args.model)
    summary["preflight"] = preflight

    if not preflight.get("ok"):
        print(f"Preflight failed: {preflight.get('reason')} (exit {preflight.get('returncode')})")
        if args.verbose:
            cmd = " ".join(preflight.get("command", []))
            print(f"Preflight command: {cmd}")
            stderr_preview = preflight.get("stderr_preview", "")
            stdout_preview = preflight.get("stdout_preview", "")
            if stderr_preview:
                print("Preflight stderr (preview):")
                print(stderr_preview)
            if stdout_preview:
                print("Preflight stdout (preview):")
                print(stdout_preview)
        print("Skipping case execution because codex exec is not healthy in this environment.")
        summary_path = out_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        if args.allow_failures:
            return 0
        return 1

    for case in cases:
        case_id = str(case.get("id", "")).strip()
        prompt = str(case.get("prompt", "")).strip()
        expected_skill = case.get("expected_skill")
        trigger_type = case.get("trigger_type")

        if not case_id or not prompt:
            failures += 1
            summary["results"].append(
                {
                    "id": case_id or "<missing-id>",
                    "error": "Case is missing required id or prompt",
                    "returncode": None,
                }
            )
            continue

        case_dir = out_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = case_dir / "events.jsonl"
        stderr_path = case_dir / "stderr.log"

        cmd = [
            "codex",
            "exec",
            "--json",
            "--cd",
            str(workdir),
            "-m",
            args.model,
            prompt,
        ]

        if args.verbose:
            print(f"Running case '{case_id}'...")

        start = time.time()
        with stdout_path.open("w", encoding="utf-8") as out_f, stderr_path.open("w", encoding="utf-8") as err_f:
            proc = subprocess.run(cmd, check=False, stdout=out_f, stderr=err_f, text=True)
        elapsed = round(time.time() - start, 3)

        line_count = 0
        if stdout_path.exists():
            line_count = sum(1 for _ in stdout_path.open("r", encoding="utf-8", errors="ignore"))

        result = {
            "id": case_id,
            "expected_skill": expected_skill,
            "trigger_type": trigger_type,
            "prompt": prompt,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "jsonl_line_count": line_count,
            "ok": proc.returncode == 0,
        }
        summary["results"].append(result)

        if proc.returncode != 0:
            failures += 1
            if args.verbose:
                print(f"Case '{case_id}' failed (exit {proc.returncode})")
                print(f"- prompt: {prompt}")
                print(f"- stderr file: {stderr_path}")
                stderr_tail = _tail_lines(stderr_path, max_lines=30)
                if stderr_tail:
                    print("- stderr tail:")
                    print(stderr_tail)
        elif args.verbose:
            print(f"Case '{case_id}' passed in {elapsed}s ({line_count} JSONL lines)")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote capture summary: {summary_path}")
    print(f"Cases: {len(summary['results'])}, Failures: {failures}")

    if failures and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
