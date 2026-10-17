# NoSub Cam release status

Updated: October 17, 2026 (Europe/Istanbul).

## App Store Connect

- App: NoSub Cam, Apple ID `6823797679`, bundle ID `com.ethem.nosubcam`.
- iOS version `1.0.0`, build `1`, uploaded successfully and selected for review.
- English metadata, review instructions, and private review contact uploaded.
- Three iPhone screenshots for each of the medium and large Dynamic Island sizes uploaded with Fastlane.
- Privacy Policy URL configured; Data Not Collected declaration published with owner approval.
- Age rating: 4+. Primary category: Photo & Video; secondary: Utilities.
- Content rights configured as no third-party content. Standard Apple EULA.
- Free pricing configured. Availability: 174 storefronts, excluding China mainland,
  with explicit owner approval. Future storefronts are not automatically enabled.
- Release option: manual. Review has **not** been submitted.
- Fastlane metadata precheck completed successfully.

## Required before review submission

The desktop companion download page currently contains preparation notices rather
than an installable companion download. Publish an accessible desktop package and
verify its download/install flow so App Review can test the iPhone app.

Developer ID Application identity was created with owner approval; its private
key remains in local Keychain. NoSub Mac host/extension identifiers and an active
Developer ID host profile with system-extension installation are prepared. The
camera-enabled Mac package is signed, signature-verified, accepted by Apple
notarization, stapled, and accepted by Gatekeeper as Notarized Developer ID.
It is installed at `/Applications/NoSub Studio.app` and launches successfully.
The owner approved the camera extension in macOS settings. Extension build
`1.0.0/4` is activated/enabled and camera discovery reports available. Native
1080p30 output starts successfully in the installed host. A real iPhone-to-video
app image/performance test is still pending; no iPhone was connected during the
installation check.

The installed Mac package now includes menu-bar background operation. Closing
the window hides it without shutting down the receiver/native output; Open and
Quit actions are available from the camera icon. The live installed app kept its
receiver listening after the window closed. Nine tray/lifecycle tests, ten camera
bridge tests and one live-localhost background-stream test passed. Windows tray
behavior is implemented in shared Qt code, but has not been tested on Windows.
Streaming uses a scoped App Nap activity; normal system sleep is still allowed.
See [native camera status](../../desktop/native/README.md). An experimental
Windows 11 x64 native implementation and unsigned portable test package are now
available in source/GitHub Actions. Windows CI passed 42 hardware-free tests,
native NV12 pixel conversion and direct COM media-source activation, sample
allocation/timing and black-fallback checks without installing a camera.
Actual Windows UAC setup, iPhone-to-Frame-Server output and video-app
interoperability still need the owner's Windows PC. Authenticode signing,
product installer and public platform download publication remain pending.

The installed Mac package also remembers its pairing identity in macOS Keychain
(Windows uses Credential Locker). Explicit Reset pairing revokes the old key;
normal receiver restarts and USB/Wi-Fi changes keep it. Seven secure-identity
tests and four live-localhost pairing lifecycle tests passed. The iPhone source
now restores its last connection from device-only Keychain, with explicit Forget
and Start actions. A generic iOS Simulator build succeeded; this iOS update has
not been installed on a phone or uploaded to App Store Connect. Build 1 above is
unchanged. The updated local privacy-policy copies must be published alongside
the remembered-pairing release. Wi-Fi address changes still require updating the
address or scanning a new QR code; automatic rediscovery is not implemented.

No GitHub release, DMG publication, source push, or App Review submission was
performed during this Mac installation. The desktop website still needs real
download links before the iOS review is submitted.

## Local-only release files

The signed iOS package is at `fastlane/build/export/FreeCam.ipa`. Archives, release
logs, and export/upload settings remain under ignored build paths.

Review phone and the optional path to the authorized shared API configuration are
in ignored `fastlane/.env`. API key material remains outside this repository.
No private configuration, signing material, or review phone belongs in Git.

## Useful commands

```sh
bundle exec fastlane ios store_assets screenshots:false
bundle exec fastlane ios select_review_build build_number:1
```

The latter selects an already processed build without submitting it to review.
Pricing is configured in App Store Connect, not through Fastlane's obsolete
`price_tier` API.
