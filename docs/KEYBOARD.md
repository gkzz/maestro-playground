# Japanese software keyboard spike

This experiment types `toukyou` by tapping seven software keys, checks that the
focused Wikipedia search field contains `とうきょう`, selects the `東京` candidate,
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
  The main flow switches input language if needed and taps the letters by label.
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
# After downloading/installing Wikipedia on a Google Play emulator:
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
