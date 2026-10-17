"""Hardware-free product asset checks, shared by Mac and Windows builders."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from branding import SOURCE_ICON, build_icons, runtime_icon


class PackagingTests(unittest.TestCase):
    def test_source_icon_exists(self):
        self.assertEqual(runtime_icon(), SOURCE_ICON)
        with Image.open(runtime_icon()) as picture:
            self.assertEqual(picture.size, (1024, 1024))

    def test_frozen_icon_is_in_runtime_resources(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', '/runtime', create=True):
            self.assertEqual(runtime_icon(), Path('/runtime/assets/AppIcon-1024.png'))

    def test_generated_native_icons_and_version(self):
        with tempfile.TemporaryDirectory() as directory:
            output = build_icons(Path(directory))
            with Image.open(output / 'NoSubStudio.ico') as picture:
                self.assertEqual(picture.format, 'ICO')
                self.assertTrue({(16, 16), (32, 32), (48, 48), (256, 256)} <= picture.ico.sizes())
            with Image.open(output / 'NoSubStudio.icns') as picture:
                self.assertEqual(picture.format, 'ICNS')
                self.assertIn((512, 512, 2), picture.info['sizes'])
            source = (output / 'windows-version.txt').read_text(encoding='utf-8')
            ast.parse(source)
            self.assertIn("StringStruct('ProductName', 'NoSub Studio')", source)


if __name__ == '__main__':
    unittest.main()
