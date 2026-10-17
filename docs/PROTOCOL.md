# Shared camera protocol

The source of truth is `ios/FreeCam/Controls/CameraMessages.swift`, the camera
settings models, `receiver/controls.py` and `receiver/server.py`. Update both
implementations together when changing messages.

## Wi-Fi

The desktop receiver listens on TCP 8765 by default.

| Endpoint | Purpose |
| --- | --- |
| `POST /frame` | Latest JPEG, at most 8 MB |
| `POST /camera` | Phone camera report; response contains the command |
| `POST /controls` | Desktop settings with session and revision |
| `GET /status` | Connection state, camera report and command revision |
| `GET /stream.mjpg` | MJPEG output for OBS |

Authorization accepts `Authorization: Bearer <key>`; stream URLs may include
the key as a query parameter. NoSub Studio remembers a random 128-bit key in
macOS Keychain or Windows Credential Locker across restarts and transport changes.
Reset pairing explicitly rotates it and invalidates remembered phone/OBS access.
Stopping a receiver revokes its old server object, including keep-alive clients,
without deleting the saved identity. If secure storage is unavailable, the key
is session-only and the UI warns the user; it is never stored in plaintext settings.
The standalone `receiver/server.py` CLI still uses an ephemeral key.
Wi-Fi uses unencrypted local HTTP; do not expose it to the internet.
The iPhone may keep up to two frame uploads in flight to overlap JPEG encoding
and network latency. `X-NoSub-Frame-Session` and `X-NoSub-Frame-Sequence` let the
receiver discard a late older response without allowing an unbounded frame queue.

## Camera messages

A report contains `session`, `capabilities`, `current`, `appliedRevision` and
`error`. A command contains `revision` and `settings`. Desktop submissions also
include the current session and revision to reject stale edits.

Settings include `iso`, `shutterMs`, `focus`, `temperature`, `tint`, `zoom`,
`exposureAuto`, `focusAuto`, `whiteBalanceAuto`, `cameraPosition`, `orientation`
`resolution` and `frameRate`. Capabilities advertise support flags, numeric ranges and
optional supported camera positions, orientations, resolutions and frame rates.
Use the camera's advertised limits rather than assumptions about a device model.

Manual exposure sends ISO and shutter together with `exposureAuto: false`.
Manual focus and white balance similarly include their manual-mode flag and
required values. Send camera-position, resolution and frame-rate changes separately; they
clear previously queued sensor commands because the active camera format and its
limits may change. A resolution change resets capture to 30 FPS; the following
report advertises the 24/30/60 FPS choices actually supported at that resolution.
`landscape` is the native unrotated sensor output. `portrait`
physically rotates captured pixel buffers before transmission and therefore costs
additional per-frame work. New capture sessions clear old settings.

Reports/commands exchange approximately every 500 ms. An applied revision
acknowledges processing; current sensor readings describe the resulting state.
Video and camera reports become stale after three seconds.

## USB and native capture

USB carries the same report/command models using a version-1 framed protocol.
See [the USB specification](../desktop/USB.md) for handshake, packet types,
limits and frame acknowledgements. Source changes retain the saved key and clear state;
HTTP phone uploads are rejected while USB or native input is selected.
macOS Continuity uses Qt multimedia and has no NoSub Cam sensor command channel.

Preserve compatibility with reports without optional camera-position, orientation,
resolution or frame-rate fields. Add appropriate Python and Swift checks when changing fields,
units or semantics.
Breaking USB framing changes require an explicit protocol-version decision.
