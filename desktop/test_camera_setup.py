"""Camera setup UI states without hardware, installation or network access."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QSplitter
from app import MainWindow
from virtual_camera import CameraController

APP = QApplication.instance() or QApplication([])


class CameraSetupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        preferences = QSettings(self.directory.name + "/settings.ini", QSettings.IniFormat)
        with patch.object(MainWindow, "start_receiver"), patch("app.controller_path", return_value=None):
            self.window = MainWindow(preferences=preferences, background=False)

    def tearDown(self):
        self.window.camera_install_pending = False
        self.window.close()
        self.directory.cleanup()

    def test_output_controls_belong_to_right_panel_not_preview(self):
        splitter = self.window.centralWidget().findChild(QSplitter)
        for control in (self.window.camera_output, self.window.camera_install, self.window.copy_obs):
            self.assertTrue(splitter.widget(2).isAncestorOf(control))
            self.assertFalse(splitter.widget(1).isAncestorOf(control))

    def test_discovered_camera_hides_install_and_enables_output(self):
        with patch("app.controller_path", return_value="bridge"), \
             patch.object(CameraController, "available", return_value=True):
            self.window.refresh_camera_installation()
        self.assertTrue(self.window.camera_install.isHidden())
        self.assertTrue(self.window.camera_output.isEnabled())
        self.assertIn("installed and ready", self.window.camera_status.text())

    def test_missing_camera_shows_install_without_enabling_output(self):
        with patch("app.controller_path", return_value="bridge"), \
             patch.object(CameraController, "available", return_value=False):
            self.window.refresh_camera_installation()
        self.assertFalse(self.window.camera_install.isHidden())
        self.assertFalse(self.window.camera_output.isEnabled())

    def test_approval_pending_then_discovered_without_reinstall(self):
        self.window.camera_install_pending = True
        with patch("app.controller_path", return_value="bridge"), \
             patch.object(CameraController, "available", return_value=False):
            self.window.camera_install_message(0, "Approve in System Settings.")
        self.assertFalse(self.window.camera_settings.isHidden())
        self.assertIn("setup" if sys.platform == "win32" else "approval", self.window.camera_status.text())
        with patch("app.controller_path", return_value="bridge"), \
             patch.object(CameraController, "available", return_value=True):
            self.window.camera_install_message(1, "Installation completed.")
        self.assertFalse(self.window.camera_install_pending)
        self.assertTrue(self.window.camera_install.isHidden())
        self.assertEqual(self.window.camera_settings.isHidden(), sys.platform != "win32")

    def test_settings_button_only_opens_settings_not_an_activation_request(self):
        with patch("app.QDesktopServices.openUrl", return_value=True) as open_url, \
             patch.object(CameraController, "install") as install:
            self.window.open_camera_settings()
        self.assertIn("privacy-webcam" if sys.platform == "win32" else "LoginItems-Settings", open_url.call_args.args[0].toString())
        install.assert_not_called()

    def test_discovery_failure_does_not_leave_a_false_ready_state(self):
        with patch("app.controller_path", return_value="bridge"), \
             patch.object(CameraController, "available", side_effect=RuntimeError("bridge unavailable")):
            self.window.refresh_camera_installation()
        self.assertFalse(self.window.camera_install.isHidden())
        self.assertFalse(self.window.camera_output.isEnabled())
        self.assertIn("could not be checked", self.window.camera_status.text())

    def test_windows_uninstall_cancel_does_not_stop_output_or_request_uac(self):
        with patch("app.sys.platform", "win32"), \
             patch("app.QMessageBox.question", return_value=0), \
             patch.object(self.window.virtual_camera, "stop") as stop, \
             patch.object(self.window.camera_controller, "uninstall") as remove:
            self.window.uninstall_camera_extension()
        stop.assert_not_called()
        remove.assert_not_called()

    def test_windows_uninstall_disables_output_until_setup_finishes(self):
        from PySide6.QtWidgets import QMessageBox
        with patch("app.sys.platform", "win32"), \
             patch("app.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(self.window.virtual_camera, "stop") as stop, \
             patch.object(self.window.camera_controller, "uninstall") as remove:
            self.window.uninstall_camera_extension()
        stop.assert_called_once()
        remove.assert_called_once()
        self.assertTrue(self.window.camera_install_pending)
        self.assertFalse(self.window.camera_output.isEnabled())


if __name__ == "__main__":
    unittest.main()
