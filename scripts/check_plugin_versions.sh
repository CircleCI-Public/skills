#!/usr/bin/env bash
# Fail when a plugin changed without a new version.
#
# Claude Code and Codex only update an installed plugin when the version in its
# manifest changes, so a change merged without a bump never reaches anyone who
# already installed it. For each plugin this checks that:
#   - if its files differ from where the branch left main, its version differs too
#   - its Claude Code and Codex manifests carry the same version
#   - its CHANGELOG.md has a "## <version>" entry
#
# On main nothing differs from the merge base, so only the last two apply there.
set -euo pipefail

json_version() {
  python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])'
}

git fetch --quiet origin main
base=$(git merge-base origin/main HEAD)
status=0

for dir in plugins/*/; do
  plugin=$(basename "$dir")
  claude="${dir}.claude-plugin/plugin.json"
  codex="${dir}.codex-plugin/plugin.json"
  changelog="${dir}CHANGELOG.md"
  version=$(json_version < "$claude")

  manifests="$claude"
  if [ -f "$codex" ]; then
    manifests="$claude and $codex"
    codex_version=$(json_version < "$codex")
    if [ "$codex_version" != "$version" ]; then
      echo "$plugin: $claude says $version but $codex says $codex_version." >&2
      status=1
    fi
  fi

  # A plugin that is new on this branch has nothing to bump from.
  if ! git diff --quiet "$base" -- "$dir" && git cat-file -e "$base:$claude" 2>/dev/null; then
    old=$(git show "$base:$claude" | json_version)
    if [ "$old" = "$version" ]; then
      echo "$plugin: changed since main but still $version. Bump \"version\" in $manifests." >&2
      status=1
    fi
  fi

  if ! awk -v v="$version" '$1 == "##" && $2 == v { found = 1 } END { exit !found }' "$changelog" 2>/dev/null; then
    echo "$plugin: $changelog has no \"## $version\" entry." >&2
    status=1
  fi
done

exit "$status"
