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

[公式手順](https://developer.android.com/tools/agents/android-cli/download)で Android CLI をインストールし、同じシェルで `ANDROID_HOME` と `ANDROID_SDK_ROOT` を同じ SDK ディレクトリに設定してください。SDK の選択順は `ANDROID_SDK_ROOT`、`ANDROID_HOME`、`/usr/local/lib/android/sdk` です。SDK ステップは `android sdk install` で Command-line Tools 22.0、Platform 36 と `google_apis;x86_64` の system image をインストールします。AVD 作成は固定した Command-line Tools 22.0 の `avdmanager` を使います。新 CLI の `android emulator create` は API / image を指定できず、標準の Play Store image は日本語切り替えに必要な `adb root` を使えないためです。ローカルでは子プロセスの環境変数は親シェルに反映されないため、SDK の `platform-tools` と `emulator` も `PATH` に追加してください。

```
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis make setup-android-sdk
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_9 make setup-android-avd
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

Flutter は [`.config/flutter/mise.toml`](../.config/flutter/mise.toml) に指定したバージョンを `make install-flutter` で導入し、Java 17.0.21+9 を用意します。配布 URL と SHA-256 は同じディレクトリの `mise.lock` で固定します。Makefile は `mise exec --locked flutter` でこの SDK を選択し、ビルドスクリプトもバージョン不一致なら停止します。SDK セットアップ時に `NDK_VERSION` を指定すると、ビルド用 NDK も同時にインストールします。`settings` / `wikipedia` では指定不要です。

Flutter の更新 PR で確認する内容は [github_actions.md](./github_actions.md) を参照してください。

```sh
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis NDK_VERSION=28.2.13676358 make setup-android-sdk
make build-demo-app
API_LEVEL=36 ARCH=x86_64 TARGET=google_apis PROFILE=pixel_9 make setup-android-avd
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

GitHub Actions での実行と artifact の保存については [github_actions.md](./github_actions.md) を参照してください。

## ロケール別のキャプチャと画像比較

Wikipedia の起動画面は、表示テキストを検証した後、`android-wikipedia-ja.png` のように OS とロケールを含む名前で保存します。現在のフローは起動画面の確認までで、検索操作は含みません。`E2E_LOCALE` は期待する表示言語の指定であり、端末の言語自体は実行前に合わせてください。

```sh
E2E_LOCALE=ja make test-android-wikipedia
E2E_LOCALE=en make test-ios-wikipedia
```

画像は各フローの artifact ディレクトリ内の `takeScreenshot/` に出力されます。基準にしたい画像を確認してから別の場所に保存し、その絶対パスを指定して再実行します。通常の実行では画像を保存するだけです。

```sh
mkdir -p local/baselines
# takeScreenshot/ 配下の画像を確認し、選んだ画像を次の名前でコピーする
# local/baselines/android-wikipedia-ja.png
E2E_LOCALE=ja E2E_SCREENSHOT_BASELINE="$PWD/local/baselines/android-wikipedia-ja.png" make test-android-wikipedia
```

比較には `assertScreenshot` を使い、`thresholdPercentage: 100` で完全一致を要求します。ベースラインが存在しない場合も失敗します。同じ OS、端末サイズ、言語、アプリバージョンで比較してください。全画面の比較には時刻などの変化も含まれます。ロケールごとの画像を上書きせず保存する場合は、各実行後にコピーしてください。`local/` と `artifacts/` は Git 管理外です。

任意の画面で比較したい場合は、対象の操作・表示待ちの後に次のコマンドを置きます。オブジェクト形式でベースラインを指定するキーは `path` です。

```yaml
- assertScreenshot:
    path: /absolute/path/home-page-baseline.png
    thresholdPercentage: 100
```

特定の要素だけを比較するときは、撮影と比較で同じ `cropOn` を指定します。次は対象アプリに `profile_card` という ID が存在する場合の例です。Wikipedia フローへそのまま追加するものではありません。

```yaml
# 初回は撮影し、出力画像を確認して別の場所にベースラインとして保存する
- takeScreenshot:
    path: profile-card-candidate
    cropOn:
      id: profile_card

# 次回から、保存した切り抜き画像と比較する
- assertScreenshot:
    path: /absolute/path/profile-card-baseline.png
    cropOn:
      id: profile_card
    thresholdPercentage: 100
```

比較対象の画像も同じ要素を切り抜いたものにしてください。判定結果と画像は実行後の artifact で確認します。詳細は [assertScreenshot の公式仕様](https://docs.maestro.dev/reference/commands-available/assertscreenshot) を参照してください。


### Flutter 入力画面のキャプチャと比較

`unicode` フローでは `東京` の入力を検証した後、Save で保存してアプリを再起動します。
入力画面を開き直し、保存した文字列の表示を確認してから、画面全体を
`android-unicode-input-ja.png`、比較用の入力欄を
`android-unicode-field-ja.png` のように保存します。iOS は `ios`、英語環境は
`en` が名前に入ります。どちらも各フローの `takeScreenshot/` 配下に出力します。

```sh
E2E_LOCALE=ja make test-android-unicode
```

初回はキャプチャを確認し、入力欄の画像を次の場所へコピーしてください。

```sh
mkdir -p e2e/baselines
# takeScreenshot/ 配下の android-unicode-field-ja.png を選んでコピーする
# 保存先: e2e/baselines/android-unicode-field-ja.png
E2E_LOCALE=ja make test-android-unicode
```

`e2e/baselines/<android|ios>-unicode-field-<ja|en>.png` が存在すると、
同じ OS・ロケールの基準画像と入力欄を `assertScreenshot` で比較します。
入力欄の `takeScreenshot` の直後に `assertScreenshot` を実行します。
この間にアプリを再起動したり、入力画面を開き直したりしません。
基準画像がまだない組み合わせは撮影のみです。
基準画像は自動更新しません。更新時は画像を確認して差し替えてください。

別の基準画像を使う場合は、既存の `E2E_SCREENSHOT_BASELINE` を指定します。
明示したパスが存在しなければ比較は失敗します。

```sh
E2E_LOCALE=ja E2E_SCREENSHOT_BASELINE="$PWD/local/baselines/android-unicode-field-ja.png" make test-android-unicode
```

画面を開き直すことで入力欄のフォーカスを外し、点滅するカーソルを比較対象から除きます。
入力欄を切り抜いて比較するため、基準画像には画面全体ではなく
`unicode-field` の画像を使用してください。完全一致を要求し、差があれば
ジョブが失敗します。比較結果と画像は既存の Maestro artifact から確認できます。
端末サイズ、OS、アプリ、フォントなどの条件は基準画像と揃えてください。

この画面のラベルは英語固定です。ロケール名を含むキャプチャや入力欄の比較は、
端末の言語が正しく設定されたこと自体の検証にはなりません。
ローカルでも同じロケールで端末をセットアップしてから実行してください。

GitHub Actions の画像比較サマリーについては [github_actions.md](./github_actions.md) を参照してください。
