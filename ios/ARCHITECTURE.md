# iOS architecture

Minimum deployment target: iOS 26. Build with Xcode 26 or later and an iOS 26 SDK.
Swift 5 language mode is intentional for the existing queue-based AVFoundation
pipeline; adopting Swift 6 strict concurrency is a separate migration.

These are feature folders within one application target. There are no external
Swift packages or framework targets to manage for the prototype.

| Folder | Responsibility |
| --- | --- |
| App | Entry point and main-actor observable session owned by the screen |
| UI | Screen composition, connection form and UIKit camera-preview bridge |
| Camera | AVFoundation capture, supported presets, readings and manual settings |
| Controls | JSON command/report envelopes and periodic desktop control exchange |
| Streaming | Receiver validation, JPEG upload, backpressure and lifecycle cancellation |

`ContentView` owns `StreamingSession` using `@State`. Its engine composes
`CameraCapture` and `CameraControlChannel`. A shared serial dispatch queue owns
capture configuration, device access, frame processing and control-channel state.
Network completions return to that queue before changing state. Observable UI
updates and the idle timer run on the main actor. The preview receives only the
capture session, not the engine or network services.

Frame uploads allow only one in-flight JPEG and skip frames to target up to 24 FPS.
Control requests run independently every 500 ms, with only one in flight. Both
paths use cancellation and generation checks to discard completions from earlier
sessions. Stopping also invalidates pending camera-permission callbacks.

A new control session receives a new UUID and resets its acknowledged revision.
Processed commands are acknowledged even when hardware validation fails, with
an error and live readings included in the next report. Resolution changes restore
supported automatic sensor modes before changing the preset; subsequent reports
refresh the desktop ranges. Manual settings validate before changing sensor values.

The pairing key lives in screen/session memory. Only the receiver address persists.
`ReceiverConnection` validates the private IPv4 or Bonjour receiver URL and constructs
control requests. Wire field names match the existing Python receiver.

`FreeCamTests` covers address validation and command decoding. Camera permissions,
start/stop/restart, resolutions and manual sensor controls still require a physical
iPhone build on a Mac. On-device validation should include stopping while permission
is pending and reconnecting after a rejected pairing key.

Direct USB adds `Streaming/USBChannel.swift`: a loopback-only Network listener
reached via the host USB multiplexing service. It shares the capture queue, reports
capabilities every 500 ms, acknowledges desktop commands and allows only one JPEG
awaiting a desktop acknowledgement. See `desktop/USB.md` for packet definitions.
