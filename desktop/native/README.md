# Native virtual camera — implementation status

Goal: select **NoSub Camera** in video software without OBS. Existing authenticated
OBS/MJPEG output remains available as a fallback.

## macOS (12.3+)

CMIO Camera Extension and in-process activation/output bridge compile for arm64
and x86_64. Developer ID identity and host provisioning are prepared. The app is
signed, notarized, stapled, and installed in Applications on the development Mac;
extension build 4 is activated/enabled and native output starts. Details are in
`docs/app-store/RELEASE_STATUS.md`. Conferencing interoperability still requires
a physical test. Compiling alone does not install anything.

```sh
# Compile native components only (both Mac architectures)
.venv/bin/python desktop/native/macos/build.py
# Embed in the desktop app; this is NOT a signed release
.venv/bin/python desktop/build.py --native-camera
```

The Python/Qt app remains host-architecture-specific even though the native
components are universal. Label downloads accordingly.

### Frame path

An opt-in worker reads the latest receiver JPEG outside the relay lock, decodes
off the GUI thread, letterboxes without cropping into 1920×1080 BGRA and publishes
a frame to a bounded CMIO sink queue at up to 30 FPS. Input resolution/FPS settings are
unchanged. **4K/60 virtual output is not implemented.** Preview rotation/mirroring
remain preview-only, not applied to native output.

The extension offers one fixed 1080p30 source with host-clock sample timestamps.
Multiple consumers share one timer. Frames expire after one second; disabled or
disconnected output becomes black. Stop closes the input stream and releases
cached pixels. Frames travel in memory through CMIO/IOSurface; the initial
disk-backed prototype was removed before installation. No camera-frame file,
new network ports, cloud services, recording or pairing keys are introduced.
The sink accepts a single writer with the host signing identifier and Apple
team requirement; ordinary camera consumers have read access only. Verification
uses `kSecGuestAttributeDynamicCode` to inspect the kernel's loaded signature:
the role-user sandbox cannot open the host executable for ordinary disk-based
validation, and the legacy CMIO bridge reports `signingID="unknown"`. Neither
an unknown identifier nor a failed signature check is accepted as a fallback.

The Swift dynamic library runs inside the provisioned Python app so activation
uses the host's restricted entitlement/profile rather than an unprovisioned
command-line helper. The helper is now discovery diagnostics only.

While streaming, the host uses a scoped user-initiated ProcessInfo activity to
avoid App Nap when its window is hidden. The activity ends when streaming stops
or the app quits and explicitly allows normal idle system sleep. No persistent
power settings or login items are changed.

### Release checklist

1. Register/enable host and extension identifiers in the Apple team.
   macOS team-prefix app group: `G478PYWXZ4.com.ethem.nosubcam.desktop`.
   Extension: `com.ethem.nosubcam.desktop.camera`.
2. Obtain Developer ID provisioning profiles where required. Keep profiles,
   private keys, certificates and review contact details outside Git.
3. Embed the host profile and sign inside-out: native dylib/diagnostic helper,
   extension with `CameraExtension.entitlements`, all nested code and host with
   the same Developer ID team and hardened runtime. Host needs camera,
   system-extension and app-group entitlements (`CameraHost.entitlements`). Preserve Qt/Python signing
   requirements. Ad-hoc signing cannot activate this extension.
4. Notarize/staple and package a DMG. Install in Applications, choose **Install
   camera** and approve in macOS settings. Never disable SIP or use developer-mode
   activation as a release workaround.
5. Verify discovery/frames in QuickTime and a conferencing app; test disconnect,
   reconnect, stop, multiple consumers, upgrade and removal.

### Local checks

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s desktop -p test_virtual_camera.py
```

Validation so far: universal native compile; ten bridge/conversion/worker tests.
Two targeted desktop lifecycle checks are also run for this package. Earlier full desktop suite:
20/21 passed; the remaining existing test expects an empty settings command after
a new capture session, whereas the current preset/cache logic reapplies controls.
That test/behavior mismatch is separate from camera output and still needs review.

Installation check: Developer ID signature verification, Apple notarization,
stapler validation and Gatekeeper assessment passed. macOS extension approval,
discovery and native input-stream startup passed. Real iPhone frames and video-app
capture/performance still need the owner's physical test. No public download is
published yet.

### Signing and notarization

```sh
# SHA-1 of an existing Developer ID identity in local Keychain, not a private key
export NOSUB_CODESIGN_IDENTITY="YOUR_DEVELOPER_ID_CERTIFICATE_SHA1"
bundle exec ruby fastlane/mac_profile.rb
.venv/bin/python desktop/build.py --native-camera
.venv/bin/python desktop/native/macos/release.py --identity "$NOSUB_CODESIGN_IDENTITY"
bundle exec ruby fastlane/mac_notarize.rb
```

The profile script may register only the two NoSub Mac identifiers, enable the
host system-extension capability, and create its Developer ID profile. It never
exports private keys. It loads the already-authorized Apple API config from local
ignored env files. Profiles/notarization archives/results stay in ignored build.
The notarization step uploads only the prepared Mac archive to Apple; it does not
publish a GitHub release or submit the iOS app for App Review.

## Windows

Initial target: **Windows 11, build 22000+**, using Media Foundation's native
`MFCreateVirtualCamera`. Windows 10 support is deferred. This needs a native COM
media-source DLL and camera registration; a Python wrapper alone is insufficient.

**Not implemented:** Windows media source, bridge, registration/unregistration,
installer and hardware validation. The desktop UI does not claim Windows-native
camera support. Build/validate on Windows before publishing an installer.

## References

- [Apple camera extensions](https://developer.apple.com/documentation/coremediaio/creating-a-camera-extension-with-core-media-i-o)
- [Apple CMIO session](https://developer.apple.com/videos/play/wwdc2022/10022/)
- [Microsoft MFCreateVirtualCamera](https://learn.microsoft.com/en-us/windows/win32/api/mfvirtualcamera/nf-mfvirtualcamera-mfcreatevirtualcamera)
- [Microsoft virtual camera sample](https://github.com/microsoft/Windows-Camera/tree/master/Samples/VirtualCamera)
