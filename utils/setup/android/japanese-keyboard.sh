#!/usr/bin/env bash
set -euo pipefail

# Requires a Google Play system image containing Gboard. Do not substitute an
# ASCII/clipboard IME: this spike must exercise Japanese composition itself.
adb_args=(-s "${ANDROID_EMULATOR_SERIAL:-emulator-5554}")
ime='com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME'
adb "${adb_args[@]}" shell ime list -s | tr -d '\r' | grep -Fx "$ime"
adb "${adb_args[@]}" shell ime enable "$ime"
adb "${adb_args[@]}" shell ime set "$ime"
adb "${adb_args[@]}" shell settings put secure show_ime_with_hard_keyboard 1
adb "${adb_args[@]}" shell am start -W -n \
  com.google.android.inputmethod.latin/com.google.android.apps.inputmethod.latin.preference.SettingsActivity
