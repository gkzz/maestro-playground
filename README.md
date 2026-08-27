# maestro-playground

Maestro で iOS Simulator / Android Emulator を操作するための最小サンプルです。

Maestro Flow から OS 標準の「設定」アプリを直接起動する検証用リポジトリです。アプリ本体、deep link、platform channel、アプリ側の画面遷移コードは使いません。

## ファイル

- `.maestro/settings_android.yml`: Android Emulator の設定アプリ `com.android.settings` を起動する Maestro Flow。
- `.maestro/settings_ios.yml`: iOS Simulator の設定アプリ `com.apple.Preferences` を起動する Maestro Flow。
- `mise.toml`: CI とローカル実行で使うツール定義。

## Maestro Flow がしていること

Android:

```yaml
appId: com.android.settings
---
- launchApp
- takeScreenshot: android-settings
```

iOS:

```yaml
appId: com.apple.Preferences
---
- launchApp
- takeScreenshot: ios-settings
```

`appId` は Maestro が起動する対象アプリです。ここでは OS 標準の設定アプリを指定しています。

`launchApp` は指定した `appId` のアプリを起動します。アプリ側に deep link、platform channel、設定画面を開くコードは不要です。

`takeScreenshot` は起動できたことを目で確認しやすくするための最小ステップです。OS の表示言語に依存する `assertVisible` は入れていません。

## 実行

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
