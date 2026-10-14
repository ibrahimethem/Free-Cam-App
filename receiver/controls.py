"""Validation for the camera control protocol. Values are in sensor units."""
import math

NUMERIC = {
    "iso": ("manualExposure", "iso"),
    "shutterMs": ("manualExposure", "shutterMs"),
    "focus": ("manualFocus", "focus"),
    "temperature": ("manualWhiteBalance", "temperature"),
    "tint": ("manualWhiteBalance", "tint"),
    "zoom": ("canZoom", "zoom"),
}
MODES = {
    "exposureAuto": ("autoExposure", "manualExposure"),
    "focusAuto": ("autoFocus", "manualFocus"),
    "whiteBalanceAuto": ("autoWhiteBalance", "manualWhiteBalance"),
}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_snapshot(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a camera report")
    if not isinstance(data.get("session"), str) or not 1 <= len(data["session"]) <= 100:
        raise ValueError("Missing camera session")
    if type(data.get("appliedRevision")) is not int or data["appliedRevision"] < 0:
        raise ValueError("Invalid acknowledgement")
    if not isinstance(data.get("error"), str) or len(data["error"]) > 1000:
        raise ValueError("Invalid camera error")
    caps, current = data.get("capabilities"), data.get("current")
    if not isinstance(caps, dict) or not isinstance(current, dict):
        raise ValueError("Missing camera capabilities or readings")
    support = set(MODES.values())
    required = {item for pair in support for item in pair} | {"canZoom"}
    if any(type(caps.get(item)) is not bool for item in required):
        raise ValueError("Invalid camera support flags")
    for name in NUMERIC:
        limits = caps.get(name)
        if not isinstance(limits, dict) or not number(limits.get("min")) or not number(limits.get("max")):
            raise ValueError("Invalid camera range")
        if limits["min"] > limits["max"] or not number(current.get(name)):
            raise ValueError("Invalid camera readings")
    if any(type(current.get(name)) is not bool for name in MODES):
        raise ValueError("Invalid camera modes")
    if "resolutions" in caps:
        options = caps["resolutions"]
        if not isinstance(options, list) or not 1 <= len(options) <= 32:
            raise ValueError("Invalid camera resolutions")
        ids = set()
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("id"), str) or not 1 <= len(option["id"]) <= 50:
                raise ValueError("Invalid resolution identifier")
            if option["id"] in ids:
                raise ValueError("Duplicate resolution")
            ids.add(option["id"])
            if not isinstance(option.get("label"), str) or not 1 <= len(option["label"]) <= 100:
                raise ValueError("Invalid resolution label")
            if any(type(option.get(key)) is not int or not 1 <= option[key] <= 8192 for key in ("width", "height")):
                raise ValueError("Invalid resolution dimensions")
        if current.get("resolution") not in ids:
            raise ValueError("Current resolution is not supported")
    return data


def validate_command(patch, caps):
    if not isinstance(patch, dict) or not patch:
        raise ValueError("Expected camera settings")
    for name, value in patch.items():
        if name == "resolution":
            if not isinstance(value, str) or value not in {item["id"] for item in caps.get("resolutions", [])}:
                raise ValueError("Resolution is unsupported by this camera")
            if len(patch) != 1:
                raise ValueError("Apply resolution separately from sensor settings")
        elif name in MODES:
            if type(value) is not bool:
                raise ValueError(f"{name} must be a boolean")
            capability = MODES[name][0 if value else 1]
            if not caps[capability]:
                raise ValueError(f"{name} is unsupported by this camera")
        elif name in NUMERIC:
            capability, limits = NUMERIC[name]
            if not caps[capability]:
                raise ValueError(f"{name} is unsupported by this camera")
            if not number(value) or not caps[limits]["min"] <= value <= caps[limits]["max"]:
                raise ValueError(f"{name} is outside the camera range")
        else:
            raise ValueError(f"Unknown camera setting: {name}")
    # Every manual value must explicitly select its manual mode in the same request.
    # This prevents accidentally changing auto exposure when a desktop UI is stale.
    for mode, fields in (("exposureAuto", ("iso", "shutterMs")),
                         ("focusAuto", ("focus",)),
                         ("whiteBalanceAuto", ("temperature", "tint"))):
        if any(field in patch for field in fields) and patch.get(mode) is not False:
            raise ValueError(f"Disable {mode} when setting manual values")
        if patch.get(mode) is False and not all(field in patch for field in fields):
            raise ValueError(f"Supply all manual values for {mode}")
    return patch
