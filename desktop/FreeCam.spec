# Build on Windows for .exe; build on macOS for .app.
from pathlib import Path
import os
import sys

root = Path(SPECPATH).parent
version = (root / 'desktop/VERSION').read_text().strip()
brand = root / 'build/branding'
signing_identity = os.environ.get('NOSUB_CODESIGN_IDENTITY') or None
credential_backend = ('keyring.backends.macOS' if sys.platform == 'darwin'
                      else 'keyring.backends.Windows' if sys.platform == 'win32' else None)
windows_camera = root / 'build' / 'native-camera-windows'
camera_binaries = []
camera_data = [(str(root / 'ios/FreeCam/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png'), 'assets')]
camera_data.extend([(str(root / 'LICENSE'), 'licenses'),
                    (str(root / 'THIRD_PARTY_NOTICES.md'), 'licenses')])
if sys.platform == 'win32' and (windows_camera / 'Release' / 'NoSubCamera.dll').is_file():
    for name in ('NoSubCamera.dll', 'NoSubCameraSetup.exe'):
        path = windows_camera / 'Release' / name
        if not path.is_file():
            raise RuntimeError('Incomplete native camera build: ' + name)
        camera_binaries.append((str(path), 'native-camera'))
    camera_data.append((str(windows_camera / 'licenses'), 'native-camera/licenses'))
a = Analysis([str(root / 'desktop' / 'app.py')],
             pathex=[str(root / 'receiver'), str(root / 'desktop')],
             binaries=camera_binaries, datas=camera_data, hiddenimports=(['PySide6.QtMultimedia'] if sys.platform == 'darwin' else []) +
                                                  ([credential_backend] if credential_backend else []),
             hookspath=[], hooksconfig={}, runtime_hooks=[str(root / 'desktop' / 'diagnostics.py')],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick', 'tkinter'] +
                      (['PySide6.QtMultimedia'] if sys.platform != 'darwin' else []), noarchive=False)
if sys.platform == 'win32':
    # Qt 6.12 uses the Windows ICU API (unsuffixed exports). The bundled development
    # runtime puts a different ICU DLL on PATH; do not let it shadow the OS DLL.
    a.binaries = [entry for entry in a.binaries
                  if Path(entry[0]).name.lower() not in ('icuuc.dll', 'icudt78.dll')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='FreeCam',
          icon=str(brand / 'NoSubStudio.ico') if sys.platform == 'win32' else None,
          version=str(brand / 'windows-version.txt') if sys.platform == 'win32' else None,
          codesign_identity=signing_identity,
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FreeCam')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='FreeCam.app', icon=str(brand / 'NoSubStudio.icns'),
                 bundle_identifier='com.ethem.nosubcam.desktop',
                 codesign_identity=signing_identity,
                 info_plist={'CFBundleDisplayName': 'NoSub Studio',
                             'CFBundleName': 'NoSub Studio',
                             'CFBundleShortVersionString': version,
                             'CFBundleVersion': version,
                             'LSMinimumSystemVersion': '14.4',
                             'NSCameraUsageDescription': 'NoSub Studio previews the camera you select, including your iPhone through Continuity Camera.',
                             'NSCameraUseContinuityCameraDeviceType': True,
                             'NSSystemExtensionUsageDescription':
                             'NoSub Camera makes your connected iPhone available as a webcam without OBS.',
                             'NSLocalNetworkUsageDescription':
                             'NoSub Studio receives video directly from NoSub Cam on your local network.'})
