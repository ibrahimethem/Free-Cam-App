"""Native NoSub Studio desktop receiver. No browser or web view is used."""
import argparse
import ipaddress
import json
import secrets
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

import qrcode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "receiver"))

from PySide6.QtCore import Qt, QTimer, QUrl, QRect, QSettings
from PySide6.QtGui import (QDesktopServices, QImage, QIcon, QPixmap, QFontDatabase,
                           QPainter, QColor, QPen)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox,
                               QScrollArea, QCheckBox, QMessageBox, QSplitter, QDialog,
                               QInputDialog)

from server import Relay
from theme import STYLE, COLORS
from widgets import GROUPS, ControlGroup, label
from preview import Preview, demo_image
from usb_transport import USBBridge
from usb_setup import USBSetupPanel

PRIVACY_URL = "https://ibrahimethem.github.io/Free-Cam-App/privacy/"
TERMS_URL = "https://ibrahimethem.github.io/Free-Cam-App/terms/"
SUPPORT_URL = "https://ibrahimethem.github.io/Free-Cam-App/support/"


class StudioComboBox(QComboBox):
    """Combo box with a visible, platform-independent studio-style chevron."""

    def wheelEvent(self, event):
        # Pass scrolling up to the settings panel without changing the selection.
        event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = COLORS["muted"] if self.isEnabled() else "#747874"
        painter.setPen(QPen(QColor(color), 1.5))
        center_x = self.width() - 14
        center_y = self.height() // 2
        painter.drawLine(center_x - 4, center_y - 2, center_x, center_y + 2)
        painter.drawLine(center_x, center_y + 2, center_x + 4, center_y - 2)


def external_link(text, url):
    button = QPushButton(text)
    button.setObjectName("link")
    button.setCursor(Qt.PointingHandCursor)
    button.setAccessibleName(text)
    button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
    return button


def pairing_payload(mode, address, key):
    values = {"mode": mode, "key": key}
    if mode == "wifi":
        values["address"] = address
    return "nosubcam://pair?" + urlencode(values)


def qr_pixmap(value, size=236):
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=3)
    code.add_data(value)
    code.make(fit=True)
    matrix = code.get_matrix()
    image = QImage(len(matrix), len(matrix), QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("black"))
    for y, row in enumerate(matrix):
        for x, filled in enumerate(row):
            if filled:
                painter.drawRect(QRect(x, y, 1, 1))
    painter.end()
    return QPixmap.fromImage(image).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.FastTransformation)


class PairingQRDialog(QDialog):
    def __init__(self, payload, mode, address, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pair NoSub Cam")
        self.setModal(True)
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = label("SCAN WITH NOSUB CAM", "section")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        qr = QLabel()
        qr.setPixmap(qr_pixmap(payload))
        qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr.setAccessibleName("Pairing QR code")
        layout.addWidget(qr)
        detail = "Direct USB · pairing key" if mode == "usb" else address
        description = label(detail)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        hint = label("On iPhone, tap Scan pairing QR. The temporary key is filled automatically.")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        close = QPushButton("Done")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


def lan_addresses():
    addresses = set()
    try:
        addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass

    # macOS commonly resolves its hostname only to loopback even while en0 has
    # an active Wi-Fi address. A UDP connect chooses the default route without
    # sending application data, giving us that interface's local address.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect(("192.0.2.1", 80))
            addresses.add(route.getsockname()[0])
    except OSError:
        pass

    private = []
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed.version == 4 and parsed.is_private and not parsed.is_loopback and not parsed.is_link_local:
            private.append(address)
    return sorted(set(private)) or ["127.0.0.1"]


def demo_report():
    caps = {"manualExposure": True, "autoExposure": True, "manualFocus": True,
            "autoFocus": True, "manualWhiteBalance": True, "autoWhiteBalance": True,
            "canZoom": True, "cameraPositions": ["rear", "front"],
            "orientations": ["landscape", "portrait"]}
    for name, minimum, maximum in (("iso", 25, 1600), ("shutterMs", 0.1, 1000),
                                    ("focus", 0, 1), ("temperature", 2000, 10000),
                                    ("tint", -150, 150), ("zoom", 1, 6)):
        caps[name] = {"min": minimum, "max": maximum}
    caps["resolutions"] = [
        {"id": f"{width}x{height}", "label": f"{title} · {width} × {height}", "width": width, "height": height}
        for title, width, height in (("480p", 640, 480), ("720p", 1280, 720),
                                     ("1080p", 1920, 1080), ("4K", 3840, 2160))]
    caps["frameRates"] = [24, 30, 60]
    return {"session": "desktop-demo", "capabilities": caps,
            "current": {"cameraPosition": "rear", "orientation": "landscape",
                        "resolution": "1280x720", "frameRate": 30,
                        "exposureAuto": False, "iso": 200, "shutterMs": 8.333,
                        "focusAuto": True, "focus": 0.5, "whiteBalanceAuto": False,
                        "temperature": 5200, "tint": 0, "zoom": 1},
            "appliedRevision": 0, "error": ""}


class MainWindow(QMainWindow):
    def __init__(self, host="0.0.0.0", port=8765, demo=False, preferences=None):
        super().__init__()
        self.host, self.port, self.demo = host, port, demo
        self.relay = None
        self.server_thread = None
        self.capture_id = None
        self.format_id = None
        self.camera_position_id = None
        self.orientation_id = None
        self.frame_rate_id = None
        self.last_sequence = -1
        self.last_frame_count = 0
        self.fps_time = time.monotonic()
        self.fps_value = 0
        self.preferences = preferences or QSettings("Ibrahim Ethem Karali", "NoSub Studio")
        self.last_sensor_settings = self.read_preference("lastSensorSettings", {})
        self.presets = self.read_preference("sensorPresets", {})
        self.last_preset = str(self.preferences.value("lastPreset", "") or "")
        self.demo_state = demo_report()
        self.demo_picture = demo_image() if demo else QImage()
        self.native_source = None
        self.usb_bridge = USBBridge(self)
        self.usb_bridge.devices_ready.connect(self.usb_devices_ready)
        self.usb_bridge.message.connect(self.source_message)
        self.usb_bridge.active_changed.connect(self.source_active_changed)
        self.usb_bridge.service_checked.connect(self.usb_service_checked)
        self.usb_setup = USBSetupPanel()
        self.usb_setup.retry.connect(self.refresh_source_devices)
        self.usb_setup.use_wifi.connect(lambda: self.source.setCurrentIndex(self.source.findData("wifi")))
        self.usb_setup.setVisible(False)
        self.source_active = False
        self.setWindowTitle("NoSub Studio" + (" — Demo" if demo else ""))
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

    def read_preference(self, key, fallback):
        try:
            value = json.loads(self.preferences.value(key, ""))
            return value if isinstance(value, type(fallback)) else fallback
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback

    def write_preference(self, key, value):
        self.preferences.setValue(key, json.dumps(value, allow_nan=False, separators=(",", ":")))
        self.preferences.sync()

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
        title.addWidget(label("NoSub Studio", "brand"))
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
        scroll = QScrollArea()
        scroll.setMinimumWidth(295)
        scroll.setMaximumWidth(380)
        scroll.setWidgetResizable(True)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        layout.addWidget(label("CAMERA SETTINGS", "section"))
        self.device_label = label("No iPhone connected", "title")
        layout.addWidget(self.device_label)
        layout.addWidget(label("Camera", ""))
        self.camera_position = StudioComboBox()
        self.camera_position.setAccessibleName("Camera position")
        self.camera_position.addItem("Connect your iPhone")
        self.camera_position.setEnabled(False)
        self.camera_position.activated.connect(self.change_camera_position)
        layout.addWidget(self.camera_position)
        layout.addWidget(label("Output orientation", ""))
        self.output_orientation = StudioComboBox()
        self.output_orientation.setAccessibleName("Output orientation")
        self.output_orientation.addItem("Connect your iPhone")
        self.output_orientation.setEnabled(False)
        self.output_orientation.activated.connect(self.change_orientation)
        layout.addWidget(self.output_orientation)
        layout.addWidget(label("Resolution", ""))
        self.resolution = StudioComboBox()
        self.resolution.setAccessibleName("Camera resolution")
        self.resolution.addItem("Connect your iPhone")
        self.resolution.setEnabled(False)
        self.resolution.activated.connect(self.change_resolution)
        layout.addWidget(self.resolution)
        layout.addWidget(label("Frame rate", ""))
        self.frame_rate = StudioComboBox()
        self.frame_rate.setAccessibleName("Camera frame rate")
        self.frame_rate.addItem("Connect your iPhone")
        self.frame_rate.setEnabled(False)
        self.frame_rate.activated.connect(self.change_frame_rate)
        layout.addWidget(self.frame_rate)
        self.capture_label = label("Capture\nWaiting for camera · native landscape · up to 30 FPS")
        layout.addWidget(self.capture_label)
        layout.addWidget(label("All camera settings apply automatically. Resolution and frame-rate changes restore automatic sensor modes."))
        layout.addWidget(label("DETAIL PRESETS", "section"))
        self.preset = StudioComboBox()
        self.preset.setAccessibleName("Saved camera preset")
        self.preset.activated.connect(self.apply_selected_preset)
        layout.addWidget(self.preset)
        preset_actions = QHBoxLayout()
        self.save_preset = QPushButton("Save preset")
        self.save_preset.clicked.connect(self.prompt_save_preset)
        preset_actions.addWidget(self.save_preset)
        self.delete_preset = QPushButton("Delete")
        self.delete_preset.clicked.connect(self.delete_selected_preset)
        preset_actions.addWidget(self.delete_preset)
        layout.addLayout(preset_actions)
        self.refresh_preset_choices(self.last_preset)
        layout.addWidget(label("CAMERA ADJUSTMENTS", "section"))
        self.control_status = label("Connect your iPhone to enable sensor controls.")
        layout.addWidget(self.control_status)
        self.groups = {}
        for name, definition in GROUPS.items():
            group = ControlGroup(definition)
            group.requested.connect(self.submit_sensor_settings)
            self.groups[name] = group
            layout.addWidget(group)
        self.restore = QPushButton("Restore automatic settings")
        self.restore.clicked.connect(self.restore_auto)
        self.restore.setEnabled(False)
        layout.addWidget(self.restore)
        layout.addWidget(label("Last detail settings are stored locally on both the computer and iPhone. Presets never leave this computer."))
        layout.addWidget(label("PREVIEW TRANSFORM", "section"))
        self.mirror = QCheckBox("Mirror preview")
        self.mirror.toggled.connect(self.transform_preview)
        layout.addWidget(self.mirror)
        self.rotation = StudioComboBox()
        self.rotation.addItems(["Rotation · 0°", "Rotation · 90°", "Rotation · 180°", "Rotation · 270°"])
        self.rotation.setAccessibleName("Preview rotation")
        self.rotation.currentIndexChanged.connect(self.transform_preview)
        layout.addWidget(self.rotation)
        layout.addWidget(label("Preview transforms affect this window only. Use OBS to transform webcam output."))
        layout.addStretch()
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
        layout.addWidget(label("CONNECTION", "section"))
        self.source = StudioComboBox()
        self.source.addItem("NoSub Cam — Wi-Fi", "wifi")
        self.source.addItem("NoSub Cam — Direct USB", "usb")
        self.source.addItem("Continuity Camera - macOS", "continuity")
        self.source.model().item(2).setEnabled(sys.platform == "darwin" and not self.demo)
        self.source.setEnabled(not self.demo)
        self.source.setAccessibleName("Camera connection source")
        layout.addWidget(self.source)
        self.source_device_label = label("Connected device")
        self.source_device_label.setVisible(False)
        layout.addWidget(self.source_device_label)
        self.source_device = StudioComboBox()
        self.source_device.setAccessibleName("USB or macOS camera device")
        self.source_device.setToolTip("Select the connected iPhone or camera. Open the list with the arrow.")
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
        layout.addWidget(label("Receiver address", ""))
        self.address = StudioComboBox()
        self.address.setAccessibleName("Receiver address")
        self.address.setToolTip("Select your computer's address on the Wi-Fi network shared with your iPhone.")
        layout.addWidget(self.address)
        self.key_label = label("Pairing key", "")
        layout.addWidget(self.key_label)
        self.key = QLineEdit()
        self.key.setReadOnly(True)
        self.key.setAccessibleName("Pairing key")
        layout.addWidget(self.key)
        self.show_pairing_qr = QPushButton("Show pairing QR")
        self.show_pairing_qr.setObjectName("primary")
        self.show_pairing_qr.clicked.connect(self.open_pairing_qr)
        layout.addWidget(self.show_pairing_qr)
        self.copy_pair = QPushButton("Copy pairing details")
        self.copy_pair.clicked.connect(self.copy_pairing)
        layout.addWidget(self.copy_pair)
        self.receiver_button = QPushButton("Stop receiver")
        self.receiver_button.clicked.connect(self.toggle_receiver)
        layout.addWidget(self.receiver_button)
        self.network_hint = label("Enter this address and key in NoSub Cam on your iPhone. Keep both devices on the same private Wi-Fi.")
        layout.addWidget(self.network_hint)
        layout.addWidget(label("Audio\nVideo only in this prototype"))
        layout.addWidget(label("LEGAL & SUPPORT", "section"))
        legal = QHBoxLayout()
        legal.setSpacing(2)
        legal.addWidget(external_link("Privacy", PRIVACY_URL))
        legal.addWidget(external_link("Terms", TERMS_URL))
        legal.addWidget(external_link("Support", SUPPORT_URL))
        layout.addLayout(legal)
        layout.addStretch()
        self.source.currentIndexChanged.connect(self.source_changed)
        scroll.setWidget(content)
        return scroll

    def start_receiver(self):
        try:
            self.relay = Relay((self.host, self.port), secrets.token_hex(8), web_ui=False)
        except OSError as error:
            self.relay = None
            QMessageBox.warning(self, "Receiver could not start", f"{error}\n\nClose another NoSub Studio receiver or choose a different port with --port.")
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
        self.camera_position_id = None
        self.orientation_id = None
        self.frame_rate_id = None
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
        self.source_device_label.setVisible(mode != "wifi")
        self.scan_source.setVisible(mode != "wifi")
        self.connect_source.setVisible(mode != "wifi")
        self.source_info.setVisible(mode != "wifi")
        self.source_info.setText("Refresh devices, select your iPhone and connect.")
        self.usb_setup.setVisible(False)
        self.address.setEnabled(mode == "wifi")
        self.key_label.setVisible(mode != "continuity")
        self.key.setVisible(mode != "continuity")
        self.show_pairing_qr.setVisible(mode != "continuity")
        hints = {
            "wifi": "Enter the receiver address and key on your iPhone. Use the same private Wi-Fi.",
            "usb": "Connect a data-capable USB cable, unlock and trust this computer. Select Direct USB in the iPhone app, enter this key and start streaming. Then select your device here and connect. No hotspot needed.",
            "continuity": "macOS only: enable Continuity Camera on iPhone and use the same Apple Account. Close NoSub Cam on iPhone; select your iPhone camera here. USB or wireless is managed by macOS. Manual sensor controls use NoSub Cam's own connection modes."}
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
            self.source_device.addItem(serial, device_id)
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
                    self.native_source.active_changed.connect(self.source_active_changed)
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
            camera = self.relay.settings.get("cameraPosition")
            if ((selected and selected != self.demo_state["current"].get("resolution")) or
                    (camera and camera != self.demo_state["current"].get("cameraPosition"))):
                self.demo_state["current"].update(exposureAuto=True, focusAuto=True, whiteBalanceAuto=True)
            if selected and selected != self.demo_state["current"].get("resolution"):
                self.demo_state["current"]["frameRate"] = 30
            if camera and camera != self.demo_state["current"].get("cameraPosition"):
                self.demo_state["current"]["resolution"] = "1280x720"
                self.demo_state["current"]["frameRate"] = 30
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
                new_session = self.capture_id != camera["session"]
                current_position = camera["current"].get("cameraPosition")
                current_orientation = camera["current"].get("orientation")
                current_frame_rate = camera["current"].get("frameRate")
                initialize = (self.capture_id != camera["session"] or
                              self.format_id != camera["current"].get("resolution") or
                              self.camera_position_id != current_position or
                              self.orientation_id != current_orientation or
                              self.frame_rate_id != current_frame_rate)
                self.capture_id = camera["session"]
                self.format_id = camera["current"].get("resolution")
                self.camera_position_id = current_position
                self.orientation_id = current_orientation
                self.frame_rate_id = current_frame_rate
                positions = camera["capabilities"].get("cameraPositions", [])
                position_choices = [("Rear camera" if item == "rear" else "Front camera", item)
                                    for item in positions]
                existing_positions = [(self.camera_position.itemText(i), self.camera_position.itemData(i))
                                      for i in range(self.camera_position.count())]
                if initialize or position_choices != existing_positions:
                    self.camera_position.clear()
                    for title, identifier in position_choices:
                        self.camera_position.addItem(title, identifier)
                    self.camera_position.setCurrentIndex(self.camera_position.findData(current_position))
                    if not position_choices:
                        self.camera_position.addItem("Update the iPhone app")
                orientations = camera["capabilities"].get("orientations", [])
                orientation_choices = [
                    ("Landscape · native" if item == "landscape" else "Portrait · rotated", item)
                    for item in orientations
                ]
                existing_orientations = [(self.output_orientation.itemText(i), self.output_orientation.itemData(i))
                                         for i in range(self.output_orientation.count())]
                if initialize or orientation_choices != existing_orientations:
                    self.output_orientation.clear()
                    for title, identifier in orientation_choices:
                        self.output_orientation.addItem(title, identifier)
                    self.output_orientation.setCurrentIndex(self.output_orientation.findData(current_orientation))
                    if not orientation_choices:
                        self.output_orientation.addItem("Update the iPhone app")
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
                frame_rate_choices = [(f"{item} FPS", item)
                                      for item in camera["capabilities"].get("frameRates", [])]
                existing_frame_rates = [(self.frame_rate.itemText(i), self.frame_rate.itemData(i))
                                        for i in range(self.frame_rate.count())]
                if initialize or frame_rate_choices != existing_frame_rates:
                    self.frame_rate.clear()
                    for title, value in frame_rate_choices:
                        self.frame_rate.addItem(title, value)
                    self.frame_rate.setCurrentIndex(self.frame_rate.findData(current_frame_rate))
                    if not frame_rate_choices:
                        self.frame_rate.addItem("Update the iPhone app")
                pending = state["revision"] > camera["appliedRevision"]
                pending_configuration = pending and any(
                    name in self.relay.settings and self.relay.settings[name] != camera["current"].get(name)
                    for name in ("cameraPosition", "orientation", "resolution", "frameRate"))
                self.camera_position.setEnabled(bool(position_choices) and not pending)
                self.output_orientation.setEnabled(bool(orientation_choices) and not pending)
                self.resolution.setEnabled(bool(choices) and not pending)
                self.frame_rate.setEnabled(bool(frame_rate_choices) and not pending)
                selected = next((item for item in options if item["id"] == self.format_id), None)
                title = selected["label"] if selected else "Resolution unavailable"
                orientation_title = current_orientation or "orientation unavailable"
                fps_title = f"{current_frame_rate} FPS" if current_frame_rate else "FPS unavailable"
                self.capture_label.setText("Capture\n" + title + f" · {orientation_title} · {fps_title}")
                for group in self.groups.values():
                    group.update_camera(camera, initialize)
                    if pending_configuration:
                        group.setEnabled(False)
                if new_session and self.last_sensor_settings:
                    self.set_sensor_editor_settings(self.last_sensor_settings)
                if state["revision"] > camera["appliedRevision"]:
                    self.control_status.setText("Waiting for iPhone acknowledgement…")
                elif camera["error"]:
                    self.control_status.setText("Camera rejected settings: " + camera["error"])
                else:
                    self.control_status.setText("Live sensor readings · changes apply automatically.")
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
            self.camera_position.setEnabled(False)
            self.output_orientation.setEnabled(False)
            self.resolution.setEnabled(False)
            self.frame_rate.setEnabled(False)
            self.capture_label.setText("Capture\nWaiting for camera · native landscape · up to 30 FPS")
            for group in self.groups.values():
                group.setEnabled(False)
            self.control_status.setText("Connect your iPhone to enable sensor controls." if self.relay else "Start the receiver to connect your iPhone.")
        self.save_preset.setEnabled(online)
        self.preset.setEnabled(online and bool(self.presets))
        self.delete_preset.setEnabled(bool(self.preset.currentData()))
        self.restore.setEnabled(online and any(camera["capabilities"][flag] for flag in ("autoExposure", "autoFocus", "autoWhiteBalance")))
        self.copy_obs.setEnabled(bool(self.relay) and not self.demo)
        self.copy_pair.setEnabled(bool(self.relay) and not self.demo)
        self.badge.setText("DEMO · SIMULATED CAMERA" if self.demo and self.relay else "IPHONE CONNECTED" if online else "WAITING FOR IPHONE" if self.relay else "RECEIVER STOPPED")
        self.device_label.setText("Demo camera" if self.demo and self.relay else "iPhone camera connected" if online else "No iPhone connected")
        if self.source.currentData() == "continuity":
            connected = bool(self.relay and self.relay.snapshot()["connected"])
            self.badge.setText("MACOS CAMERA CONNECTED" if connected else "WAITING FOR MACOS CAMERA")
            self.device_label.setText(self.source_device.currentText() if connected else "Select your iPhone camera")
            self.control_status.setText("Continuity Camera: sensor controls are managed by macOS. Use NoSub Cam Wi-Fi or Direct USB for manual settings.")
            self.capture_label.setText("Capture\nmacOS camera source" + (" · up to 24 FPS" if connected else " · waiting"))
        self.copy_pair.setEnabled(bool(self.relay) and not self.demo and self.source.currentData() != "continuity")
        self.preview.update()

    def submit(self, settings):
        if not self.relay:
            return False
        state = self.relay.snapshot()
        try:
            self.relay.submit_controls({"session": self.capture_id, "revision": state["revision"], "settings": settings})
            self.statusBar().showMessage("Settings sent · waiting for camera acknowledgement", 4000)
            self.refresh()
            return True
        except ValueError as error:
            self.statusBar().showMessage(str(error), 6000)
            return False

    def sensor_editor_settings(self):
        settings = {}
        for group in self.groups.values():
            settings.update(group.settings())
        return settings

    def set_sensor_editor_settings(self, settings):
        if not isinstance(settings, dict):
            return
        for group in self.groups.values():
            group.set_settings(settings)

    def remember_sensor_settings(self):
        self.last_sensor_settings = self.sensor_editor_settings()
        self.write_preference("lastSensorSettings", self.last_sensor_settings)

    def submit_sensor_settings(self, settings, preset_name=None):
        accepted = self.submit(settings)
        if accepted:
            self.remember_sensor_settings()
            self.last_preset = preset_name or ""
            self.preferences.setValue("lastPreset", self.last_preset)
            self.preferences.sync()
            if not preset_name:
                self.preset.blockSignals(True)
                self.preset.setCurrentIndex(0)
                self.preset.blockSignals(False)
        return accepted

    def refresh_preset_choices(self, selected=None):
        self.preset.blockSignals(True)
        self.preset.clear()
        self.preset.addItem("Select a saved preset…", None)
        for name in sorted(self.presets, key=str.casefold):
            self.preset.addItem(name, name)
        if selected in self.presets:
            self.preset.setCurrentIndex(self.preset.findData(selected))
        self.preset.blockSignals(False)
        self.delete_preset.setEnabled(bool(self.preset.currentData()))

    def prompt_save_preset(self):
        name, accepted = QInputDialog.getText(self, "Save camera preset", "Preset name")
        if accepted:
            self.save_preset_named(name)

    def save_preset_named(self, name):
        name = " ".join(str(name).split())[:60]
        if not name:
            self.statusBar().showMessage("Enter a preset name.", 3000)
            return False
        self.presets[name] = self.sensor_editor_settings()
        self.last_preset = name
        self.preferences.setValue("lastPreset", name)
        self.write_preference("sensorPresets", self.presets)
        self.refresh_preset_choices(name)
        self.statusBar().showMessage(f"Preset saved · {name}", 3000)
        return True

    def apply_selected_preset(self, _index=None):
        name = self.preset.currentData()
        settings = self.presets.get(name)
        if not isinstance(settings, dict) or not settings:
            return
        self.set_sensor_editor_settings(settings)
        if self.submit_sensor_settings(self.sensor_editor_settings(), preset_name=name):
            self.statusBar().showMessage(f"Preset applied · {name}", 3000)

    def delete_selected_preset(self):
        name = self.preset.currentData()
        if name not in self.presets:
            return
        del self.presets[name]
        if self.last_preset == name:
            self.last_preset = ""
            self.preferences.setValue("lastPreset", "")
        self.write_preference("sensorPresets", self.presets)
        self.refresh_preset_choices()
        self.statusBar().showMessage(f"Preset deleted · {name}", 3000)

    def restore_auto(self):
        if not self.relay:
            return
        camera = self.relay.snapshot()["camera"]
        if not camera:
            return
        settings = {group["mode"]: True for group in GROUPS.values()
                    if "mode" in group and camera["capabilities"][group["auto"]]}
        # Refresh the editor's mode switches as well as sending to the sensor.
        for group in self.groups.values():
            if group.auto and group.definition["mode"] in settings:
                group.set_settings({group.definition["mode"]: True})
        self.submit_sensor_settings(settings)

    def change_resolution(self, *_):
        selected = self.resolution.currentData()
        if selected and selected != self.format_id:
            self.submit({"resolution": selected})

    def change_frame_rate(self, *_):
        selected = self.frame_rate.currentData()
        if selected and selected != self.frame_rate_id:
            self.submit({"frameRate": selected})

    def change_camera_position(self, *_):
        selected = self.camera_position.currentData()
        if selected and selected != self.camera_position_id:
            self.submit({"cameraPosition": selected})

    def change_orientation(self, *_):
        selected = self.output_orientation.currentData()
        if selected and selected != self.orientation_id:
            self.submit({"orientation": selected})

    def copy_pairing(self):
        if self.relay:
            connection = "Connection: Direct USB" if self.source.currentData() == "usb" else f"Receiver: {self.address.currentText()}"
            QApplication.clipboard().setText(f"{connection}\nPairing key: {self.relay.token}")
            self.statusBar().showMessage("Pairing details copied", 3000)

    def open_pairing_qr(self):
        if not self.relay:
            self.statusBar().showMessage("Start the receiver before pairing.")
            return
        mode = self.source.currentData()
        if mode not in ("wifi", "usb"):
            return
        address = self.address.currentText() if mode == "wifi" else ""
        PairingQRDialog(pairing_payload(mode, address, self.relay.token), mode, address, self).exec()

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
    app.setApplicationName("NoSub Studio")
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
