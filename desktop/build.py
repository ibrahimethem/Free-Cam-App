"""Package the desktop app for the current OS, without requiring Python to run it."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                "--distpath", str(root / "dist"), "--workpath", str(root / "build"),
                str(root / "desktop" / "FreeCam.spec")], cwd=root, check=True)
