"""Build a styled drag-to-Applications DMG from an already notarized app."""
import argparse
import hashlib
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def verify_payload(image):
    """Finder customization must never mutate the signed bundle's metadata."""
    with tempfile.TemporaryDirectory(prefix='nosub-dmg-verify-') as directory:
        directory = str(Path(directory).resolve())  # macOS /var is a /private/var alias.
        result = subprocess.check_output(['hdiutil', 'attach', '-readonly', '-nobrowse',
            '-noautoopen', '-plist', '-mountpoint', directory, str(image)])
        mounts = [entry['mount-point'] for entry in plistlib.loads(result)['system-entities']
                  if 'mount-point' in entry]
        try:
            if [str(Path(mount).resolve()) for mount in mounts] != [directory]:
                raise RuntimeError('Unexpected DMG mount layout')
            root = Path(directory)
            if (root / 'Applications').readlink() != Path('/Applications'):
                raise RuntimeError('Invalid Applications shortcut')
            subprocess.run(['codesign', '--verify', '--deep', '--strict',
                            str(root / 'NoSub Studio.app')], check=True)
        finally:
            subprocess.run(['hdiutil', 'detach', directory], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=ROOT / 'dist/FreeCam.app')
    parser.add_argument('--identity', required=True, help='Local Developer ID certificate SHA-1, never a private key')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Build DMGs on macOS')
    app = args.app.resolve()
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != 'com.ethem.nosubcam.desktop':
        parser.error('Unexpected application bundle')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    subprocess.run(['xcrun', 'stapler', 'validate', str(app)], check=True)
    version = (ROOT / 'desktop/VERSION').read_text().strip()
    if info.get('CFBundleShortVersionString') != version:
        parser.error('Rebuild the app with the current desktop/VERSION')
    # Do not claim universal support just because the camera extension is universal.
    arches = subprocess.check_output(['lipo', '-archs', str(app / 'Contents/MacOS/FreeCam')], text=True).strip().split()
    architecture = {('arm64',): 'Apple-Silicon', ('x86_64',): 'Intel'}.get(tuple(arches))
    if not architecture:
        parser.error('Universal app runtime validation has not been configured')
    output = ROOT / 'dist/installers' / f'NoSub-Studio-{version}-macOS-{architecture}.dmg'
    output.parent.mkdir(parents=True, exist_ok=True)
    import dmgbuild
    dmgbuild.build_dmg(str(output), 'NoSub Studio', settings={
        'files': [(str(app), 'NoSub Studio.app'), str(ROOT / 'desktop/packaging/MAC-INSTALL.txt')],
        'symlinks': {'Applications': '/Applications'},
        'icon': str(ROOT / 'build/branding/NoSubStudio.icns'),
        'format': 'UDZO', 'filesystem': 'HFS+',
        'window_rect': ((160, 160), (660, 420)),
        'background': 'builtin-arrow',
        'icon_locations': {'NoSub Studio.app': (160, 180), 'Applications': (500, 180), 'MAC-INSTALL.txt': (330, 335)},
        'icon_size': 112, 'text_size': 14,
        # Do not set hide_extensions on the .app: that adds FinderInfo to the
        # signed bundle and invalidates strict codesign verification.
        'hide_extensions': ['MAC-INSTALL.txt'],
        'show_toolbar': False, 'show_status_bar': False,
        'default_view': 'icon-view', 'include_icon_view_settings': True,
    })
    verify_payload(output)
    subprocess.run(['codesign', '--sign', args.identity, '--timestamp', str(output)], check=True)
    subprocess.run(['hdiutil', 'verify', str(output)], check=True)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.dmg.sha256').write_text(f'{digest}  {output.name}\n')
    print('Signed DMG created. Notarize/staple this DMG before public distribution:', output)


if __name__ == '__main__':
    main()
