#!/usr/bin/env bash
set -euo pipefail

api_level="${API_LEVEL:?API_LEVEL is required}"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-/usr/local/lib/android/sdk}}"
adb_cmd="$sdk_root/platform-tools/adb"
emulator_cmd="$sdk_root/emulator/emulator"
avd_name="${AVD_NAME:-maestro-android-api-${api_level}}"
emulator_port="${EMULATOR_PORT:-5554}"
emulator_boot_timeout="${EMULATOR_BOOT_TIMEOUT:-1200}"
emulator_options="${EMULATOR_OPTIONS:-no-window -gpu swiftshader -no-snapshot -noaudio -no-boot-anim -accel on -no-metrics -camera-back emulated}"
device_serial="emulator-${emulator_port}"
deadline=$((SECONDS + emulator_boot_timeout))
emulator_log="${RUNNER_TEMP:-/tmp}/android-emulator.log"
e2e_locale="${E2E_LOCALE:-ja}"

case "$e2e_locale" in
  en) device_locale="en-US" ;;
  ja) device_locale="ja-JP" ;;
  *)
    echo "E2E_LOCALE must be one of: en, ja" >&2
    exit 1
    ;;
esac

if [[ -n "${GITHUB_ENV:-}" ]]; then
  {
    echo "ANDROID_EMULATOR_SERIAL=$device_serial"
    echo "ANDROID_EMULATOR_LOG=$emulator_log"
  } >> "$GITHUB_ENV"
fi

echo "Available AVDs:"
"$emulator_cmd" -list-avds
echo "Starting Android Emulator ${device_serial} from AVD ${avd_name}."
start_emulator() {
  # shellcheck disable=SC2086
  nohup "$emulator_cmd" @"$avd_name" -port "$emulator_port" $emulator_options > "$emulator_log" 2>&1 &
  emulator_pid="$!"
}
start_emulator

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

echo "Restarting adbd as root to apply locale ${device_locale}."
if ! "$adb_cmd" -s "$device_serial" root; then
  echo "Android Emulator does not allow adbd to run as root." >&2
  tail -n 200 "$emulator_log" >&2 || true
  exit 1
fi

until [[ "$("$adb_cmd" -s "$device_serial" shell id -u 2>/dev/null | tr -d '\r')" == "0" ]]; do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    echo "Android Emulator process exited while restarting adbd as root." >&2
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  if (( SECONDS >= deadline )); then
    echo "Android Emulator did not reconnect with root adbd within ${emulator_boot_timeout} seconds." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  sleep 2
done

"$adb_cmd" -s "$device_serial" shell setprop persist.sys.locale "$device_locale"
"$adb_cmd" -s "$device_serial" reboot

# Bound reconnection by the same deadline used for startup.
restart_attempted=false
until [[ "$("$adb_cmd" -s "$device_serial" get-state 2>/dev/null || true)" == "device" ]]; do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    if [[ "$restart_attempted" == false ]] && (( SECONDS < deadline )); then
      echo "Android Emulator exited during locale reboot; starting it once more with the saved locale." >&2
      tail -n 80 "$emulator_log" >&2 || true
      restart_attempted=true
      start_emulator
      continue
    fi
    echo "Android Emulator process exited while reconnecting after reboot for locale ${device_locale}." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  if (( SECONDS >= deadline )); then
    echo "Android Emulator did not reconnect after reboot for locale ${device_locale}." >&2
    "$adb_cmd" devices -l >&2 || true
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  sleep 2
done

# init.svc.bootanim may be empty with -no-boot-anim; use boot completion instead.
echo "Waiting for Android to finish restarting with locale ${device_locale}."
while true; do
  boot_completed=$("$adb_cmd" -s "$device_serial" shell getprop sys.boot_completed 2>&1 | tr -d '\r' || true)
  bootanim=$("$adb_cmd" -s "$device_serial" shell getprop init.svc.bootanim 2>&1 | tr -d '\r' || true)
  current_locale=$("$adb_cmd" -s "$device_serial" shell getprop persist.sys.locale 2>&1 | tr -d '\r' || true)
  package_ready=false
  if package_path=$("$adb_cmd" -s "$device_serial" shell pm path android 2>&1 | tr -d '\r'); then
    [[ "$package_path" == package:* ]] && package_ready=true
  fi
  echo "Android readiness: sys.boot_completed=[$boot_completed], init.svc.bootanim=[$bootanim], persist.sys.locale=[$current_locale], pm path android=[$package_path]"
  if [[ "$boot_completed" == "1" \
    && "$current_locale" == "$device_locale" && "$package_ready" == "true" ]]; then
    break
  fi
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    if [[ "$restart_attempted" == false ]] && (( SECONDS < deadline )); then
      echo "Android Emulator exited while applying locale; starting it once more with the saved locale." >&2
      tail -n 80 "$emulator_log" >&2 || true
      restart_attempted=true
      start_emulator
      sleep 5
      continue
    fi
    echo "Android Emulator process exited while applying locale ${device_locale}." >&2
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  if (( SECONDS >= deadline )); then
    echo "Android Emulator did not become ready after applying locale ${device_locale}." >&2
    tail -n 200 "$emulator_log" >&2 || true
    exit 1
  fi
  sleep 5
done

"$adb_cmd" -s "$device_serial" shell input keyevent 82 >/dev/null 2>&1 || true
"$adb_cmd" -s "$device_serial" shell settings put global window_animation_scale 0
"$adb_cmd" -s "$device_serial" shell settings put global transition_animation_scale 0
"$adb_cmd" -s "$device_serial" shell settings put global animator_duration_scale 0
