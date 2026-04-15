#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ARTIFACT_DIR="${ROOT_DIR}/evals/circleci/artifacts/invocation-smoke/latest"
STRICT="${STRICT:-0}"
VERBOSE="${VERBOSE:-0}"

FLAGS=()
if [[ "${STRICT}" != "1" ]]; then
  FLAGS+=(--allow-failures)
fi
if [[ "${VERBOSE}" == "1" ]]; then
  FLAGS+=(--verbose)
fi

echo "Invocation smoke run configuration:"
echo "- strict: ${STRICT}"
echo "- verbose: ${VERBOSE}"
echo "- artifacts: ${ARTIFACT_DIR}"

python3 "${SCRIPT_DIR}/run_invocation_smoke_evals.py" \
  --cases "${ROOT_DIR}/evals/circleci/cases/skill-invocation-smoke-cases.json" \
  --workspace-root "${ROOT_DIR}" \
  --out-dir "${ARTIFACT_DIR}" \
  "${FLAGS[@]}"
