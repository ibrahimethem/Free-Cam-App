# Third-party software

The root MIT license covers original NoSub project material, not third-party
components. Upstream copyright notices, license conditions and any applicable
source/relinking obligations remain in force. This inventory is not a claim
that the final distribution compliance audit is complete.

## Windows camera implementation

- Microsoft Windows-Camera sample, MIT, pinned commit
  `626f8b19c5f367602f2e89c6b314573d3776c9df`:
  https://github.com/microsoft/Windows-Camera
- Microsoft Windows Implementation Library (WIL), MIT, pinned commit
  `f6f3069ab39fb19c1f89fa5f2d3aa8a1118ace43`:
  https://github.com/microsoft/wil

`desktop/native/windows/prepare_source.py` explicitly transforms selected files
from the pinned camera sample. The resulting camera DLL is derived from that
sample; it must not be represented as wholly original NoSub code. The build
copies both upstream MIT licenses into the package and protected camera folder.
Foundation approval for signing this derived DLL must be confirmed separately.

## Desktop runtime inventory

Python, PySide6/Qt, Shiboken, qrcode, keyring and its transitive dependencies,
plus platform-specific libraries collected by PyInstaller, retain their own
licenses. Mac packages also collect Qt Multimedia and FFmpeg libraries.
PyInstaller has its own license and bootloader exception. NoSub's MIT license
does not replace any of these licenses or authorize relicensing their code.

Before public binary distribution, enumerate the exact collected libraries,
include their required notices/licenses, and document corresponding source and
replacement/relinking provisions where applicable. Do not sign upstream runtime
DLLs under the NoSub/SignPath project certificate merely because they are bundled.
