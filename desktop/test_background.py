"""Lifecycle tests without registering real tray icons or opening network sockets."""
import os
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from app import MainWindow, run_window
from virtual_camera import CameraController

APP = QApplication.instance() or QApplication([])


class Tray(QObject):
    activated = Signal(object)
    ActivationReason = QSystemTrayIcon.ActivationReason
    present = True

    def __init__(self, icon, parent):
        super().__init__(parent)
        self.visible = False
        self.tooltip = ""

    @staticmethod
    def isSystemTrayAvailable():
        return Tray.present

    def setContextMenu(self, menu):
        self.menu = menu

    def setToolTip(self, text):
        self.tooltip = text

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def isVisible(self):
        return self.visible


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.old_quit_policy = APP.quitOnLastWindowClosed()
        Tray.present = True
        self.tray_patch = patch("background.QSystemTrayIcon", Tray)
        self.tray_patch.start()
        with patch.object(MainWindow, "start_receiver"):
            self.window = MainWindow(background=True)

    def tearDown(self):
        self.window.camera_install_pending = False
        self.window.shutdown()
        self.window.close()
        APP.setQuitOnLastWindowClosed(self.old_quit_policy)
        self.tray_patch.stop()

    def test_close_hides_without_stopping_receiver_or_output(self):
        self.window.show()
        self.window.virtual_camera = MagicMock(running=True)
        with patch.object(self.window, "stop_receiver") as stop:
            self.window.close()
            self.assertFalse(self.window.isVisible())
            self.assertTrue(self.window.background_hidden)
            self.assertTrue(self.window.timer.isActive())
            self.assertFalse(self.window.shutdown_complete)
            stop.assert_not_called()
            self.window.virtual_camera.stop.assert_not_called()

    def test_menu_restores_the_window(self):
        self.window.show()
        self.window.close()
        self.window.background.show_action.trigger()
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.background_hidden)

    def test_explicit_quit_cleans_up_once(self):
        with patch.object(APP, "quit") as quit_app, patch.object(self.window, "stop_receiver") as stop:
            self.window.background.quit_action.trigger()
            self.window.shutdown()
            stop.assert_called_once()
            quit_app.assert_called_once()
        self.assertFalse(self.window.timer.isActive())
        self.assertFalse(self.window.background.tray.isVisible())

    def test_missing_tray_closes_normally_instead_of_stranding_process(self):
        Tray.present = False
        event = QCloseEvent()
        self.window.closeEvent(event)
        self.assertTrue(event.isAccepted())
        self.assertTrue(self.window.shutdown_complete)
        self.assertTrue(APP.quitOnLastWindowClosed())

    def test_native_output_stop_failure_still_closes_wifi_receiver(self):
        relay = SimpleNamespace(changed=threading.Condition(), token="test", accept_phone=True,
                                frame=b"private-frame", shutdown=MagicMock(), server_close=MagicMock())
        self.window.relay = relay
        with patch.object(self.window.virtual_camera, "stop", side_effect=RuntimeError("Output still stopping")), \
             patch.object(self.window, "refresh"):
            self.window.stop_receiver()
        relay.shutdown.assert_called_once()
        relay.server_close.assert_called_once()
        self.assertIsNone(self.window.relay)
        self.assertIsNone(relay.frame)
        self.assertFalse(relay.accept_phone)

    def test_receiver_start_failure_does_not_leave_an_empty_second_host(self):
        window = MagicMock(relay=None)
        application = MagicMock()
        args = SimpleNamespace(host=None, port=8765, demo=False, screenshot=None)
        with patch("app.MainWindow", return_value=window):
            self.assertEqual(run_window(application, args), 1)
        window.shutdown.assert_called_once()
        window.close.assert_called_once()
        window.show.assert_not_called()
        application.exec.assert_not_called()

    def test_windows_tray_click_opens_window(self):
        self.window.close()
        with patch("background.sys.platform", "win32"):
            self.window.background.activated(QSystemTrayIcon.ActivationReason.Trigger)
        self.assertTrue(self.window.isVisible())

    def test_mac_menu_click_does_not_also_open_window(self):
        self.window.close()
        with patch("background.sys.platform", "darwin"):
            self.window.background.activated(QSystemTrayIcon.ActivationReason.Trigger)
        self.assertFalse(self.window.isVisible())

    def test_mac_dock_or_finder_reopen_restores_hidden_window_without_restart(self):
        self.window.show()
        self.window.close()
        with patch("app.sys.platform", "darwin"), patch.object(self.window, "start_receiver") as start, \
             patch.object(self.window.virtual_camera, "stop") as stop:
            self.window.application_activation(Qt.ApplicationState.ApplicationActive)
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.background_hidden)
        start.assert_not_called()
        stop.assert_not_called()

    def test_menu_status_contains_no_pairing_credentials(self):
        self.window.background.update_status(True, True, True)
        self.assertEqual(self.window.background.status_action.text(), "Streaming · native output on")

    def test_pending_install_can_hide_but_cannot_explicitly_quit(self):
        self.window.camera_install_pending = True
        self.window.show()
        self.window.close()
        self.assertFalse(self.window.isVisible())
        with patch.object(APP, "quit") as quit_app:
            self.window.request_quit()
            quit_app.assert_not_called()
        self.assertTrue(self.window.isVisible())

    def test_activity_changes_only_on_streaming_transitions(self):
        controller = CameraController()
        library = MagicMock()
        with patch("virtual_camera.controller_path", return_value="packaged"), patch.object(controller, "load", return_value=library):
            controller.set_streaming_activity(True)
            controller.set_streaming_activity(True)
            controller.set_streaming_activity(False)
        self.assertEqual([call.args for call in library.nosub_camera_activity.call_args_list], [(1,), (0,)])


if __name__ == "__main__":
    unittest.main()
