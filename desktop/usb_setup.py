"""Actionable Windows USB setup guidance without guessing installation state."""
from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton

from widgets import label

APPLE_DEVICES_URL = "https://apps.microsoft.com/detail/9NP83LWLPZ9K"


class USBSetupPanel(QFrame):
    retry = Signal()
    use_wifi = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("usbSetup")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)
        layout.addWidget(label("USB bağlantısını hazırlayalım", "title"))
        layout.addWidget(label("USB bağlantısı şu anda hazır değil. Apple Devices yüklü değilse "
                               "Microsoft Store’dan kurun. Zaten kuruluysa uygulamayı açıp yeniden deneyin."))
        layout.addWidget(label("Ardından iPhone’unuzu USB kablosuyla bağlayın, kilidini açın ve "
                               "‘Bu bilgisayara güven’ isteğini onaylayın. iTunes gerekmez."))
        self.download = QPushButton("Apple Devices’ı indir")
        self.download.setObjectName("primary")
        self.download.setToolTip("Microsoft Store’daki resmî Apple Devices sayfasını açar.")
        self.download.clicked.connect(self.open_download)
        layout.addWidget(self.download)
        self.retry_button = QPushButton("Tekrar kontrol et")
        self.retry_button.clicked.connect(self.retry.emit)
        layout.addWidget(self.retry_button)
        self.wifi_button = QPushButton("Wi-Fi ile devam et")
        self.wifi_button.clicked.connect(self.use_wifi.emit)
        layout.addWidget(self.wifi_button)

    def open_download(self):
        QDesktopServices.openUrl(QUrl(APPLE_DEVICES_URL))
