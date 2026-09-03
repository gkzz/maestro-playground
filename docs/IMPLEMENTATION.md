# Implementation Notes

このリポジトリは、Maestro の最小 E2E 検証をローカルと CI で同じ手順に寄せるための playground です。この PR では、Maestro CLI のバージョン、flow の実行方法、mobile runtime の setup 手順を分散させず、薄い入口から同じ実体を呼ぶ構成を目指します。

## Goals

- Maestro CLI のバージョンは `mise.toml` で一元管理する。
- flow 実行の本体は `mise run maestro:*` に集約する。
- GitHub Actions の composite action とローカル手順は `utils/setup/*` の同じ script を使う。
- ローカル固有の接続情報は git 管理外の `local/*` に閉じ込める。
- CI とローカルの artifact 出力先を揃え、失敗調査で同じファイル構造を見られるようにする。

## Layers

### Maestro flows

`.maestro/*/*.yml` は OS 標準アプリや配布済みテストアプリを操作するテスト仕様です。flow は platform ごとに分け、実行対象の選択は `E2E_FLOW` で行います。

### Tooling

`mise.toml` は Maestro CLI のバージョンと実行 task を定義します。CI もローカルも `maestro:test-android`、`maestro:test-ios`、`maestro:check-syntax` を呼ぶことで、コマンドライン引数と artifact 出力先を揃えます。

`Makefile` は人間向けの短い入口です。Make target は実行本体を持たず、mise task や setup script を呼ぶだけにします。

### Runtime setup

`utils/setup/*` は mobile runtime の準備を担当します。

- `android-sdk.sh`: Android SDK package の install と PATH / environment の設定
- `android-avd.sh`: Android Virtual Device の作成と存在確認
- `android-emulator.sh`: emulator の起動、boot 待ち、animation 無効化
- `ios-simulator.sh`: runtime / device type の解決、Simulator 作成、boot 待ち

GitHub Actions の composite action はこれらの script を呼ぶだけにして、CI 固有の YAML に長い shell 実装を持たせません。

### Local configuration

`local/` は `.gitignore` 済みのローカル設定置き場です。WSL から Windows 側 Android Studio の emulator / adb server に接続する場合は、`local/android.env` に `ADB_SERVER_SOCKET`、`MAESTRO_HOST`、必要に応じて `ANDROID_EMULATOR_SERIAL` を置きます。

このファイルは `e2e/install_apps` と `maestro:test-android` から読み込まれます。CI では workflow が一時的に `local/android.env` を生成します。

### Artifacts

Maestro の debug output と test output は同じ directory に出します。

- Android: `artifacts/maestro/android/<flow>`
- iOS: `artifacts/maestro/ios/<flow>`

`artifacts/` は git 管理外です。CI では job ごとに upload し、ローカルでは同じ構造を直接確認します。

## Expected Flow

ローカルでは次の順で使います。

```sh
make install
make check-syntax
make test-android-settings
```

追加アプリを使う flow は、先に app を取得して install します。

```sh
make download-android-apps
make install-android-apps
make test-android-wikipedia
```

CI では PR ごとに `Validate` と `E2E` が走ります。Validate は workflow / shell / Maestro syntax を確認し、E2E は Android と iOS の matrix job で各 flow を実行します。
