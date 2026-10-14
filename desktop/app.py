"""Native Free Cam desktop receiver. No browser or web view is used."""
import argparse
import secrets
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "receiver"))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QIcon, QPixmap, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox,
                               QScrollArea, QCheckBox, QMessageBox, QSplitter)

from server import Relay
from theme import STYLE, COLORS
from widgets import GROUPS, ControlGroup, label
from preview import Preview, demo_image
from usb_transport import USBBridge
from usb_setup import USBSetupPanel


def lan_addresses():
    try:
        addresses = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        addresses = []
    addresses = sorted({a for a in addresses if a.startswith(("10.", "192.168."))
                        or (a.startswith("172.") and 16 <= int(a.split(".")[1]) <= 31)})
    return addresses or ["127.0.0.1"]


def demo_report():
    caps = {"manualExposure": True, "autoExposure": True, "manualFocus": True,
            "autoFocus": True, "manualWhiteBalance": True, "autoWhiteBalance": True,
            "canZoom": True}
    for name, minimum, maximum in (("iso", 25, 1600), ("shutterMs", 0.1, 1000),
                                    ("focus", 0, 1), ("temperature", 2000, 10000),
                                    ("tint", -150, 150), ("zoom", 1, 6)):
        caps[name] = {"min": minimum, "max": maximum}
    caps["resolutions"] = [
        {"id": f"{width}x{height}", "label": f"{title} · {width} × {height}", "width": width, "height": height}
        for title, width, height in (("480p", 640, 480), ("720p", 1280, 720),
                                     ("1080p", 1920, 1080), ("4K", 3840, 2160))]
    return {"session": "desktop-demo", "capabilities": caps,
            "current": {"resolution": "1280x720", "exposureAuto": False, "iso": 200, "shutterMs": 8.333,
                        "focusAuto": True, "focus": 0.5, "whiteBalanceAuto": False,
                        "temperature": 5200, "tint": 0, "zoom": 1},
            "appliedRevision": 0, "error": ""}


class MainWindow(QMainWindow):
    def __init__(self, host="0.0.0.0", port=8765, demo=False):
        super().__init__()
        self.host, self.port, self.demo = host, port, demo
        self.relay = None
        self.server_thread = None
        self.capture_id = None
        self.format_id = None
        self.last_sequence = -1
        self.last_frame_count = 0
        self.fps_time = time.monotonic()
        self.fps_value = 0
        self.demo_state = demo_report()
        self.demo_picture = demo_image() if demo else QImage()
        self.native_source = None
        self.usb_bridge = USBBridge(self)
        self.usb_bridge.devices_ready.connect(self.usb_devices_ready)
        self.usb_bridge.message.connect(self.source_message)
        self.usb_bridge.active_changed.connect(self.source_active_changed)
        self.usb_bridge.service_checked.connect(self.usb_service_checked)
        self.source_active = False
        self.setWindowTitle("Free Cam Studio" + (" — Demo" if demo else ""))
        self.resize(1400, 900)
        self.setMinimumSize(1060, 690)
        icon = QPixmap(64, 64)
        icon.fill(Qt.GlobalColor.transparent)
        from PySide6.QtGui import QPainter, QColor, QFont
        painter = QPainter(icon)
        painter.setBrush(QColor(COLORS["accent"]))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 64, 64, 4, 4)
        painter.setPen(QColor(COLORS["input"]))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        painter.drawText(icon.rect(), Qt.AlignCenter, "F")
        painter.end()
        self.setWindowIcon(QIcon(icon))
        self.build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.start_receiver()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(64)
        top = QHBoxLayout(toolbar)
        top.setContentsMargins(18, 12, 18, 12)
        title = QVBoxLayout()
        title.setSpacing(2)
        title.addWidget(label("Free Cam Studio", "brand"))
        title.addWidget(label("iPhone camera · desktop control", "subtitle"))
        top.addLayout(title)
        top.addStretch()
        self.badge = label("DEMO · SIMULATED CAMERA" if self.demo else "WAITING FOR IPHONE", "badge")
        self.badge.setWordWrap(False)
        top.addWidget(self.badge)
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self.build_left())
        splitter.addWidget(self.build_center())
        splitter.addWidget(self.build_right())
        splitter.setSizes([255, 775, 310])
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)
        self.statusBar().showMessage("Starting receiver…")

    def build_left(self):
        panel = QWidget()
        panel.setMinimumWidth(235)
        panel.setMaximumWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(label("CAMERA SETTINGS", "section"))
        self.device_label = label("No iPhone connected", "title")
        layout.addWidget(self.device_label)
        layout.addWidget(label("Camera selection\nFront / rear selected on iPhone"))
        layout.addWidget(label("Lens\nWide angle"))
        layout.addWidget(label("Resolution", ""))
        self.resolution = QComboBox()
        self.resolution.setAccessibleName("Camera resolution")
        self.resolution.addItem("Connect your iPhone")
        self.resolution.setEnabled(False)
        layout.addWidget(self.resolution)
        self.apply_resolution = QPushButton("Apply resolution")
        self.apply_resolution.clicked.connect(self.change_resolution)
        self.apply_resolution.setEnabled(False)
        layout.addWidget(self.apply_resolution)
        self.capture_label = label("Capture\nWaiting for camera · portrait · up to 24 FPS")
        layout.addWidget(self.capture_label)
        layout.addWidget(label("Resolution changes restore automatic camera modes. Higher resolutions use more Wi-Fi bandwidth."))
        layout.addWidget(label("Audio\nVideo only in this prototype"))
        layout.addWidget(label("CONNECTION", "section"))
        self.source = QComboBox()
        self.source.addItem("Free Cam - Wi-Fi", "wifi")
        self.source.addItem("Free Cam - Direct USB", "usb")
        self.source.addItem("Continuity Camera - macOS", "continuity")
        self.source.model().item(2).setEnabled(sys.platform == "darwin" and not self.demo)
        self.source.setEnabled(not self.demo)
        self.source.setAccessibleName("Camera connection source")
        layout.addWidget(self.source)
        self.source_device = QComboBox()
        self.source_device.setAccessibleName("USB or macOS camera device")
        self.source_device.setVisible(False)
        layout.addWidget(self.source_device)
        self.scan_source = QPushButton("Refresh devices")
        self.scan_source.clicked.connect(self.refresh_source_devices)
        self.scan_source.setVisible(False)
        layout.addWidget(self.scan_source)
        self.connect_source = QPushButton("Connect camera")
        self.connect_source.clicked.connect(self.toggle_source)
        self.connect_source.setVisible(False)
        layout.addWidget(self.connect_source)
        self.source_info = label("")
        self.source_info.setVisible(False)
        layout.addWidget(self.source_info)
        self.usb_setup = USBSetupPanel()
        self.usb_setup.retry.connect(self.refresh_source_devices)
        self.usb_setup.use_wifi.connect(lambda: self.source.setCurrentIndex(self.source.findData("wifi")))
        self.usb_setup.setVisible(False)
        self.source.currentIndexChanged.connect(self.source_changed)
        layout.addWidget(label("Receiver address", ""))
        self.address = QComboBox()
        self.address.setAccessibleName("Receiver address")
        self.address.setToolTip("Select your computer's address on the Wi-Fi network shared with your iPhone.")
        layout.addWidget(self.address)
        layout.addWidget(label("Pairing key", ""))
        self.key = QLineEdit()
        self.key.setReadOnly(True)
        self.key.setAccessibleName("Pairing key")
        layout.addWidget(self.key)
        self.copy_pair = QPushButton("Copy pairing details")
        self.copy_pair.clicked.connect(self.copy_pairing)
        layout.addWidget(self.copy_pair)
        self.receiver_button = QPushButton("Stop receiver")
        self.receiver_button.clicked.connect(self.toggle_receiver)
        layout.addWidget(self.receiver_button)
        self.network_hint = label("Enter this address and key in Free Cam on your iPhone. Keep both devices on the same private Wi-Fi.")
        layout.addWidget(self.network_hint)
        layout.addWidget(label("QUICK ACTIONS", "section"))
        self.restore = QPushButton("Restore automatic settings")
        self.restore.clicked.connect(self.restore_auto)
        self.restore.setEnabled(False)
        layout.addWidget(self.restore)
        layout.addWidget(label("PREVIEW TRANSFORM", "section"))
        self.mirror = QCheckBox("Mirror preview")
        self.mirror.toggled.connect(self.transform_preview)
        layout.addWidget(self.mirror)
        self.rotation = QComboBox()
        self.rotation.addItems(["Rotation · 0°", "Rotation · 90°", "Rotation · 180°", "Rotation · 270°"])
        self.rotation.setAccessibleName("Preview rotation")
        self.rotation.currentIndexChanged.connect(self.transform_preview)
        layout.addWidget(self.rotation)
        layout.addWidget(label("Preview transforms affect this window only. Use OBS to transform webcam output."))
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setMinimumWidth(235)
        scroll.setMaximumWidth(320)
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        return scroll

    def build_center(self):
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(18, 12, 18, 12)
        bar.addWidget(label("CAMERA PREVIEW", "section"))
        bar.addStretch()
        self.fps_label = label("— FPS")
        self.fps_label.setWordWrap(False)
        bar.addWidget(self.fps_label)
        layout.addLayout(bar)
        layout.addWidget(self.usb_setup)
        self.preview = Preview()
        layout.addWidget(self.preview, 1)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(18, 14, 18, 14)
        descriptions = QVBoxLayout()
        descriptions.setSpacing(4)
        descriptions.addWidget(label("Webcam output", "title"))
        descriptions.addWidget(label("Add the stream as an OBS Media Source, then start OBS Virtual Camera."))
        bottom.addLayout(descriptions, 1)
        self.copy_obs = QPushButton("Copy OBS stream URL")
        self.copy_obs.setObjectName("primary")
        self.copy_obs.clicked.connect(self.copy_obs_url)
        bottom.addWidget(self.copy_obs)
        layout.addLayout(bottom)
        return center

    def build_right(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(295)
        scroll.setMaximumWidth(380)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        layout.addWidget(label("CAMERA ADJUSTMENTS", "section"))
        self.control_status = label("Connect your iPhone to enable sensor controls.")
        layout.addWidget(self.control_status)
        self.groups = {}
        for name, definition in GROUPS.items():
            group = ControlGroup(definition)
            group.requested.connect(self.submit)
            self.groups[name] = group
            layout.addWidget(group)
        layout.addWidget(label("Settings apply to the iPhone sensor. Availability depends on the selected camera. White balance gains are bounded by hardware."))
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def start_receiver(self):
        try:
            self.relay = Relay((self.host, self.port), secrets.token_hex(8), web_ui=False)
        except OSError as error:
            self.relay = None
            QMessageBox.warning(self, "Receiver could not start", f"{error}\n\nClose another Free Cam receiver or choose a different port with --port.")
            self.receiver_button.setText("Start receiver")
            self.refresh()
            return
        self.relay.accept_phone = self.source.currentData() == "wifi"
        self.server_thread = threading.Thread(target=self.relay.serve_forever, daemon=True)
        self.server_thread.start()
        self.address.clear()
        for address in lan_addresses():
            self.address.addItem(f"http://{address}:{self.relay.server_port}")
        self.key.setText(self.relay.token)
        self.receiver_button.setText("Stop receiver")
        self.capture_id = None
        self.format_id = None
        self.last_sequence = -1
        self.last_frame_count = 0
        self.fps_time = time.monotonic()
        self.fps_value = 0
        if self.address.currentText().startswith("http://127.") and not self.demo:
            self.network_hint.setText("No Wi-Fi address detected. Connect your computer to Wi-Fi and restart the receiver. An iPhone cannot connect to 127.0.0.1 on your computer.")
        self.statusBar().showMessage("Receiver running · connect your iPhone" if not self.demo else "Demo mode · no iPhone is connected")
        self.refresh()

    def stop_receiver(self):
        self.usb_bridge.stop()
        if self.native_source:
            self.native_source.stop()
        if self.relay:
            self.relay.shutdown()
            self.relay.server_close()
            if self.server_thread:
                self.server_thread.join(timeout=2)
        self.relay = None
        self.key.clear()
        self.address.clear()
        self.receiver_button.setText("Start receiver")
        self.statusBar().showMessage("Receiver stopped · pairing key revoked")
        self.refresh()

    def source_changed(self):
        mode = self.source.currentData()
        self.stop_receiver()
        self.start_receiver()
        self.source_device.setVisible(mode != "wifi")
        self.scan_source.setVisible(mode != "wifi")
        self.connect_source.setVisible(mode != "wifi")
        self.source_info.setVisible(mode != "wifi")
        self.source_info.setText("Refresh devices, select your iPhone and connect.")
        self.usb_setup.setVisible(False)
        self.address.setEnabled(mode == "wifi")
        self.key.setVisible(mode != "continuity")
        hints = {
            "wifi": "Enter the receiver address and key on your iPhone. Use the same private Wi-Fi.",
            "usb": "Connect a data-capable USB cable, unlock and trust this computer. Select Direct USB in the iPhone app, enter this key and start streaming. Then select your device here and connect. No hotspot needed.",
            "continuity": "macOS only: enable Continuity Camera on iPhone and use the same Apple Account. Close Free Cam on iPhone; select your iPhone camera here. USB or wireless is managed by macOS. Manual sensor controls use Free Cam's own connection modes."}
        self.network_hint.setText(hints[mode])
        self.preview.detail = hints[mode]
        if mode != "wifi":
            self.refresh_source_devices()

    def source_message(self, text):
        if self.source.currentData() != "wifi":
            self.source_info.setText(text)
            self.statusBar().showMessage(text)

    def source_active_changed(self, active):
        self.source_active = active
        self.connect_source.setText("Disconnect camera" if active else "Connect camera")

    def usb_service_checked(self, available):
        if self.source.currentData() != "usb":
            return
        self.usb_setup.setVisible(not available and sys.platform == "win32")
        self.connect_source.setEnabled(available)
        if available:
            self.source_info.setText("USB connection ready. Select your connected iPhone.")
        elif sys.platform == "win32":
            self.source_info.setText("USB için tek seferlik kurulum")
        else:
            self.source_info.setText("USB service could not be reached. Reconnect your iPhone and retry.")

    def usb_devices_ready(self, devices):
        if self.source.currentData() != "usb":
            return
        self.source_device.clear()
        for device_id, serial in devices:
            self.source_device.addItem("iPhone / iPad - " + serial, device_id)
        if not devices:
            self.source_device.addItem("No USB device detected")
            if self.usb_setup.isHidden():
                self.source_info.setText("No USB device detected. Connect your iPhone, unlock it and trust this computer.")

    def refresh_source_devices(self):
        if self.source.currentData() == "usb":
            self.connect_source.setEnabled(False)
            self.source_device.clear()
            self.source_device.addItem("Looking for USB devices...")
            self.usb_bridge.scan()
        elif self.source.currentData() == "continuity":
            self.connect_source.setEnabled(True)
            if self.native_source is None:
                try:
                    from native_camera import NativeCameraSource
                    self.native_source = NativeCameraSource(self)
                    self.native_source.frame.connect(self.native_frame)
                    self.native_source.message.connect(self.source_message)
                    self.native_source.devices_changed.connect(self.refresh_source_devices)
                except (ImportError, RuntimeError) as error:
                    self.source_message(str(error))
                    return
            selected = self.source_device.currentData()
            self.source_device.clear()
            for device_id, name in self.native_source.devices():
                self.source_device.addItem(name, device_id)
            if self.source_device.count() == 0:
                self.source_device.addItem("No macOS cameras detected")
            elif selected is not None:
                self.source_device.setCurrentIndex(max(0, self.source_device.findData(selected)))

    def native_frame(self, frame):
        if self.relay and self.source.currentData() == "continuity":
            self.relay.publish_native_frame(frame)
            self.source_active_changed(True)

    def toggle_source(self):
        if self.source_active:
            self.usb_bridge.stop()
            if self.native_source:
                self.native_source.stop()
            self.source_active_changed(False)
            if self.relay:
                with self.relay.changed:
                    self.relay.frame = None
                    self.relay.camera = None
                    self.relay.last_camera = self.relay.last_frame = 0
            self.refresh()
            return
        device_id = self.source_device.currentData()
        if self.relay is None or device_id is None:
            self.source_message("Start the receiver and select a device first.")
        elif self.source.currentData() == "usb":
            self.usb_bridge.start(device_id, self.relay)
        elif self.native_source:
            self.native_source.start(device_id)

    def toggle_receiver(self):
        if self.relay:
            self.stop_receiver()
        else:
            self.start_receiver()

    def simulate(self):
        with self.relay.changed:
            selected = self.relay.settings.get("resolution")
            if selected and selected != self.demo_state["current"].get("resolution"):
                self.demo_state["current"].update(exposureAuto=True, focusAuto=True, whiteBalanceAuto=True)
            self.demo_state["current"].update(self.relay.settings)
            self.demo_state["appliedRevision"] = self.relay.revision
            self.relay.camera = self.demo_state
            self.relay.last_camera = time.monotonic()

    def refresh(self):
        online = False
        camera = None
        if self.relay:
            if self.demo:
                self.simulate()
            state = self.relay.snapshot()
            online = state["cameraConnected"]
            camera = state["camera"]
            if online:
                initialize = self.capture_id != camera["session"] or self.format_id != camera["current"].get("resolution")
                self.capture_id = camera["session"]
                self.format_id = camera["current"].get("resolution")
                options = camera["capabilities"].get("resolutions", [])
                choices = [(item["label"], item["id"]) for item in options]
                existing = [(self.resolution.itemText(i), self.resolution.itemData(i)) for i in range(self.resolution.count())]
                if initialize or choices != existing:
                    self.resolution.clear()
                    for title, id in choices:
                        self.resolution.addItem(title, id)
                    self.resolution.setCurrentIndex(self.resolution.findData(self.format_id))
                    if not choices:
                        self.resolution.addItem("Update the iPhone app")
                pending_resolution = (state["revision"] > camera["appliedRevision"] and
                                      self.relay.settings.get("resolution") != self.format_id and
                                      "resolution" in self.relay.settings)
                self.resolution.setEnabled(bool(choices) and not pending_resolution)
                self.apply_resolution.setEnabled(bool(choices) and not pending_resolution)
                selected = next((item for item in options if item["id"] == self.format_id), None)
                title = selected["label"] if selected else "Resolution unavailable"
                self.capture_label.setText("Capture\n" + title + " · portrait · up to 24 FPS")
                for group in self.groups.values():
                    group.update_camera(camera, initialize)
                    if pending_resolution:
                        group.setEnabled(False)
                if state["revision"] > camera["appliedRevision"]:
                    self.control_status.setText("Waiting for iPhone acknowledgement…")
                elif camera["error"]:
                    self.control_status.setText("Camera rejected settings: " + camera["error"])
                else:
                    self.control_status.setText("Live sensor readings · click Apply to send changes.")
            if self.demo:
                self.preview.image = self.demo_picture
                self.fps_label.setText("DEMO · simulated readings")
            else:
                with self.relay.changed:
                    sequence, frame = self.relay.sequence, self.relay.frame
                if state["connected"] and sequence != self.last_sequence and frame:
                    decoded = QImage.fromData(frame, "JPEG")
                    if not decoded.isNull():
                        self.preview.image = decoded
                        self.last_sequence = sequence
                if not state["connected"]:
                    self.preview.image = QImage()
                elapsed = time.monotonic() - self.fps_time
                if elapsed >= 1:
                    self.fps_value = max(0, state["frames"] - self.last_frame_count) / elapsed
                    self.last_frame_count = state["frames"]
                    self.fps_time = time.monotonic()
                self.fps_label.setText(f"{self.fps_value:.0f} FPS" if state["connected"] else "— FPS")
        else:
            self.preview.image = QImage()
            self.fps_label.setText("— FPS")
        if not online:
            self.resolution.setEnabled(False)
            self.apply_resolution.setEnabled(False)
            self.capture_label.setText("Capture\nWaiting for camera · portrait · up to 24 FPS")
            for group in self.groups.values():
                group.setEnabled(False)
            self.control_status.setText("Connect your iPhone to enable sensor controls." if self.relay else "Start the receiver to connect your iPhone.")
        self.restore.setEnabled(online and any(camera["capabilities"][flag] for flag in ("autoExposure", "autoFocus", "autoWhiteBalance")))
        self.copy_obs.setEnabled(bool(self.relay) and not self.demo)
        self.copy_pair.setEnabled(bool(self.relay) and not self.demo)
        self.badge.setText("DEMO · SIMULATED CAMERA" if self.demo and self.relay else "IPHONE CONNECTED" if online else "WAITING FOR IPHONE" if self.relay else "RECEIVER STOPPED")
        self.device_label.setText("Demo camera" if self.demo and self.relay else "iPhone camera connected" if online else "No iPhone connected")
        if self.source.currentData() == "continuity":
            connected = bool(self.relay and self.relay.snapshot()["connected"])
            self.badge.setText("MACOS CAMERA CONNECTED" if connected else "WAITING FOR MACOS CAMERA")
            self.device_label.setText(self.source_device.currentText() if connected else "Select your iPhone camera")
            self.control_status.setText("Continuity Camera: sensor controls are managed by macOS. Use Free Cam Wi-Fi or Direct USB for manual settings.")
            self.capture_label.setText("Capture\nmacOS camera source" + (" · up to 24 FPS" if connected else " · waiting"))
        self.copy_pair.setEnabled(bool(self.relay) and not self.demo and self.source.currentData() != "continuity")
        self.preview.update()

    def submit(self, settings):
        if not self.relay:
            return
        state = self.relay.snapshot()
        try:
            self.relay.submit_controls({"session": self.capture_id, "revision": state["revision"], "settings": settings})
            self.statusBar().showMessage("Settings sent · waiting for camera acknowledgement", 4000)
            self.refresh()
        except ValueError as error:
            self.statusBar().showMessage(str(error), 6000)

    def restore_auto(self):
        if not self.relay:
            return
        camera = self.relay.snapshot()["camera"]
        if not camera:
            return
        settings = {group["mode"]: True for group in GROUPS.values()
                    if "mode" in group and camera["capabilities"][group["auto"]]}
        self.submit(settings)
        # Refresh the editor's mode switches as well as sending to the sensor.
        for group in self.groups.values():
            if group.auto and group.definition["mode"] in settings:
                group.auto.setChecked(True)

    def change_resolution(self):
        selected = self.resolution.currentData()
        if selected and selected != self.format_id:
            self.submit({"resolution": selected})

    def copy_pairing(self):
        if self.relay:
            connection = "Connection: Direct USB" if self.source.currentData() == "usb" else f"Receiver: {self.address.currentText()}"
            QApplication.clipboard().setText(f"{connection}\nPairing key: {self.relay.token}")
            self.statusBar().showMessage("Pairing details copied", 3000)

    def copy_obs_url(self):
        if self.relay:
            url = f"http://127.0.0.1:{self.relay.server_port}/stream.mjpg?key={self.relay.token}"
            QApplication.clipboard().setText(url)
            self.statusBar().showMessage("OBS stream URL copied · paste it into an OBS Media Source", 5000)

    def transform_preview(self):
        self.preview.mirror = self.mirror.isChecked()
        self.preview.rotation = self.rotation.currentIndex() * 90
        self.preview.update()

    def closeEvent(self, event):
        self.timer.stop()
        self.stop_receiver()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default=None)
    parser.add_argument("--demo", action="store_true", help="Show explicitly simulated camera controls and a test image")
    parser.add_argument("--screenshot", type=Path, help="Save a UI screenshot and exit (for development)")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    if app.platformName() == "offscreen" and sys.platform == "win32":
        # The offscreen plugin has no Windows font enumeration; load local fonts for QA.
        for name in ("segoeui.ttf", "segoeuib.ttf"):
            path = Path("C:/Windows/Fonts") / name
            if path.exists():
                QFontDatabase.addApplicationFont(str(path))
    app.setApplicationName("Free Cam Studio")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow(args.host or ("127.0.0.1" if args.demo else "0.0.0.0"), args.port, args.demo)
    window.show()
    if args.screenshot:
        def capture():
            window.grab().save(str(args.screenshot), "PNG")
            window.close()
            app.quit()
        QTimer.singleShot(500, capture)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
