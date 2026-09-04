# Development

ローカル環境で Maestro のテストを実行するための手順をまとめています。

ローカルでは Makefile を入口にして、mise task とセットアップ用スクリプトを呼び出します。

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md) の `Using mise Tasks in Local and CI` に記載しています。

## Setup

必要なツールをインストールします。

```
make install
```

Maestro CLI のバージョンは [mise.toml](../mise.toml) で管理しています。

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

```
API_LEVEL=32 ARCH=x86_64 TARGET=google_apis make setup-android-sdk
API_LEVEL=32 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_7 make setup-android-avd
API_LEVEL=32 EMULATOR_PORT=5554 make boot-android-emulator
```

## Syntax Check

Maestro のテストを実行する前に構文を確認できます。

```
make check-syntax
```

内部では `mise run maestro:check-syntax` を実行します。

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

Pull Request では `Validate` と `E2E` を実行します。

`Validate` では workflow、shell script、Maestro flow などの構文を確認します。

`E2E` では Android / iOS の各 flow を実行します。

CI の構成については [ARCHITECTURE.md](./ARCHITECTURE.md) の `CI` を参照してください。
