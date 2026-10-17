"""Package the desktop app for the current OS, without requiring Python to run it."""
import argparse
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--native-camera", action="store_true",
                    help="Embed the macOS camera components; still requires release signing")
args = parser.parse_args()
if args.native_camera and sys.platform != "darwin":
    parser.error("Native camera packaging is currently implemented only for macOS")
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                "--distpath", str(root / "dist"), "--workpath", str(root / "build"),
                str(root / "desktop" / "FreeCam.spec")], cwd=root, check=True)
if args.native_camera:
    subprocess.run([sys.executable, str(root / "desktop/native/macos/build.py"),
                    "--app", str(root / "dist/FreeCam.app")], check=True)
    print("Camera-enabled app staged UNSIGNED. Provision, sign and notarize before installation.")
