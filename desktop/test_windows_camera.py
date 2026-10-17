"""Windows routing and worker tests; never elevate, register COM, or access a camera."""
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from virtual_camera import CameraController, NativeFrameWriter, VirtualCamera, controller_path
from native.windows.prepare_source import CLSID, replace_once, transform


class WindowsCameraTests(unittest.TestCase):
    def windows(self, build=22631):
        return patch.multiple(sys, platform="win32", getwindowsversion=lambda: SimpleNamespace(build=build), create=True)

    def test_windows_10_does_not_load_windows_11_api(self):
        with self.windows(19045), patch("virtual_camera.Path.is_file") as exists:
            self.assertIsNone(controller_path())
            exists.assert_not_called()

    def test_windows_source_uses_local_native_build(self):
        with self.windows(), patch.object(sys, "frozen", False, create=True), \
             patch("virtual_camera.struct.calcsize", return_value=8), patch("virtual_camera.Path.is_file", return_value=True):
            path = controller_path()
        self.assertEqual(path.name, "NoSubCamera.dll")
        self.assertIn("native-camera-windows", str(path))

    def test_windows_frozen_uses_packaged_native_component(self):
        with self.windows(), patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", "/test/internal", create=True), \
             patch("virtual_camera.struct.calcsize", return_value=8), patch("virtual_camera.Path.is_file", return_value=True):
            self.assertEqual(controller_path(), Path("/test/internal/native-camera/NoSubCamera.dll"))

    def test_32_bit_process_cannot_load_x64_camera(self):
        with self.windows(), patch("virtual_camera.struct.calcsize", return_value=4):
            self.assertIsNone(controller_path())

    def test_uninstall_requires_explicit_call_not_discovery(self):
        controller = CameraController()
        library = MagicMock()
        library.nosub_camera_available.return_value = 1
        with patch.object(controller, "load", return_value=library), patch("virtual_camera.controller_path", return_value="bridge"):
            self.assertTrue(controller.available())
            library.nosub_camera_request.assert_not_called()
            controller.uninstall()
            library.nosub_camera_request.assert_called_once_with(0, controller.callback)

    def test_windows_start_and_stop_share_worker_thread(self):
        output = VirtualCamera()
        events = []
        writer = MagicMock()
        def create(controller):
            events.append(("start", threading.get_ident()))
            output.stop_event.set()
            return writer
        writer.close.side_effect = lambda: events.append(("stop", threading.get_ident()))
        with patch("virtual_camera.NativeFrameWriter", side_effect=create):
            thread = threading.Thread(target=output._run, args=(None, None))
            thread.start(); thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual([event[0] for event in events], ["start", "stop"])
        self.assertEqual(events[0][1], events[1][1])
        self.assertNotEqual(events[0][1], threading.get_ident())

    def test_windows_start_failure_is_reported_without_closing_a_nonexistent_writer(self):
        output = VirtualCamera()
        with patch("virtual_camera.NativeFrameWriter", side_effect=RuntimeError("camera access denied")):
            output._run(None, None)
        self.assertEqual(output.error, "camera access denied")

    def test_windows_privacy_error_is_actionable(self):
        controller = MagicMock()
        controller.load.return_value.nosub_camera_output_start.return_value = -2147024891
        with self.assertRaisesRegex(RuntimeError, "Allow desktop apps"):
            NativeFrameWriter(controller)

    def test_pinned_transform_fails_instead_of_silently_patching_unexpected_source(self):
        with self.assertRaises(ValueError):
            replace_once("unexpected", "expected block", "replacement")
        with self.assertRaises(ValueError):
            replace_once("twice twice", "twice", "replacement")

    def test_no_microsoft_sample_clsid_collision(self):
        result = transform("VirtualCameraMediaSourceActivate.h", 'uuid("7B89B92E-FE71-42D0-8A41-E137D06EA184")')
        self.assertIn(CLSID, result)
        self.assertNotIn("7B89B92E", result)


if __name__ == "__main__":
    unittest.main()
