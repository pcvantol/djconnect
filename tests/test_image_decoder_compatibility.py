"""The same original image bytes must retain their admission on both decoders."""
import base64
import hashlib
import importlib
import json
import sys
import unittest

from tests import test_session_runtime as runtime_tests


class ImageDecoderCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = ('custom_components.djconnect.const',
                 'custom_components.djconnect.session_runtime')
        previous = {name: sys.modules.get(name) for name in names}

        def restore_modules():
            for name, module in previous.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

        cls.addClassCleanup(restore_modules)
        cls.runtime, _ = runtime_tests._load_runtime_module()
        cls.artwork = importlib.import_module('custom_components.djconnect.session_artwork')

    def test_original_fixed_byte_corpus(self):
        fixture = runtime_tests.ROOT / 'tests/fixtures/image_decoder_compatibility_v1/corpus.json'
        data = json.loads(fixture.read_text())
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(len(data['cases']), 22)
        for case in data['cases']:
            with self.subTest(case=case['name']):
                body = base64.b64decode(case['body'], validate=True)
                self.assertEqual(hashlib.sha256(body).hexdigest(), case['sha256'])
                if case['accepted']:
                    self.assertEqual(self.artwork._decoded_size(body), tuple(case['size']))
                else:
                    with self.assertRaises((OSError, ValueError, SyntaxError)):
                        self.artwork._decoded_size(body)
