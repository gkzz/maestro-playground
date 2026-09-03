# Architecture

## Repository Overview

ローカルと CI で同じバージョンの `maestro-cli` を使用し、Maestro の実行とテスト環境のセットアップで同じ処理を利用できる構成にしています。

Maestro の実行コマンドや引数は [mise.toml](../mise.toml) の task にまとめています。

ローカルでは Makefile を入口として mise task やセットアップスクリプトを呼び出し、CI では GitHub Actions から直接呼び出します。

Android Emulator / iOS Simulator のセットアップ処理の実体は [mise.toml](../mise.toml) や [Makefile](../Makefile) には含めず、[utils/setup/](../utils/setup/) のスクリプトにまとめています。ローカルでは Makefile の target からそれらのスクリプトを呼び出します。

> [!NOTE]
> iOS の実行は GitHub Actions のみ対応しています。

```mermaid
flowchart TB
  developer[Developer]
  ci[GitHub Actions]

  make[Makefile]
  mise[mise.toml]
  flows[.maestro flows]
  setup[utils/setup/android and utils/setup/ios scripts]
  local[local/android.env]
  apps[e2e app scripts]
  artifacts[artifacts/maestro]

  developer --> make
  make --> mise
  make --> setup
  make --> apps

  ci --> mise
  ci --> setup
  ci --> apps

  local -. Android only .-> mise
  local -. Android only .-> apps

  mise --> flows
  mise --> artifacts
```

## Using mise Tasks in Local and CI

Maestro の実行コマンドや引数は [mise.toml](../mise.toml) の task にまとめています。

ローカルでは [Makefile](../Makefile) をラッパーとして使い、用途ごとの target から mise task を呼び出します。

CI では [e2e.yml](../.github/workflows/e2e.yml) から mise task を直接実行し、flow などの値は job や matrix から渡します。

```mermaid
flowchart TB
  mise[mise.toml<br/>Maestro tasks]

  subgraph Local
    developer[Developer]
    make[Makefile]

    developer --> make --> mise
  end

  subgraph CI
    workflow[e2e.yml]
    workflow --> mise
  end

  mise --> maestro[Maestro CLI]
```

## Runtime Setup

セットアップ処理の実体は [utils/setup/android/](../utils/setup/android/) と [utils/setup/ios/](../utils/setup/ios/) に置きます。

ローカルでは [Makefile](../Makefile) の target を入口にします。

```mermaid
flowchart TB
  developer[Developer]
  make[Makefile]
  androidSdk[utils/setup/android/android-sdk.sh]
  androidAvd[utils/setup/android/android-avd.sh]
  androidEmulator[utils/setup/android/android-emulator.sh]
  iosSimulator[utils/setup/ios/ios-simulator.sh]

  developer --> make
  make --> androidSdk
  make --> androidAvd
  make --> androidEmulator
  make --> iosSimulator
```

## CI

Pull Request では、`Validate` と `E2E` の workflow を実行します。

### Workflows

```mermaid
flowchart TB
  pr[Pull Request]

  subgraph validate[Validate]
    actionlint[actionlint]
    shell[shell-check-syntax]
    syntax[maestro-check-syntax]
    renovate[renovate-validate-config]
  end

  subgraph e2e[E2E]
    androidSettings[Android / settings]
    androidWikipedia[Android / wikipedia]
    iosSettings[iOS / settings]
    iosWikipedia[iOS / wikipedia]
  end

  pr --> validate
  pr --> e2e
```

`Validate` では workflow、shell script、Maestro flow などの構文を確認します。

`E2E` では Android / iOS の各 flow を実行します。

### Runtime Setup in CI

```mermaid
flowchart LR
  subgraph Android
    androidAction[setup-android-emulator]
    androidSdk[android-sdk.sh]
    androidAvd[android-avd.sh]
    androidEmulator[android-emulator.sh]

    androidAction --> androidSdk --> androidAvd --> androidEmulator
  end

  subgraph iOS
    iosAction[setup-ios-simulator]
    iosSimulator[ios-simulator.sh]

    iosAction --> iosSimulator
  end
```

E2E の実行環境は GitHub Actions の composite action から [utils/setup/](../utils/setup/) のスクリプトを直接呼び出してセットアップします。

### Artifacts

```mermaid id="d5b2ya"
flowchart LR
  subgraph Android
    androidFlow[Maestro flow]
    androidArtifacts[artifacts/maestro/android/flow]

    androidFlow --> androidArtifacts
  end

  subgraph iOS
    iosFlow[Maestro flow]
    iosArtifacts[artifacts/maestro/ios/flow]

    iosFlow --> iosArtifacts
  end

  androidArtifacts --> upload[actions/upload-artifact]
  iosArtifacts --> upload
```

Maestro のテスト結果は `artifacts/maestro/<platform>/<flow>` に出力し、CI では `actions/upload-artifact` を使って保存します。

ローカルでのセットアップやテストの実行方法については [DEVELOPMENT.md](./DEVELOPMENT.md) を参照します。
