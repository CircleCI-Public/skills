#!/usr/bin/env bash
# Tag main for a plugin release and publish it as a GitHub release.
#
# The version comes from the plugin's manifest on main and the release notes
# from its CHANGELOG.md entry, so nobody has to type either. Tagging origin/main
# rather than HEAD means it works from any branch or an out-of-date checkout.
#
# A circleci-v<version> tag also starts the codex-bundle job, which builds the
# zip for the Codex directory listing.
set -euo pipefail

# Checked before anything is pushed, so a missing login doesn't leave a tag
# without a release.
gh auth status >/dev/null

plugin="${1:-circleci}"
manifest="plugins/${plugin}/.claude-plugin/plugin.json"
changelog="plugins/${plugin}/CHANGELOG.md"

git fetch --quiet origin +refs/heads/main:refs/remotes/origin/main
version=$(git show "origin/main:${manifest}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
tag="${plugin}-v${version}"

# The lines under "## <version>", up to the next entry.
notes=$(git show "origin/main:${changelog}" \
  | awk -v v="$version" '$1 == "##" { if (on) exit; on = ($2 == v); next } on')
if [ -z "$notes" ]; then
  echo "$changelog on main has no \"## $version\" entry." >&2
  exit 1
fi

# A released version means the manifest on main still needs a bump. A tag
# without a release means an earlier run stopped after pushing it, so this run
# only creates the release.
if git ls-remote --exit-code --tags origin "refs/tags/${tag}" >/dev/null; then
  if gh release view "$tag" >/dev/null 2>&1; then
    echo "$tag is already released. Bump \"version\" in $manifest on main first." >&2
    exit 1
  fi
  echo "$tag exists without a release, so creating only the release." >&2
else
  git push --quiet origin "origin/main:refs/tags/${tag}"
fi

gh release create "$tag" --verify-tag --title "$plugin $version" --notes "$notes"
echo "Released $tag."
