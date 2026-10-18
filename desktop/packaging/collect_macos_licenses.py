"""Prepare notices and exact Qt/PySide source assets before Mac packaging.

Downloads only pinned public upstream archives. No credentials are read. Output
is generated under ignored build/ and dist/; it contains no local environment.
"""
import hashlib
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
QT_VERSION = '6.12.0'
SOURCES = {
    'qtbase': 'a951bd163c7b80fc6b8c88d7668fb56abf91c152373e13c10666763238131307',
    'qtmultimedia': '3143f53b64257ba2a0685c940f5dce476c75871ff86b516de45cfd54ea93a62d',
    'qtsvg': 'e4ab39534ec97987b1b9b60ef7f4d3253d5912a69f8c713a01753174a4029331',
    'qtimageformats': '0943132b5db8de6b6a7f1d162682173e8763c7ed94e80fd39113292845f67762',
    'qttranslations': '85929c0c30d6f273f23bd879bb69803ea17b010ab73cab2f8abf95357f6f6bbb',
    'pyside-setup': '099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751',
}
PACKAGES = ('qrcode', 'keyring', 'jaraco.classes', 'jaraco.context',
            'jaraco.functools', 'more-itertools', 'packaging', 'setuptools', 'pyinstaller')


def is_notice(name):
    path = PurePosixPath(name)
    basename = path.name.lower()
    return (basename.startswith(('license', 'licence', 'copying', 'copyright', 'notice'))
            or 'LICENSES' in path.parts or basename == 'qt_attribution.json')


def source_url(module):
    base = ('https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/'
            if module == 'pyside-setup' else
            'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/')
    return base + f'{module}-everywhere-src-{QT_VERSION}.tar.xz'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if sys.platform != 'darwin':
        raise SystemExit('This inventory is for the macOS runtime only.')
    for package in ('PySide6_Essentials', 'PySide6_Addons', 'shiboken6'):
        if metadata.version(package) != QT_VERSION:
            raise SystemExit(f'Review source pins after upgrading {package}.')
    output = ROOT / 'build/runtime-licenses'
    output.mkdir(parents=True, exist_ok=True)
    cache = ROOT / 'build/upstream-sources'
    cache.mkdir(parents=True, exist_ok=True)
    inventory = []
    archives = []
    for module, expected in SOURCES.items():
        url = source_url(module)
        archive = cache / url.rsplit('/', 1)[-1]
        if not archive.is_file() or digest(archive) != expected:
            print(f'Downloading public source: {module}', flush=True)
            temporary = archive.with_suffix('.download')
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as stream:
                shutil.copyfileobj(response, stream)
            if digest(temporary) != expected:
                raise RuntimeError(f'Upstream source checksum mismatch: {module}')
            temporary.replace(archive)
        archives.append(archive)
        inventory.append({'component': module, 'version': QT_VERSION, 'source': url, 'sha256': expected})
        # Read regular notice files only; never extract archive paths or links.
        with tarfile.open(archive, 'r:xz') as source:
            for member in source:
                if member.isfile() and member.size < 4_000_000 and is_notice(member.name):
                    parts = PurePosixPath(member.name).parts
                    if '..' in parts or PurePosixPath(member.name).is_absolute():
                        raise RuntimeError('Unsafe upstream archive member')
                    target = output / 'Qt-and-PySide' / Path(*parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.extractfile(member).read())
    for package in PACKAGES:
        distribution = metadata.distribution(package)
        count = 0
        for file in distribution.files or []:
            if is_notice(str(file)) and '..' not in file.parts:
                source = distribution.locate_file(file)
                if source.is_file():
                    target = output / 'Python-packages' / package / Path(*file.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    count += 1
        if not count:
            raise RuntimeError(f'Missing package license: {package}')
        inventory.append({'component': package, 'version': distribution.version})
    shutil.copyfile(Path(sysconfig.get_path('stdlib')) / 'LICENSE.txt', output / 'Python-LICENSE.txt')
    inventory.append({'component': 'Python', 'version': sys.version.split()[0],
                      'source': 'https://www.python.org/downloads/source/'})
    # Follow the actual Python extension linkage, not an unrelated Homebrew version.
    for module, library, names in (
            ('_ssl', 'libssl.', ('LICENSE.txt',)),
            ('_decimal', 'libmpdec.', ('COPYRIGHT.txt',)),
            ('_lzma', 'liblzma.', ('COPYING', 'COPYING.0BSD'))):
        imported = __import__(module)
        linkage = subprocess.check_output(['otool', '-L', imported.__file__], text=True)
        dependency = next(line.strip().split(' (')[0] for line in linkage.splitlines()[1:]
                          if library in line)
        prefix = Path(dependency).resolve().parent.parent
        for name in names:
            shutil.copyfile(prefix / name, output / f'{prefix.parent.name}-{prefix.name}-{name}')
        inventory.append({'component': prefix.parent.name, 'version': prefix.name})
    shutil.copyfile(ROOT / 'desktop/packaging/THIRD-PARTY-SOURCES.md', output / 'THIRD-PARTY-SOURCES.md')
    (output / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    version = (ROOT / 'desktop/VERSION').read_text().strip()
    release = ROOT / 'dist/installers'
    release.mkdir(parents=True, exist_ok=True)
    bundle = release / f'NoSub-Studio-{version}-Third-Party-Sources.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path in archives:
            archive.write(path, path.name)
        archive.write(output / 'inventory.json', 'inventory.json')
        archive.write(output / 'THIRD-PARTY-SOURCES.md', 'README.md')
    bundle.with_suffix('.zip.sha256').write_text(f'{digest(bundle)}  {bundle.name}\n')
    print('Prepared runtime notices and source release asset.', flush=True)


if __name__ == '__main__':
    main()
