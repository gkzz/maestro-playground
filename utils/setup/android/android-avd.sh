#!/usr/bin/env bash
set -euo pipefail

api_level="${API_LEVEL:?API_LEVEL is required}"
arch="${ARCH:-x86_64}"
target="${TARGET:-google_apis}"
profile="${PROFILE:-pixel_7}"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/usr/local/lib/android/sdk}}"
avdmanager_cmd="$sdk_root/cmdline-tools/latest/bin/avdmanager"
emulator_cmd="$sdk_root/emulator/emulator"
avd_name="${AVD_NAME:-maestro-android-api-${api_level}}"
avd_home="${ANDROID_AVD_HOME:-${HOME}/.android/avd}"

mkdir -p "$avd_home"

set +o pipefail
printf "no\n" | "$avdmanager_cmd" create avd \
  --force \
  --name "$avd_name" \
  --package "system-images;android-${api_level};${target};${arch}" \
  --device "$profile"
avdmanager_status="${PIPESTATUS[1]}"
set -o pipefail

if [[ "$avdmanager_status" -ne 0 ]]; then
  echo "Failed to create Android Virtual Device: $avd_name" >&2
  exit "$avdmanager_status"
fi

if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "ANDROID_AVD_NAME=$avd_name" >> "$GITHUB_ENV"
fi

if [[ ! -f "${avd_home}/${avd_name}.ini" ]]; then
  echo "AVD was not created at expected path: ${avd_home}/${avd_name}.ini" >&2
  echo "Available AVDs:" >&2
  "$emulator_cmd" -list-avds >&2 || true
  find "$avd_home" -maxdepth 2 -type f -print >&2 || true
  exit 1
fi

if ! "$emulator_cmd" -list-avds | grep -Fxq "$avd_name"; then
  echo "Created AVD is not visible to the emulator: $avd_name" >&2
  echo "Available AVDs:" >&2
  "$emulator_cmd" -list-avds >&2 || true
  exit 1
fi
