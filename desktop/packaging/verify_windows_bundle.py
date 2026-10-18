"""Audit native payload and product icon without installing/starting a camera."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]


def ico_payloads(path):
    data = path.read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', data)
    if reserved or kind != 1 or not count:
        raise ValueError('Not a Windows product icon')
    payloads = []
    for i in range(count):
        size, offset = struct.unpack_from('<II', data, 6 + i * 16 + 8)
        payload = data[offset:offset + size]
        if len(payload) != size:
            raise ValueError('Truncated icon payload')
        payloads.append(payload)
    return payloads


def verify_icon(executable, icon):
    import pefile
    expected = set(ico_payloads(icon))
    pe = pefile.PE(str(executable))
    try:
        resources = next(entry for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries if entry.id == 3)
        actual = {pe.get_data(language.data.struct.OffsetToData, language.data.struct.Size)
                  for entry in resources.directory.entries for language in entry.directory.entries}
        if not expected <= actual:
            raise RuntimeError('Executable does not contain all generated product icon sizes')
    finally:
        pe.close()


def known_dll(path):
    name = path.name.lower()
    if name in {'python3.dll', 'python313.dll', 'libcrypto-3-x64.dll', 'libssl-3-x64.dll',
                'libffi-8.dll', 'nosubcamera.dll', 'pyside6.abi3.dll', 'shiboken6.abi3.dll'}:
        return True
    if re.fullmatch(r'(?:vcruntime|msvcp)140(?:_\d+)?\.dll', name):
        return True
    if name in {f'qt6{module}.dll' for module in ('core', 'gui', 'widgets', 'network', 'svg')}:
        return True
    return name in {f'{module}.dll' for module in (
        'qoffscreen', 'qdirect2d', 'qwindows', 'qminimal', 'qmodernwindowsstyle',
        'qcertonlybackend', 'qschannelbackend', 'qsvgicon', 'qico', 'qicns', 'qjpeg',
        'qtga', 'qwebp', 'qgif', 'qsvg', 'qtiff', 'qwbmp', 'qtuiotouchplugin', 'qnetworklistmanager')}


def main():
    app = ROOT / 'dist/FreeCam'
    from runtime_policy import include_windows_binary
    dlls = sorted(app.rglob('*.dll'))
    for path in dlls:
        if not known_dll(path) or not include_windows_binary(path.as_posix()):
            raise RuntimeError('Unreviewed native library: ' + path.relative_to(app).as_posix())
    if any(path.name == 'PIL' for path in app.rglob('*')):
        raise RuntimeError('Build-only Pillow unexpectedly bundled')
    for name in ('inventory.json', 'Python-Windows-LICENSE.txt', 'WINDOWS-SOURCES.md'):
        if not (app / '_internal/licenses/runtime' / name).is_file():
            raise RuntimeError('Missing runtime notice: ' + name)
    executable = app / 'FreeCam.exe'
    verify_icon(executable, ROOT / 'build/branding/NoSubStudio.ico')
    with executable.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'product_icon_verified': True, 'app_sha256': digest, 'native_files': []}
    for path in sorted([*dlls, *app.rglob('*.pyd')]):
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        report['native_files'].append({'path': path.relative_to(app).as_posix(), 'sha256': digest})
    (ROOT / 'build/windows-bundle-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Native library allowlist, runtime notices and embedded mobile-derived EXE icon verified.')


if __name__ == '__main__':
    main()
