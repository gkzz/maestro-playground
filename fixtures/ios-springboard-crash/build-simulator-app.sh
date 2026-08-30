#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
build_root="${1:-"$script_dir/build"}"
app_dir="$build_root/Build/Products/Release-iphonesimulator/Maestro3494.app"
sdk_root="$(xcrun --sdk iphonesimulator --show-sdk-path)"
arch="$(uname -m)"

rm -rf "$build_root"
mkdir -p "$app_dir"

xcrun swiftc \
  -target "${arch}-apple-ios17.0-simulator" \
  -sdk "$sdk_root" \
  -Osize \
  -parse-as-library \
  "$script_dir/App/App.swift" \
  -framework UIKit \
  -framework WebKit \
  -o "$app_dir/Maestro3494"

cp "$script_dir/App/Info.plist" "$app_dir/Info.plist"

plutil -replace CFBundleSupportedPlatforms -json '["iPhoneSimulator"]' "$app_dir/Info.plist"
plutil -replace DTPlatformName -string iphonesimulator "$app_dir/Info.plist"
plutil -replace DTSDKName -string "$(basename "$sdk_root")" "$app_dir/Info.plist"
plutil -replace MinimumOSVersion -string "17.0" "$app_dir/Info.plist"

codesign --force --sign - "$app_dir"

echo "$app_dir"
