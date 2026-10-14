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
the key as a query parameter. Restarting the receiver rotates the pairing key.
Wi-Fi uses unencrypted local HTTP; do not expose it to the internet.

## Camera messages

A report contains `session`, `capabilities`, `current`, `appliedRevision` and
`error`. A command contains `revision` and `settings`. Desktop submissions also
include the current session and revision to reject stale edits.

Settings include `iso`, `shutterMs`, `focus`, `temperature`, `tint`, `zoom`,
`exposureAuto`, `focusAuto`, `whiteBalanceAuto` and `resolution`. Capabilities
advertise support flags, numeric ranges and optional supported resolutions.
Use the camera's advertised limits rather than assumptions about a device model.

Manual exposure sends ISO and shutter together with `exposureAuto: false`.
Manual focus and white balance similarly include their manual-mode flag and
required values. Send resolution changes separately; they clear previously
queued sensor commands. New capture sessions clear old settings.

Reports/commands exchange approximately every 500 ms. An applied revision
acknowledges processing; current sensor readings describe the resulting state.
Video and camera reports become stale after three seconds.

## USB and native capture

USB carries the same report/command models using a version-1 framed protocol.
See [the USB specification](../desktop/USB.md) for handshake, packet types,
limits and frame acknowledgements. Source changes rotate keys and clear state;
HTTP phone uploads are rejected while USB or native input is selected.
macOS Continuity uses Qt multimedia and has no Free Cam sensor command channel.

Preserve compatibility with reports without optional resolution fields. Add
appropriate Python and Swift checks when changing fields, units or semantics.
Breaking USB framing changes require an explicit protocol-version decision.
