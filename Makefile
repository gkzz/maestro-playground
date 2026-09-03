SHELL := /bin/bash

.PHONY: help install maestro-version check-syntax \
	test-android test-android-settings test-android-wikipedia \
	test-ios test-ios-settings test-ios-wikipedia \
	download-android-apps download-ios-apps install-android-apps install-ios-apps \
	setup-android-sdk setup-android-avd boot-android-emulator setup-ios-simulator

help:
	@printf '%s\n' \
		'Targets:' \
		'  install                 Install mise-managed tools' \
		'  maestro-version         Print Maestro CLI version' \
		'  check-syntax            Check all Maestro flow YAML files' \
		'  test-android            Run all Android flows' \
		'  test-android-settings   Run Android settings flow' \
		'  test-android-wikipedia  Run Android wikipedia flow' \
		'  test-ios                Run all iOS flows' \
		'  test-ios-settings       Run iOS settings flow' \
		'  test-ios-wikipedia      Run iOS wikipedia flow' \
		'  download-android-apps   Download Android test apps' \
		'  download-ios-apps       Download iOS test apps' \
		'  install-android-apps    Install Android test apps' \
		'  install-ios-apps        Install iOS test apps' \
		'  setup-android-sdk       Install Android SDK packages' \
		'  setup-android-avd       Create Android AVD' \
		'  boot-android-emulator   Boot Android Emulator' \
		'  setup-ios-simulator     Create and boot iOS Simulator'

install:
	mise install

maestro-version:
	mise run maestro:version

check-syntax:
	mise run maestro:check-syntax

test-android:
	mise run maestro:test-android

test-android-settings:
	E2E_FLOW=settings mise run maestro:test-android

test-android-wikipedia:
	E2E_FLOW=wikipedia mise run maestro:test-android

test-ios:
	mise run maestro:test-ios

test-ios-settings:
	E2E_FLOW=settings mise run maestro:test-ios

test-ios-wikipedia:
	E2E_FLOW=wikipedia mise run maestro:test-ios

download-android-apps:
	e2e/download_apps android

download-ios-apps:
	e2e/download_apps ios

install-android-apps:
	e2e/install_apps android

install-ios-apps:
	e2e/install_apps ios

setup-android-sdk:
	utils/setup/android/android-sdk.sh

setup-android-avd:
	utils/setup/android/android-avd.sh

boot-android-emulator:
	utils/setup/android/android-emulator.sh

setup-ios-simulator:
	utils/setup/ios/ios-simulator.sh
