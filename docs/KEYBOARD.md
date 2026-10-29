# Japanese software keyboard spike

This experiment types `toukyou` by tapping seven software keys, checks that the
focused search field (Android Settings; Wikipedia on iOS) contains `とうきょう`, selects the `東京` candidate,
and checks the search field again. It does not use `inputText`, clipboard paste,
or ADB text injection. A result containing Tokyo cannot satisfy the final assertion.

## CI

The E2E workflow has a separate `keyboard` matrix entry on each platform. Android
runs on pull requests and manual dispatch. iOS follows the existing manual-only
policy: run **E2E → Run workflow**, select this branch, and choose `all` or `ios`.
The device locale can be Japanese or English; the keyboard is always Japanese.

- Android: the keyboard job uses the API 32 `google_apis_playstore` image rather
  than the ordinary Google APIs image, to obtain Gboard. The setup script checks
  that Gboard exists, enables it, allows the software keyboard with hardware
  input connected, and opens its settings. The setup subflow adds Japanese QWERTY.
  The main flow opens Android Settings search, switches input language if needed and taps the letters by label.
- iOS: only the keyboard job sets `E2E_JAPANESE_KEYBOARD=1`. Simulator setup
  disables the host hardware keyboard, sets `AppleKeyboards` to Japanese Romaji,
  and reboots the simulator to load the preferences. The flow taps keys by label.

These are experimental settings and locators, not verified working recipes.
In particular, Gboard settings labels/key accessibility and the iOS 26 keyboard
preference identifier must be validated in CI. If a key is absent from the
accessibility tree, inspect the screenshot before considering a device-specific
coordinate. No automatic fallback masks a failed keyboard operation.

## Artifacts and interpretation

Each job uploads `maestro-<platform>-keyboard`. Screenshots mark keyboard opening,
Japanese layout, hiragana composition, and kanji selection. Maestro also saves
failure screenshots and command logs. The Android job additionally collects the
final UI hierarchy, screenshot, and `dumpsys input_method`, including when setup
fails before Maestro starts.

A failure during Gboard setup means the IME prerequisite is unresolved. A failure
on a Latin key tests whether that key is accessible by label. A failure at the
hiragana assertion means the Japanese layout/composition needs investigation.
A failure selecting Tokyo tests candidate accessibility/availability. Only the
final search-field assertion counts as success. Repeat successful CI runs before
calling the experiment stable.

## Local entry points (optional)

The spike is explicitly selected; existing default local suites still run settings
and Wikipedia only. Use a fresh emulator/simulator, as adding the Gboard language
is intended for a clean profile, not repeated setup on an already configured one.

```sh
# On a Google Play emulator (no app installation required):
utils/setup/android/japanese-keyboard.sh
make test-android-keyboard

# On macOS, before downloading/installing Wikipedia:
E2E_JAPANESE_KEYBOARD=1 RUNTIME_NAME="iOS 26.2" DEVICE_TYPE_NAME="iPhone 17 Pro" make setup-ios-simulator
# Then download/install Wikipedia and run:
make test-ios-keyboard
```

References: [Maestro selectors](https://docs.maestro.dev/reference/selectors/core-selectors),
[tapOn](https://docs.maestro.dev/reference/commands-available/tapon),
[inputText and Android Unicode limitation](https://docs.maestro.dev/reference/commands-available/inputtext).

## Android Unicode input (PR #3211)

A separate `unicode` flow exercises the bundled Maestro IME introduced by
[PR #3211](https://github.com/mobile-dev-inc/Maestro/pull/3211), using the pinned
CLI 2.11.0. Non-ASCII `inputText` automatically switches to Maestro's IME and
restores the previous input method afterward; no Japanese Gboard setup is needed.

The flow currently diagnoses Wikipedia onboarding before testing input. It launches
Wikipedia (`org.wikipedia`) with cleared state, checks the first introduction title,
taps the unlabeled next arrow once at `94%,96%`, and captures
`wikipedia-onboarding-next`. Inspect that screenshot and the final UI hierarchy
before adding any further onboarding steps. A passing diagnostic does not establish
that onboarding is complete or that Unicode input works.

The observed first screen has neither `fragment_onboarding_skip_button` nor
`search_container`. The separate Android Wikipedia flow now requires
`org.wikipedia:id/search_container` to be visible; introduction text containing
`百科事典` cannot satisfy its home-screen check. It will fail while onboarding blocks
access to search.

After confirming the remaining onboarding screens and search field IDs, restore
the Unicode check: open search, input `東京`, check the field by resource ID and
exact text, then use `copyTextFrom` and assert that `maestro.copiedText === "東京"`.
Search results must not serve as proof of successful input.

The first Settings-search run lost its input target during `inputText`: Android
terminated `com.google.android.settings.intelligence` with reason `change
com.google.android.settings.intelligence`, removed its search activity, and returned
to Settings home. Maestro IME later reported a successful commit after the input
package had changed to `com.android.settings`. That run does not establish whether
Unicode input into the original field succeeded; the trigger for the package
change remains unconfirmed.

Only direct Japanese input is tested initially. ASCII/Unicode append, emoji, and
clipboard round trips are deferred until this case passes in CI. `copyTextFrom`
reads into Maestro memory; it does not test the Android native clipboard.

The Android CI runs `wikipedia` and `unicode` in one job on the ordinary API 32
Google APIs image, sharing the emulator and test app installation. The `unicode`
step runs even if the `wikipedia` step fails. Artifacts are uploaded together as
`maestro-android-wikipedia-unicode`, including the screenshot after the onboarding tap,
command logs, and final input-method/UI diagnostics. The default local suite still
runs settings and Wikipedia only. Install Wikipedia before running this explicitly:

```sh
e2e/download_apps android
e2e/install_apps android
make test-android-unicode
```

Runtime validation of the Wikipedia case is pending CI. The earlier software-keyboard
experiment remains a separate check of Japanese composition and candidate selection.
