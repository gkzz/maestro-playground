#!/usr/bin/env bash
set -euo pipefail

api_level="${API_LEVEL:?API_LEVEL is required}"
arch="${ARCH:-x86_64}"
target="${TARGET:-google_apis}"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/usr/local/lib/android/sdk}}"
ndk_version="${NDK_VERSION:-}"
android_cmd="${ANDROID_CLI:-android}"
cmdline_tools_version=22.0

export ANDROID_SDK_ROOT="$sdk_root"
export ANDROID_HOME="$sdk_root"

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
    echo "$sdk_root/cmdline-tools/$cmdline_tools_version/bin"
  } >> "$GITHUB_PATH"
fi

command -v "$android_cmd" >/dev/null || {
  echo "Install Android CLI: https://developer.android.com/tools/agents/android-cli/download" >&2
  exit 1
}

packages=(
  "platform-tools"
  "emulator"
  "platforms/android-${api_level}"
  "system-images/android-${api_level}/${target}/${arch}"
  "cmdline-tools/$cmdline_tools_version"
  # Build Tools for the demo app's Android Gradle Plugin (see e2e/build_demo_app).
  "build-tools/35.0.0"
)
# Keep avdmanager for explicit API/image selection and root-capable google_apis images.
# android emulator create currently selects a Play Store image that cannot run adb root.
"$android_cmd" --no-metrics --sdk="$sdk_root" sdk install "${packages[@]}"

if [[ -n "$ndk_version" ]]; then
  # Large NDK downloads can fail with a transient connection close in CI.
  for attempt in 1 2 3; do
    if "$android_cmd" --no-metrics --sdk="$sdk_root" sdk install "ndk/${ndk_version}"; then
      break
    fi
    if (( attempt == 3 )); then
      echo "Failed to install NDK ${ndk_version} after ${attempt} attempts" >&2
      exit 1
    fi
    echo "NDK install failed (attempt ${attempt}/3); retrying in $((attempt * 10)) seconds" >&2
    sleep "$((attempt * 10))"
  done
fi

for cmd in "$sdk_root/emulator/emulator" "$sdk_root/platform-tools/adb" "$sdk_root/cmdline-tools/$cmdline_tools_version/bin/avdmanager"; do
  if [[ ! -x "$cmd" ]]; then
    echo "Required Android SDK command is missing or not executable after install: $cmd" >&2
    exit 1
  fi
done
