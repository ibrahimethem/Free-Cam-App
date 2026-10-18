# NoSub Studio macOS: third-party components and modification

NoSub's MIT license applies only to original project code. Qt, PySide6 and
Shiboken are used under LGPLv3; their bundled dependencies retain their own
licenses. Copyright notices, license texts and Qt attribution records are in
`Contents/Resources/licenses/runtime` inside the app (Finder: Show Package
Contents). Qt/PySide are dynamically linked, not statically incorporated into
the application's source.

The matching `NoSub-Studio-<version>-Third-Party-Sources.zip` is provided at no
charge beside the DMG at https://github.com/ibrahimethem/Free-Cam-App/releases.
It contains the unmodified official Qt 6.12.0 source modules used by this Mac
package and pyside-setup 6.12.0 (including Shiboken), with SHA-256 hashes in
inventory.json. NoSub makes no modifications to those upstream sources. Their
included CMake/build documentation and license directories are preserved.

Application source and build scripts are available from the same release's
source tag at https://github.com/ibrahimethem/Free-Cam-App. To modify or replace
the LGPL components, build the desired Qt modules and PySide/Shiboken using
their included instructions, install those builds into the project's Python
environment, and run `python desktop/build.py`. See desktop/requirements-build.txt
and docs/RELEASING.md for the build dependencies and packaging commands. To use
a different dependency version, update the source pins and notices collector
accordingly; this gate is not a restriction on modifying the software.

Modified Python/Qt components can also be used directly from source with
`python desktop/app.py`. Replacing files in an already signed .app invalidates
Apple's signature; use a locally rebuilt app, or re-sign your modified app and
changed nested code with your own identity/ad-hoc signature as appropriate.
The optional Apple camera system extension requires your own Apple-authorized
Developer ID/provisioning configuration for a modified host/extension; it is
not required for receiving/previewing iPhone video. No NoSub secret key, server
permission or activation is required to run the application source. This
distribution does not prohibit modification or reverse engineering for
debugging modifications to the LGPL libraries. No warranty is provided.

Python's license and bundled notices, the PyInstaller bootloader license and
exception, and licenses of the other Python packages and native runtime
libraries are included in the app. Official additional upstream sources:

- Python: https://www.python.org/downloads/source/
- OpenSSL: https://openssl-library.org/source/
- mpdecimal: https://www.bytereef.org/mpdecimal/download.html
- liblzma (XZ): https://tukaani.org/xz/
- qrcode: https://github.com/lincolnloop/python-qrcode
- keyring: https://github.com/jaraco/keyring
- jaraco classes/context/functools: https://github.com/jaraco
- more-itertools: https://github.com/more-itertools/more-itertools
- packaging: https://github.com/pypa/packaging
- setuptools: https://github.com/pypa/setuptools
- PyInstaller: https://github.com/pyinstaller/pyinstaller

This Mac package omits the unused Qt Virtual Keyboard, Qt QML/Quick, FFmpeg
backend and Pillow. Its native camera capture uses Apple's AVFoundation backend.
No Windows dependency audit or signing approval is implied by this inventory.
