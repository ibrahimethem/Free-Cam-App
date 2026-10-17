"""Package the desktop app for the current OS, without requiring Python to run it."""
import argparse
import subprocess
import sys
from pathlib import Path
from branding import build_icons

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--native-camera", action="store_true",
                    help="Build/embed native macOS or Windows 11 camera components; release signing is separate")
args = parser.parse_args()
build_icons(root / "build/branding")
if args.native_camera and sys.platform not in ("darwin", "win32"):
    parser.error("Native camera packaging requires macOS or Windows 11")
if args.native_camera and sys.platform == "win32":
    subprocess.run([sys.executable, str(root / "desktop/native/windows/build.py")], check=True)
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                "--distpath", str(root / "dist"), "--workpath", str(root / "build"),
                str(root / "desktop" / "FreeCam.spec")], cwd=root, check=True)
if args.native_camera and sys.platform == "darwin":
    subprocess.run([sys.executable, str(root / "desktop/native/macos/build.py"),
                    "--app", str(root / "dist/FreeCam.app")], check=True)
    print("Camera-enabled app staged UNSIGNED. Provision, sign and notarize before installation.")
