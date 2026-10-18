"""Keep unused, automatically collected Qt backends out of the Mac product."""
from pathlib import PurePosixPath


def include_macos_binary(name):
    parts = PurePosixPath(name.replace('\\', '/')).parts
    if any(part.startswith(('QtVirtualKeyboard', 'QtQml', 'QtQuick')) for part in parts):
        return False
    basename = parts[-1].lower()
    return not (basename == 'libqtvirtualkeyboardplugin.dylib'
                or basename == 'libffmpegmediaplugin.dylib'
                or basename.startswith(('libavcodec.', 'libavformat.', 'libavutil.',
                                        'libswresample.', 'libswscale.')))


def include_windows_binary(name):
    # Windows 11 already provides UCRT/API sets and Windows ICU. Do not ship
    # accidentally collected OS shims. Qt Widgets uses the normal Windows raster
    # backend; the optional Mesa renderer and Qt OpenSSL backend are unused.
    basename = PurePosixPath(name.replace('\\', '/')).name.lower()
    return not (basename.startswith('api-ms-win-') or basename in (
        'ucrtbase.dll', 'icuuc.dll', 'icudt78.dll', 'opengl32sw.dll',
        'qopensslbackend.dll', 'libssl-3.dll', 'libcrypto-3.dll'))
