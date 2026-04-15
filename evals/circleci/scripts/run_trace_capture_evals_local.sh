#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ARTIFACT_DIR="${ROOT_DIR}/evals/circleci/artifacts/latest"
STRICT="${STRICT:-0}"
VERBOSE="${VERBOSE:-0}"

CAPTURE_FLAGS=()
GRADE_FLAGS=()
if [[ "${STRICT}" != "1" ]]; then
  CAPTURE_FLAGS+=(--allow-failures)
  GRADE_FLAGS+=(--allow-failures)
fi
if [[ "${VERBOSE}" == "1" ]]; then
  CAPTURE_FLAGS+=(--verbose)
  GRADE_FLAGS+=(--verbose)
fi

echo "Trace eval run configuration:"
echo "- strict: ${STRICT}"
echo "- verbose: ${VERBOSE}"
echo "- artifacts: ${ARTIFACT_DIR}"

python3 "${SCRIPT_DIR}/capture_trace_eval_jsonl.py" \
  --cases "${ROOT_DIR}/evals/circleci/cases/trace-cases.json" \
  --workspace-root "${ROOT_DIR}" \
  --out-dir "${ARTIFACT_DIR}" \
  "${CAPTURE_FLAGS[@]}"

python3 "${SCRIPT_DIR}/grade_trace_eval_jsonl.py" \
  --summary "${ARTIFACT_DIR}/summary.json" \
  --report "${ARTIFACT_DIR}/report.json" \
  "${GRADE_FLAGS[@]}"

echo "Final report:"
cat "${ARTIFACT_DIR}/report.json"
