#!/usr/bin/env bash
set -euo pipefail

api_level="${API_LEVEL:?API_LEVEL is required}"
arch="${ARCH:-x86_64}"
target="${TARGET:-google_apis}"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/usr/local/lib/android/sdk}}"

if [[ -n "${GITHUB_ENV:-}" ]]; then
  {
    echo "ANDROID_SDK_ROOT=$sdk_root"
    echo "ANDROID_HOME=$sdk_root"
    echo "ANDROID_AVD_HOME=${HOME}/.android/avd"
  } >> "$GITHUB_ENV"
fi

if [[ -n "${GITHUB_PATH:-}" ]]; then
  {
    echo "$sdk_root/platform-tools"
    echo "$sdk_root/emulator"
    echo "$sdk_root/cmdline-tools/latest/bin"
  } >> "$GITHUB_PATH"
fi

sdkmanager_cmd="$sdk_root/cmdline-tools/latest/bin/sdkmanager"
avdmanager_cmd="$sdk_root/cmdline-tools/latest/bin/avdmanager"

for cmd in "$sdkmanager_cmd" "$avdmanager_cmd"; do
  if [[ ! -x "$cmd" ]]; then
    echo "Required Android SDK command is missing or not executable: $cmd" >&2
    exit 1
  fi
done

set +o pipefail
yes | "$sdkmanager_cmd" --licenses >/dev/null
sdkmanager_status="${PIPESTATUS[1]}"
set -o pipefail
if [[ "$sdkmanager_status" -ne 0 ]]; then
  echo "Failed to accept Android SDK licenses." >&2
  exit "$sdkmanager_status"
fi

"$sdkmanager_cmd" --install \
  "platform-tools" \
  "emulator" \
  "platforms;android-${api_level}" \
  "system-images;android-${api_level};${target};${arch}"

for cmd in "$sdk_root/emulator/emulator" "$sdk_root/platform-tools/adb"; do
  if [[ ! -x "$cmd" ]]; then
    echo "Required Android SDK command is missing or not executable after install: $cmd" >&2
    exit 1
  fi
done
