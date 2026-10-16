"""USB framing, multiplexing and real receiver integration without an iPhone."""
import json
import os
import plistlib
import socket
import struct
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from app import demo_report
from server import Relay
from usb_transport import USBBridge, USBMux, read_exact, receive_packet, send_packet


class USBTests(unittest.TestCase):
    def test_fragmented_packets_and_disconnect(self):
        left, right = socket.socketpair()
        with left, right:
            body = struct.pack("!I", 4) + b"\x02abc"
            def send():
                for byte in body:
                    right.sendall(bytes([byte]))
                right.close()
            thread = threading.Thread(target=send)
            thread.start()
            self.assertEqual(receive_packet(left), (2, b"abc"))
            with self.assertRaises(ConnectionError):
                receive_packet(left)
            thread.join()

    def test_oversized_packet_rejected_before_body_read(self):
        left, right = socket.socketpair()
        with left, right:
            right.sendall(struct.pack("!I", 8_000_002))
            with self.assertRaises(ValueError):
                receive_packet(left)

    def test_mux_wire_request_and_usb_only_discovery(self):
        left, right = socket.socketpair()
        seen = []
        def daemon():
            with right:
                length, version, kind, tag = struct.unpack("<IIII", read_exact(right, 16))
                seen.append(plistlib.loads(read_exact(right, length - 16)))
                payload = plistlib.dumps({"DeviceList": [
                    {"DeviceID": 1, "Properties": {"ConnectionType": "USB", "SerialNumber": "wired"}},
                    {"DeviceID": 2, "Properties": {"ConnectionType": "Network", "SerialNumber": "wireless"}}]})
                right.sendall(struct.pack("<IIII", 16 + len(payload), version, kind, tag) + payload)
        thread = threading.Thread(target=daemon)
        thread.start()
        mux = USBMux()
        with patch.object(mux, "open", return_value=left), patch.object(
                mux, "device_info", return_value={"DeviceName": "Studio iPhone", "ProductType": "iPhone14,4"}):
            self.assertEqual(mux.devices(), [(1, "Studio iPhone · iPhone 13 mini")])
        thread.join()
        self.assertEqual(seen[0]["MessageType"], "ListDevices")

    def test_mux_connect_uses_network_order_port(self):
        mux = USBMux()
        left, right = socket.socketpair()
        with left, right, patch.object(mux, "open", return_value=left), patch.object(mux, "request", return_value={"Number": 0}) as request:
            self.assertIs(mux.connect(42), left)
            self.assertEqual(request.call_args.args[1]["PortNumber"], socket.htons(8766))

    def test_usb_frame_and_sensor_commands_share_receiver(self):
        relay = Relay(("127.0.0.1", 0), "secret", web_ui=False)
        relay.accept_phone = False
        bridge = USBBridge()
        left, right = socket.socketpair()
        left.settimeout(2)
        right.settimeout(2)
        errors = []
        def phone():
            try:
                with right:
                    kind, data = receive_packet(right)
                    self.assertEqual(kind, 1)
                    self.assertEqual(json.loads(data), {"version": 1, "key": "secret"})
                    send_packet(right, 5, b'{"version":1}')
                    send_packet(right, 2, b"\xff\xd8test\xff\xd9")
                    self.assertEqual(receive_packet(right), (6, b""))
                    send_packet(right, 3, json.dumps(demo_report()).encode())
                    kind, data = receive_packet(right)
                    self.assertEqual(kind, 4)
                    self.assertEqual(json.loads(data)["revision"], 0)
                    relay.submit_controls({"session": "desktop-demo", "revision": 0,
                                           "settings": {"exposureAuto": False, "iso": 400, "shutterMs": 8.33}})
                    send_packet(right, 3, json.dumps(demo_report()).encode())
                    kind, data = receive_packet(right)
                    self.assertEqual(json.loads(data)["settings"]["iso"], 400)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=phone)
        thread.start()
        try:
            with patch.object(bridge.mux, "connect", return_value=left):
                bridge.run(1, relay, threading.Event())
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(relay.frame, b"\xff\xd8test\xff\xd9")
            self.assertEqual(relay.camera["session"], "desktop-demo")
        finally:
            bridge.stop()
            relay.server_close()

    def test_native_frames_do_not_replace_wifi_source(self):
        relay = Relay(("127.0.0.1", 0), "secret", web_ui=False)
        try:
            relay.publish_native_frame(b"test")
            self.assertIsNone(relay.frame)
            relay.accept_phone = False
            relay.publish_native_frame(b"test")
            self.assertEqual(relay.sequence, 1)
        finally:
            relay.server_close()
