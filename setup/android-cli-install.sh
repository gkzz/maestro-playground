#!/usr/bin/env bash
# Official Linux CLI download: https://developer.android.com/tools/agents/android-cli/download
set -euo pipefail

: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_PATH:?GITHUB_PATH is required}"
cli_dir="$RUNNER_TEMP/android-cli/bin"
mkdir -p "$cli_dir"
curl --fail --silent --show-error --location --retry 3 \
  https://dl.google.com/android/cli/latest/linux_x86_64/android \
  --output "$cli_dir/android"
chmod +x "$cli_dir/android"
echo "$cli_dir" >> "$GITHUB_PATH"
"$cli_dir/android" --no-metrics --version
