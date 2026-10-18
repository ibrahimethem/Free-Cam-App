"""Create a Windows 11 x64 installer. No install, publish or credential import."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def package_name(version, public_beta=False):
    import re
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid product version')
    channel = 'Public-Beta-1' if public_beta else 'TEST'
    return f'NoSub-Studio-{version}-Windows-x64-{channel}-Setup'


def prepare_installer_license(root):
    # Preserve the Windows binary build's CRT redistribution conditions in the
    # installer's agreement, not just as a file discoverable after installation.
    runtime = root / 'dist/FreeCam/_internal/licenses/runtime/Python-Windows-LICENSE.txt'
    notice = runtime.read_text(encoding='utf-8')
    if 'Microsoft Distributable Code' not in notice:
        raise RuntimeError('Windows runtime redistribution conditions missing')
    output = root / 'build/windows-installer-license.txt'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text((root / 'LICENSE').read_text(encoding='utf-8') +
        '\n\nTHIRD-PARTY SOFTWARE\n\nNoSub\'s MIT license does not replace third-party '
        'licenses. Qt/PySide/Shiboken are LGPLv3; their notices and source/rebuild '
        'instructions are installed under _internal/licenses/runtime. The Microsoft '
        'component restrictions below apply only to Microsoft Distributable Code, '
        'not NoSub or the LGPL libraries.\n\n' + notice, encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-unsigned', action='store_true', help='Explicit TEST installer; not a production release')
    parser.add_argument('--public-beta', action='store_true', help='Explicitly labeled unsigned public beta; requires --allow-unsigned')
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Compile on Windows using Inno Setup 6.4 or newer')
    compiler = shutil.which('ISCC.exe') or str(Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Inno Setup 6/ISCC.exe')
    if not Path(compiler).is_file():
        parser.error('Install Inno Setup 6.4 or newer first')
    if not args.allow_unsigned:
        # A production signing pipeline must be configured before release. Never
        # silently label an unsigned executable as a finished public release.
        parser.error('Windows Authenticode signing is not configured. Use --allow-unsigned for testing only.')
    for file in ('dist/FreeCam/FreeCam.exe', 'build/branding/NoSubStudio.ico',
                 'build/native-camera-windows/Release/NoSubCamera.dll'):
        if not (ROOT / file).is_file():
            parser.error('Run python desktop/build.py --native-camera first: missing ' + file)
    version = (ROOT / 'desktop/VERSION').read_text().strip()
    name = package_name(version, args.public_beta)
    prepare_installer_license(ROOT)
    if args.public_beta:
        import json
        inventory = ROOT / 'dist/FreeCam/_internal/licenses/runtime/inventory.json'
        report = ROOT / 'build/windows-bundle-report.json'
        sources = ROOT / f'dist/installers/NoSub-Studio-{version}-Windows-Third-Party-Sources.zip'
        if not inventory.is_file() or not sources.is_file() or not report.is_file():
            parser.error('Public beta requires runtime notices, matching sources and bundle verification')
        validation = json.loads(report.read_text(encoding='utf-8'))
        with (ROOT / 'dist/FreeCam/FreeCam.exe').open('rb') as stream:
            app_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if validation.get('app_sha256') != app_digest or not validation.get('product_icon_verified'):
            parser.error('Bundle verification does not match this executable')
    subprocess.run([compiler, f'/DProductVersion={version}', f'/DRepoRoot={ROOT}',
                    *(['/DPublicBeta=1'] if args.public_beta else []),
                    f'/DPackageName={name}', str(ROOT / 'desktop/packaging/windows.iss')], check=True)
    output = ROOT / 'dist/installers' / (name + '.exe')
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.exe.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8', newline='\n')
    print('Unsigned ' + ('PUBLIC BETA' if args.public_beta else 'TEST') +
          ' installer created; do not disable Windows security to run it:', output)


if __name__ == '__main__':
    main()
