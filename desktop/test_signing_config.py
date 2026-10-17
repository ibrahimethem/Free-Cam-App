"""Signing scope must never expand to every bundled third-party binary."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
NS = {'s': 'http://signpath.io/artifact-configuration/v1'}


class SigningConfigTests(unittest.TestCase):
    def test_exact_owned_artifact_scope(self):
        root = ET.parse(ROOT / 'desktop/packaging/signpath-binaries.xml').getroot()
        elements = root.findall('s:zip-file/s:pe-file', NS)
        self.assertEqual({item.attrib['path'] for item in elements}, {
            'FreeCam.exe', '_internal/native-camera/NoSubCamera.dll',
            '_internal/native-camera/NoSubCameraSetup.exe'})
        self.assertEqual(len(elements), 3)
        for item in elements:
            self.assertEqual(item.attrib['product-name'], 'NoSub Studio')
            self.assertEqual(item.attrib['product-version'], '${version}')
            self.assertIsNotNone(item.find('s:authenticode-sign', NS))

    def test_license_keeps_third_party_provenance(self):
        license_text = (ROOT / 'LICENSE').read_text()
        self.assertIn('MIT License', license_text)
        self.assertIn('İbrahim Ethem Karalı', license_text)
        notices = (ROOT / 'THIRD_PARTY_NOTICES.md').read_text()
        self.assertIn('626f8b19c5f367602f2e89c6b314573d3776c9df', notices)
        self.assertIn('derived from that', notices)


if __name__ == '__main__':
    unittest.main()
