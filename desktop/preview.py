from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QImage, QFont, QPen
from PySide6.QtWidgets import QWidget
from theme import COLORS


class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.mirror = False
        self.rotation = 0
        self.message = "Camera offline"
        self.detail = "Start streaming in NoSub Cam on your iPhone to see your camera here."
        self.setMinimumSize(300, 300)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(COLORS["preview"]))
        if self.image.isNull():
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(COLORS["muted"]), 1.5))
            painter.drawRoundedRect(QRectF(self.width() / 2 - 24, self.height() / 2 - 65, 48, 32), 3, 3)
            painter.drawEllipse(QRectF(self.width() / 2 - 8, self.height() / 2 - 57, 16, 16))
            painter.setPen(QColor(COLORS["text"]))
            painter.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
            painter.drawText(QRectF(30, self.height() / 2, self.width() - 60, 45), Qt.AlignCenter, self.message)
            painter.setPen(QColor(COLORS["muted"]))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(40, self.height() / 2 + 45, self.width() - 80, 70),
                             Qt.AlignHCenter | Qt.TextWordWrap, self.detail)
            return
        width, height = self.image.width(), self.image.height()
        if self.rotation % 180:
            width, height = height, width
        scale = min(self.width() / width, self.height() / height)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(-scale if self.mirror else scale, scale)
        painter.rotate(self.rotation)
        painter.drawImage(QRectF(-self.image.width() / 2, -self.image.height() / 2,
                                self.image.width(), self.image.height()), self.image)


def demo_image():
    image = QImage(1280, 720, QImage.Format_RGB32)
    painter = QPainter(image)
    painter.fillRect(image.rect(), QColor(COLORS["preview"]))
    painter.setRenderHint(QPainter.Antialiasing)

    body = QRectF(540, 288, 200, 134)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(COLORS["muted"]), 5))
    painter.drawRoundedRect(body, 10, 10)
    painter.drawEllipse(QRectF(597, 316, 86, 86))

    painter.setBrush(QColor(COLORS["accent"]))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QRectF(704, 306, 14, 14))
    painter.end()
    return image
