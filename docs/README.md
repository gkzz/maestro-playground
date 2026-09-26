# Documentation

このリポジトリでは、Maestro を使った Android / iOS の E2E テストを試しています。

Maestro CLI のバージョンとテストの実行方法は [.config/mise/config.toml](../.config/mise/config.toml) で管理し、ローカルと CI から同じコマンドを実行できるようにしています。

## Overview

主な構成は次のとおりです。

* `.maestro/`: Maestro のテスト
* [.config/mise/config.toml](../.config/mise/config.toml): Maestro CLI のバージョンとテスト実行用の task
* [Makefile](../Makefile): ローカルでよく使うコマンドとセットアップスクリプトの入口
* `utils/setup/android/`, `utils/setup/ios/`: Android Emulator / iOS Simulator のセットアップ
* `e2e/`: テストで使用するアプリのダウンロードやインストール
* `local/`: ローカル環境固有の設定
* `artifacts/`: Maestro のテスト結果

全体の構成は [ARCHITECTURE.md](./ARCHITECTURE.md) の `Repository Overview` を参照してください。

## Development

ローカル環境のセットアップやテストの実行方法については [DEVELOPMENT.md](./DEVELOPMENT.md) を参照してください。

## Architecture

ローカルと CI で共有している処理や、それぞれのコマンドの関係については [ARCHITECTURE.md](./ARCHITECTURE.md) を参照してください。

### mise本体のバージョン

`.config/mise/config.toml` の `min_version` は、このプロジェクトの設定を利用するために必要なmiseの最低バージョンを表します。

ローカル環境では、`min_version` 以上のmiseが利用可能であることを前提とします。mise本体のインストール方法やバージョン管理方法は、このリポジトリでは規定しません。

CIでは、[`.github/actions/setup-mise/action.yml`](../.github/actions/setup-mise/action.yml) に記載したバージョンとSHA-256でmiseをbootstrapして使用します。CIで使用するmiseのバージョンは `min_version` と同じ値に揃えます。

mise本体を更新するときは、`min_version` と `action.yml` のバージョン、およびプラットフォーム別SHA-256を同じリリースへまとめて更新してください。
