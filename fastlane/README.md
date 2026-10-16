fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## iOS

### ios create_app_record

```sh
[bundle exec] fastlane ios create_app_record
```

Create the App ID and App Store Connect record (one-time, interactive if needed)

### ios validate_release

```sh
[bundle exec] fastlane ios validate_release
```

Validate local files required for screenshots and App Store upload

### ios screenshots

```sh
[bundle exec] fastlane ios screenshots
```

Capture deterministic English App Store screenshots

### ios store_assets

```sh
[bundle exec] fastlane ios store_assets
```

Upload English metadata and screenshots without a binary

### ios privacy

```sh
[bundle exec] fastlane ios privacy
```

Upload the current no-data-collected App Privacy answer

### ios beta

```sh
[bundle exec] fastlane ios beta
```

Build and upload the next TestFlight build

### ios release

```sh
[bundle exec] fastlane ios release
```

Capture screenshots, build, and upload everything without submitting for review

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
