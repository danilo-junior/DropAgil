"""Release versions must rise when Android sources change and stay stable on rebuilds."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from android.tools import build


class AndroidVersionTests(unittest.TestCase):
    def test_source_change_advances_version_once(self):
        manifest = ET.parse(build.ANDROID / 'AndroidManifest.xml').getroot()
        namespace = '{http://schemas.android.com/apk/res/android}'
        base_code = int(manifest.attrib[namespace + 'versionCode'])
        base_name = manifest.attrib[namespace + 'versionName']
        with tempfile.TemporaryDirectory() as folder:
            temporary = Path(folder)
            metadata = temporary / 'version.json'
            with patch.object(build, 'BUILD', temporary), patch.object(build, 'METADATA', metadata):
                _, initial_code, initial_name, source_hash = build.versioned_manifest()
                self.assertEqual((initial_code, initial_name), (base_code, base_name))
                metadata.write_text(json.dumps({'versionCode':initial_code,
                    'versionName':initial_name,'sourceSha256':source_hash}), encoding='utf-8')
                self.assertEqual(build.versioned_manifest()[1:3], (base_code, base_name))
                metadata.write_text(json.dumps({'versionCode':initial_code,
                    'versionName':initial_name,'sourceSha256':'outdated'}), encoding='utf-8')
                self.assertEqual(build.versioned_manifest()[1:3], (base_code + 1, base_name + '.1'))


if __name__ == '__main__':
    unittest.main()
