"""Native widget + embedded receiver tests. Run with QT_QPA_PLATFORM=offscreen."""
import copy
import http.client
import json
import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication

from app import MainWindow, demo_report
from theme import STYLE
from usb_setup import APPLE_DEVICES_URL

APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")
APP.setStyleSheet(STYLE)


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow("127.0.0.1", 0)
        self.report = demo_report()

    def tearDown(self):
        self.window.close()

    def post(self, path, data, content_type="application/json"):
        relay = self.window.relay
        connection = http.client.HTTPConnection("127.0.0.1", relay.server_port, timeout=3)
        body = json.dumps(data).encode() if content_type == "application/json" else data
        connection.request("POST", path, body, {"Authorization": "Bearer " + relay.token,
                                                 "Content-Type": content_type})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def connect_camera(self):
        self.assertEqual(self.post("/camera", self.report)[0], 200)
        self.window.refresh()

    def test_disconnected_state_disables_controls(self):
        self.assertTrue(all(not group.isEnabled() for group in self.window.groups.values()))
        self.assertFalse(self.window.restore.isEnabled())
        self.assertFalse(self.window.relay.web_ui)
        self.assertFalse(self.window.key.text() == "")

    def test_usb_source_revokes_wifi_key_and_preserves_manual_controls(self):
        self.connect_camera()
        old_key = self.window.relay.token
        with patch.object(self.window.usb_bridge, "scan"):
            self.window.source.setCurrentIndex(self.window.source.findData("usb"))
        self.assertNotEqual(self.window.relay.token, old_key)
        self.assertFalse(self.window.relay.accept_phone)
        self.assertEqual(self.post("/frame", b"\xff\xd8test\xff\xd9", "image/jpeg")[0], 409)
        self.window.relay.exchange_camera(self.report)
        self.window.refresh()
        self.assertTrue(self.window.groups["exposure"].isEnabled())
        self.window.groups["exposure"].auto.setChecked(False)
        self.window.groups["exposure"].parameters["iso"].spin.setValue(400)
        self.window.groups["exposure"].submit()
        self.assertEqual(self.window.relay.settings["iso"], 400)

    def test_usb_setup_only_appears_for_unavailable_windows_service(self):
        with patch.object(self.window.usb_bridge, "scan"):
            self.window.source.setCurrentIndex(self.window.source.findData("usb"))
        with patch("app.sys.platform", "win32"):
            self.window.usb_service_checked(False)
            self.assertFalse(self.window.usb_setup.isHidden())
            self.assertFalse(self.window.connect_source.isEnabled())
            self.window.usb_service_checked(True)
            self.window.usb_devices_ready([])
            self.assertTrue(self.window.usb_setup.isHidden())
            self.assertIn("No USB device", self.window.source_info.text())
            self.window.usb_service_checked(False)
            self.window.usb_setup.wifi_button.click()
            self.assertEqual(self.window.source.currentData(), "wifi")
            self.assertTrue(self.window.usb_setup.isHidden())
            self.window.usb_service_checked(False)
            self.assertTrue(self.window.usb_setup.isHidden())

    def test_usb_setup_download_and_retry_actions(self):
        with patch("usb_setup.QDesktopServices.openUrl", return_value=True) as open_url:
            self.window.usb_setup.download.click()
            self.assertEqual(open_url.call_args.args[0].toString(), APPLE_DEVICES_URL)
        with patch.object(self.window.usb_bridge, "scan") as scan:
            self.window.source.setCurrentIndex(self.window.source.findData("usb"))
            scan.reset_mock()
            self.window.usb_setup.retry_button.click()
            scan.assert_called_once()

    def test_native_controls_use_phone_protocol(self):
        self.connect_camera()
        exposure = self.window.groups["exposure"]
        self.assertTrue(exposure.isEnabled())
        exposure.auto.setChecked(False)
        exposure.parameters["iso"].spin.setValue(400)
        exposure.parameters["shutterMs"].spin.setValue(8.33)
        exposure.submit()
        code, data = self.post("/camera", self.report)
        self.assertEqual(code, 200)
        command = json.loads(data)
        self.assertEqual(command["settings"], {"exposureAuto": False, "iso": 400, "shutterMs": 8.33})
        self.assertIn("acknowledgement", self.window.control_status.text())
        self.report["current"].update(command["settings"])
        self.report["appliedRevision"] = command["revision"]
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertIn("400", exposure.reading.text())
        self.assertNotIn("Waiting", self.window.control_status.text())

    def test_editor_preserves_unsent_values_and_reports_hardware_state(self):
        self.connect_camera()
        exposure = self.window.groups["exposure"]
        exposure.parameters["iso"].spin.setValue(500)
        self.report["current"]["iso"] = 250
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertEqual(exposure.parameters["iso"].spin.value(), 500)
        self.assertIn("250", exposure.reading.text())

    def test_unsupported_and_stale_camera_controls_are_disabled(self):
        self.report["capabilities"].update(manualFocus=False, autoFocus=False)
        self.connect_camera()
        self.assertFalse(self.window.groups["focus"].isEnabled())
        self.window.relay.last_camera = time.monotonic() - 5
        self.window.refresh()
        self.assertTrue(all(not group.isEnabled() for group in self.window.groups.values()))

    def test_frame_decode_and_offline_preview_clearing(self):
        image = QImage(64, 48, QImage.Format_RGB32)
        image.fill(QColor("#345678"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        self.assertTrue(image.save(buffer, "JPEG"))
        self.assertEqual(self.post("/frame", bytes(data), "image/jpeg")[0], 204)
        self.window.refresh()
        self.assertEqual(self.window.preview.image.size(), image.size())
        self.window.relay.last_frame = time.monotonic() - 5
        self.window.refresh()
        self.assertTrue(self.window.preview.image.isNull())

    def test_restore_auto_and_new_capture_session(self):
        self.connect_camera()
        self.window.restore_auto()
        self.assertEqual(self.window.relay.settings, {"exposureAuto": True, "whiteBalanceAuto": True, "focusAuto": True})
        self.assertTrue(self.window.groups["exposure"].auto.isChecked())
        self.report["session"] = "new-phone-session"
        self.report["current"]["iso"] = 640
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertEqual(self.window.relay.settings, {})
        self.assertEqual(self.window.groups["exposure"].parameters["iso"].spin.value(), 640)

    def test_stop_revokes_key_and_clears_preview(self):
        self.connect_camera()
        self.window.stop_receiver()
        self.assertIsNone(self.window.relay)
        self.assertEqual(self.window.key.text(), "")
        self.assertTrue(all(not group.isEnabled() for group in self.window.groups.values()))
        self.assertTrue(self.window.preview.image.isNull())

    def test_snapshots_cannot_modify_receiver_state(self):
        self.connect_camera()
        snapshot = self.window.relay.snapshot()
        snapshot["camera"]["current"]["iso"] = 999
        self.assertEqual(self.window.relay.camera["current"]["iso"], 200)

    def test_numeric_fields_have_readable_layout(self):
        self.connect_camera()
        self.window.show()
        APP.processEvents()
        for group in self.window.groups.values():
            for parameter in group.parameters.values():
                self.assertGreater(parameter.spin.lineEdit().width(), 50)

    def test_resolution_selection_and_range_refresh(self):
        self.connect_camera()
        self.assertEqual(self.window.resolution.count(), 4)
        self.window.resolution.setCurrentIndex(self.window.resolution.findData("1920x1080"))
        self.window.change_resolution()
        self.assertEqual(self.window.relay.settings, {"resolution": "1920x1080"})
        self.assertFalse(self.window.apply_resolution.isEnabled())
        self.assertFalse(self.window.groups["exposure"].isEnabled())
        self.report["current"].update(resolution="1920x1080", exposureAuto=True, iso=100)
        self.report["capabilities"]["iso"] = {"min": 50, "max": 800}
        self.report["appliedRevision"] = self.window.relay.revision
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertTrue(self.window.apply_resolution.isEnabled())
        self.assertEqual(self.window.format_id, "1920x1080")
        self.assertEqual(self.window.groups["exposure"].parameters["iso"].spin.maximum(), 800)
        self.assertIn("1080p", self.window.capture_label.text())

    def test_resolutions_follow_connected_device(self):
        self.report["capabilities"]["resolutions"] = self.report["capabilities"]["resolutions"][:2]
        self.connect_camera()
        self.assertEqual(self.window.resolution.count(), 2)
        self.assertEqual(self.window.resolution.findData("3840x2160"), -1)
        self.window.relay.last_camera = time.monotonic() - 5
        self.window.refresh()
        self.assertFalse(self.window.apply_resolution.isEnabled())

    def test_legacy_phone_shows_update_hint(self):
        del self.report["capabilities"]["resolutions"]
        del self.report["current"]["resolution"]
        self.connect_camera()
        self.assertFalse(self.window.resolution.isEnabled())
        self.assertIn("Update", self.window.resolution.currentText())


if __name__ == "__main__":
    unittest.main()
