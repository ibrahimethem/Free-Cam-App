# NoSub Studio on Windows

This is the current source snapshot, not a prebuilt Windows executable.

1. Extract the entire ZIP to a local folder.
2. Install 64-bit Python 3.13 from https://www.python.org/downloads/windows/ if needed.
   Enable the Python launcher or the option to add Python to PATH.
3. Double-click `Run-Windows.cmd`. The first run downloads the dependencies and
   creates a Windows environment inside this folder. Internet is needed for setup.
4. Leave the console open. Errors will remain visible there.

## Wi-Fi test

- Connect the PC and iPhone to the same private Wi-Fi network.
- Allow NoSub Studio/Python through Windows Firewall on the private network if prompted.
- Select Wi-Fi in NoSub Studio and scan its pairing QR using NoSub Cam on iPhone.
- Start streaming and check the preview, FPS, resolution selection, and live sensor sliders.
- Click anywhere on a slider to move its value directly to that position.

## Direct USB test

Install Apple Devices from the Microsoft Store if the Apple USB service is unavailable:
https://apps.microsoft.com/detail/9NP83LWLPZ9K

Connect the iPhone using a data cable, unlock it, and trust the PC. Choose Direct USB
on both apps, pair using the QR, start streaming on iPhone, and connect the selected
device in NoSub Studio. Continuity Camera is only available on macOS.

## Optional portable EXE build

From PowerShell in the extracted folder, after running the launcher once:

```powershell
& .\.venv-windows\Scripts\python.exe -m pip install -r desktop/requirements-build.txt
& .\.venv-windows\Scripts\python.exe desktop/build.py
```

Open `dist/FreeCam/FreeCam.exe`. Copy the whole `dist/FreeCam` folder when moving
the executable; `_internal` must remain beside it. This development package is unsigned.
