"""Optional macOS camera input, including Apple Continuity Camera devices."""
import os
import sys
import time

from PySide6.QtCore import (QObject, Signal, QByteArray, QBuffer, QIODevice,
                            QCameraPermission, QCoreApplication, Qt, QTimer)


class NativeCameraSource(QObject):
    frame = Signal(bytes)
    message = Signal(str)
    devices_changed = Signal()
    active_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        if sys.platform != "darwin":
            raise RuntimeError("Continuity Camera is available on macOS only.")
        # Select Apple's native camera backend before Qt Multimedia initializes.
        # Respect an explicit backend override used for diagnostics.
        os.environ.setdefault("QT_MEDIA_BACKEND", "darwin")
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
        self.received_frame = False
        self.conversion_error_reported = False
        self.startup_timer = QTimer(self)
        self.startup_timer.setSingleShot(True)
        self.startup_timer.setInterval(15000)
        self.startup_timer.timeout.connect(self.check_startup)

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
        self.camera.errorOccurred.connect(self.camera_error)
        self.camera.activeChanged.connect(self.camera_active_changed)
        # Use a conventional SDR format rather than leaving Continuity's
        # high-resolution/HDR default to the frame-to-image converter.
        from PySide6.QtMultimedia import QVideoFrameFormat
        pixel_formats = (QVideoFrameFormat.PixelFormat.Format_NV12,
                         QVideoFrameFormat.PixelFormat.Format_BGRA8888,
                         QVideoFrameFormat.PixelFormat.Format_YUYV)
        formats = [fmt for fmt in device.videoFormats()
                   if fmt.pixelFormat() in pixel_formats
                   and fmt.resolution().width() <= 1920
                   and fmt.resolution().height() <= 1080
                   and fmt.minFrameRate() <= 30 <= fmt.maxFrameRate()]
        if formats:
            selected = max(formats, key=lambda fmt:
                           fmt.resolution().width() * fmt.resolution().height())
            self.camera.setCameraFormat(selected)
        self.capture.setCamera(self.camera)
        self.last_frame = 0.0
        self.received_frame = False
        self.conversion_error_reported = False
        self.message.emit("Opening " + device.description() + "...")
        self.startup_timer.start()
        self.camera.start()

    def camera_active_changed(self, active):
        self.active_changed.emit(active)
        if active:
            self.message.emit("Camera open. Waiting for video from macOS...")
        else:
            self.message.emit("Camera stopped. Close other camera apps and reconnect.")

    def camera_error(self, error, description):
        self.stop()
        self.message.emit(description or "macOS could not open the selected camera.")

    def check_startup(self):
        if self.camera is not None and not self.received_frame:
            self.message.emit(
                "No video received. Close NoSub Cam and other camera apps on your iPhone, "
                "lock the iPhone, then disconnect and reconnect the camera here.")

    def stop(self):
        self.generation += 1
        self.startup_timer.stop()
        if self.camera is not None:
            self.camera.activeChanged.disconnect(self.camera_active_changed)
            self.camera.errorOccurred.disconnect(self.camera_error)
            self.camera.stop()
            self.capture.setCamera(None)
            self.camera.deleteLater()
            self.camera = None
        self.active_changed.emit(False)

    def receive_frame(self, frame):
        now = time.monotonic()
        if self.camera is None or not frame.isValid() or now - self.last_frame < 1 / 24:
            return
        image = frame.toImage()
        if image.isNull():
            if not self.conversion_error_reported:
                self.conversion_error_reported = True
                self.message.emit("macOS supplied video, but its pixel format could not be converted. Disconnect and reconnect the camera.")
            return
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if image.save(buffer, "JPEG", 75) and len(data) <= 8_000_000:
            self.last_frame = now
            if not self.received_frame:
                self.received_frame = True
                self.startup_timer.stop()
                self.message.emit("Live - Continuity Camera")
            self.frame.emit(bytes(data))
