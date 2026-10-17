# Build outputs and releases

For the native virtual camera implementation and remaining release requirements,
see [desktop/native/README.md](../desktop/native/README.md). Windows initially
targets Windows 11; native camera packages are not release-ready yet.

Keep source code in Git and publish executables/installers as GitHub Release
assets. Use one source tag for all platforms. Do not commit signing credentials.

## Current packages

```sh
python -m pip install -r desktop/requirements-build.txt
python desktop/build.py
```

| Build host | Output | Status |
| --- | --- | --- |
| Windows | `dist/FreeCam/FreeCam.exe` and runtime folder | Portable prototype, smoke-tested |
| macOS | `dist/FreeCam.app` | Mac build and validation pending |
| Mac/Xcode | iOS app from `ios/project.yml` | Compilation and device validation pending |

Copy the entire Windows folder. End users do not need Python. Desktop outputs
are unsigned development packages.

## Planned installers

- Windows: use Inno Setup to create `FreeCam-Setup.exe`, shortcuts and an
  uninstaller. Installer configuration is not implemented yet. Apple's USB
  drivers are separate; the app guides users to Apple Devices when needed.
- macOS: package the app in a DMG on Mac. Developer ID signing and notarization
  remain to be configured for public distribution.
- iOS: install through Xcode during development. TestFlight/App Store require
  separate Apple distribution setup. GitHub stores source, not iPhone installs.

## Release sequence

1. Run automated and physical checks in [DEVELOPMENT.md](DEVELOPMENT.md).
2. Commit changes and choose a version/tag, such as `v0.1.0` for the first
   prototype. No release tag has been created yet.
3. Build on Windows and Mac from the same source tag.
4. Test installation, launch, connections, upgrades and removal as applicable.
5. Upload packages to a GitHub Release with platform/architecture labels,
   checksums and known limitations. Mark prototypes as prereleases.

CI and automatic release publishing are not configured in this initial repo.
