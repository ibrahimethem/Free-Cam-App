# Build outputs and releases

## Installer commands (current)

The desktop product is **NoSub Studio**; the phone app is **NoSub Cam**. Both
use the existing product artwork. `desktop/VERSION` controls desktop versions.
Build outputs, credentials and certificates must never be committed.

### macOS

Install `desktop/requirements-build.txt`, then use the existing local Developer
ID certificate and provisioning profile (private key stays in Keychain):

```sh
NOSUB_CODESIGN_IDENTITY=<certificate-sha1> python desktop/build.py --native-camera
python desktop/native/macos/release.py --identity <certificate-sha1>
bundle exec ruby fastlane/mac_notarize.rb
python desktop/packaging/package_macos.py --identity <certificate-sha1>
bundle exec ruby fastlane/mac_notarize.rb --dmg dist/installers/NoSub-Studio-1.0.0-macOS-Apple-Silicon.dmg
```

The DMG builder verifies the app signature, stapled ticket, version and main
executable architecture. It supplies a styled drag-to-Applications window,
product icon, instructions and Developer ID signature. Notarize/staple the
outer DMG too; its SHA-256 sidecar is regenerated after stapling.

`desktop/build.py` first collects pinned upstream Qt/PySide source archives and
runtime license notices. Publish the generated Third-Party-Sources.zip and its
checksum **alongside** the Mac DMG, not merely a link to upstream. The app embeds
notices and modification/rebuild instructions. The Mac runtime excludes unused
Qt Virtual Keyboard, QML/Quick, FFmpeg and Pillow. After any dependency upgrade,
review the pins, actual bundle contents and native linkage before publishing.

Current target: **Apple Silicon, macOS 14.4+** (bundled Qt minimum). The camera extension is universal,
but the Python/Qt runtime is not. Intel and minimum-OS runtime testing remain
release gates. Quit the installed app before replacing it; closing the window
only hides it. Removal: Remove camera in-app, approve removal, Quit, Trash app.

### Windows 11 x64

Requires Visual Studio C++ tools, Windows 11 SDK, Python 3.13 x64 and Inno Setup
6.4+ on the Windows builder. No installation/elevation happens during CI builds.

```powershell
python -m pip install -r desktop/requirements-build.txt
python desktop/build.py --native-camera
python desktop/packaging/package_windows.py --allow-unsigned
```

Installer and checksum appear in `dist/installers/`. CI uploads the portable app
and installer as separate **test artifacts**, not public Releases. Downloading
artifacts requires GitHub sign-in.

The installer provides administrator-approved Program Files installation, a
Start menu shortcut, optional desktop shortcut, optional native camera, product
icons/version metadata, stable upgrade identity and Windows Installed Apps
uninstallation. The host is launched as the original non-elevated user. Camera
DLL and Microsoft MIT notices go in the same protected location as in-app setup.
Only owned files/registry values are removed; presets and secure pairing remain.
No startup task, firewall exception, Apple driver or security bypass is added.

Quit the app from its notification-area menu before upgrade/removal and close
video apps holding the camera DLL. The installer checks an application mutex;
old builds without that guard and other users' sessions must be quit manually.
Apple Devices/USB drivers remain a separate user-controlled prerequisite.

**Windows Authenticode signing is not configured.** Production mode refuses to
create an unsigned release. Obtain a signing identity/service, then integrate
signing of app, DLL, setup helper, uninstaller and outer installer. Never commit
a PFX/password/service token. Do not disable Windows security to test packages.

The owner approved an explicitly unsigned public beta after SignPath declined
the initial eligibility application. Prepare it with:

```powershell
python desktop/build.py --native-camera
python desktop/packaging/verify_windows_bundle.py
python desktop/packaging/package_windows.py --allow-unsigned --public-beta
```

Or dispatch `windows-camera.yml` with `public_beta=true`, `request_signing=false`.
This does not publish anything. The output filename contains `Public-Beta-1`;
the installer displays the unsigned warning. The build includes Windows runtime
notices, a matching Windows source archive, and a native-file hash/icon report.
The verifier checks the embedded EXE icon against the ICO generated from the
mobile artwork. Unknown native DLLs fail the audit for review. Unused Mesa,
Qt OpenSSL backend/libraries and Windows 11's built-in UCRT/API shims are excluded.
Python's own OpenSSL x64 libraries remain, with official binary license notices.

Keep beta and signed production publication distinct. Do not enable the site's
signed Windows `published` flag for this beta, overwrite the stable Mac assets,
or claim Store certification. A public beta needs its own release/channel label,
checksum, matching sources and honest testing limitations. Later signing can
retain the stable installer AppId and settings/pairing locations.

### Remaining publication gates

- Clean install, first launch, camera approval/output, Wi-Fi/USB, background and
  reopen, repeat install, upgrade with saved settings, uninstall on both OSes.
- Standard-user Windows installation with UAC; full and receiver-only choices;
  verify the host is non-elevated. Open video apps must not cause silent damage.
- Inspect Finder/Explorer, Dock/taskbar and shortcut icons. Verify final package
  signatures, tickets and download checksums.
- Complete bundled dependency license/source-offer audit (Qt/PySide, FFmpeg,
  Python and transitive packages). Microsoft notices alone are not a complete
  desktop distribution compliance audit.
- Review support/legal pages, requirements, release notes and download URLs.

Only then publish versioned GitHub Release assets from one reviewed source
commit and update website downloads. Do not auto-submit iOS App Review.

Website activation: `site/download/releases.json` holds the version and a
`published` flag for each desktop platform. Only set a flag to true after the
corresponding signed asset and `.sha256` exist in public release `v<version>`.
The download page constructs the filenames used above; Windows must use the
production `NoSub-Studio-<version>-Windows-x64-Setup.exe`, never a TEST artifact.
Commit/push the config to deploy Pages. Until then the page shows Coming soon;
its Releases link stays usable without linking to nonexistent package files.

Native camera implementation notes: [desktop/native/README.md](../desktop/native/README.md).
Physical test checklist: [DEVELOPMENT.md](DEVELOPMENT.md). Publish only after
acceptance, using a reviewed source tag and explicit platform/architecture labels.
