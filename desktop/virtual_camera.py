"""Opt-in native camera output. Frame conversion never runs on the GUI/relay thread."""
import ctypes
import struct
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QImage, QPainter

WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4


def controller_path():
    if sys.platform == "win32":
        if sys.getwindowsversion().build < 22000 or struct.calcsize("P") != 8:
            return None
        if getattr(sys, "frozen", False):
            path = Path(sys._MEIPASS) / "native-camera" / "NoSubCamera.dll"
        else:
            path = Path(__file__).resolve().parent.parent / "build/native-camera-windows/Release/NoSubCamera.dll"
    elif sys.platform == "darwin" and getattr(sys, "frozen", False):
        path = Path(sys.executable).parent.parent / "Frameworks" / "libNoSubCamera.dylib"
    else:
        return None
    return path if path.is_file() else None


class CameraController(QObject):
    message = Signal(int, str)
    CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_int32, ctypes.c_char_p)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.library = None
        self.activity_active = False
        self.callback = self.CALLBACK(lambda state, message:
                                      self.message.emit(state, (message or b"").decode(errors="replace")))

    def load(self):
        if self.library is None:
            path = controller_path()
            if path is None:
                raise RuntimeError("Native camera requires the signed macOS release package or a built Windows 11 camera component.")
            library = ctypes.CDLL(str(path))
            library.nosub_camera_request.argtypes = [ctypes.c_int32, self.CALLBACK]
            library.nosub_camera_request.restype = None
            library.nosub_camera_output_start.argtypes = []
            library.nosub_camera_output_start.restype = ctypes.c_int32
            library.nosub_camera_output_send.argtypes = [ctypes.c_void_p, ctypes.c_int32]
            library.nosub_camera_output_send.restype = ctypes.c_int32
            library.nosub_camera_output_stop.argtypes = []
            library.nosub_camera_output_stop.restype = None
            library.nosub_camera_activity.argtypes = [ctypes.c_int32]
            library.nosub_camera_activity.restype = None
            library.nosub_camera_available.argtypes = []
            library.nosub_camera_available.restype = ctypes.c_int32
            self.library = library
        return self.library

    def install(self):
        self.load().nosub_camera_request(1, self.callback)

    def uninstall(self):
        self.load().nosub_camera_request(0, self.callback)

    def available(self):
        """Discovery only: never starts capture or requests installation/permission."""
        return controller_path() is not None and self.load().nosub_camera_available() == 1

    def set_streaming_activity(self, active):
        if active == self.activity_active or controller_path() is None:
            return
        self.load().nosub_camera_activity(int(active))
        self.activity_active = active


class NativeFrameWriter:
    """Frames stay in CMIO/IOSurface or a local Windows pipe, never disk files."""
    def __init__(self, controller):
        self.library = controller.load()
        result = self.library.nosub_camera_output_start()
        if result != 1:
            reason = {-1001: "Camera not discovered", -1002: "Camera input stream not discovered",
                      -1003: "Camera input queue unavailable",
                      -2147024891: "Camera access denied. Allow desktop apps in Windows Settings > Privacy & security > Camera"}.get(
                          result, "Native camera input could not start")
            raise RuntimeError(f"{reason} ({result}). Install/approve the camera, then retry.")

    def write(self, pixels):
        if len(pixels) != FRAME_SIZE:
            raise ValueError("Expected a 1920 × 1080 BGRA frame")
        pointer = (ctypes.c_ubyte * len(pixels)).from_buffer(pixels)
        if self.library.nosub_camera_output_send(pointer, len(pixels)) < 0:
            raise RuntimeError("Native camera input stopped. Disable and re-enable output.")

    def clear(self):
        self.library.nosub_camera_output_send(None, 0)

    def close(self):
        self.library.nosub_camera_output_stop()


def output_image(jpeg):
    image = QImage.fromData(jpeg)
    if image.isNull():
        return None
    output = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32)
    output.fill(QColor("black"))
    scaled = image.scaled(WIDTH, HEIGHT, Qt.KeepAspectRatio, Qt.FastTransformation)
    painter = QPainter(output)
    painter.drawImage((WIDTH - scaled.width()) // 2, (HEIGHT - scaled.height()) // 2, scaled)
    painter.end()
    # ARGB32 is native-endian BGRA on the supported little-endian desktop CPUs.
    return output


class VirtualCamera:
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.error = ""

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, relay, controller=None):
        self.stop()
        if controller_path() is None:
            raise RuntimeError("Native camera requires the signed macOS release package or a built Windows 11 camera component.")
        # Windows MF/COM must start and stop on the same MTA worker, never on
        # the UI thread. A startup failure is surfaced via the existing error UI.
        if sys.platform == "win32":
            writer = None
        else:
            writer = NativeFrameWriter(controller or CameraController())
        self.error = ""
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(relay, writer, controller),
                                       name="NoSub camera output", daemon=True)
        self.thread.start()

    def _run(self, relay, writer, controller=None):
        sequence = -1
        blank = False
        next_frame = time.monotonic()
        try:
            if writer is None:
                writer = NativeFrameWriter(controller or CameraController())
            while not self.stop_event.wait(max(0, next_frame - time.monotonic())):
                # Budget conversion inside the frame interval, not after it.
                next_frame = max(next_frame + 1 / 30, time.monotonic())
                with relay.changed:
                    current, frame, age = relay.sequence, relay.frame, time.monotonic() - relay.last_frame
                if frame is None or age >= 1:
                    if not blank:
                        writer.clear()
                        blank = True
                    continue
                if current == sequence:
                    continue
                sequence = current
                image = output_image(frame)
                if image is not None:
                    writer.write(image.bits())
                    blank = False
        except Exception as error:
            self.error = str(error)
        finally:
            if writer is not None:
                writer.close()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Camera output is still stopping")
            self.thread = None
