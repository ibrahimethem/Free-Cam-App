"""Direct USB via the host's existing usbmux service; no iTunes process required."""
import json
import plistlib
import socket
import struct
import sys
import threading

from PySide6.QtCore import QObject, Signal

PORT = 8766
LOCKDOWN_PORT = 62078
MAX_PACKET = 8_000_001

APPLE_MODEL_NAMES = {
    "iPhone14,4": "iPhone 13 mini",
}


class USBServiceUnavailable(ConnectionError):
    """The service could not be reached; installation state is unknown."""


def read_exact(stream, length):
    chunks = bytearray()
    while len(chunks) < length:
        data = stream.recv(length - len(chunks))
        if not data:
            raise ConnectionError("USB connection closed")
        chunks.extend(data)
    return bytes(chunks)


def send_packet(stream, kind, data):
    payload = bytes([kind]) + data
    if not 1 <= len(payload) <= MAX_PACKET:
        raise ValueError("USB packet exceeds size limit")
    stream.sendall(struct.pack("!I", len(payload)) + payload)


def receive_packet(stream):
    length, = struct.unpack("!I", read_exact(stream, 4))
    if not 1 <= length <= MAX_PACKET:
        raise ValueError("Invalid USB packet size")
    payload = read_exact(stream, length)
    return payload[0], payload[1:]


class USBMux:
    def open(self):
        try:
            if sys.platform == "win32":
                return socket.create_connection(("127.0.0.1", 27015), timeout=3)
            stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            stream.settimeout(3)
            try:
                stream.connect("/var/run/usbmuxd")
            except OSError:
                stream.close()
                raise
            return stream
        except OSError as error:
            raise USBServiceUnavailable("Apple USB service unavailable. Windows needs Apple Mobile Device "
                                  "drivers/service (Apple Devices can provide them); iTunes does not need to run.") from error

    def request(self, stream, message):
        body = plistlib.dumps({"BundleID": "com.freecam.desktop", "ClientVersionString": "FreeCam-1",
                               "ProgName": "FreeCam", "kLibUSBMuxVersion": 3, **message})
        stream.sendall(struct.pack("<IIII", len(body) + 16, 1, 8, 1) + body)
        length, version, kind, tag = struct.unpack("<IIII", read_exact(stream, 16))
        if not 16 <= length <= 1_000_000 or (version, kind, tag) != (1, 8, 1):
            raise ValueError("Invalid Apple USB service response")
        return plistlib.loads(read_exact(stream, length - 16))

    def devices(self):
        with self.open() as stream:
            result = self.request(stream, {"MessageType": "ListDevices"})
        if "DeviceList" not in result:
            raise ConnectionError("Apple USB service could not list devices")
        devices = []
        for item in result["DeviceList"]:
            properties = item.get("Properties", {})
            if properties.get("ConnectionType") != "USB":
                continue
            device_id = item["DeviceID"]
            serial = properties.get("SerialNumber", "")
            try:
                info = self.device_info(device_id)
                name = info.get("DeviceName") or info.get("DeviceClass") or "iPhone / iPad"
                product = info.get("ProductType", "")
                model = APPLE_MODEL_NAMES.get(product, product)
                display = f"{name} · {model}" if model and model not in name else name
            except (OSError, ValueError, KeyError, plistlib.InvalidFileException):
                suffix = serial[-6:] if serial else "USB"
                display = f"iPhone / iPad · {suffix}"
            devices.append((device_id, display))
        return devices

    def connect(self, device_id, port=PORT):
        stream = self.open()
        try:
            reply = self.request(stream, {"MessageType": "Connect", "DeviceID": device_id,
                                           "PortNumber": socket.htons(port)})
            if reply.get("Number") != 0:
                raise ConnectionError("Cannot open NoSub Cam on iPhone. Unlock, trust this computer, "
                                      "select Direct USB in the iPhone app and start streaming.")
            return stream
        except Exception:
            stream.close()
            raise

    def device_info(self, device_id):
        with self.connect(device_id, LOCKDOWN_PORT) as stream:
            body = plistlib.dumps({"Label": "NoSub Studio", "Request": "GetValue"})
            stream.sendall(struct.pack("!I", len(body)) + body)
            length, = struct.unpack("!I", read_exact(stream, 4))
            if not 1 <= length <= 1_000_000:
                raise ValueError("Invalid iPhone identity response")
            response = plistlib.loads(read_exact(stream, length))
        value = response.get("Value")
        if not isinstance(value, dict):
            raise ValueError("iPhone identity is unavailable")
        return value


class USBBridge(QObject):
    devices_ready = Signal(list)
    message = Signal(str)
    active_changed = Signal(bool)
    service_checked = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mux = USBMux()
        self.stream = None
        self.worker = None
        self.cancelled = threading.Event()
        self.generation = 0

    def scan(self):
        self.generation += 1
        generation = self.generation
        def discover():
            try:
                devices = self.mux.devices()
                if generation != self.generation:
                    return
                self.service_checked.emit(True)
                self.devices_ready.emit(devices)
            except USBServiceUnavailable:
                if generation != self.generation:
                    return
                self.service_checked.emit(False)
                self.devices_ready.emit([])
            except (OSError, ValueError) as error:
                if generation != self.generation:
                    return
                self.message.emit(str(error))
                self.devices_ready.emit([])
        threading.Thread(target=discover, daemon=True).start()

    def start(self, device_id, relay):
        self.stop()
        cancelled = self.cancelled = threading.Event()
        self.worker = threading.Thread(target=self.run, args=(device_id, relay, cancelled), daemon=True)
        self.worker.start()

    def stop(self):
        self.generation += 1
        self.cancelled.set()
        stream = self.stream
        if stream:
            try:
                stream.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            stream.close()
        if self.worker:
            self.worker.join(timeout=0.1)
        self.active_changed.emit(False)

    def run(self, device_id, relay, cancelled):
        stream = None
        try:
            stream = self.mux.connect(device_id)
            if cancelled.is_set():
                return
            self.stream = stream
            self.service_checked.emit(True)
            send_packet(stream, 1, json.dumps({"version": 1, "key": relay.token}).encode())
            kind, data = receive_packet(stream)
            if kind != 5 or json.loads(data).get("version") != 1:
                raise ConnectionError("Pairing key rejected or incompatible iPhone app")
            self.active_changed.emit(True)
            self.message.emit("Direct USB connected")
            while not cancelled.is_set():
                kind, data = receive_packet(stream)
                if cancelled.is_set():
                    break
                if kind == 2:
                    if not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
                        raise ValueError("Invalid JPEG from USB camera")
                    relay.publish_native_frame(data)
                    send_packet(stream, 6, b"")
                elif kind == 3 and len(data) <= 65536:
                    command = relay.exchange_camera(json.loads(data))
                    send_packet(stream, 4, json.dumps(command, allow_nan=False).encode())
                else:
                    raise ValueError("Unexpected USB packet")
        except USBServiceUnavailable:
            if not cancelled.is_set():
                self.service_checked.emit(False)
        except (OSError, ValueError, TypeError, KeyError) as error:
            if not cancelled.is_set():
                self.message.emit("USB: " + str(error))
        finally:
            if stream:
                stream.close()
            if self.stream is stream:
                self.stream = None
            if not cancelled.is_set():
                self.active_changed.emit(False)
