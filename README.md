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
