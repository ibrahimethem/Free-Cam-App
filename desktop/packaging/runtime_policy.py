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
