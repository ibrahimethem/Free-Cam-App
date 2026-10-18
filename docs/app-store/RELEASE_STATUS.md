# NoSub Cam release status

Updated: October 18, 2026 (Europe/Istanbul).

## App Store Connect

- App: NoSub Cam, Apple ID `6823797679`, bundle ID `com.ethem.nosubcam`.
- iOS version `1.0.0`, build `2`, processed/valid and selected for review.
- English metadata, review instructions, and private review contact uploaded.
- Three iPhone screenshots for each of the medium and large Dynamic Island sizes uploaded with Fastlane.
- Privacy Policy URL configured; Data Not Collected declaration published with owner approval.
- Age rating: 4+. Primary category: Photo & Video; secondary: Utilities.
- Content rights configured as no third-party content. Standard Apple EULA.
- Free pricing configured. Availability: 174 storefronts, excluding China mainland,
  with explicit owner approval. Future storefronts are not automatically enabled.
- Release option: **manual**, preserved. Approval does not automatically publish the app.
- App Store Review: **WAITING_FOR_REVIEW**, submitted October 18.
- TestFlight Beta App Review: **WAITING_FOR_BETA_REVIEW**, submitted October 18.
- Friends & Family external group includes build 2, public link enabled, limit 10:
  https://testflight.apple.com/join/kfnGFXRK. Installation depends on Apple approval.
- Both review instructions now include the public notarized Mac DMG and Wi-Fi/QR
  pairing steps. Other existing TestFlight groups were not modified.
- Fastlane metadata precheck completed successfully.

## Public Mac download and current validation

Public release: https://github.com/ibrahimethem/Free-Cam-App/releases/tag/v1.0.0

Website: https://ibrahimethem.github.io/Free-Cam-App/download/

The signed/notarized app and drag-to-Applications DMG are stapled and accepted by
Gatekeeper. Target: **Apple Silicon, macOS 14.4+**; no Intel package. Published
asset sizes and SHA-256 digests match local outputs; anonymous download URLs
return HTTP 200. GitHub Pages deployed successfully; only Mac downloads are active.

Runtime notices and modification/rebuild instructions are embedded in the app.
Matching Qt/PySide/Shiboken sources and checksum are release assets. Unused Qt
Virtual Keyboard, QML/Quick, FFmpeg and Pillow are excluded. 66 hardware-free
regression tests passed; bundled Qt/AVFoundation/native bridge linkage passed.
The installed app was not replaced/relaunched during this packaging pass. No
new physical streaming or clean minimum-macOS installation test was performed.

## Earlier installation and implementation checks (historical)

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

The installation notes above describe earlier checks, not current release gates.
Since then the owner has tested Windows, the installer has been implemented, and
iOS build 2 has been uploaded and submitted as stated above. The original build 1
and earlier pending-upload statements do not describe the current submission.

**Windows signed-production download stays disabled; unsigned public beta 1 is
published separately:**
https://github.com/ibrahimethem/Free-Cam-App/releases/tag/v1.0.0-windows-beta.1

CI run `39158635643` built source `f0906628c497fba142cb6063d8bc5ce57b9022ce`.
71 Python regression tests, native conversion/activation/restart checks, bridge
loading, native-file inventory and embedded product-icon verification passed.
Packaged offscreen demo startup passed (simulated, not physical camera proof).
Windows runtime notices, corresponding source archive and a 60-native-file hash
report accompany this beta. Published sizes/digests match local outputs; the
anonymous installer URL returns HTTP 200. Checksum sidecars were normalized to
LF on the release host without modifying the installer/source archives.
The signed Mac release remains latest stable. No installed Mac app was replaced:
the public Mac bundle icon matches the mobile artwork; the legacy installed
development app still has PyInstaller's template icon/version `0.0.0`.

The owner reports that SignPath
Foundation declined the initial application due to insufficient established
usage/reputation history. Approval is not pending. Store/MSIX assessment found
that the current native camera needs a separate system-wide COM installation;
a self-contained Store-signed solution is not yet demonstrated. The owner accepts
an unsigned public beta as fallback. A clean physical Windows install/upgrade/
uninstall and video-app test of this exact beta is not claimed completed.
See [Windows Store assessment](../WINDOWS-STORE.md).
The protected `windows-signing` environment
is main-only with owner review. No signing API token has been installed. Windows
complete production installer/uninstaller signing remains a separate gate;
unsigned beta/Actions artifacts are not signed production releases.

## Local-only release files

The signed iOS package is at `fastlane/build/export/FreeCam.ipa`. Archives, release
logs, and export/upload settings remain under ignored build paths.

Review phone and the optional path to the authorized shared API configuration are
in ignored `fastlane/.env`. API key material remains outside this repository.
No private configuration, signing material, or review phone belongs in Git.

## Useful commands

```sh
bundle exec fastlane ios store_assets screenshots:false
bundle exec fastlane ios select_review_build build_number:2
```

The latter selects an already processed build without submitting it to review.
Pricing is configured in App Store Connect, not through Fastlane's obsolete
`price_tier` API.

The normal Fastlane upload lanes still do not auto-submit future versions. These
two submissions were explicit owner-authorized operations through Fastlane's
Spaceship API against the existing build; no new iOS build was created.
Track review progress: https://appstoreconnect.apple.com/apps/6823797679
