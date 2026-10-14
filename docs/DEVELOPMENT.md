# Windows and Mac development workflow

## One repository

```text
desktop/    Shared Windows/macOS Python and Qt app
ios/        Swift iPhone app, XcodeGen specification and tests
receiver/   Embedded JPEG relay and camera command validation
docs/       Development, protocol and release process
```

Change both implementations together when modifying camera messages. Windows
and macOS share source code but require builds on their respective platforms.

## First GitHub upload

Create an empty private repository named `freecam`, without an initial README,
.gitignore or license. The local repository is initialized on `main`. If Git has
no author configured, use your actual name and GitHub email/noreply address:

```sh
git config user.name "YOUR NAME"
git config user.email "YOUR GITHUB EMAIL OR NOREPLY ADDRESS"
git add .
git diff --cached --stat
git commit -m "Initialize Free Cam monorepo"
git remote add origin https://github.com/YOUR-ACCOUNT/freecam.git
git push -u origin main
```

Replace placeholders with your details. Authenticate using your Git client or
credential manager. Do not put tokens in URLs or commit credentials.

## Windows

From the project directory in PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r desktop/requirements.txt
& .\.venv\Scripts\python.exe desktop/app.py
```

Add `--demo` to preview without a phone. Real camera tests require normal mode.
The portable app is `dist/FreeCam/FreeCam.exe`; keep `_internal` beside it.

## Mac and iPhone

```sh
git clone https://github.com/YOUR-ACCOUNT/freecam.git
cd freecam
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r desktop/requirements.txt
python desktop/app.py
```

Install Xcode 26+ with the iOS 26 SDK and XcodeGen, then generate the project:

```sh
cd ios
xcodegen generate
open FreeCam.xcodeproj
```

Select your own signing team and a unique bundle identifier if needed. Choose
your iPhone, enable Developer Mode if requested, and build/run. Signing files
and Xcode user state stay on the Mac. Do not copy the Windows environment or
binaries to the Mac. Regenerate after changes to `project.yml` or source files.

## Daily synchronization

Before working on either computer:

```sh
git status
git pull --ff-only
```

Commit or otherwise save unfinished changes before pulling. Review, commit and
push small completed changes; pull on the other computer before continuing.
Avoid editing the same file concurrently on both computers. For larger work,
use a feature branch and merge through a pull request.

## First physical milestone

1. Keep the Windows desktop app open in Wi-Fi mode.
2. Build on the Mac and install the iOS app on the iPhone.
3. Use the same private network; enter the Windows address and current pairing key.
4. Confirm live video, then ISO at fixed shutter, shutter duration, focus, white
   balance, zoom and restoration of auto modes. Compare actual live readings.
5. Test supported resolutions and stop/restart/reconnect.
6. Test direct USB to Windows, then Wi-Fi/USB on Mac and Continuity Camera.

Continuity has no Free Cam manual sensor controls. Read the README and
`desktop/USB.md` for connection setup. Physical iPhone/USB and Mac validation
are pending; simulated tests do not establish physical camera behavior.

## Automated checks

With desktop dependencies installed, run from the repository root:

```sh
python -m unittest discover -s receiver -p "test_*.py"
python -m unittest discover -s desktop -p "test_*.py"
```

For headless Qt tests set `QT_QPA_PLATFORM=offscreen` for the test process. On Mac,
generate the Xcode project and run Product > Test for the FreeCam scheme on an
iOS simulator. Real camera behavior still needs a physical iPhone.
