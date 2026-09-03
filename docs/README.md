# Documentation

このリポジトリでは、Maestro を使った Android / iOS の E2E テストを試しています。

Maestro CLI のバージョンとテストの実行方法は `mise.toml` で管理し、ローカルと CI から同じコマンドを実行できるようにしています。

## Overview

主な構成は次のとおりです。

* `.maestro/`: Maestro のテスト
* `mise.toml`: Maestro CLI のバージョンとテスト実行用の task
* `Makefile`: ローカルでよく使うコマンドとセットアップスクリプトの入口
* `utils/setup/android/`, `utils/setup/ios/`: Android Emulator / iOS Simulator のセットアップ
* `e2e/`: テストで使用するアプリのダウンロードやインストール
* `local/`: ローカル環境固有の設定
* `artifacts/`: Maestro のテスト結果

全体の構成は [ARCHITECTURE.md](./ARCHITECTURE.md) の `Repository Overview` を参照してください。

## Development

ローカル環境のセットアップやテストの実行方法については [DEVELOPMENT.md](./DEVELOPMENT.md) を参照してください。

## Architecture

ローカルと CI で共有している処理や、それぞれのコマンドの関係については [ARCHITECTURE.md](./ARCHITECTURE.md) を参照してください。
