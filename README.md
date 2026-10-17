# NoSub Cam

A subscription-free prototype for using an iPhone camera on Windows and macOS.
The native iOS app sends JPEG frames over Wi-Fi or direct USB to a standalone
desktop receiver. Signed Mac builds expose NoSub Camera directly; OBS remains
an optional output path (and is currently required on Windows). No account,
cloud relay, or paid service is used by the code.

## Repository and development

This is one repository for the entire product: `desktop/` is shared by Windows
and macOS, `ios/` is the iPhone app, and `receiver/` is the embedded video/control
server. Both apps must use compatible camera messages.

- [Windows and Mac development workflow](docs/DEVELOPMENT.md)
- [Shared connection and camera protocol](docs/PROTOCOL.md)
- [Build outputs and release process](docs/RELEASING.md)

Commit source code and XcodeGen's `ios/project.yml`; regenerate the Xcode project
on the Mac. Local environments, generated projects, packages, signing material
and previews are excluded from Git. Executables belong in GitHub Releases.

## Current scope

- iOS 26+ camera app with pairing, start/stop, and foreground streaming. Video is
  intentionally previewed only on the desktop to reserve phone resources for capture.
- Native Qt desktop interface for Windows/macOS: camera controls on the left,
  a large live preview in the center, and a dedicated connection panel on the right.
- One normal desktop instance per OS user on macOS and Windows. Opening another
  copy restores the existing window without restarting its receiver or webcam.
  Demo/screenshot modes are separate. On the first upgrade from an older build
  without this control, quit that old build via the menu bar/system tray once.
- Embedded receiver with automatic startup and a random pairing identity saved
  in macOS Keychain/Windows Credential Locker. Scan once on iPhone; its Keychain
  restores the last connection and transport on the next launch. Reset pairing
  explicitly revokes old keys. Wi-Fi IP changes still require an updated address/QR.
  No browser, web view, or separate server process is needed for the desktop app.
- Desktop camera settings: rear/front camera, portrait/landscape output, manual
  ISO/shutter, focus, white balance temperature/tint, zoom, and automatic modes,
  with live iPhone readings and capability-based ranges.
- Device-supported 480p, 720p, 1080p, and 4K selection from the desktop, plus
  capability-based 24, 30, and 60 FPS choices. Capture starts at 720p30 with native
  landscape output; delivered FPS depends on resolution, transport, and JPEG encoding.
- Signed macOS packages include NoSub Camera for direct 1080p30 webcam output
  without OBS. An experimental Windows 11 x64 native camera is now in source;
  OBS/MJPEG output is still available on both platforms.
- Direct USB transport without Personal Hotspot, using the host Apple USB service; physical device validation is pending.
- Optional macOS camera input for Continuity Camera, with camera selection and permission handling; Mac validation is pending.
- No audio, automatic Wi-Fi discovery, installer, or background capture yet.

## Run the standalone desktop app

**Windows:** open `dist/FreeCam/FreeCam.exe`. Keep the whole `dist/FreeCam` folder,
including `_internal`, together. The packaged app includes Python and Qt; no
Python installation or browser is needed to run it. This is a portable app,
not an installer.

The app starts its receiver automatically. Select your computer's Wi-Fi address
in the right connection panel, then enter it and the displayed pairing key in the iPhone app.
Permit inbound TCP port 8765 on your private network if the firewall prompts.
Do not run the older command-line receiver at the same time on that port.
If the port is already in use, close that receiver or run with `--port 8766`.
Stopping/restarting the desktop receiver keeps its securely saved pairing key.
Use **Reset pairing…** to revoke previously paired devices.

**macOS / source development:** install Python 3.10+ and run these commands
from the project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r desktop/requirements.txt
python desktop/app.py
```

For source development on Windows, activate `.venv/Scripts/Activate.ps1` instead.
The Qt-based code and packaging specification support both platforms; the Mac
build still needs to be built and tested on your Mac.

To inspect the UI without an iPhone, run `python desktop/app.py --demo`.

### Background operation

On macOS and Windows, closing the desktop window keeps the receiver, USB link
and enabled camera output running. A small camera icon remains in the macOS menu
bar or Windows notification area. Choose **Open NoSub Studio** to reopen the
window, or **Quit NoSub Studio** to stop streaming and exit. Windows tray clicks
also reopen the window; macOS uses the icon's menu. Cmd+Q remains a full quit.

If the system tray is unavailable, closing the window exits normally rather than
leaving an inaccessible process. Demo/screenshot runs keep the normal close-to-exit
behavior. This does not enable launch-at-login or streaming during system sleep.
On signed Mac builds, active streaming prevents App Nap without blocking normal
idle system sleep. Hidden windows skip preview decoding; camera output continues.
Demo mode is visibly labeled and uses a test image and synthetic camera settings.
It does not verify physical camera behavior, and listens on loopback only.

## Package a desktop executable

```sh
python -m pip install -r desktop/requirements-build.txt
python desktop/build.py
```

Build on Windows for `dist/FreeCam/FreeCam.exe`; build on macOS for
`dist/FreeCam.app`. The Mac app includes a local-network usage description.
Build outputs are unsigned development packages. Copy the full Windows folder
or the Mac app bundle when moving the app to another computer.
The original browser receiver remains available via `python receiver/server.py`
for development, but the native app disables those browser UI routes.

## Build the iPhone app on your Mac

1. Copy this folder to the Mac. Install Xcode 26 or later with an iOS 26 SDK, and XcodeGen (https://github.com/yonaskolb/XcodeGen).
2. Run `cd ios` followed by `xcodegen generate`.
3. Open the generated `FreeCam.xcodeproj` in Xcode.
4. Under Signing & Capabilities, select your development team and change the bundle
   identifier to a unique value if necessary. Select your connected iPhone as the destination.
5. Enable Developer Mode on the phone if Xcode requests it, then build and run.
6. Enter the receiver URL (for example `http://192.168.1.10:8765`) and its pairing key.
   Allow camera and local network access. Tap **Start streaming** and keep the app open.

If you do not use XcodeGen, create an iOS SwiftUI app in Xcode, replace its generated
Swift files with all files inside `ios/FreeCam/` (including subfolders), set iOS deployment target 26.0, and add the
camera/local-network usage descriptions and `NSAppTransportSecurity` →
`NSAllowsLocalNetworking = YES` from `ios/project.yml` to the target's Info settings.
Use Swift 5 language mode, as declared in the supplied project specification.

## iOS source structure

The iOS app uses small feature modules within one application target, rather than
separate framework targets. See [ios/ARCHITECTURE.md](ios/ARCHITECTURE.md) for ownership
and threading rules. `App` composes the observable session; `UI` contains SwiftUI
screens and preview; `Camera` owns capture, supported resolutions and sensor settings;
`Controls` handles telemetry and desktop commands; `Streaming` handles connection
validation, JPEG uploads and lifecycle cancellation. UI state uses Observation.

After generating the project, run the `FreeCam` scheme's tests in Xcode (Product > Test)
on an iOS simulator. The tests check receiver URL validation and desktop command
JSON compatibility without requiring camera hardware. They have been added but
cannot be run in this Windows environment.

## Studio appearance

Desktop and iOS use a neutral studio palette inspired by Ableton-style panels:
anthracite backgrounds, medium-gray surfaces and a warm orange accent. Controls
have compact corners, clear outlines and restrained highlighting. Desktop tokens
live in `desktop/theme.py`; matching iOS colors and panel/field styles live in
`ios/FreeCam/UI/StudioTheme.swift`. The iOS app uses a dark appearance and system
fonts that follow Dynamic Type. The new iOS styling still needs Xcode compilation
and on-device visual verification on a Mac.

## Direct USB (no hotspot)

1. Use a USB data cable, unlock your iPhone and trust the computer if prompted.
2. In the desktop connection selector, choose **NoSub Cam — Direct USB**.
3. In the updated iPhone app, enable **Direct USB connection**, enter the desktop
   pairing key, and tap **Start streaming**. The receiver address is unused in this mode.
4. On desktop, click **Refresh devices**, select the connected device and click
   **Connect camera**. Camera position, output orientation, ISO, shutter, focus,
   white balance, zoom and resolution use the same controls and acknowledgements
   as Wi-Fi.

No hotspot, internet access, IP entry or iTunes process is required. macOS supplies
its USB multiplexing service. Windows must have a working Apple Mobile Device USB
service and driver; Apple Devices can provide these without using iTunes. This app
detects an unavailable service and shows a setup panel with the official Apple Devices
Store link, retry and Wi-Fi fallback. The panel explains what to do if Apple Devices
is already installed; an unavailable service does not prove the app is missing.
The panel disappears when the service becomes available, including when no phone
is connected. NoSub Cam does not install
or redistribute drivers. Plugging in a cable alone cannot replace missing drivers.

USB communicates through the local Apple USB service to a loopback-only TCP listener
inside the iPhone app, port 8766. It does not turn the iPhone into a USB UVC webcam.
OBS is still used for webcam output. See [desktop/USB.md](desktop/USB.md) for protocol
and validation details. Rebuild the iPhone app on your Mac to use this mode.

## macOS Continuity Camera

Choose **Continuity Camera - macOS**, refresh cameras, select your iPhone from the
system camera list, and click **Connect camera**. The list can also contain built-in
and other macOS cameras; select your iPhone explicitly. Grant macOS camera access.
Use a packaged FreeCam.app for the supplied camera permission and Continuity plist keys.
The Mac build installs the optional PySide6-Addons multimedia module.

Enable Continuity Camera on your iPhone, use the same Apple Account with two-factor
authentication, and satisfy Apple's device requirements. Apple manages USB/wireless
selection; NoSub Cam does not force a route. Close NoSub Cam's iPhone capture session
before using Continuity Camera. See Apple's [Continuity Camera guide](https://support.apple.com/en-gb/102546).

This mode feeds preview and OBS output, but NoSub Cam's sensor controls and resolution
selector are disabled. Use NoSub Cam Wi-Fi or Direct USB for manual ISO/shutter and
other sensor settings. Windows shows Continuity Camera as unavailable.

Changing the desktop source restarts the receiver and clears previous frames and
settings, but keeps the saved pairing key. Switching between USB and Wi-Fi does
not require a new key.

## Control the iPhone camera from the desktop

After starting streaming on your iPhone, the native desktop app's right-hand
**Camera adjustments** panel enables controls supported by the selected camera.

Choose the rear or front camera and the portrait or landscape output orientation
in the left sidebar. Landscape uses the camera sensor's native 16:9 orientation
without rotating every frame; hold the iPhone horizontally for the intended framing.
Portrait physically rotates output buffers and costs additional processing. Changing cameras
restores the default 720p preset and supported automatic sensor modes because each
camera may expose different formats and limits.

Choose a resolution in the left sidebar to apply it immediately. Only
standard capture presets supported by the selected iPhone camera are offered:
480p (640×480), 720p (1280×720), 1080p (1920×1080), and 4K (3840×2160).
These dimensions name the capture preset; portrait video swaps width and height.
Front and rear cameras may expose different options. The selector and sensor
controls pause while a resolution change awaits acknowledgement.

Choose a frame rate after selecting the resolution; it applies immediately. The desktop only offers 24,
30, or 60 FPS when the active iPhone camera has a matching hardware format. A
resolution or camera change returns capture to 30 FPS and refreshes these choices.
Selecting 60 FPS configures the sensor for 60 FPS, but delivered FPS can still be
lower when JPEG encoding, USB/Wi-Fi transport, or the computer cannot keep up.

Resolution changes restore supported automatic exposure, focus, and white balance
modes, discard previously queued sensor commands, and refresh the displayed ISO,
shutter, and zoom limits. Reapply manual settings afterward. Higher resolutions
use more bandwidth and may lower the delivered FPS. The prototype accepts JPEGs
up to 8 MB; if a high-resolution frame exceeds that limit, select a lower resolution.
Rebuild the updated iPhone app to enable these features. Older builds still stream
and accept sensor controls, but the desktop resolution and frame-rate selectors show an update hint.

- **Exposure:** turn off Automatic, enter ISO and shutter speed (for example,
  `1/125` or `0.5` seconds), and changes apply automatically. Camera messages
  and saved presets still store the exposure duration in milliseconds.
  ISO and shutter must be locked together; the phone reports its active format's ranges.
- **Focus:** turn off Automatic and adjust lens position from 0 (nearest) to 1
  (furthest). Changes apply automatically. The value is not a calibrated distance in meters.
- **White balance:** turn off Automatic and enter temperature and tint,
  which apply automatically. The 2000–10000 K and -150–150 tint ranges are UI limits.
  The iPhone converts these to RGB gains and bounds them to hardware limits;
  the live readout may therefore differ from your requested values.
- **Zoom:** set the zoom factor to apply it automatically. This version uses the selected
  wide-angle camera's zoom, including digital zoom; it does not switch among physical lenses.
- To restore an automatic mode, check its Automatic box; it applies immediately.
  The left sidebar's Restore automatic settings button restores all supported auto modes.

Detailed ISO/shutter, focus, white-balance, and zoom choices are cached locally by
both NoSub Studio and NoSub Cam after a valid change. They are restored when capture
starts again; incompatible cached values are discarded safely. Selecting a saved
preset applies its resolution, FPS, and detailed camera settings. The desktop waits
for each format change to be acknowledged before applying sensor settings. The
selected preset is also reapplied when a new streaming session connects. Older
presets without resolution/FPS keep the current format. Unsupported settings are
reported without changing the stored preset. Editing keeps that preset selected and shows
**Modified** without changing its saved values. **Save** overwrites the selected
preset, while **Save As…** creates a new named preset. With no preset selected,
**Save** asks for a name. Both save buttons are disabled until settings differ
from the selected preset or the initial settings. Returning to the saved values
clears the modified indicator. Presets remain on the computer and can be deleted
from the same section.

The sliders and numeric fields stay in sync. Exposure and zoom sliders use a
logarithmic scale for easier adjustment across a large range. Mirror and rotation
controls affect the desktop preview only; configure webcam transforms in OBS.

Live readouts are separate from the editable fields, so automatic adjustments
do not overwrite what you are typing. Turning auto off initializes the manual
fields from the current readings. Unsupported controls remain disabled; front
camera capabilities can differ from those of the rear camera. Long shutter
durations can lower the capture frame rate.

Commands are exchanged separately from video every 0.5 seconds over Wi-Fi or direct USB. The desktop
shows when a command is waiting for an acknowledgement, and reports camera errors.
An acknowledgement means the phone processed the command; live readings reflect
the resulting sensor state as settings settle. Every new capture session resets
queued commands. Controls disable after three seconds without camera reports.
Pairing keys protect both the video stream and the control endpoints.

## Use it as a webcam

1. Install OBS Studio from https://obsproject.com on the receiving computer.
2. In OBS, add a **Media Source** and uncheck **Local File**.
3. Click **Copy OBS stream URL** in NoSub Studio and paste it into **Input**.
   If needed, set **Input Format** to `mpjpeg` and disable buffering.
4. Fit the source in the OBS scene. Native landscape is the recommended, fastest mode;
   choose portrait in NoSub Studio only when a vertical output is required.
   An additional OBS rotation is optional.
5. Click **Start Virtual Camera**, then select **OBS Virtual Camera** in your calling app.

Official virtual camera guide: https://obsproject.com/kb/virtual-camera-guide.

## Privacy and prototype limits

Wi-Fi mode uses unencrypted HTTP on your local network. Direct USB authenticates
its local connection with the pairing key but does not add application-level encryption. The pairing key gates
frame uploads and viewing, but does not encrypt video or authenticate the computer.
Use a trusted private Wi-Fi network; do not expose the port to the internet.
Stream URLs contain the pairing key, so treat them as private. No recordings are
saved; the receiver keeps only the latest JPEG in memory. The native app clears
stale preview frames after three seconds. OBS may retain its last displayed frame.
Stop the OBS virtual camera
when you finish. Use **Reset pairing…** to revoke shared desktop stream URLs;
the separate command-line receiver still generates a new key at launch.

The receiver bounds upload sizes and drops old frames instead of building a queue.
JPEG transport is deliberately simple for the initial prototype; H.264/WebRTC
and native Windows/macOS virtual camera integrations are the next engineering steps.

## Validation

Run `python -m unittest discover -s receiver -p "test_*.py"` for receiver integration tests,
and `python -m unittest discover -s desktop -p "test_*.py"` for native UI integration tests.
All 37 tests passed on Windows: 16 receiver tests and 21 desktop/USB tests.
These cover command delivery,
acknowledgement/error reports, range and support validation, stale-session rejection,
and the original video transport checks, plus native controls, preservation of
unsent edits, JPEG decoding, stale-preview clearing, receiver lifecycle, and
numeric-field layout. The packaged Windows app was also smoke-tested with a
headless screenshot. The demo preview uses synthetic camera readings and a test
image; this does not verify physical sensor behavior.
USB tests simulate the multiplexing service and phone packets, including fragmented
reads, disconnects, packet limits, device filtering, camera commands and source isolation.
They do not establish that real iPhone USB streaming works. macOS native capture
also requires a Mac for verification.
iOS compilation and physical iPhone/OBS testing require a Mac and devices; these
have not been performed in the Windows development environment.

On the Mac, regenerate the Xcode project after copying the updated Swift files.
On a physical phone, check that changing ISO at fixed shutter changes brightness,
manual focus changes sharpness, and manual white balance changes color. Confirm
auto modes resume adjustment after re-enabling them, and unsupported controls
remain disabled on cameras that lack them. Compare requested values to the live
readouts, and verify that stopping/restarting capture clears queued settings.
