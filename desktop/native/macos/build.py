"""Compile native components only; never register or install a system extension.

Default: compile both Mac architectures. --app embeds the unsigned build into a
PyInstaller .app for subsequent provisioning, inside-out signing and notarization.
"""
import argparse
import platform
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def build(output, architectures):
    output.mkdir(parents=True, exist_ok=True)
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    extension = output / "com.ethem.nosubcam.desktop.camera.systemextension"
    executables = extension / "Contents" / "MacOS"
    executables.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "Info.plist", extension / "Contents" / "Info.plist")
    for name, sources in {
        "NoSubCameraExtension": ["FrameFormat.swift", "CameraProvider.swift", "extension/main.swift"],
        "NoSubCameraControl": ["controller/main.swift"],
        "libNoSubCamera.dylib": ["FrameFormat.swift", "controller/Bridge.swift", "controller/CameraOutput.swift"],
    }.items():
        slices = []
        for architecture in architectures:
            target = output / f"{name}-{architecture}"
            subprocess.run(["xcrun", "swiftc", "-O", "-sdk", sdk,
                "-target", f"{architecture}-apple-macosx12.3",
                "-module-cache-path", str(output / "ModuleCache"),
                *(["-emit-library", "-Xlinker", "-install_name", "-Xlinker", "@rpath/libNoSubCamera.dylib"]
                  if name.endswith(".dylib") else []),
                *[str(HERE / source) for source in sources], "-o", str(target)], check=True)
            slices.append(str(target))
        binary = executables / name if name == "NoSubCameraExtension" else output / name
        subprocess.run(["xcrun", "lipo", "-create", *slices, "-output", str(binary)], check=True)
        if name.endswith(".dylib"):
            symbols = subprocess.check_output(["xcrun", "nm", "-gU", str(binary)], text=True)
            for symbol in ("nosub_camera_request", "nosub_camera_output_start",
                           "nosub_camera_output_send", "nosub_camera_output_stop", "nosub_camera_activity",
                           "nosub_camera_available"):
                if f"_{symbol}" not in symbols:
                    raise RuntimeError(f"Native bridge export missing: {symbol}")
    return extension


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "native-camera")
    parser.add_argument("--current-arch", action="store_true", help="Faster compile check, not a universal release")
    parser.add_argument("--app", type=Path, help="Embed in an existing .app (invalidates its signature)")
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("This target requires macOS and Xcode")
    if args.app and not (args.app / "Contents" / "MacOS" / "FreeCam").is_file():
        parser.error("--app must be a built NoSub Studio .app")
    extension = build(args.output.resolve(), [platform.machine()] if args.current_arch else ["arm64", "x86_64"])
    if args.app:
        destination = args.app / "Contents" / "Library" / "SystemExtensions" / extension.name
        shutil.copytree(extension, destination, dirs_exist_ok=True)
        shutil.copy2(args.output / "NoSubCameraControl", args.app / "Contents" / "MacOS")
        shutil.copy2(args.output / "libNoSubCamera.dylib", args.app / "Contents" / "Frameworks")
    print("Native components compiled. NOT signed, installed, notarized or release-ready.")


if __name__ == "__main__":
    main()
