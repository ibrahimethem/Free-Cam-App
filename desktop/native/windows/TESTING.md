# Windows 11 native camera — test build

This is an **unsigned, experimental implementation**, not a verified public
Windows release. Native compilation, 42 hardware-free Python checks, pixel
conversion and direct COM media-source/frame checks passed on Windows CI without
registering a camera. Actual Windows 11 installation and camera interoperability
still need a physical test before publishing an installer. Do not disable Defender, SmartScreen,
driver-signature enforcement, or camera privacy settings as a workaround.

## Requirements

- x64 Windows 11 build 22000 or later. ARM64 and Windows 10 native output are not
  supported by this initial build. Wi-Fi/USB reception remains independent.
- For source builds: 64-bit Python 3.13, Git, Visual Studio 2022 with Desktop
  development with C++, CMake tools, and Windows 11 SDK 22621 or later.
- The first build downloads pinned, MIT-licensed Microsoft Windows-Camera and
  WIL sources. No Apple keys, paid SDKs, OBS install or kernel driver is needed.

## Build and test from source

1. Pull the updated source and run `Run-Windows.cmd` once, then quit the app via
   the system tray (closing its window only hides it).
2. Run `Build-Windows-Camera.cmd`. Compilation does not install anything.
3. Run `Run-Windows.cmd` again. In the right panel choose **Install camera**.
   Confirm the explanation, then approve the Windows UAC prompt yourself.
4. The helper copies only the camera DLL to
   `C:\Program Files\NoSub Studio Camera\NoSubCamera.dll` and registers its own
   x64 COM class under HKLM. It does not install a service or kernel driver,
   change the firewall, or add a login/startup item. The normal app stays unelevated.
5. Pair the iPhone over Wi-Fi or Direct USB and start streaming. Choose **Enable
   NoSub Camera** on desktop. A current-user/session-lifetime virtual camera is
   created; it disappears when output/app stops. Windows may append
   “Windows Virtual Camera” to its display name.
6. Open Windows Camera and a conferencing app; select **NoSub Camera**. Output
   is 1920×1080 NV12 at up to 30 FPS, letterboxed without cropping. 4K/60 native
   output is not implemented. Preview transforms do not affect webcam output.

If camera access is denied, check Windows Settings → Privacy & security → Camera
and the policy for desktop apps; the app provides a shortcut. Windows privacy
controls are respected, not bypassed. An unsigned build may be blocked by your
security policy; use an approved/signed build rather than weakening protections.

## Regression checklist

- Color/orientation: use a bright scene, verify no crop or flipped image.
- Stop/restart output, switch USB/Wi-Fi, disconnect/reconnect the phone.
- Stop phone streaming: webcam must turn black within one second, not retain a
  private image. Quit desktop: virtual device must disappear.
- Close desktop window: system tray, receiver and output must remain active.
- Two camera consumers, closing one then both, reopening each.
- Cancel UAC: app must remain usable and show setup cancelled.
- Relaunch desktop: pairing key remains unchanged.
- Close all video apps and choose **Uninstall camera…**; confirm/UAC. Only this
  camera COM registration/DLL are removed; pairing/presets are retained.

## Build a portable test package

```powershell
.\.venv-windows\Scripts\python.exe -m pip install -r desktop/requirements-build.txt
.\.venv-windows\Scripts\python.exe desktop/build.py --native-camera
```

Keep the entire `dist/FreeCam` folder, including `_internal/native-camera` and
its third-party license notices. The optional GitHub workflow
`Build Windows camera test package` builds a downloadable test artifact, **not**
a public release, and never installs the camera on the CI runner. A successful
CI build does not substitute for the physical checks above. Authenticode signing
and a product-wide installer/uninstaller are still separate release work.

## Implementation

Microsoft's event queue, presentation descriptors and sample-allocator lifecycle
are staged from an immutable commit. Hardware camera wrapping and synthetic
frames are removed. The NoSub host converts the latest BGRA frame once into
NV12, with a bounded, memory-only local named pipe to Frame Server. The pipe
name is random per output session and supplied as a camera activation attribute.
Remote clients are rejected; its ACL permits only the host user, SYSTEM and
Local Service. Client I/O uses identification-only security quality of service
so a pipe server cannot impersonate Frame Server. I/O deadlines, latest-frame
replacement and a one-second stale-frame cutoff bound queueing and shutdown.

References: [MFCreateVirtualCamera](https://learn.microsoft.com/en-us/windows/win32/api/mfvirtualcamera/nf-mfvirtualcamera-mfcreatevirtualcamera),
[Microsoft's sample](https://github.com/microsoft/Windows-Camera/tree/626f8b19c5f367602f2e89c6b314573d3776c9df/Samples/VirtualCamera).
