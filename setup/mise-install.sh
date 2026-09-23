#!/usr/bin/env bash
set -euo pipefail

# CLIのusageを表示する。
usage() {
  echo 'usage: ./setup/mise-install.sh [--dry-run|--apply]'
}

# 最初のCLI引数を検証し、選択されたmodeをstdoutへ出力する。
# 引数がない場合は--dry-runを使用する。
parse_mode() {
  case "${1:---dry-run}" in
    --dry-run|--apply) printf '%s\n' "${1:---dry-run}" ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
}

# CIから渡されたmiseのversionとplatformごとのSHA256を検証する。
# これらの値はcomposite actionからenvironment variablesとして意図的に渡す。
require_ci_pin() {
  MISE_VERSION="${MISE_VERSION:?MISE_VERSION is required}"
  MISE_SHA256_LINUX_X64="${MISE_SHA256_LINUX_X64:?MISE_SHA256_LINUX_X64 is required}"
  MISE_SHA256_LINUX_ARM64="${MISE_SHA256_LINUX_ARM64:?MISE_SHA256_LINUX_ARM64 is required}"
  MISE_SHA256_MACOS_X64="${MISE_SHA256_MACOS_X64:?MISE_SHA256_MACOS_X64 is required}"
  MISE_SHA256_MACOS_ARM64="${MISE_SHA256_MACOS_ARM64:?MISE_SHA256_MACOS_ARM64 is required}"
}

# 現在のOS/architectureを判定し、download用のplatformとSHA256を選択する。
# install_miseで使うglobalなplatformとsha variablesを設定する。
resolve_platform() {
  case "$(uname -s):$(uname -m)" in
    Linux:x86_64|Linux:amd64)
      platform=linux-x64
      archive_suffix=.tar.xz
      sha="$MISE_SHA256_LINUX_X64"
      ;;
    Linux:aarch64|Linux:arm64)
      platform=linux-arm64
      archive_suffix=.tar.xz
      sha="$MISE_SHA256_LINUX_ARM64"
      ;;
    Darwin:x86_64|Darwin:amd64)
      platform=macos-x64
      archive_suffix=.tar.xz
      sha="$MISE_SHA256_MACOS_X64"
      ;;
    Darwin:arm64|Darwin:aarch64)
      platform=macos-arm64
      archive_suffix=.tar.xz
      sha="$MISE_SHA256_MACOS_ARM64"
      ;;
    *)
      echo "error: unsupported platform: $(uname -s):$(uname -m)" >&2
      return 1
      ;;
  esac
}

# installation pathがabsoluteで、まだ存在していないことを検証する。
# MISE_BOOTSTRAP_TARGETを読み取り、未指定の場合は~/.local/bin/miseを使用する。
validate_target() {
  case "$install_path" in
    /*) ;;
    *) echo "error: install path must be absolute" >&2; return 1 ;;
  esac

  if [ -e "$install_path" ] || [ -L "$install_path" ]; then
    echo "error: target exists: $install_path" >&2
    return 1
  fi
}

# miseをdownload、検証し、install_pathへinstallする。
# filesystemを変更したりnetworkへアクセスしたりするのはこのfunctionだけ。
install_mise() {
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' RETURN
  archive="$tmp_dir/mise$archive_suffix"
  extracted_dir="$tmp_dir/extracted"
  mkdir -p "$extracted_dir"

  curl -fsSL \
    -o "$archive" \
    "https://github.com/jdx/mise/releases/download/v${MISE_VERSION}/mise-v${MISE_VERSION}-${platform}${archive_suffix}"

  printf '%s  %s\n' "$sha" "$archive" |
    if command -v sha256sum >/dev/null; then sha256sum -c -; else shasum -a 256 -c -; fi

  case "$platform" in
    linux-*) tar -xJf "$archive" -C "$extracted_dir" ;;
    macos-*) tar -xJf "$archive" -C "$extracted_dir" ;;
  esac

  install -d "$(dirname "$install_path")"
  install -m 755 "$(find "$extracted_dir" -type f -name mise -print -quit)" "$install_path"
}

# Main CLI entry point。
# 最初の引数に--dry-runまたは--applyを受け取り、デフォルトは--dry-runとする。
# CI専用のversionとSHA256はenvironment variablesから読み取る。
main() {
  local mode
  if [ "${1:-}" = '-h' ] || [ "${1:-}" = '--help' ]; then
    usage
    return 0
  fi
  mode="$(parse_mode "${1:-}")"
  install_path="${MISE_BOOTSTRAP_TARGET:-$HOME/.local/bin/mise}"

  validate_target

  if [ "$mode" = '--dry-run' ]; then
    echo "plan: bootstrap_mise $install_path"
    return 0
  fi

  require_ci_pin
  resolve_platform
  install_mise
}

main "$@"
