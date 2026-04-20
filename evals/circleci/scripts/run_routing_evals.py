#!/usr/bin/env python3
"""Runnable eval loop for CircleCI plugin skills.

Checks:
1) Skill file/frontmatter sanity for all skills under plugins/circleci/skills.
2) Optional quick_validate.py pass when available.
3) Prompt-routing regression cases from evals/circleci/cases/skill-routing-cases.json.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
KV_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.+?)\s*$")


@dataclass
class SkillFile:
    folder: str
    path: Path
    name: str
    description: str


def parse_frontmatter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("Missing YAML frontmatter fence")

    fields: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        kv = KV_RE.match(line)
        if not kv:
            raise ValueError(f"Unparseable frontmatter line: {raw_line!r}")
        key, value = kv.group(1), kv.group(2)
        fields[key] = value.strip().strip('"').strip("'")
    return fields


def discover_skills(skills_root: Path) -> list[SkillFile]:
    skill_files: list[SkillFile] = []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        folder = skill_md.parent.name
        fields = parse_frontmatter(skill_md)
        name = fields.get("name", "")
        description = fields.get("description", "")
        skill_files.append(SkillFile(folder=folder, path=skill_md, name=name, description=description))
    return skill_files


def run_quick_validate(quick_validate_py: Path, skill_dir: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(quick_validate_py), str(skill_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def tokenize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def predict_skill(prompt: str, skill_phrases: dict[str, list[str]]) -> str | None:
    norm = tokenize(prompt)

    # Explicit invocation should win immediately, e.g. "$circleci-builds".
    for skill_name in skill_phrases.keys():
        if f"${skill_name.lower()}" in norm:
            return skill_name

    best_name: str | None = None
    best_score = 0

    for skill_name, phrases in skill_phrases.items():
        score = 0
        for phrase in phrases:
            if tokenize(phrase) in norm:
                score += 1
        if score > best_score:
            best_score = score
            best_name = skill_name

    if best_score == 0:
        return None
    return best_name


def run_routing_eval(eval_data: dict[str, Any]) -> tuple[list[str], int, int]:
    skills_blob = eval_data.get("skills", {})
    cases = eval_data.get("cases", [])

    skill_phrases: dict[str, list[str]] = {
        name: list(meta.get("phrases", [])) for name, meta in skills_blob.items()
    }

    failures: list[str] = []
    passed = 0
    total = 0

    for i, case in enumerate(cases, start=1):
        prompt = str(case.get("prompt", "")).strip()
        expected = case.get("expected")
        predicted = predict_skill(prompt, skill_phrases)
        total += 1

        if predicted == expected:
            passed += 1
            continue

        failures.append(
            "\n".join(
                [
                    f"Case {i} failed",
                    f"  prompt: {prompt}",
                    f"  expected: {expected}",
                    f"  predicted: {predicted}",
                ]
            )
        )

    return failures, passed, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CircleCI skill eval loop")
    parser.add_argument(
        "--skills-root",
        default=str(Path(__file__).resolve().parents[3] / "plugins/circleci/skills"),
        help="Path to CircleCI plugin skills directory",
    )
    parser.add_argument(
        "--cases-file",
        default=str(Path(__file__).resolve().parents[1] / "cases/skill-routing-cases.json"),
        help="Path to eval case JSON file",
    )
    parser.add_argument(
        "--quick-validate-path",
        default=str(Path(__file__).resolve().parent / "quick_validate.py"),
        help="Path to skill-creator quick_validate.py",
    )
    args = parser.parse_args()

    skills_root = Path(args.skills_root).expanduser().resolve()
    eval_file = Path(args.cases_file).expanduser().resolve()
    quick_validate_py = Path(args.quick_validate_path).expanduser().resolve()

    if not skills_root.exists():
        print(f"ERROR: skills root not found: {skills_root}")
        return 2
    if not eval_file.exists():
        print(f"ERROR: eval file not found: {eval_file}")
        return 2

    errors: list[str] = []
    warnings: list[str] = []

    skills = discover_skills(skills_root)
    if not skills:
        print(f"ERROR: No SKILL.md files found under {skills_root}")
        return 2

    print("== Frontmatter checks ==")
    for skill in skills:
        print(f"- {skill.folder}: {skill.path}")

        if skill.name == "":
            errors.append(f"{skill.path}: missing 'name' in frontmatter")
        if skill.description == "":
            errors.append(f"{skill.path}: missing 'description' in frontmatter")

    if quick_validate_py.exists():
        print("\n== quick_validate checks ==")
        for skill in skills:
            ok, output = run_quick_validate(quick_validate_py, skill.path.parent)
            if ok:
                print(f"- {skill.folder}: PASS")
            else:
                errors.append(f"quick_validate failed for {skill.path.parent}\n{output}")
    else:
        warnings.append(f"quick_validate.py not found at {quick_validate_py}; skipped")

    print("\n== Routing eval checks ==")
    eval_data = json.loads(eval_file.read_text(encoding="utf-8"))
    failures, passed, total = run_routing_eval(eval_data)
    print(f"- cases: {passed}/{total} passed")
    errors.extend(failures)

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nFailures:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("\nAll CircleCI skill evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
