# Direct USB transport

No hotspot or iTunes process is used. Windows needs the Apple Mobile Device USB
driver and multiplexing service; macOS provides the service. The app lists only
USB devices, excluding wireless devices exposed by the same service. It cannot
replace a missing Windows driver and does not install drivers.

The desktop connects to the existing service at 127.0.0.1:27015 (Windows) or
/var/run/usbmuxd (macOS). Plist protocol version 1 lists devices and opens iPhone
port 8766; the connect request's port is in network byte order. The iOS application
binds only to 127.0.0.1:8766 using Network.framework. Device trust is established
by the operating system, with an additional NoSub Cam pairing-key handshake.

Each application packet is a four-byte big-endian payload length, followed by a
one-byte type and body. The length includes the type byte. Protocol version is 1.

| Type | Direction | Body |
| --- | --- | --- |
| 1 | Desktop to iPhone | JSON: version and desktop pairing key |
| 5 | iPhone to desktop | JSON: accepted version |
| 2 | iPhone to desktop | JPEG, at most 8 MB |
| 6 | Desktop to iPhone | Empty body; frame consumed acknowledgement |
| 3 | iPhone to desktop | CameraReport JSON, at most 64 KiB |
| 4 | Desktop to iPhone | CameraCommand JSON |

At most two frames wait for desktop acknowledgements, allowing capture and USB
transfer to overlap without building an unbounded queue. Capture drops frames
while that two-frame window is full. Reports run every 500 ms; their
response carries pending sensor commands. The sensor validation, revision and
session semantics are shared with the Wi-Fi receiver. Cancellation closes sockets;
a new connection creates a new capture session ID. An unpaired connection times
out after five seconds. The listener remains available after a cable disconnect.

Source changes restart the receiver and rotate its pairing key. HTTP camera/frame
uploads are rejected while USB or macOS native capture is selected, preventing
an older Wi-Fi session from overwriting the chosen source. Local OBS stream viewing
remains authenticated with the current key.

Run the Python receiver and desktop suites for simulated protocol checks. Tests
cover fragmented reads, EOF, size bounds, USB-only enumeration, port encoding,
frame acknowledgements, command delivery and source isolation. Physical USB is
not yet verified: build the updated iPhone app on a Mac, then test cable removal,
wrong keys, reconnect, manual sensor settings, all supported resolutions and advertised frame rates.

Protocol reference: https://github.com/libimobiledevice/libusbmuxd
Our Python implementation uses the local wire protocol directly; it does not
bundle libimobiledevice binaries or drivers.
