# Build on Windows for .exe; build on macOS for .app.
from pathlib import Path
import sys

root = Path(SPECPATH).parent
a = Analysis([str(root / 'desktop' / 'app.py')],
             pathex=[str(root / 'receiver'), str(root / 'desktop')],
             binaries=[], datas=[], hiddenimports=['PySide6.QtMultimedia'] if sys.platform == 'darwin' else [],
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
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FreeCam')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='FreeCam.app', icon=None,
                 bundle_identifier='com.freecam.desktop',
                 info_plist={'CFBundleDisplayName': 'NoSub Studio',
                             'NSCameraUsageDescription': 'NoSub Studio previews the camera you select, including your iPhone through Continuity Camera.',
                             'NSCameraUseContinuityCameraDeviceType': True,
                             'NSLocalNetworkUsageDescription':
                             'NoSub Studio receives video directly from NoSub Cam on your local network.'})
