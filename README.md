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
├── README.md
├── mise.toml
└── renovate.json5
```

## Getting started

Maestro CLI をインストールします。

```sh
curl -fsSL https://get.maestro.mobile.dev | bash
```

Android Emulator を起動してから実行します。

```sh
e2e/download_apps android
e2e/install_apps android
maestro --platform android test .maestro/settings/android.yml
maestro --platform android test .maestro/wikipedia/android.yml
```

iOS Simulator を起動してから実行します。

```sh
e2e/download_apps ios
e2e/install_apps ios
maestro --platform ios test .maestro/settings/ios.yml
maestro --platform ios test .maestro/wikipedia/ios.yml
```

## Test target apps

- `settings/android.yml`: Android OS Settings (`com.android.settings`)
- `settings/ios.yml`: iOS Settings (`com.apple.Preferences`)
- `wikipedia/android.yml`: Wikipedia Android app (`org.wikipedia`)
- `wikipedia/ios.yml`: Wikipedia iOS app (`org.wikimedia.wikipedia`)

`e2e/apps/` はダウンロード済みアプリ置き場で、git 管理外です。

## Artifacts

CI や失敗調査でログとキャプチャを残したい場合は、`--test-output-dir` と `--debug-output` を同じディレクトリに向けます。

```sh
maestro --platform android test .maestro/settings/android.yml .maestro/wikipedia/android.yml \
  --test-output-dir artifacts/maestro/android \
  --debug-output artifacts/maestro/android \
  --flatten-debug-output
```

```sh
maestro --platform ios test .maestro/settings/ios.yml .maestro/wikipedia/ios.yml \
  --test-output-dir artifacts/maestro/ios \
  --debug-output artifacts/maestro/ios \
  --flatten-debug-output
```

Maestro `cli-2.8.0` では、主な artifact は次のファイルとディレクトリに出力されます。

- `maestro.log`: Maestro 実行ログ
- `manifest.json`: artifact 一覧
- `commands.json`: 各ステップの実行結果と、そのステップが出力した artifact
- `takeScreenshot/`: Flow の `takeScreenshot` で保存したキャプチャ
- `screenshots/`: 失敗ステップなど Maestro が自動保存したキャプチャ

レポートが必要な場合は、artifact 出力とは別に `--format` と `--output` を指定します。

```sh
maestro --platform android test .maestro/settings/android.yml .maestro/wikipedia/android.yml \
  --test-output-dir artifacts/maestro/android \
  --debug-output artifacts/maestro/android \
  --flatten-debug-output \
  --format junit \
  --output artifacts/maestro/android/report.xml
```
