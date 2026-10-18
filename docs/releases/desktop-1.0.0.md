# NoSub Studio 1.0.0 — macOS

Free desktop companion for NoSub Cam on iPhone. Receive a local camera feed,
control supported camera settings, save presets, and use NoSub Camera output
without OBS. No account, subscription, analytics or cloud video relay.

## Download and install

- **Apple Silicon Mac, macOS 14.4 or later.** Intel Mac is not supported by this package.
- Download `NoSub-Studio-1.0.0-macOS-Apple-Silicon.dmg`, open it and drag
  NoSub Studio to Applications. Quit an older version from its menu-bar menu
  before replacing it; closing the window does not quit the app.
- The app and disk image are Developer ID signed, Apple notarized and stapled.
- Pair your iPhone using Show pairing QR on the desktop and Scan pairing QR
  in NoSub Cam. Use a trusted local Wi-Fi network; VPNs must allow LAN traffic.
- Installing the optional NoSub Camera extension requires macOS approval.
  Native webcam output is 1080p30. Receiving/previewing works without it.

**iOS availability:** NoSub Cam 1.0.0 (2) was submitted to both TestFlight Beta
App Review and App Store Review on October 18, 2026; both await Apple review.
App Store publication remains manual. The desktop does not replace the iPhone app; a beta
invitation is usable only after Apple's external-testing approval.

**Windows:** Windows 11 x64 has been tested, but the signed production installer
is not included in this release. Signing-provider approval is still pending.
Do not treat GitHub Actions unsigned test artifacts as signed public installers.

## Verification and open source

SHA-256 checksum sidecars accompany both binary and source assets. On Mac:

```sh
shasum -a 256 -c NoSub-Studio-1.0.0-macOS-Apple-Silicon.dmg.sha256
```

Original NoSub code is MIT-licensed. Third-party licenses remain in effect.
License notices and modification/rebuild instructions are inside the app at
`Contents/Resources/licenses`. Qt/PySide/Shiboken are dynamically linked under
LGPLv3; their matching unmodified upstream sources are provided in the
`NoSub-Studio-1.0.0-Third-Party-Sources.zip` asset alongside this DMG.
Application source is available from this release's source tag.

This packaging revision removes unused Qt Virtual Keyboard, QML/Quick, FFmpeg
and Pillow components. It does not change the streaming protocol or require
existing users to reset pairing. macOS camera capture uses AVFoundation.

Setup, privacy, and support: https://ibrahimethem.github.io/Free-Cam-App/
