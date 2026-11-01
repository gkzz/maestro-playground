#!/usr/bin/env bash
# CI-only Flutter setup from the official repository; no third-party Action.
set -euo pipefail

version=3.38.5
revision=f6ff1529fd6d8af5f706051d9251ac9231c83407
flutter_root="${RUNNER_TEMP:?RUNNER_TEMP is required}/flutter-$version"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
: "${GITHUB_PATH:?GITHUB_PATH is required}"

# Use a fresh checkout and pin the commit as well as the documented version.
git init --quiet "$flutter_root"
git -C "$flutter_root" remote add origin https://github.com/flutter/flutter.git
git -C "$flutter_root" fetch --depth 1 origin "refs/tags/$version:refs/tags/$version"
if [[ "$(git -C "$flutter_root" rev-parse FETCH_HEAD)" != "$revision" ]]; then
  echo "Flutter $version tag does not match the pinned commit." >&2
  exit 1
fi
git -C "$flutter_root" checkout --quiet --detach FETCH_HEAD

echo "FLUTTER_ROOT=$flutter_root" >> "$GITHUB_ENV"
echo "$flutter_root/bin" >> "$GITHUB_PATH"
"$flutter_root/bin/flutter" --version
