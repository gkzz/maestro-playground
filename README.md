# maestro-playground

Maestro で iOS Simulator / Android Emulator を操作するための最小サンプルです。

Maestro Flow から OS 標準の「設定」アプリを直接起動する検証用リポジトリです。アプリ本体、deep link、platform channel、アプリ側の画面遷移コードは使いません。

## File tree

```
.
├── .github
│   └── workflows
│       ├── e2e.yml
│       └── validate.yml
├── .gitignore
├── .maestro
│   ├── settings_android.yml
│   └── settings_ios.yml
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
maestro --platform android test .maestro/settings_android.yml
```

iOS Simulator を起動してから実行します。

```sh
maestro --platform ios test .maestro/settings_ios.yml
```

## Artifacts

CI や失敗調査でログとキャプチャを残したい場合は、`--test-output-dir` と `--debug-output` を同じディレクトリに向けます。

```sh
maestro --platform android test .maestro/settings_android.yml \
  --test-output-dir artifacts/maestro/android \
  --debug-output artifacts/maestro/android \
  --flatten-debug-output
```

```sh
maestro --platform ios test .maestro/settings_ios.yml \
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
maestro --platform android test .maestro/settings_android.yml \
  --test-output-dir artifacts/maestro/android \
  --debug-output artifacts/maestro/android \
  --flatten-debug-output \
  --format junit \
  --output artifacts/maestro/android/report.xml
```
