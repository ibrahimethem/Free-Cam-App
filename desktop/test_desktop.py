"""Native widget + embedded receiver tests. Run with QT_QPA_PLATFORM=offscreen."""
import copy
import http.client
import json
import os
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSettings
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication, QMessageBox

from app import (MainWindow, PRIVACY_URL, demo_report, external_link, lan_addresses,
                 pairing_payload, qr_pixmap)
from theme import STYLE
from usb_setup import APPLE_DEVICES_URL
from pairing import PairingIdentity, SessionCredentials

APP = QApplication.instance() or QApplication([])
APP.setStyle("Fusion")
APP.setStyleSheet(STYLE)


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.settings_directory = tempfile.TemporaryDirectory()
        self.preferences = QSettings(self.settings_directory.name + "/settings.ini", QSettings.IniFormat)
        self.window = MainWindow("127.0.0.1", 0, preferences=self.preferences,
                                 pairing=PairingIdentity(SessionCredentials()))
        self.report = demo_report()

    def tearDown(self):
        self.window.close()
        self.settings_directory.cleanup()

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

    def test_external_legal_link_opens_expected_url(self):
        with patch("app.QDesktopServices.openUrl", return_value=True) as open_url:
            external_link("Privacy", PRIVACY_URL).click()
        self.assertEqual(open_url.call_args.args[0].toString(), PRIVACY_URL)

    def test_pairing_qr_payload_and_rendering(self):
        payload = pairing_payload("wifi", "http://192.168.1.20:8765", "temporary key")
        parsed = urlsplit(payload)
        self.assertEqual((parsed.scheme, parsed.netloc), ("nosubcam", "pair"))
        self.assertEqual(parse_qs(parsed.query), {
            "mode": ["wifi"], "address": ["http://192.168.1.20:8765"],
            "key": ["temporary key"]})
        image = qr_pixmap(payload, 200)
        self.assertFalse(image.isNull())
        self.assertEqual((image.width(), image.height()), (200, 200))

    def test_lan_address_uses_active_route_when_hostname_is_loopback(self):
        route = MagicMock()
        route.__enter__.return_value = route
        route.getsockname.return_value = ("192.168.0.18", 49152)
        with patch("app.socket.gethostbyname_ex", return_value=("mac", [], ["127.0.0.1"])), \
             patch("app.socket.socket", return_value=route):
            self.assertEqual(lan_addresses(), ["192.168.0.18"])
        route.connect.assert_called_once_with(("192.0.2.1", 80))

    def connect_camera(self):
        self.assertEqual(self.post("/camera", self.report)[0], 200)
        self.window.refresh()

    def test_disconnected_state_disables_controls(self):
        self.assertTrue(all(not group.isEnabled() for group in self.window.groups.values()))
        self.assertFalse(self.window.restore.isEnabled())
        self.assertFalse(self.window.relay.web_ui)
        self.assertFalse(self.window.key.text() == "")

    def test_background_close_keeps_live_receiver_and_native_output_running(self):
        old_quit_policy = APP.quitOnLastWindowClosed()
        original_background = self.window.background
        self.window.background = MagicMock(available=True)
        writer = MagicMock()
        old_key = self.window.relay.token
        try:
            with patch("virtual_camera.controller_path", return_value="native-library"), \
                 patch("virtual_camera.NativeFrameWriter", return_value=writer):
                self.window.virtual_camera.start(self.window.relay, self.window.camera_controller)
            self.window.show()
            self.window.close()
            self.assertFalse(self.window.isVisible())
            self.assertTrue(self.window.virtual_camera.running)
            self.assertEqual(self.window.relay.token, old_key)
            image = QImage(64, 48, QImage.Format.Format_RGB32)
            image.fill(QColor("red"))
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, "JPEG")
            self.assertEqual(self.post("/frame", bytes(data), "image/jpeg")[0], 204)
            deadline = time.monotonic() + 1
            while not writer.write.called and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(writer.write.called)
            self.window.restore_window()
            self.assertTrue(self.window.isVisible())
        finally:
            self.window.shutdown()
            self.window.background = original_background
            original_background.close()
            APP.setQuitOnLastWindowClosed(old_quit_policy)

    def test_usb_source_reuses_pairing_but_disables_wifi_ingest(self):
        self.connect_camera()
        old_key = self.window.relay.token
        with patch.object(self.window.usb_bridge, "scan"):
            self.window.source.setCurrentIndex(self.window.source.findData("usb"))
        self.assertEqual(self.window.relay.token, old_key)
        self.assertFalse(self.window.relay.accept_phone)
        self.assertEqual(self.post("/frame", b"\xff\xd8test\xff\xd9", "image/jpeg")[0], 409)
        self.window.relay.exchange_camera(self.report)
        self.window.refresh()
        self.assertTrue(self.window.groups["exposure"].isEnabled())
        self.window.groups["exposure"].auto.setChecked(False)
        self.window.groups["exposure"].parameters["iso"].spin.setValue(400)
        self.window.groups["exposure"].submit()
        self.assertEqual(self.window.relay.settings["iso"], 400)

    def test_virtual_camera_toggles_do_not_restart_or_block_wifi_receiver(self):
        image = QImage(16, 9, QImage.Format_RGB32)
        image.fill(QColor("red"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "JPEG")
        relay, key = self.window.relay, self.window.relay.token
        writer = MagicMock()
        with patch("virtual_camera.controller_path", return_value="native-library"), \
             patch("virtual_camera.NativeFrameWriter", return_value=writer):
            for cycle in range(3):
                self.window.toggle_camera_output()
                self.assertTrue(self.window.virtual_camera.running)
                self.assertEqual(self.post("/frame", bytes(data), "image/jpeg")[0], 204)
                self.window.toggle_camera_output()
                self.assertFalse(self.window.virtual_camera.running)
                self.assertEqual(self.post("/frame", bytes(data), "image/jpeg")[0], 204)
                self.assertIs(self.window.relay, relay)
                self.assertEqual(relay.token, key)
                self.assertTrue(relay.accept_phone)
        self.assertEqual(relay.sequence, 6)
        self.assertEqual(writer.close.call_count, 3)

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

    def test_receiver_restart_remembers_pairing_and_revokes_old_server(self):
        old_server = self.window.relay
        token = old_server.token
        self.window.stop_receiver()
        self.assertNotEqual(old_server.token, token)
        self.window.start_receiver()
        self.assertEqual(self.window.relay.token, token)

    def test_reset_pairing_revokes_old_key_and_keeps_new_key(self):
        token = self.window.relay.token
        with patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window.reset_pairing()
        self.assertNotEqual(self.window.relay.token, token)
        saved = self.window.relay.token
        self.window.stop_receiver()
        self.window.start_receiver()
        self.assertEqual(self.window.relay.token, saved)

    def test_cancel_reset_keeps_pairing_and_receiver(self):
        server = self.window.relay
        token = server.token
        with patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            self.window.reset_pairing()
        self.assertIs(self.window.relay, server)
        self.assertEqual(server.token, token)

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
        self.window.resolution.activated.emit(self.window.resolution.currentIndex())
        self.assertEqual(self.window.relay.settings, {"resolution": "1920x1080"})
        self.assertFalse(self.window.resolution.isEnabled())
        self.assertFalse(self.window.groups["exposure"].isEnabled())
        self.report["current"].update(resolution="1920x1080", exposureAuto=True, iso=100)
        self.report["capabilities"]["iso"] = {"min": 50, "max": 800}
        self.report["appliedRevision"] = self.window.relay.revision
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertTrue(self.window.resolution.isEnabled())
        self.assertEqual(self.window.format_id, "1920x1080")
        self.assertEqual(self.window.groups["exposure"].parameters["iso"].spin.maximum(), 800)
        self.assertIn("1080p", self.window.capture_label.text())

    def test_frame_rate_selection_follows_connected_camera(self):
        self.connect_camera()
        self.assertEqual(self.window.frame_rate.count(), 3)
        self.assertEqual(self.window.frame_rate.currentData(), 30)
        self.window.frame_rate.setCurrentIndex(self.window.frame_rate.findData(60))
        self.window.frame_rate.activated.emit(self.window.frame_rate.currentIndex())
        self.assertEqual(self.window.relay.settings, {"frameRate": 60})
        self.assertFalse(self.window.frame_rate.isEnabled())

        self.report["current"]["frameRate"] = 60
        self.report["appliedRevision"] = self.window.relay.revision
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertEqual(self.window.frame_rate_id, 60)
        self.assertIn("60 FPS", self.window.capture_label.text())

        self.report["capabilities"]["frameRates"] = [24, 30]
        self.report["current"]["frameRate"] = 30
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertEqual(self.window.frame_rate.findData(60), -1)

    def test_camera_position_and_output_orientation_are_desktop_controls(self):
        self.connect_camera()
        self.assertEqual(self.window.camera_position.currentData(), "rear")
        self.assertEqual(self.window.output_orientation.currentData(), "landscape")

        index = self.window.camera_position.findData("front")
        self.window.camera_position.setCurrentIndex(index)
        self.window.camera_position.activated.emit(index)
        self.assertEqual(self.window.relay.settings, {"cameraPosition": "front"})
        self.report["current"].update(cameraPosition="front", resolution="1280x720")
        self.report["appliedRevision"] = self.window.relay.revision
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertEqual(self.window.camera_position_id, "front")

        index = self.window.output_orientation.findData("portrait")
        self.window.output_orientation.setCurrentIndex(index)
        self.window.output_orientation.activated.emit(index)
        self.assertEqual(self.window.relay.settings["orientation"], "portrait")
        self.report["current"]["orientation"] = "portrait"
        self.report["appliedRevision"] = self.window.relay.revision
        self.post("/camera", self.report)
        self.window.refresh()
        self.assertIn("portrait", self.window.capture_label.text())

    def test_detail_settings_are_cached_and_named_presets_can_be_applied(self):
        self.connect_camera()
        exposure = self.window.groups["exposure"]
        exposure.auto.setChecked(False)
        exposure.parameters["iso"].spin.setValue(400)
        exposure.parameters["shutterMs"].spin.setValue(8.33)
        exposure.submit()

        cached = json.loads(self.preferences.value("lastSensorSettings"))
        self.assertFalse(cached["exposureAuto"])
        self.assertEqual(cached["iso"], 400)
        self.assertTrue(self.window.save_preset_named("Desk shot"))
        self.assertIn("Desk shot", json.loads(self.preferences.value("sensorPresets")))

        command = self.window.relay.settings.copy()
        self.report["current"].update(command)
        self.report["appliedRevision"] = self.window.relay.revision
        self.post("/camera", self.report)
        self.window.refresh()

        exposure.parameters["iso"].spin.setValue(200)
        self.window.preset.setCurrentIndex(self.window.preset.findData("Desk shot"))
        self.window.apply_selected_preset()
        self.assertEqual(exposure.parameters["iso"].spin.value(), 400)
        self.assertEqual(self.window.relay.settings["iso"], 400)
        self.assertEqual(self.preferences.value("lastPreset"), "Desk shot")

        self.window.delete_selected_preset()
        self.assertNotIn("Desk shot", json.loads(self.preferences.value("sensorPresets")))

    def test_resolutions_follow_connected_device(self):
        self.report["capabilities"]["resolutions"] = self.report["capabilities"]["resolutions"][:2]
        self.connect_camera()
        self.assertEqual(self.window.resolution.count(), 2)
        self.assertEqual(self.window.resolution.findData("3840x2160"), -1)
        self.window.relay.last_camera = time.monotonic() - 5
        self.window.refresh()
        self.assertFalse(self.window.resolution.isEnabled())

    def test_legacy_phone_shows_update_hint(self):
        del self.report["capabilities"]["resolutions"]
        del self.report["current"]["resolution"]
        del self.report["capabilities"]["cameraPositions"]
        del self.report["capabilities"]["orientations"]
        del self.report["current"]["cameraPosition"]
        del self.report["current"]["orientation"]
        del self.report["capabilities"]["frameRates"]
        del self.report["current"]["frameRate"]
        self.connect_camera()
        self.assertFalse(self.window.resolution.isEnabled())
        self.assertIn("Update", self.window.resolution.currentText())
        self.assertFalse(self.window.camera_position.isEnabled())
        self.assertIn("Update", self.window.camera_position.currentText())
        self.assertFalse(self.window.frame_rate.isEnabled())
        self.assertIn("Update", self.window.frame_rate.currentText())


if __name__ == "__main__":
    unittest.main()
