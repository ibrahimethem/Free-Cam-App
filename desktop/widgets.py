import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                               QDoubleSpinBox, QCheckBox, QPushButton, QFrame)


GROUPS = {
    "exposure": {"title": "Exposure", "mode": "exposureAuto", "manual": "manualExposure", "auto": "autoExposure",
                 "fields": [("iso", "ISO", "", 0), ("shutterMs", "Shutter", " ms", 3)]},
    "wb": {"title": "White balance", "mode": "whiteBalanceAuto", "manual": "manualWhiteBalance", "auto": "autoWhiteBalance",
           "fields": [("temperature", "Temperature", " K", 0), ("tint", "Tint", "", 1)]},
    "focus": {"title": "Focus", "mode": "focusAuto", "manual": "manualFocus", "auto": "autoFocus",
              "fields": [("focus", "Lens position", "", 2)]},
    "zoom": {"title": "Zoom", "manual": "canZoom", "fields": [("zoom", "Magnification", "×", 2)]},
}


def label(text, name="muted"):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(name not in ("brand", "subtitle", "badge"))
    return widget


class Parameter(QWidget):
    def __init__(self, name, title, suffix, decimals):
        super().__init__()
        self.name = name
        self.lower, self.upper = 0.0, 1.0
        self.logarithmic = name in ("iso", "shutterMs", "zoom")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        row = QHBoxLayout()
        row.addWidget(label(title, ""))
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(suffix)
        self.spin.setKeyboardTracking(False)
        self.spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin.setMinimumHeight(28)
        self.spin.setAccessibleName(title)
        row.addWidget(self.spin)
        layout.addLayout(row)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setAccessibleName(title + " slider")
        layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self.from_slider)
        self.spin.valueChanged.connect(self.from_spin)
        if name == "shutterMs":
            self.spin.setToolTip("Exposure duration in milliseconds. Longer shutter times can lower FPS.")
        elif name == "focus":
            self.spin.setToolTip("0 = nearest, 1 = furthest. Lens position is not a distance in meters.")

    def set_limits(self, minimum, maximum, value):
        self.lower, self.upper = minimum, maximum
        # Preserve device bounds without rounding an allowed value beyond them.
        decimals = 6 if self.name == "shutterMs" else 3 if self.name in ("iso", "zoom") else self.spin.decimals()
        self.spin.setDecimals(decimals)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(1 if self.name in ("iso", "temperature") else 0.01)
        self.spin.setValue(min(max(value, minimum), maximum))
        self.from_spin(self.spin.value())

    def from_slider(self, position):
        ratio = position / 1000
        if self.logarithmic and self.lower > 0 and self.upper > self.lower:
            value = math.exp(math.log(self.lower) + ratio * math.log(self.upper / self.lower))
        else:
            value = self.lower + ratio * (self.upper - self.lower)
        self.spin.setValue(value)

    def from_spin(self, value):
        if self.upper <= self.lower:
            ratio = 0
        elif self.logarithmic and self.lower > 0:
            ratio = math.log(max(value, self.lower) / self.lower) / math.log(self.upper / self.lower)
        else:
            ratio = (value - self.lower) / (self.upper - self.lower)
        self.slider.blockSignals(True)
        self.slider.setValue(round(ratio * 1000))
        self.slider.blockSignals(False)


class ControlGroup(QFrame):
    requested = Signal(dict)

    def __init__(self, definition):
        super().__init__()
        self.definition = definition
        self.camera = None
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        layout.addWidget(label(definition["title"], "title"))
        self.auto = None
        if "mode" in definition:
            self.auto = QCheckBox("Automatic")
            self.auto.setAccessibleName("Automatic " + definition["title"].lower())
            self.auto.toggled.connect(self.mode_changed)
            layout.addWidget(self.auto)
        self.parameters = {}
        for args in definition["fields"]:
            parameter = Parameter(*args)
            self.parameters[args[0]] = parameter
            layout.addWidget(parameter)
        self.reading = label("Waiting for camera")
        layout.addWidget(self.reading)
        self.apply = QPushButton("Apply " + definition["title"].lower())
        self.apply.setStyleSheet("QPushButton { padding: 4px 8px; }")
        self.apply.clicked.connect(self.submit)
        layout.addWidget(self.apply)
        self.setEnabled(False)

    def update_camera(self, camera, initialize=False):
        self.camera = camera
        caps = camera["capabilities"]
        self.setEnabled(caps[self.definition["manual"]] or caps.get(self.definition.get("auto"), False))
        if initialize:
            if self.auto:
                self.auto.blockSignals(True)
                self.auto.setChecked(camera["current"][self.definition["mode"]])
                self.auto.blockSignals(False)
            self.seed()
        if self.auto:
            self.auto.setEnabled(caps[self.definition["manual"]] and caps[self.definition["auto"]])
        self.enable_parameters()
        parts = []
        for name, title, suffix, decimals in self.definition["fields"]:
            value = camera["current"][name]
            parts.append(f"{title} {value:.{decimals}f}{suffix}")
        mode = " · auto" if self.auto and camera["current"][self.definition["mode"]] else ""
        self.reading.setText("Live: " + " · ".join(parts) + mode)

    def seed(self):
        if not self.camera:
            return
        for name, parameter in self.parameters.items():
            bounds = self.camera["capabilities"][name]
            parameter.set_limits(bounds["min"], bounds["max"], self.camera["current"][name])

    def mode_changed(self, automatic):
        if not automatic:
            self.seed()
        self.enable_parameters()

    def enable_parameters(self):
        if not self.camera:
            return
        manual = self.camera["capabilities"][self.definition["manual"]]
        for parameter in self.parameters.values():
            parameter.setEnabled(manual and not (self.auto and self.auto.isChecked()))

    def settings(self):
        settings = {}
        if self.auto:
            settings[self.definition["mode"]] = self.auto.isChecked()
        if not self.auto or not self.auto.isChecked():
            settings.update({name: parameter.spin.value() for name, parameter in self.parameters.items()})
        return settings

    def submit(self):
        self.requested.emit(self.settings())
