#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SKILLS_ROOT="${WORKSPACE_ROOT}/plugins/circleci/skills"
CASES_FILE="${WORKSPACE_ROOT}/evals/circleci/cases/skill-routing-cases.json"

"${SCRIPT_DIR}/run_routing_evals.py" \
  --skills-root "${SKILLS_ROOT}" \
  --cases-file "${CASES_FILE}" \
  "$@"
