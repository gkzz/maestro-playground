# Development

ローカル環境で Maestro のテストを実行するための手順をまとめています。

ローカルでは Makefile を入口にして、mise task とセットアップ用スクリプトを呼び出します。

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md) の `Using mise Tasks in Local and CI` に記載しています。

## Setup

必要なツールをインストールします。

```
make install
```

Maestro CLI のバージョンは [.config/mise/config.toml](../.config/mise/config.toml) で管理しています。

セットアップ用のスクリプトは [utils/setup/](../utils/setup/) にあります。

```
utils/setup/
├── android
│   ├── android-avd.sh // Android Virtual Device の作成と確認
│   ├── android-emulator.sh //  Emulator の起動と起動完了の待機
│   └── android-sdk.sh // Android SDK のインストールと環境変数の設定
└── ios
    └── ios-simulator.sh // Simulator の作成と起動完了の待機
```

Android / iOS のセットアップの図は [ARCHITECTURE.md](./ARCHITECTURE.md) の `Runtime Setup` を参照してください。

ローカルではスクリプトを直接実行せず、[Makefile](../Makefile) の target 経由で呼び出します。

Android command-line tools（`cmdline-tools/latest/bin`）を事前に配置し、同じシェルで `ANDROID_HOME` と `ANDROID_SDK_ROOT` を同じ SDK ディレクトリに設定してください。SDK の選択順は `ANDROID_SDK_ROOT`、`ANDROID_HOME`、`/usr/local/lib/android/sdk` です。SDK ステップは Platform 36 と `google_apis;x86_64` の system image をインストールします。ローカルでは子プロセスの環境変数は親シェルに反映されないため、SDK の `platform-tools` と `emulator` も `PATH` に追加してください。

```
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis make setup-android-sdk
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_7 make setup-android-avd
API_LEVEL=36 EMULATOR_PORT=5554 make boot-android-emulator
```

## Android

Android の settings flow は次のコマンドで実行します。

```
make test-android-settings
```

WSL から Windows 側の Android Studio で起動した Emulator や adb server を使用する場合は、`local/android.env` に接続情報を設定します。

```
ADB_SERVER_SOCKET=...
MAESTRO_HOST=...
```

複数の Emulator がある場合など、必要に応じて `ANDROID_EMULATOR_SERIAL` も設定します。

```
ANDROID_EMULATOR_SERIAL=...
```

`local/android.env` は git では管理しません。

### Test apps

Wikipedia など追加のアプリを使用するテストでは、先にアプリをダウンロードしてインストールします。

```
make download-android-apps
make install-android-apps
make test-android-wikipedia
```

### Flutter Unicode flow

Flutter 3.38.5 と Java 17.0.21+9 を用意します。SDK セットアップ時に `NDK_VERSION` を指定すると、ビルド用 NDK も同時にインストールします。`settings` / `wikipedia` では指定不要です。

```sh
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis NDK_VERSION=28.2.13676358 make setup-android-sdk
make build-demo-app
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_7 make setup-android-avd
API_LEVEL=36 EMULATOR_PORT=5554 make boot-android-emulator
make install-android-apps
make test-android-unicode
```

## iOS

iOS の settings flow は次のコマンドで実行します。

```
make test-ios-settings
```

Simulator のセットアップには [Makefile](../Makefile) の target を使用します。

```
RUNTIME_NAME="iOS 26.2" DEVICE_TYPE_NAME="iPhone 17 Pro" make setup-ios-simulator
```

## Artifacts

Maestro のテスト結果は `artifacts/maestro/` に出力します。

```
artifacts/maestro/android/<flow>
artifacts/maestro/ios/<flow>
```

`artifacts/` は git では管理しません。

CI でも同じディレクトリ構成を使用します。

テスト結果が CI でどのように保存されるかについては [ARCHITECTURE.md](./ARCHITECTURE.md) の `Artifacts` を参照してください。

## CI

Pull Request では `Lint` と `E2E` を実行します。

`Lint` では workflow、shell script、Maestro flow などの構文を確認します。

PR の `E2E` では Android の `settings` / `wikipedia` / `unicode` を実行します。`workflow_dispatch` では `platform` に応じて Android / iOS を選択し、各プラットフォームの同じ3フローを実行します。

CI の構成については [ARCHITECTURE.md](./ARCHITECTURE.md) の `CI` を参照してください。
