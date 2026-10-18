# NoSub Studio Windows: source and third-party notices

Original NoSub code is MIT licensed. Qt/PySide/Shiboken are dynamically linked
under LGPLv3. Their dependencies keep their own licenses. Notices, license texts
and Qt attribution records are installed at `_internal/licenses/runtime` under
NoSub Studio; Microsoft camera/WIL notices also accompany the protected camera
DLL. The environment inventory includes some build-only tools conservatively.

Matching, unmodified Qt/PySide/Shiboken 6.12.0 sources are in the Windows
Third-Party-Sources.zip asset beside the installer on
https://github.com/ibrahimethem/Free-Cam-App/releases. That archive also includes
matching Python and PyInstaller sources. inventory.json identifies versions,
upstream source URLs and SHA-256 hashes. This source access is free and does
not require a GitHub account. No FFmpeg, Qt Virtual Keyboard, QML/Quick, Pillow
runtime or optional Mesa software-OpenGL renderer is included in this package.

To modify/replace the LGPL components, build Qt and PySide/Shiboken from those
archives using their included CMake/build instructions, install your builds in
the project's Python environment, and run the app from source with
`python desktop/app.py`, or rebuild it with `python desktop/build.py`. The
package's `_internal/PySide6` and `_internal/shiboken6` contain dynamically loaded
libraries, not statically linked copies in NoSub's source. Compatible replacement
libraries can be used there. Updating dependency versions requires updating the
notices/source pins, not permission from NoSub. Modification and reverse
engineering to debug LGPL library modifications are not prohibited.

Application source and packaging instructions are in this release's source tag:
https://github.com/ibrahimethem/Free-Cam-App. Build requirements are listed in
desktop/requirements-build.txt; native Windows camera compilation requires
Visual Studio C++ tools/CMake and Windows 11 SDK. The camera's Microsoft-derived
source transformation and exact upstream commits are in desktop/native/windows.
Building/running the host does not require a secret signing key or activation.
Replacing the separate camera DLL under Program Files requires administrator
permission; do not weaken its permissions or Windows security policy.

Python's official Windows binary license contains its bundled Microsoft CRT,
OpenSSL, libffi and bzip2 notices. Additional Python notices, PyInstaller license
and bootloader exception and Python-package notices are preserved. Microsoft
runtime components are proprietary redistributables, not MIT NoSub code.
No warranty is provided. Unsigned beta status does not waive any license terms.
