"""Hardware-free product asset checks, shared by Mac and Windows builders."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from branding import SOURCE_ICON, build_icons, runtime_icon
import importlib.util

def packaging_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / 'packaging' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
                with Image.open(SOURCE_ICON) as original:
                    self.assertEqual(picture.convert('RGBA').tobytes(), original.convert('RGBA').tobytes())
            source = (output / 'windows-version.txt').read_text(encoding='utf-8')
            ast.parse(source)
            self.assertIn("StringStruct('ProductName', 'NoSub Studio')", source)

    def test_beta_and_test_names_are_not_production_names(self):
        module = packaging_module('package_windows')
        self.assertIn('-Public-Beta-1-Setup', module.package_name('1.0.0', True))
        self.assertIn('-TEST-Setup', module.package_name('1.0.0'))
        with self.assertRaises(ValueError):
            module.package_name('../invalid', True)

    def test_product_ico_contains_generated_image_payloads(self):
        module = packaging_module('verify_windows_bundle')
        with tempfile.TemporaryDirectory() as directory:
            output = build_icons(Path(directory))
            payloads = module.ico_payloads(output / 'NoSubStudio.ico')
            self.assertGreaterEqual(len(payloads), 7)
        self.assertTrue(module.known_dll(Path('Qt6Widgets.dll')))
        self.assertFalse(module.known_dll(Path('Qt6VirtualKeyboard.dll')))
        self.assertFalse(module.known_dll(Path('opengl32sw.dll')))

    def test_python_windows_license_requires_binary_dependency_notices(self):
        import sys
        with patch.object(sys, 'path', [str(Path(__file__).parent / 'packaging'), *sys.path]):
            module = packaging_module('collect_windows_licenses')
        module.validate_python_license('Apache License\nMicrosoft Distributable Code\nlibffi')
        with self.assertRaises(RuntimeError):
            module.validate_python_license('PSF source license with an office address')


if __name__ == '__main__':
    unittest.main()
