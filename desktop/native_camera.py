"""Optional macOS camera input, including Apple Continuity Camera devices."""
import sys
import time

from PySide6.QtCore import (QObject, Signal, QByteArray, QBuffer, QIODevice,
                            QCameraPermission, QCoreApplication, Qt)


class NativeCameraSource(QObject):
    frame = Signal(bytes)
    message = Signal(str)
    devices_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        if sys.platform != "darwin":
            raise RuntimeError("Continuity Camera is available on macOS only.")
        # Imported only when selected. Windows builds need no multimedia backend.
        from PySide6.QtMultimedia import QMediaDevices, QMediaCaptureSession, QVideoSink
        self.media_devices = QMediaDevices(self)
        self.media_devices.videoInputsChanged.connect(self.devices_changed)
        self.capture = QMediaCaptureSession(self)
        self.sink = QVideoSink(self)
        self.capture.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self.receive_frame)
        self.camera = None
        self.generation = 0
        self.last_frame = 0.0

    def devices(self):
        return [(bytes(device.id()), device.description())
                for device in self.media_devices.videoInputs()]

    def start(self, device_id):
        self.stop()
        generation = self.generation
        app = QCoreApplication.instance()
        permission = QCameraPermission()

        def permitted(result):
            if generation != self.generation:
                return
            if result.status() != Qt.PermissionStatus.Granted:
                self.message.emit("Allow camera access in macOS System Settings > Privacy & Security.")
                return
            self.open_camera(device_id)

        status = app.checkPermission(permission)
        if status == Qt.PermissionStatus.Undetermined:
            self.message.emit("Waiting for macOS camera permission...")
            app.requestPermission(permission, self, permitted)
        elif status == Qt.PermissionStatus.Granted:
            self.open_camera(device_id)
        else:
            self.message.emit("Camera permission denied. Enable it in macOS System Settings.")

    def open_camera(self, device_id):
        from PySide6.QtMultimedia import QCamera
        device = next((item for item in self.media_devices.videoInputs()
                       if bytes(item.id()) == device_id), None)
        if device is None:
            self.message.emit("Camera disconnected. Refresh cameras and select your iPhone again.")
            return
        self.camera = QCamera(device, self)
        self.camera.errorOccurred.connect(lambda error, description: self.message.emit(description))
        self.capture.setCamera(self.camera)
        self.last_frame = 0.0
        self.camera.start()
        self.message.emit("Opening " + device.description() + "...")

    def stop(self):
        self.generation += 1
        if self.camera is not None:
            self.camera.stop()
            self.capture.setCamera(None)
            self.camera.deleteLater()
            self.camera = None

    def receive_frame(self, frame):
        now = time.monotonic()
        if self.camera is None or not self.camera.isActive() or now - self.last_frame < 1 / 24:
            return
        image = frame.toImage()
        if image.isNull():
            return
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if image.save(buffer, "JPEG", 75) and len(data) <= 8_000_000:
            self.last_frame = now
            self.frame.emit(bytes(data))
