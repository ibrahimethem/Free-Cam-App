"""Sign a staged NoSub Studio app, validate it, and create a notarization archive.

No credential values are accepted/saved by this script. The Developer ID private
key stays in Keychain. Notarization is a separate explicit Fastlane/Ruby step.
"""
import argparse
import datetime
import hashlib
import plistlib
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TEAM = "G478PYWXZ4"
BUNDLE = "com.ethem.nosubcam.desktop"


def run(*arguments):
    subprocess.run([str(argument) for argument in arguments], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=ROOT / "dist/FreeCam.app")
    parser.add_argument("--profile", type=Path, default=ROOT / "build/native-camera/NoSubStudio.provisionprofile")
    parser.add_argument("--identity", required=True, help="Developer ID certificate SHA-1 (not a private key)")
    args = parser.parse_args()
    app = args.app.resolve()
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if info.get("CFBundleIdentifier") != BUNDLE:
        parser.error("Refusing to sign a different app bundle")
    profile = plistlib.loads(subprocess.check_output(["security", "cms", "-D", "-i", str(args.profile)]))
    entitlements = profile["Entitlements"]
    if (entitlements.get("com.apple.application-identifier") != f"{TEAM}.{BUNDLE}"
            or not entitlements.get("com.apple.developer.system-extension.install")
            or TEAM not in profile.get("TeamIdentifier", [])
            or profile["ExpirationDate"] <= datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)):
        parser.error("Provisioning profile does not authorize this host and system extension")
    if not any(hashlib.sha1(certificate).hexdigest().upper() == args.identity.upper()
               for certificate in profile.get("DeveloperCertificates", [])):
        parser.error("Provisioning profile does not include the selected certificate")
    shutil.copy2(args.profile, app / "Contents/embedded.provisionprofile")
    extension = app / "Contents/Library/SystemExtensions/com.ethem.nosubcam.desktop.camera.systemextension"
    library = app / "Contents/Frameworks/libNoSubCamera.dylib"
    controller = app / "Contents/MacOS/NoSubCameraControl"
    for path in (extension, library, controller):
        if not path.exists():
            parser.error(f"Missing native component: {path.name}")

    def sign(path, entitlement_file=None):
        command = ["codesign", "--force", "--sign", args.identity, "--options", "runtime", "--timestamp"]
        if entitlement_file:
            command.extend(["--entitlements", str(entitlement_file)])
        run(*command, path)

    sign(library)
    sign(controller)
    sign(extension, HERE / "CameraExtension.entitlements")
    sign(app, HERE / "CameraHost.entitlements")
    run("codesign", "--verify", "--deep", "--strict", app)
    output = ROOT / "build/native-camera/NoSub-Studio-notarization.zip"
    run("ditto", "-c", "-k", "--keepParent", app, output)
    print("Signed and verified. Submit the archive for notarization before distributing.")


if __name__ == "__main__":
    main()
