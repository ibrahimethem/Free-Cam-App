"""macOS menu-bar / Windows notification-area lifecycle, without a second process."""
import sys

from PySide6.QtCore import QObject, Qt, QRectF, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def camera_icon():
    picture = QPixmap(44, 44)
    picture.fill(Qt.GlobalColor.transparent)
    painter = QPainter(picture)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("white" if sys.platform == "darwin" else "#65d58b"), 3))
    painter.drawRoundedRect(QRectF(4, 11, 28, 23), 3, 3)
    painter.drawEllipse(QRectF(12, 17, 12, 12))
    painter.drawLine(32, 18, 40, 13)
    painter.drawLine(40, 13, 40, 32)
    painter.drawLine(40, 32, 32, 27)
    painter.end()
    icon = QIcon(picture)
    icon.setIsMask(sys.platform == "darwin")
    return icon


class BackgroundController(QObject):
    show_requested = Signal()
    quit_requested = Signal()

    def __init__(self, window, enabled=True):
        super().__init__(window)
        self.tray = None
        self.menu = QMenu(window)
        self.show_action = self.menu.addAction("Open NoSub Studio")
        self.show_action.triggered.connect(self.show_requested)
        self.status_action = self.menu.addAction("Waiting for camera")
        self.status_action.setEnabled(False)
        self.menu.addSeparator()
        self.quit_action = QAction("Quit NoSub Studio", self)
        self.quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        self.quit_action.triggered.connect(self.quit_requested)
        self.menu.addAction(self.quit_action)
        if enabled and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(camera_icon(), self)
            self.tray.setContextMenu(self.menu)
            self.tray.setToolTip("NoSub Studio")
            self.tray.activated.connect(self.activated)
            self.tray.show()

    @property
    def available(self):
        return bool(self.tray and self.tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable())

    def activated(self, reason):
        # macOS presents the context menu on click; don't also reopen the window.
        if sys.platform != "darwin" and reason in (
                QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_requested.emit()

    def update_status(self, receiver, connected, output):
        if not receiver:
            status = "Receiver stopped"
        elif connected:
            status = "Streaming · native output on" if output else "Camera connected"
        else:
            status = "Output on · waiting for camera" if output else "Waiting for camera"
        self.status_action.setText(status)
        if self.tray:
            self.tray.setToolTip("NoSub Studio · " + status)

    def close(self):
        if self.tray:
            self.tray.hide()
