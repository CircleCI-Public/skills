#!/usr/bin/env bash
# Package a plugin as the zip the Codex portal expects.
#
# The Codex listing is uploaded by hand and there is no API to automate it, so
# the most that can be automated is producing the exact artifact to upload. CI
# runs this on a <plugin>-v<version> tag, so every upload comes from a tagged
# commit rather than from whatever happens to be in someone's working copy.
#
# Run it locally to preview the bundle for HEAD.
set -euo pipefail

plugin="${1:-circleci}"
out="${2:-dist}"
src="plugins/${plugin}"
manifest="${src}/.codex-plugin/plugin.json"

# Read from HEAD, not the working tree, so the version matches the contents.
manifest_json=$(git show "HEAD:${manifest}")
version=$(printf '%s' "$manifest_json" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')

if [ -n "${CIRCLE_TAG:-}" ] && [ "$CIRCLE_TAG" != "${plugin}-v${version}" ]; then
  echo "Tag $CIRCLE_TAG does not match $manifest, which says $version" >&2
  exit 1
fi

zip_path="${out}/${plugin}-${version}.zip"
mkdir -p "$out"

# Archiving the HEAD:<dir> tree includes tracked files only and puts the
# plugin's own files at the root of the zip, which is the layout the portal
# expects.
#
# .claude-plugin is excluded: it is the other channel's manifest and would put a
# second, conflicting source of truth inside the bundle. So are .lsp.json and
# lsp/, the language server that only Claude Code starts.
git archive --format=zip --output="$zip_path" "HEAD:${src}" \
  ':(exclude).claude-plugin' ':(exclude).lsp.json' ':(exclude)lsp'

echo "$zip_path"
echo "  version  $version"
echo "  commit   $(git rev-parse --short HEAD)"
echo "  skills   $(unzip -Z1 "$zip_path" | grep -c 'SKILL.md$')"
