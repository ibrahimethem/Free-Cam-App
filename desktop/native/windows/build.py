"""Build NoSub's x64 Windows 11 camera; never install, elevate or publish it."""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def cmake_executable():
    found = shutil.which("cmake")
    if found:
        return found
    vswhere = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if vswhere.is_file():
        found = subprocess.check_output([str(vswhere), "-latest", "-products", "*", "-find",
                                         "Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe"], text=True).strip()
        if found and Path(found).is_file():
            return found
    raise RuntimeError("Install Visual Studio 2022 Desktop development with C++, CMake tools and Windows 11 SDK (22621+).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/native-camera-windows")
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        parser.error("The initial camera build requires x64 Windows 11, not macOS, ARM64 or 32-bit Python.")
    # Compiling on a Windows Server CI host is fine. Only runtime camera use
    # requires Windows 11; controller_path enforces that before loading the DLL.
    cmake = cmake_executable()
    subprocess.run([cmake, "-S", str(HERE), "-B", str(args.output), "-G", "Visual Studio 17 2022", "-A", "x64",
                    f"-DPython3_EXECUTABLE={sys.executable}"], check=True)
    subprocess.run([cmake, "--build", str(args.output), "--config", "Release", "--parallel"], check=True)
    print("Native camera compiled, NOT installed or signed. Use Install camera inside NoSub Studio for explicit UAC setup.")


if __name__ == "__main__":
    main()
