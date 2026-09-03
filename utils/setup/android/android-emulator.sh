#!/usr/bin/env bash
set -euo pipefail

api_level="${API_LEVEL:?API_LEVEL is required}"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/usr/local/lib/android/sdk}}"
adb_cmd="$sdk_root/platform-tools/adb"
emulator_cmd="$sdk_root/emulator/emulator"
avd_name="${AVD_NAME:-maestro-android-api-${api_level}}"
emulator_port="${EMULATOR_PORT:-5554}"
emulator_boot_timeout="${EMULATOR_BOOT_TIMEOUT:-1200}"
emulator_options="${EMULATOR_OPTIONS:-no-window -gpu swiftshader_indirect -no-snapshot -noaudio -no-boot-anim -accel on -no-metrics -camera-back emulated}"
device_serial="emulator-${emulator_port}"
deadline=$((SECONDS + emulator_boot_timeout))
emulator_log="${RUNNER_TEMP:-/tmp}/android-emulator.log"

if [[ -n "${GITHUB_ENV:-}" ]]; then
  {
    echo "ANDROID_EMULATOR_SERIAL=$device_serial"
    echo "ANDROID_EMULATOR_LOG=$emulator_log"
  } >> "$GITHUB_ENV"
fi

echo "Available AVDs:"
"$emulator_cmd" -list-avds
echo "Starting Android Emulator ${device_serial} from AVD ${avd_name}."
# shellcheck disable=SC2086
nohup "$emulator_cmd" @"$avd_name" -port "$emulator_port" $emulator_options > "$emulator_log" 2>&1 &
emulator_pid="$!"

until [[ "$("$adb_cmd" -s "$device_serial" get-state 2>/dev/null || true)" == "device" ]]; do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    echo "Android Emulator process exited before connecting." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  if (( SECONDS >= deadline )); then
    echo "Android Emulator did not connect within ${emulator_boot_timeout} seconds." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  sleep 5
done

until [[ "$("$adb_cmd" -s "$device_serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    echo "Android Emulator process exited before boot completed." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  if (( SECONDS >= deadline )); then
    echo "Android Emulator did not boot within ${emulator_boot_timeout} seconds." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  sleep 5
done

"$adb_cmd" -s "$device_serial" shell input keyevent 82 >/dev/null 2>&1 || true
"$adb_cmd" -s "$device_serial" shell settings put global window_animation_scale 0
"$adb_cmd" -s "$device_serial" shell settings put global transition_animation_scale 0
"$adb_cmd" -s "$device_serial" shell settings put global animator_duration_scale 0
