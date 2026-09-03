#!/usr/bin/env bash
set -euo pipefail

runtime_name="${RUNTIME_NAME:?RUNTIME_NAME is required}"
device_type_name="${DEVICE_TYPE_NAME:?DEVICE_TYPE_NAME is required}"
simulator_name="${SIMULATOR_NAME:-MaestroPlayground}"

runtime_identifier="$(xcrun simctl list runtimes --json | python3 -c 'import json, sys; data = json.load(sys.stdin); name = sys.argv[1]; matches = [runtime["identifier"] for runtime in data["runtimes"] if runtime.get("name") == name and runtime.get("isAvailable")]; available = ", ".join(runtime.get("name", "") for runtime in data["runtimes"] if runtime.get("isAvailable")); matches or sys.exit(f"Runtime {name!r} is not available. Available runtimes: {available}"); print(matches[-1])' "$runtime_name")"
device_type_identifier="$(xcrun simctl list devicetypes --json | python3 -c 'import json, sys; data = json.load(sys.stdin); name = sys.argv[1]; matches = [device_type["identifier"] for device_type in data["devicetypes"] if device_type.get("name") == name]; available = ", ".join(device_type.get("name", "") for device_type in data["devicetypes"]); matches or sys.exit(f"Device type {name!r} is not available. Available device types: {available}"); print(matches[-1])' "$device_type_name")"

echo "Using runtime: $runtime_name ($runtime_identifier)"
echo "Using device type: $device_type_name ($device_type_identifier)"
device_id="$(xcrun simctl create "${simulator_name}-$(uuidgen)" "$device_type_identifier" "$runtime_identifier")"
xcrun simctl boot "$device_id"
xcrun simctl bootstatus "$device_id" -b

if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "SIMULATOR_UDID=$device_id" >> "$GITHUB_ENV"
fi
