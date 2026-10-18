"""Prepare Windows runtime notices and matching sources; never sign or publish."""
import hashlib
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import shutil
import re
import ssl
import sys
import tarfile
import urllib.request
import zipfile

from collect_macos_licenses import ROOT, QT_VERSION, SOURCES, digest, is_notice, source_url

MODULES = ('qtbase', 'qtsvg', 'qtimageformats', 'qttranslations', 'pyside-setup')


def validate_python_license(text):
    # OpenSSL 3's LICENSE.txt is the generic Apache text, without "OpenSSL".
    # CPython concatenates it after its CRT/bzip2/libffi notices.
    for required in ('Apache License', 'Microsoft Distributable Code', 'libffi'):
        if required.lower() not in text.lower():
            raise RuntimeError('Official Python Windows binary notices are incomplete: ' + required)


def fetch(url, target, expected=None):
    if target.is_file() and expected and digest(target) == expected:
        return
    temporary = target.with_suffix('.download')
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
        shutil.copyfileobj(response, output)
    if expected and digest(temporary) != expected:
        raise RuntimeError('Upstream source checksum mismatch: ' + target.name)
    temporary.replace(target)


def collect_archive(archive, output):
    with tarfile.open(archive, 'r:xz') as source:
        for member in source:
            if member.isfile() and member.size < 4_000_000 and is_notice(member.name):
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or any(':' in p for p in path.parts):
                    raise RuntimeError('Unsafe upstream archive member')
                target = output / Path(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.extractfile(member).read())


def main():
    if sys.platform != 'win32':
        raise SystemExit('Prepare this inventory on the Windows builder.')
    for package in ('PySide6_Essentials', 'shiboken6'):
        if metadata.version(package) != QT_VERSION:
            raise SystemExit('Review Qt source pins after upgrading ' + package)
    output = ROOT / 'build/windows-runtime-licenses'
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / 'build/upstream-sources'
    cache.mkdir(parents=True, exist_ok=True)
    archives, inventory = [], []
    for module in MODULES:
        url = source_url(module)
        archive = cache / url.rsplit('/', 1)[-1]
        print('Preparing public upstream source: ' + module, flush=True)
        fetch(url, archive, SOURCES[module])
        collect_archive(archive, output / 'Qt-and-PySide')
        archives.append(archive)
        inventory.append({'component': module, 'version': QT_VERSION, 'source': url,
                          'sha256': SOURCES[module]})
    # The official Windows binary LICENSE includes CRT, OpenSSL, libffi and
    # bzip2 notices; the short source-tree PSF license is not a substitute.
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    text = python_license.read_text(encoding='utf-8')
    validate_python_license(text)
    shutil.copyfile(python_license, output / 'Python-Windows-LICENSE.txt')
    openssl_version = ssl.OPENSSL_VERSION.split()[1]
    if not re.fullmatch(r'3\.\d+\.\d+', openssl_version):
        raise RuntimeError('Review notices for this OpenSSL version')
    license_url = f'https://raw.githubusercontent.com/openssl/openssl/openssl-{openssl_version}/LICENSE.txt'
    fetch(license_url, output / 'OpenSSL-LICENSE.txt')
    python_version = sys.version.split()[0]
    url = f'https://www.python.org/ftp/python/{python_version}/Python-{python_version}.tar.xz'
    archive = cache / f'Python-{python_version}.tar.xz'
    fetch(url, archive)
    collect_archive(archive, output / 'Python-source-notices')
    with tarfile.open(archive, 'r:xz') as source:
        member = source.getmember(f'Python-{python_version}/Doc/license.rst')
        (output / 'Python-additional-licenses.rst').write_bytes(source.extractfile(member).read())
    archives.append(archive)
    inventory.append({'component': 'Python', 'version': python_version, 'source': url,
                      'sha256': digest(archive), 'openssl': ssl.OPENSSL_VERSION})
    # Preserve package/vendor notices conservatively, including build tools.
    # This is an environment inventory, not a claim that every tool is shipped.
    for distribution in sorted(metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
        name = distribution.metadata['Name']
        if name.lower() in ('pillow', 'pyside6-essentials', 'shiboken6'):
            continue  # Pillow is build-only; Qt/PySide notices come from sources.
        for file in distribution.files or []:
            if is_notice(str(file)) and '..' not in file.parts:
                origin = distribution.locate_file(file)
                if origin.is_file():
                    target = output / 'Python-environment' / name / Path(*file.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(origin, target)
        inventory.append({'component': name, 'version': distribution.version,
                          'scope': 'Python build environment; notices may cover build-only tools'})
    # The PyInstaller bootloader is unmodified; include matching sources too.
    version = metadata.version('pyinstaller')
    with urllib.request.urlopen(f'https://pypi.org/pypi/pyinstaller/{version}/json', timeout=60) as response:
        package = json.load(response)
    source = next(item for item in package['urls'] if item['packagetype'] == 'sdist')
    archive = cache / source['filename']
    if not source['url'].startswith('https://files.pythonhosted.org/'):
        raise RuntimeError('Unexpected PyPI source host')
    fetch(source['url'], archive, source['digests']['sha256'])
    archives.append(archive)
    inventory.append({'component': 'PyInstaller bootloader source', 'version': version,
                      'source': source['url'], 'sha256': source['digests']['sha256']})
    shutil.copyfile(ROOT / 'desktop/packaging/WINDOWS-SOURCES.md', output / 'WINDOWS-SOURCES.md')
    (output / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    release = ROOT / 'dist/installers'
    release.mkdir(parents=True, exist_ok=True)
    version = (ROOT / 'desktop/VERSION').read_text().strip()
    bundle = release / f'NoSub-Studio-{version}-Windows-Third-Party-Sources.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_STORED) as target:
        for archive in archives:
            target.write(archive, archive.name)
        target.write(output / 'inventory.json', 'inventory.json')
        target.write(output / 'WINDOWS-SOURCES.md', 'README.md')
    bundle.with_suffix('.zip.sha256').write_text(f'{digest(bundle)}  {bundle.name}\n', encoding='utf-8')
    print('Windows notices and matching source asset prepared.', flush=True)


if __name__ == '__main__':
    main()
