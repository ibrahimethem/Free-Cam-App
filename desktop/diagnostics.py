"""Optional startup diagnostics for packaged development builds."""
import os
import sys

path = os.environ.get("FREECAM_DIAGNOSTICS")
if path:
    stream = open(path, "w", encoding="utf-8", buffering=1)
    sys.stdout = stream
    sys.stderr = stream
