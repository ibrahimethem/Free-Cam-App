from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QImage, QLinearGradient, QFont, QPen
from PySide6.QtWidgets import QWidget
from theme import COLORS


class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.mirror = False
        self.rotation = 0
        self.message = "Camera offline"
        self.detail = "Start streaming in Free Cam on your iPhone to see your camera here."
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
    gradient = QLinearGradient(0, 0, 1280, 720)
    gradient.setColorAt(0, QColor("#202728"))
    gradient.setColorAt(0.55, QColor("#424b4c"))
    gradient.setColorAt(1, QColor("#727872"))
    painter.fillRect(image.rect(), gradient)
    painter.setPen(QColor("#18ffffff"))
    for x in range(0, 1280, 80):
        painter.drawLine(x, 0, x, 720)
    for y in range(0, 720, 80):
        painter.drawLine(0, y, 1280, y)
    painter.setBrush(QColor("#12ffffff"))
    painter.setPen(QColor(COLORS["accent"]))
    painter.drawEllipse(455, 175, 370, 370)
    painter.drawEllipse(515, 235, 250, 250)
    painter.drawEllipse(575, 295, 130, 130)
    painter.setPen(QColor(COLORS["text"]))
    painter.setFont(QFont("Segoe UI", 28, QFont.Weight.DemiBold))
    painter.drawText(QRectF(0, 575, 1280, 50), Qt.AlignCenter, "FREE CAM  /  STUDIO PREVIEW")
    painter.setFont(QFont("Segoe UI", 15))
    painter.drawText(QRectF(0, 635, 1280, 40), Qt.AlignCenter, "Demo image · simulated camera settings")
    painter.end()
    return image
