#!/usr/bin/env bash
# CI-only setup using the same mise config and lockfile as local builds.
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
export MISE_CONFIG_FILE="$script_dir/../.config/flutter/mise.toml"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
: "${GITHUB_PATH:?GITHUB_PATH is required}"

mise trust --yes "$MISE_CONFIG_FILE"
mise install --locked flutter
flutter_root="$(mise where flutter)"
echo "FLUTTER_ROOT=$flutter_root" >> "$GITHUB_ENV"
echo "$flutter_root/bin" >> "$GITHUB_PATH"
"$flutter_root/bin/flutter" --version
