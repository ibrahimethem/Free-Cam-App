import math

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                               QDoubleSpinBox, QCheckBox, QFrame, QStyle,
                               QStyleOptionSlider)


GROUPS = {
    "exposure": {"title": "Exposure", "mode": "exposureAuto", "manual": "manualExposure", "auto": "autoExposure",
                 "fields": [("iso", "ISO", "", 0), ("shutterMs", "Shutter speed", "", 3)]},
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


def shutter_text(milliseconds):
    if milliseconds <= 0 or not math.isfinite(milliseconds):
        return "—"
    if milliseconds >= 1000:
        return f"{milliseconds / 1000:g} s"
    denominator = 1000 / milliseconds
    nearest = round(denominator)
    if abs(denominator - nearest) <= denominator * 0.001:
        return f"1/{nearest} s"
    return f"1/{denominator:.2f} s"


class ShutterSpinBox(QDoubleSpinBox):
    """Edit seconds/fractions while retaining milliseconds for camera commands."""

    def textFromValue(self, value):
        return shutter_text(value)

    def valueFromText(self, text):
        value = text.strip().lower().removesuffix("s").strip()
        if "/" in value:
            numerator, denominator = value.split("/")
            return 1000 * float(numerator) / float(denominator)
        return 1000 * float(value)

    def validate(self, text, position):
        value = text.strip().lower().removesuffix("s").strip()
        if value in ("", ".") or value.endswith(("/", "/.")):
            state = QValidator.State.Intermediate
        else:
            try:
                milliseconds = self.valueFromText(text)
                if not math.isfinite(milliseconds) or milliseconds <= 0:
                    state = QValidator.State.Invalid
                elif self.minimum() <= milliseconds <= self.maximum():
                    state = QValidator.State.Acceptable
                else:
                    state = QValidator.State.Intermediate
            except (ValueError, ZeroDivisionError):
                state = QValidator.State.Invalid
        return state, text, position


class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            handle = self.style().subControlRect(
                QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
            if not handle.contains(event.position().toPoint()):
                groove = self.style().subControlRect(
                    QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self)
                horizontal = self.orientation() == Qt.Horizontal
                start = groove.x() if horizontal else groove.y()
                length = groove.width() if horizontal else groove.height()
                handle_length = handle.width() if horizontal else handle.height()
                position = event.position().x() if horizontal else event.position().y()
                span = max(0, length - handle_length)
                offset = min(span, max(0, round(position - start - handle_length / 2)))
                self.setValue(QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(), offset, span, option.upsideDown))
        # Let Qt retain its normal handle dragging and keyboard behavior.
        super().mousePressEvent(event)


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
        self.spin = ShutterSpinBox() if name == "shutterMs" else QDoubleSpinBox()
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(suffix)
        self.spin.setKeyboardTracking(False)
        self.spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin.setMinimumHeight(28)
        self.spin.setAccessibleName(title)
        row.addWidget(self.spin)
        layout.addLayout(row)
        self.slider = ClickableSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setAccessibleName(title + " slider")
        layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self.from_slider)
        self.spin.valueChanged.connect(self.from_spin)
        if name == "shutterMs":
            self.spin.setToolTip("Enter shutter speed as 1/125 or seconds as 0.5. Longer exposures can lower FPS.")
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
        self.updating = False
        self.send_timer = QTimer(self)
        self.send_timer.setSingleShot(True)
        self.send_timer.setInterval(80)
        self.send_timer.timeout.connect(self.submit)
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
            parameter.spin.valueChanged.connect(self.schedule_submit)
            layout.addWidget(parameter)
        self.reading = label("Waiting for camera")
        layout.addWidget(self.reading)
        self.setEnabled(False)

    def update_camera(self, camera, initialize=False):
        self.camera = camera
        caps = camera["capabilities"]
        self.setEnabled(caps[self.definition["manual"]] or caps.get(self.definition.get("auto"), False))
        if initialize:
            self.send_timer.stop()
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
            formatted = shutter_text(value) if name == "shutterMs" else f"{value:.{decimals}f}{suffix}"
            parts.append(f"{title} {formatted}")
        mode = " · auto" if self.auto and camera["current"][self.definition["mode"]] else ""
        self.reading.setText("Live: " + " · ".join(parts) + mode)

    def seed(self):
        if not self.camera:
            return
        self.updating = True
        for name, parameter in self.parameters.items():
            bounds = self.camera["capabilities"][name]
            parameter.set_limits(bounds["min"], bounds["max"], self.camera["current"][name])
        self.updating = False

    def mode_changed(self, automatic):
        if not automatic:
            self.seed()
        self.enable_parameters()
        self.send_timer.stop()
        self.submit()

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

    def set_settings(self, settings):
        self.send_timer.stop()
        self.updating = True
        if self.auto and self.definition["mode"] in settings:
            self.auto.blockSignals(True)
            self.auto.setChecked(bool(settings[self.definition["mode"]]))
            self.auto.blockSignals(False)
        for name, parameter in self.parameters.items():
            if name in settings:
                parameter.spin.setValue(float(settings[name]))
        self.enable_parameters()
        self.updating = False

    def schedule_submit(self, *_):
        # Throttle rather than debounce: dragging sends the latest value every
        # 80 ms, including the final value, without flooding the camera queue.
        if not self.updating and self.isEnabled() and not self.send_timer.isActive():
            self.send_timer.start()

    def submit(self):
        self.send_timer.stop()
        if not self.updating and self.isEnabled() and self.camera:
            self.requested.emit(self.settings())
