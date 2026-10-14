import http.client
import json
import threading
import unittest

from server import Relay


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.server = Relay(("127.0.0.1", 0), "test-key")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def upload(self, body, key="test-key", content_type="image/jpeg"):
        return self.request("POST", "/frame", body,
                            {"Authorization": f"Bearer {key}", "Content-Type": content_type})

    def post_json(self, path, data, key="test-key"):
        return self.request("POST", path, json.dumps(data),
                            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})

    def camera_report(self, session="camera-one", revision=0, error=""):
        caps = {"manualExposure": True, "autoExposure": True,
                "manualFocus": True, "autoFocus": True,
                "manualWhiteBalance": True, "autoWhiteBalance": True, "canZoom": True}
        for name, bounds in {"iso": (25, 1600), "shutterMs": (0.1, 1000), "focus": (0, 1),
                             "temperature": (2000, 10000), "tint": (-150, 150), "zoom": (1, 6)}.items():
            caps[name] = {"min": bounds[0], "max": bounds[1]}
        current = {"exposureAuto": True, "iso": 100, "shutterMs": 16.67,
                   "focusAuto": True, "focus": 0.5, "whiteBalanceAuto": True,
                   "temperature": 5000, "tint": 0, "zoom": 1}
        return {"session": session, "capabilities": caps, "current": current,
                "appliedRevision": revision, "error": error}

    def command(self, settings, revision=0, session="camera-one"):
        return self.post_json("/controls", {"session": session, "revision": revision, "settings": settings})

    def test_pairing_required_for_read_and_write(self):
        self.assertEqual(self.request("GET", "/status")[0], 401)
        self.assertEqual(self.request("GET", "/stream.mjpg?key=wrong")[0], 401)
        self.assertEqual(self.upload(b"\xff\xd8test\xff\xd9", key="wrong")[0], 401)
        self.assertEqual(self.server.sequence, 0)

    def test_rejects_malformed_and_oversized_frames(self):
        self.assertEqual(self.upload(b"not a jpeg")[0], 400)
        self.assertEqual(self.upload(b"\xff\xd8test\xff\xd9", content_type="text/plain")[0], 415)
        self.assertEqual(self.request("POST", "/frame", headers={
            "Authorization": "Bearer test-key", "Content-Length": "8000001"})[0], 413)
        self.assertEqual(self.server.sequence, 0)

    def test_latest_frame_and_connection_status(self):
        _, body = self.request("GET", "/status?key=test-key")
        self.assertFalse(json.loads(body)["connected"])
        for frame in (b"\xff\xd8first\xff\xd9", b"\xff\xd8second\xff\xd9"):
            self.assertEqual(self.upload(frame)[0], 204)
        self.assertEqual(self.server.frame, frame)
        _, body = self.request("GET", "/status?key=test-key")
        self.assertTrue(json.loads(body)["connected"])
        self.assertEqual(json.loads(body)["frames"], 2)
        self.server.last_frame -= 5
        _, body = self.request("GET", "/status?key=test-key")
        self.assertFalse(json.loads(body)["connected"])

    def test_stream_delivers_multipart_frame(self):
        # JPEG markers exercise transport framing; no image decoder is involved.
        frame = b"\xff\xd8payload\xff\xd9"
        self.upload(frame)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("GET", "/stream.mjpg?key=test-key")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn("multipart/x-mixed-replace", response.getheader("Content-Type"))
        self.assertEqual(response.readline(), b"--frame\r\n")
        self.assertEqual(response.readline(), b"Content-Type: image/jpeg\r\n")
        self.assertEqual(response.readline(), f"Content-Length: {len(frame)}\r\n".encode())
        self.assertEqual(response.readline(), b"\r\n")
        self.assertEqual(response.read(len(frame)), frame)
        response.close()
        connection.close()

    def test_preview_is_available_without_key(self):
        code, body = self.request("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn(b"Free Cam", body)

    def test_camera_control_roundtrip_and_acknowledgement(self):
        code, body = self.post_json("/camera", self.camera_report())
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body), {"revision": 0, "settings": {}})
        settings = {"exposureAuto": False, "iso": 400, "shutterMs": 8.33}
        code, body = self.command(settings)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["revision"], 1)
        code, body = self.post_json("/camera", self.camera_report())
        self.assertEqual(json.loads(body), {"revision": 1, "settings": settings})
        report = self.camera_report(revision=1)
        report["current"].update(settings)
        self.post_json("/camera", report)
        _, body = self.request("GET", "/status?key=test-key")
        state = json.loads(body)
        self.assertTrue(state["cameraConnected"])
        self.assertEqual(state["camera"]["appliedRevision"], state["revision"])
        self.assertEqual(state["camera"]["current"]["iso"], 400)

    def test_control_endpoints_require_pairing(self):
        self.assertEqual(self.post_json("/camera", self.camera_report(), key="wrong")[0], 401)
        self.assertEqual(self.post_json("/controls", {"settings": {"zoom": 2}}, key="wrong")[0], 401)

    def test_invalid_controls_are_not_forwarded(self):
        self.post_json("/camera", self.camera_report())
        for patch in ({"iso": 400}, {"exposureAuto": False, "iso": 9999, "shutterMs": 10},
                      {"zoom": float("nan")}, {"zoom": True}, {"focusAuto": False},
                      {"whiteBalanceAuto": False, "temperature": 5000}, {"unknown": 1},
                      {"focusAuto": "false"}, {"zoom": 0.5}):
            with self.subTest(patch=patch):
                self.assertEqual(self.command(patch)[0], 400)
        self.assertEqual(self.server.settings, {})
        self.assertEqual(self.server.revision, 0)

    def test_unsupported_camera_controls(self):
        report = self.camera_report()
        report["capabilities"]["manualFocus"] = False
        report["capabilities"]["manualExposure"] = False
        self.post_json("/camera", report)
        self.assertEqual(self.command({"focusAuto": False, "focus": 0.5})[0], 400)
        self.assertEqual(self.command({"exposureAuto": False, "iso": 100, "shutterMs": 10})[0], 400)
        self.assertEqual(self.command({"focusAuto": True})[0], 200)

    def test_offline_conflicts_and_capture_session_reset(self):
        self.assertEqual(self.command({"zoom": 2})[0], 409)
        self.post_json("/camera", self.camera_report())
        self.assertEqual(self.command({"zoom": 2}, session="other")[0], 409)
        self.assertEqual(self.command({"zoom": 2})[0], 200)
        self.assertEqual(self.command({"zoom": 3})[0], 409)
        self.server.last_camera -= 5
        self.assertEqual(self.command({"zoom": 3}, revision=1)[0], 409)
        self.post_json("/camera", self.camera_report(session="new-camera"))
        self.assertEqual(self.server.settings, {})
        self.assertEqual(self.server.revision, 0)

    def test_error_reports_and_command_merging(self):
        self.post_json("/camera", self.camera_report())
        self.command({"zoom": 2})
        self.assertEqual(self.command({"focusAuto": False, "focus": 0.2}, revision=1)[0], 200)
        self.assertEqual(self.server.settings, {"zoom": 2, "focusAuto": False, "focus": 0.2})
        self.post_json("/camera", self.camera_report(revision=2, error="Camera configuration lock failed"))
        _, body = self.request("GET", "/status?key=test-key")
        self.assertIn("lock failed", json.loads(body)["camera"]["error"])

    def test_malformed_reports_cannot_replace_valid_camera(self):
        self.post_json("/camera", self.camera_report())
        self.command({"zoom": 2})
        for report in ({}, [], self.camera_report(revision=5), self.camera_report(session="bad-new-camera", revision=1)):
            self.assertEqual(self.post_json("/camera", report)[0], 400)
        self.assertEqual(self.server.camera["session"], "camera-one")
        self.assertEqual(self.server.settings, {"zoom": 2})
        self.assertEqual(self.server.revision, 1)

    def resolution_report(self):
        report = self.camera_report()
        report["capabilities"]["resolutions"] = [
            {"id": "1280x720", "label": "720p", "width": 1280, "height": 720},
            {"id": "1920x1080", "label": "1080p", "width": 1920, "height": 1080}]
        report["current"]["resolution"] = "1280x720"
        return report

    def test_resolution_change_discards_old_sensor_commands(self):
        report = self.resolution_report()
        self.post_json("/camera", report)
        self.command({"exposureAuto": False, "iso": 400, "shutterMs": 10})
        self.assertEqual(self.command({"resolution": "1920x1080"}, revision=1)[0], 200)
        self.assertEqual(self.server.settings, {"resolution": "1920x1080"})
        self.assertEqual(self.command({"zoom": 2}, revision=2)[0], 409)
        report["appliedRevision"] = 2
        report["current"]["resolution"] = "1920x1080"
        self.post_json("/camera", report)
        self.assertEqual(self.command({"zoom": 2}, revision=2)[0], 200)

    def test_resolution_must_be_supported_by_selected_device(self):
        self.post_json("/camera", self.resolution_report())
        for settings in ({"resolution": "3840x2160"}, {"resolution": True},
                         {"resolution": "1920x1080", "zoom": 2}):
            self.assertEqual(self.command(settings)[0], 400)
        self.assertEqual(self.server.revision, 0)

    def test_legacy_phone_cannot_receive_resolution_commands(self):
        self.post_json("/camera", self.camera_report())
        self.assertEqual(self.command({"resolution": "1280x720"})[0], 400)
        self.assertEqual(self.command({"zoom": 2})[0], 200)

    def test_invalid_resolution_report_is_rejected(self):
        report = self.resolution_report()
        report["current"]["resolution"] = "3840x2160"
        self.assertEqual(self.post_json("/camera", report)[0], 400)
        report = self.resolution_report()
        report["capabilities"]["resolutions"][0]["width"] = False
        self.assertEqual(self.post_json("/camera", report)[0], 400)


if __name__ == "__main__":
    unittest.main()
