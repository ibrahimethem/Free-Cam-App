"""Neutral studio palette shared by widgets and painted preview surfaces."""
COLORS = {
    "background": "#292b2c", "surface": "#343637", "toolbar": "#414445",
    "input": "#242627", "border": "#555859", "text": "#eceeea",
    "muted": "#b5b9b5", "accent": "#ffb16b", "preview": "#1d1f20",
}

STYLE = """
QWidget { background: #292b2c; color: #eceeea; font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 12px; }
QMainWindow { background: #292b2c; }
QFrame#toolbar { background: #414445; border-bottom: 1px solid #555859; }
QLabel#brand { font-size: 15px; font-weight: 700; }
QLabel#subtitle, QLabel#muted { color: #b5b9b5; font-size: 11px; }
QLabel#section { color: #d1d4cf; font-weight: 600; font-size: 11px; padding-top: 8px; }
QLabel#title { font-size: 13px; font-weight: 600; }
QLabel#badge { background: #292b2c; color: #ffb16b; border: 1px solid #62635c; border-radius: 3px; padding: 5px 10px; font-size: 11px; }
QFrame#panel { background: #343637; border: 1px solid #555859; border-radius: 3px; }
QFrame#usbSetup { background: #343637; border: 1px solid #ffb16b; border-radius: 3px; }
QLabel, QCheckBox { background: transparent; }
QScrollArea, QScrollArea > QWidget > QWidget { background: #343637; border: none; }
QLineEdit, QComboBox { background: #242627; border: 1px solid #555859; border-radius: 3px; padding: 6px; selection-background-color: #ffb16b; selection-color: #242627; }
QLineEdit:focus, QComboBox:focus { border-color: #ffb16b; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #343637; selection-background-color: #ffb16b; selection-color: #242627; }
QDoubleSpinBox { background: #242627; min-width: 100px; }
QPushButton { background: #454849; border: 1px solid #606465; padding: 7px 10px; border-radius: 3px; font-weight: 500; }
QPushButton:hover { background: #55595a; border-color: #a8aca6; }
QPushButton:pressed { background: #242627; }
QPushButton:focus { border-color: #ffb16b; }
QPushButton#primary { background: #ffb16b; border: 1px solid #ffb16b; color: #242627; font-weight: 600; }
QPushButton#primary:hover { background: #ffc28c; border-color: #ffc28c; }
QPushButton#primary:pressed { background: #e79b57; }
QWidget:disabled { color: #929791; }
QPushButton:disabled { background: #343637; border-color: #4b4e4f; color: #929791; }
QCheckBox { spacing: 7px; }
QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #8c928b; border-radius: 2px; background: #242627; }
QCheckBox::indicator:checked { background: #ffb16b; border-color: #ffb16b; }
QCheckBox::indicator:disabled { background: #343637; border-color: #626762; }
QSlider::groove:horizontal { background: #222425; height: 4px; border-radius: 1px; }
QSlider::sub-page:horizontal { background: #ffb16b; }
QSlider::handle:horizontal { background: #dce0d9; width: 7px; margin: -4px 0; border-radius: 1px; }
QSlider::sub-page:horizontal:disabled { background: #626762; }
QSlider::handle:horizontal:disabled { background: #8c928b; }
QScrollBar:vertical { background: #343637; width: 6px; }
QScrollBar::handle:vertical { background: #737972; min-height: 25px; border-radius: 1px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #555859; }
QStatusBar { background: #242627; color: #b5b9b5; border-top: 1px solid #555859; }
QToolTip { color: #eceeea; background: #343637; border: 1px solid #8c928b; }
"""
