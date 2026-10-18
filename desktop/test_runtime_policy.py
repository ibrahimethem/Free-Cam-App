"""Packaging guardrails without building or running the camera."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runtime_policy', HERE / 'packaging/runtime_policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class RuntimePolicyTests(unittest.TestCase):
    def test_unused_backends_are_excluded_at_every_destination(self):
        for name in ('QtVirtualKeyboard', 'QtQml', 'QtQmlMeta', 'QtQmlModels', 'QtQuick'):
            self.assertFalse(policy.include_macos_binary(f'PySide6/Qt/lib/{name}.framework/Versions/A/{name}'))
        for name in ('libqtvirtualkeyboardplugin.dylib', 'libffmpegmediaplugin.dylib',
                     'libavcodec.63.dylib', 'libavformat.63.dylib', 'libavutil.61.dylib',
                     'libswresample.7.dylib', 'libswscale.10.dylib'):
            self.assertFalse(policy.include_macos_binary(name))
            self.assertFalse(policy.include_macos_binary(f'PySide6/Qt/lib/{name}'))

    def test_capture_and_image_decoding_remain(self):
        for name in ('QtCore', 'QtGui', 'QtWidgets', 'QtMultimedia', 'QtNetwork', 'QtSvg'):
            self.assertTrue(policy.include_macos_binary(f'PySide6/Qt/lib/{name}.framework/Versions/A/{name}'))
        for name in ('libdarwinmediaplugin.dylib', 'libqjpeg.dylib', 'libNoSubCamera.dylib'):
            self.assertTrue(policy.include_macos_binary(name))


if __name__ == '__main__':
    unittest.main()
