# NoSub Studio 1.0.0 — Windows public beta 1 (UNSIGNED)

Free Windows desktop companion for NoSub Cam on iPhone, including native webcam
output without OBS. **This is an unsigned beta, not a signed production release
or a Microsoft Store package.** Requires Windows 11 x64 and the iPhone app.
Windows ARM64/Windows 10 are not supported by this package.
Access to NoSub Cam on iPhone is distributed separately; this desktop download
does not grant TestFlight access or replace the iOS app. If you do not yet have
the iPhone app, wait for its availability before expecting a live camera feed.

## Download and install

Download `NoSub-Studio-1.0.0-Windows-x64-Public-Beta-1-Setup.exe` from this release.
Quit older NoSub Studio from the system tray first; closing its window only hides
it. Close video apps using NoSub Camera before upgrading/removing it. Choose the
full installation to include native camera output; receiver-only remains an
option. Setup requires administrator approval; normal operation does not.
No firewall exception, startup task, security bypass or root certificate is added.

Windows may show unknown-publisher/SmartScreen warnings or block this beta under
Smart App Control or organizational policy. **Do not disable Windows security,
antivirus, Defender or signature enforcement to run it.** If it is blocked on
your computer, wait for a signed release. A SHA-256 checksum detects file changes;
it is not a trusted-publisher signature. The app, camera DLL, setup helper,
installer and uninstaller are not Authenticode signed by NoSub.

Verify with PowerShell and compare the value to the `.exe.sha256` sidecar:

```powershell
Get-FileHash .\NoSub-Studio-1.0.0-Windows-x64-Public-Beta-1-Setup.exe -Algorithm SHA256
```

## Pair and use

- Keep iPhone and PC on the same trusted private network. Allow LAN traffic if
  using a VPN. Wi-Fi video uses unencrypted local HTTP; do not expose the port
  to the internet. Direct USB additionally requires Apple's USB software/service.
- On desktop, select NoSub Cam — Wi-Fi and Show pairing QR. Scan it in NoSub Cam
  on iPhone, allow camera/local-network access, and start streaming. Keep NoSub
  Cam in the foreground. No account, subscription or cloud video relay is used.
- Enable NoSub Camera on desktop and select it in your video app. Native output
  is 1080p30. Windows camera privacy permissions must allow desktop apps.
- Existing pairing and presets are retained; Reset pairing explicitly revokes
  the key. Uninstall through Windows Settings > Apps after quitting video apps.

## Validation and limitations

The maintainer previously tested the Windows iPhone/native-camera workflow.
This beta packaging revision adds licensing/source assets, explicit unsigned
warnings and verification of the embedded mobile-derived product icon. It removes
unused software-OpenGL/Qt OpenSSL components and accidentally collected Windows
OS shims. The normal Qt Widgets renderer and Python's own OpenSSL remain.
The streaming/camera protocol has not been redesigned for Microsoft Store.

CI checks Python regressions, native frame conversion, media-source activation,
repeated output transport lifecycle, packaged bridge loading, native-file
inventory and product EXE icon. A packaged **simulated** offscreen startup image
is a smoke test, not proof of a real iPhone/video-app session. A fresh physical
Windows 11 installer/upgrade/uninstall and third-party-video-app test of this
exact beta remains for users/maintainer; it is not claimed as completed in CI.

Report the Windows version and reproduction steps, without private footage or
pairing keys: https://github.com/ibrahimethem/Free-Cam-App/issues

## Open source and signatures

Original NoSub code is MIT licensed; third-party licenses remain in effect.
Installed runtime notices/modification instructions are under
`_internal/licenses/runtime`. Microsoft camera/WIL notices also accompany the
protected camera component. Matching Qt/PySide/Shiboken, Python and PyInstaller
sources are in `NoSub-Studio-1.0.0-Windows-Third-Party-Sources.zip` beside this
installer, with a SHA-256 sidecar. The tagged application source includes exact
upstream Microsoft camera/WIL pins and build/packaging scripts. No warranty.

SignPath's initial application was declined because the project lacks established
usage/reputation history; no Foundation sponsorship/certificate is claimed.
A later signed release can replace this beta through the normal installer
upgrade path, subject to validation. Approval by any provider is not guaranteed.

The separate macOS 1.0.0 download remains Developer ID signed and Apple notarized:
https://github.com/ibrahimethem/Free-Cam-App/releases/tag/v1.0.0

Privacy, support and downloads: https://ibrahimethem.github.io/Free-Cam-App/
