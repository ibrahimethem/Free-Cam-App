"""Camera conversion/bridge tests: no hardware, disk frames or OS installation."""
import ctypes
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage
from virtual_camera import NativeFrameWriter, FRAME_SIZE, HEIGHT, VirtualCamera, WIDTH, output_image


def jpeg(width, height):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG")
    return bytes(data)


class CameraTests(unittest.TestCase):
    def writer(self):
        controller = MagicMock()
        library = controller.load.return_value
        library.nosub_camera_output_start.return_value = 1
        library.nosub_camera_output_send.return_value = 1
        return NativeFrameWriter(controller), library

    def test_portrait_is_letterboxed_not_cropped(self):
        image = output_image(jpeg(90, 160))
        self.assertEqual((image.width(), image.height()), (WIDTH, HEIGHT))
        self.assertEqual(image.pixelColor(0, HEIGHT // 2), QColor("black"))
        self.assertGreater(image.pixelColor(WIDTH // 2, 0).red(), 240)
        self.assertGreater(image.pixelColor(WIDTH // 2, HEIGHT - 1).red(), 240)

    def test_invalid_jpeg_is_ignored(self):
        self.assertIsNone(output_image(b"not a JPEG"))

    def test_native_writer_passes_bgra_without_an_extra_python_copy(self):
        writer, library = self.writer()
        image = output_image(jpeg(160, 90))
        def send(pointer, length):
            self.assertEqual(length, FRAME_SIZE)
            self.assertGreater(ctypes.string_at(pointer, 4)[2], 240)
            return 1
        library.nosub_camera_output_send.side_effect = send
        writer.write(image.bits())
        library.nosub_camera_output_send.assert_called_once()

    def test_bad_frame_size_is_rejected(self):
        writer, library = self.writer()
        with self.assertRaises(ValueError):
            writer.write(bytearray(4))
        library.nosub_camera_output_send.assert_not_called()

    def test_missing_camera_is_explicit(self):
        controller = MagicMock()
        controller.load.return_value.nosub_camera_output_start.return_value = 0
        with self.assertRaisesRegex(RuntimeError, "Install/approve"):
            NativeFrameWriter(controller)

    def test_full_queue_drops_instead_of_failing(self):
        writer, library = self.writer()
        library.nosub_camera_output_send.return_value = 0
        image = output_image(jpeg(160, 90))
        writer.write(image.bits())

    def test_native_stream_error_is_visible(self):
        writer, library = self.writer()
        library.nosub_camera_output_send.return_value = -1
        image = output_image(jpeg(160, 90))
        with self.assertRaisesRegex(RuntimeError, "input stopped"):
            writer.write(image.bits())

    def test_clear_sends_black_and_close_stops_native_stream(self):
        writer, library = self.writer()
        writer.clear()
        library.nosub_camera_output_send.assert_called_once_with(None, 0)
        writer.close()
        library.nosub_camera_output_stop.assert_called_once()

    def test_worker_clears_stale_frame_and_stops(self):
        class Relay:
            changed = threading.Condition()
            sequence = 1
            frame = jpeg(160, 90)
            last_frame = time.monotonic()
        written, cleared = threading.Event(), threading.Event()
        writer = MagicMock()
        writer.write.side_effect = lambda pixels: written.set()
        writer.clear.side_effect = cleared.set
        output = VirtualCamera()
        output.thread = threading.Thread(target=output._run, args=(Relay, writer))
        output.thread.start()
        try:
            self.assertTrue(written.wait(2))
            with Relay.changed:
                Relay.last_frame = 0
            self.assertTrue(cleared.wait(2))
        finally:
            output.stop()
        self.assertFalse(output.running)
        self.assertEqual(output.error, "")
        writer.close.assert_called_once()

    def test_unbundled_camera_fails_explicitly(self):
        with patch("virtual_camera.controller_path", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "signed macOS"):
                VirtualCamera().start(None)


if __name__ == "__main__":
    unittest.main()
