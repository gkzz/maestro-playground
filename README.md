# maestro-playground

[![Lint](https://github.com/gkzz/maestro-playground/actions/workflows/lint.yml/badge.svg)](https://github.com/gkzz/maestro-playground/actions/workflows/lint.yml)
[![E2E](https://github.com/gkzz/maestro-playground/actions/workflows/e2e.yml/badge.svg)](https://github.com/gkzz/maestro-playground/actions/workflows/e2e.yml)

Maestro で iOS Simulator / Android Emulator を操作するための最小サンプルです。

Maestro Flow から OS 標準の「設定」アプリと、追加のテスト対象アプリを起動する検証用リポジトリです。追加アプリは [mobile-dev-inc/Maestro](https://github.com/mobile-dev-inc/Maestro/tree/main/e2e) の E2E と同じ配布済みアプリを [e2e/manifest.txt](e2e/manifest.txt) から取得します。

## File tree

```
.
├── .github
│   ├── actions
│   │   ├── setup-android-emulator
│   │   └── setup-ios-simulator
│   └── workflows
│       ├── e2e.yml
│       └── lint.yml
├── .gitignore
├── .maestro
│   ├── settings
│   │   ├── android.yml
│   │   └── ios.yml
│   └── wikipedia
│       ├── android.yml
│       └── ios.yml
├── e2e
│   ├── download_apps
│   ├── install_apps
│   └── manifest.txt
├── docs
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   └── README.md
├── utils
│   └── setup
│       ├── android
│       │   ├── android-avd.sh
│       │   ├── android-emulator.sh
│       │   └── android-sdk.sh
│       └── ios
│           └── ios-simulator.sh
├── .config
│   └── mise
│       └── config.toml
├── Makefile
├── README.md
└── renovate.json5
```

## Getting started

Makefile 経由で [.config/mise/config.toml](.config/mise/config.toml) に定義された Maestro CLI をインストールします。
インストール対象を `maestro` に限定し、リポジトリの `mise.lock` に従ってインストールします。ホームの mise 設定による lockfile の警告が出る場合がありますが、他のツールはインストールしません。

```sh
make install
```

Android Emulator を起動してから実行します。WSL から Windows 側の Android Emulator / adb server に接続する場合は、git 管理外の `local/android.env` を作成します。

```sh
mkdir -p local
cat > local/android.env <<'EOF'
ADB_SERVER_SOCKET=tcp:127.0.0.1:5037
MAESTRO_HOST=127.0.0.1
EOF
```

`MAESTRO_HOST` が不要な環境では省略できます。`local/` は git 管理外です。

Linux 上で Android SDK と Emulator もセットアップする場合は、Makefile の target を使います。

Android command-line tools（`cmdline-tools/latest/bin`）を事前に配置し、同じシェルで `ANDROID_HOME` と `ANDROID_SDK_ROOT` を同じ SDK ディレクトリに設定してください。SDK の選択順は `ANDROID_SDK_ROOT`、`ANDROID_HOME`、`/usr/local/lib/android/sdk` です。SDK ステップは Platform 36 と `google_apis;x86_64` の system image をインストールします。ローカルでは子プロセスの環境変数は親シェルに反映されないため、SDK の `platform-tools` と `emulator` も `PATH` に追加してください。

```sh
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis make setup-android-sdk
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_7 make setup-android-avd
API_LEVEL=36 EMULATOR_PORT=5554 make boot-android-emulator
```

```sh
make download-android-apps
make install-android-apps
make test-android-settings
make test-android-wikipedia
```

iOS Simulator を起動してから実行します。

```sh
RUNTIME_NAME="iOS 26.2" DEVICE_TYPE_NAME="iPhone 17 Pro" make setup-ios-simulator
make download-ios-apps
make install-ios-apps
make test-ios-settings
make test-ios-wikipedia
```

全 flow の syntax check は次で実行できます。

```sh
make check-syntax
```

この PR で目指す構成は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) に、ローカルでの実行手順は [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) にまとめています。

## Test target apps

- `settings/android.yml`: Android OS Settings (`com.android.settings`)
- `settings/ios.yml`: iOS Settings (`com.apple.Preferences`)
- `wikipedia/android.yml`: Wikipedia Android app (`org.wikipedia`)
- `wikipedia/ios.yml`: Wikipedia iOS app (`org.wikimedia.wikipedia`)

`e2e/apps/` はダウンロード済みアプリ置き場で、git 管理外です。

## Artifacts

CI や失敗調査でログとキャプチャを残したい場合は、mise task が `--test-output-dir` と `--debug-output` を同じディレクトリに向けます。

```sh
make test-android
```

```sh
make test-ios
```

[.config/mise/config.toml](.config/mise/config.toml) で管理している Maestro CLI では、主な artifact は次のファイルとディレクトリに出力されます。

- `maestro.log`: Maestro 実行ログ
- `manifest.json`: artifact 一覧
- `commands.json`: 各ステップの実行結果と、そのステップが出力した artifact
- `takeScreenshot/`: Flow の `takeScreenshot` で保存したキャプチャ
- `screenshots/`: 失敗ステップなど Maestro が自動保存したキャプチャ

レポートが必要な場合は、[.config/mise/config.toml](.config/mise/config.toml) の task に `--format` と `--output` を追加します。

```sh
make test-android
```

## Flutter Unicode input

Build the upstream [Flutter demo app](https://github.com/mobile-dev-inc/Maestro/tree/7b0d53fb3e1e1740aba00444808718fda279e112/e2e/demo_app)
with Flutter 3.38.5, Java 17.0.21+9 and Android Platform 36. Set `NDK_VERSION`
to explicitly install the build NDK; settings and Wikipedia do not require it.
After SDK setup, build the APK, start the emulator and install the app:

```sh
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis NDK_VERSION=28.2.13676358 make setup-android-sdk
make build-demo-app
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_7 make setup-android-avd
API_LEVEL=36 EMULATOR_PORT=5554 make boot-android-emulator
make install-android-apps
make test-android-unicode
```

On macOS, use Flutter 3.38.5, Xcode and CocoaPods to build for iOS Simulator.
Start the simulator before installing the app:

```sh
make build-demo-app-ios
RUNTIME_NAME="iOS 26.2" DEVICE_TYPE_NAME="iPhone 17 Pro" make setup-ios-simulator
make install-ios-apps
make test-ios-unicode
```

CI installs Flutter 3.38.5 from the official Flutter repository using
`setup/flutter-install.sh`, pinned to its release commit. The SDK is downloaded
for each job without an Actions cache. Android CI uses Temurin 17.0.21+9.

The source revision is pinned in `e2e/build_demo_app`. Source and app output go to
ignored `local/` and `e2e/apps/` directories. No upstream Actions artifact is required.
The flow opens `Input/Keyboard`, inputs `東京` with `inputText`, and checks the
`textInput` field by ID and exact text, then checks `copyTextFrom` for exact equality.
This tests direct Unicode input, not Japanese keyboard composition or conversion.
`copyTextFrom` reads into Maestro memory; it does not verify the system clipboard.

Both Android and iOS CI matrices include `unicode`. iOS runs only through manual
**E2E → Run workflow** dispatch; select this branch and `ios` or `all`.
Artifacts are saved as `maestro-ios-unicode` for the iOS flow.
The default local suites remain settings and Wikipedia; select
`make test-android-unicode` or `make test-ios-unicode` explicitly.
Previous runtime validation passed on both Android and iOS; Android API 36 requires a new E2E run.
