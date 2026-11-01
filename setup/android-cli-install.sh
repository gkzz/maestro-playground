#!/usr/bin/env bash
# Official Linux CLI download: https://developer.android.com/tools/agents/android-cli/download
set -euo pipefail

: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_PATH:?GITHUB_PATH is required}"
cli_dir="$RUNNER_TEMP/android-cli/bin"
cli_version=1.1.16717390
# Update the version and digest together. Hash the CLI itself, not its downloader.
cli_sha256=b34ed0baeeffa2aaee2720d82491b975835696e2e56840449078bec885436564
mkdir -p "$cli_dir"
curl --fail --silent --show-error --location --retry 3 \
  "https://dl.google.com/android/cli/$cli_version/linux_x86_64/android-cli" \
  --output "$cli_dir/android"
printf '%s  %s\n' "$cli_sha256" "$cli_dir/android" | sha256sum --check --status
chmod +x "$cli_dir/android"
echo "$cli_dir" >> "$GITHUB_PATH"
"$cli_dir/android" --no-metrics --version
