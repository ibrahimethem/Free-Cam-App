# iOS architecture

Minimum deployment target: iOS 26. Build with Xcode 26 or later and an iOS 26 SDK.
Swift 5 language mode is intentional for the existing queue-based AVFoundation
pipeline; adopting Swift 6 strict concurrency is a separate migration.

These are feature folders within one application target. There are no external
Swift packages or framework targets to manage for the prototype.

| Folder | Responsibility |
| --- | --- |
| App | Entry point and main-actor observable session owned by the screen |
| UI | Screen composition and connection form; live video is previewed on desktop |
| Camera | AVFoundation capture, supported presets, readings and manual settings |
| Controls | JSON command/report envelopes and periodic desktop control exchange |
| Streaming | Receiver validation, JPEG upload, backpressure and lifecycle cancellation |

`ContentView` owns `StreamingSession` using `@State`. Its engine composes
`CameraCapture` and `CameraControlChannel`. A shared serial dispatch queue owns
capture configuration, device access, frame processing and control-channel state.
Network completions return to that queue before changing state. Observable UI
updates and the idle timer run on the main actor. The phone UI intentionally avoids
a live capture preview so its rendering work is reserved for encoding and transport.

Frame uploads allow at most two in-flight JPEGs and skip frames when encoding or transport
cannot keep up with the selected 24, 30 or 60 FPS capture rate.
Wi-Fi uses persistent HTTP/1.1 connections so a new TCP connection is not created
for each JPEG. Per-session sequence headers prevent a late parallel upload from
replacing a newer frame. Native landscape avoids AVFoundation's per-frame buffer rotation.
The active camera format is configured for 30 FPS by default. Desktop frame-rate
changes select a concrete device format that supports the current resolution and requested
rate; unsupported combinations are never advertised. Capture callbacks are not
time-gated again because a second wall-clock threshold can alias a jittery 30 FPS
source down to roughly half rate. Frames drop only when the bounded transfer window is full.
Control requests run independently every 500 ms, with only one in flight. Both
paths use cancellation and generation checks to discard completions from earlier
sessions. Stopping also invalidates pending camera-permission callbacks.

A new control session receives a new UUID and resets its acknowledged revision.
Processed commands are acknowledged even when hardware validation fails, with
an error and live readings included in the next report. Resolution changes restore
supported automatic sensor modes and 30 FPS before changing the preset; subsequent reports
refresh the desktop ranges and valid frame rates. Manual settings validate before changing sensor values.
After every successfully applied command, the phone stores a sensor-only snapshot in
`UserDefaults`. Capture startup restores that snapshot after selecting the default camera
format. Camera position, orientation, resolution, connection details, and pairing keys are
excluded; an incompatible snapshot is discarded rather than blocking capture.

The last explicitly scanned/started pairing (key, address, and transport) is
stored in iOS Keychain with AfterFirstUnlockThisDeviceOnly protection and no
iCloud synchronization. It restores connection fields, not camera streaming:
the user still explicitly starts capture. Forget saved pairing removes this
local credential; Reset pairing on the desktop revokes access for all phones.
Secure-storage failure is surfaced and never falls back to plaintext key storage.
`ReceiverConnection` validates the private IPv4 or Bonjour receiver URL and constructs
control requests. Wire field names match the existing Python receiver.

`FreeCamTests` covers address validation and command decoding. Camera permissions,
start/stop/restart, resolutions and manual sensor controls still require a physical
iPhone build on a Mac. On-device validation should include stopping while permission
is pending and reconnecting after a rejected pairing key.

Direct USB adds `Streaming/USBChannel.swift`: a loopback-only Network listener
reached via the host USB multiplexing service. It shares the capture queue, reports
capabilities every 500 ms, acknowledges desktop commands and allows at most two
JPEGs awaiting desktop acknowledgements. See `desktop/USB.md` for packet definitions.
