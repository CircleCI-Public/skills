#!/usr/bin/env bash
# Tag main for a Codex directory listing release.
#
# The version comes from the Codex manifest on main, so the tag always matches
# what the codex-bundle job checks and nobody has to type a version number.
# Tagging origin/main rather than HEAD means it works from any branch or an
# out-of-date checkout.
set -euo pipefail

plugin="${1:-circleci}"
manifest="plugins/${plugin}/.codex-plugin/plugin.json"

git fetch --quiet origin main
manifest_json=$(git show "origin/main:${manifest}")
version=$(printf '%s' "$manifest_json" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
tag="${plugin}-v${version}"

# Refuses if this version was already tagged, which means the manifest on main
# still needs a version bump.
if git ls-remote --exit-code --tags origin "refs/tags/${tag}" >/dev/null; then
  echo "$tag already exists. Bump \"version\" in $manifest on main first." >&2
  exit 1
fi

git tag "$tag" origin/main
git push --quiet origin "$tag"
echo "Pushed $tag. The codex-bundle job will build the zip to upload."
