# maestro-playground

Maestro で iOS Simulator / Android Emulator を操作するための最小サンプルです。

Maestro Flow から OS 標準の「設定」アプリと、追加のテスト対象アプリを起動する検証用リポジトリです。追加アプリは [mobile-dev-inc/Maestro](https://github.com/mobile-dev-inc/Maestro/tree/main/e2e) の E2E と同じ配布済みアプリを `e2e/manifest.txt` から取得します。

## File tree

```
.
├── .github
│   ├── actions
│   │   ├── setup-android-emulator
│   │   └── setup-ios-simulator
│   └── workflows
│       ├── e2e.yml
│       └── validate.yml
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
│   └── IMPLEMENTATION.md
├── utils
│   └── setup
│       ├── android-avd.sh
│       ├── android-emulator.sh
│       ├── android-sdk.sh
│       └── ios-simulator.sh
├── Makefile
├── README.md
├── mise.toml
└── renovate.json5
```

## Getting started

mise で `mise.toml` に定義された Maestro CLI をインストールします。

```sh
mise install
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

Linux 上で Android SDK と Emulator もセットアップする場合は、GitHub Actions と同じ script を使えます。

```sh
API_LEVEL=32 ARCH=x86_64 TARGET=google_apis utils/setup/android-sdk.sh
API_LEVEL=32 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_7 utils/setup/android-avd.sh
API_LEVEL=32 EMULATOR_PORT=5554 utils/setup/android-emulator.sh
```

```sh
e2e/download_apps android
e2e/install_apps android
E2E_FLOW=settings mise run maestro:test-android
E2E_FLOW=wikipedia mise run maestro:test-android
```

iOS Simulator を起動してから実行します。

```sh
RUNTIME_NAME="iOS 26.2" DEVICE_TYPE_NAME="iPhone 17 Pro" utils/setup/ios-simulator.sh
e2e/download_apps ios
e2e/install_apps ios
E2E_FLOW=settings mise run maestro:test-ios
E2E_FLOW=wikipedia mise run maestro:test-ios
```

全 flow の syntax check は次で実行できます。

```sh
mise run maestro:check-syntax
```

よく使うコマンドは Makefile からも実行できます。

```sh
make check-syntax
make test-android-settings
```

この PR で目指す構成は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) に、詳しい設計メモは [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) にまとめています。

## Test target apps

- `settings/android.yml`: Android OS Settings (`com.android.settings`)
- `settings/ios.yml`: iOS Settings (`com.apple.Preferences`)
- `wikipedia/android.yml`: Wikipedia Android app (`org.wikipedia`)
- `wikipedia/ios.yml`: Wikipedia iOS app (`org.wikimedia.wikipedia`)

`e2e/apps/` はダウンロード済みアプリ置き場で、git 管理外です。

## Artifacts

CI や失敗調査でログとキャプチャを残したい場合は、mise task が `--test-output-dir` と `--debug-output` を同じディレクトリに向けます。

```sh
mise run maestro:test-android
```

```sh
mise run maestro:test-ios
```

`mise.toml` で管理している Maestro CLI では、主な artifact は次のファイルとディレクトリに出力されます。

- `maestro.log`: Maestro 実行ログ
- `manifest.json`: artifact 一覧
- `commands.json`: 各ステップの実行結果と、そのステップが出力した artifact
- `takeScreenshot/`: Flow の `takeScreenshot` で保存したキャプチャ
- `screenshots/`: 失敗ステップなど Maestro が自動保存したキャプチャ

レポートが必要な場合は、`mise.toml` の task に `--format` と `--output` を追加します。

```sh
mise run maestro:test-android
```
