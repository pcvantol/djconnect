import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from tools.verification.oci_manifest_digest import manifest_digest


class OCIManifestDigestTests(unittest.TestCase):
    def archive(self, path, *, tamper=False, duplicate=False, multiple=False, tamper_blob=False):
        config = b"{}"
        config_digest = "sha256:" + hashlib.sha256(config).hexdigest()
        manifest = json.dumps({"schemaVersion": 2, "config": {"digest": config_digest, "size": len(config)}, "layers": []}).encode()
        digest = "sha256:" + hashlib.sha256(manifest).hexdigest()
        item = {"digest": digest, "size": len(manifest)}
        index = json.dumps({"schemaVersion": 2, "manifests": [item, item] if multiple else [item]}).encode()
        with tarfile.open(path, "w") as archive:
            def add(name, data):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            add("index.json", index)
            add("blobs/sha256/" + config_digest[7:], b"[]" if tamper_blob else config)
            add("blobs/sha256/" + digest[7:], manifest + (b"x" if tamper else b""))
            if duplicate:
                add("index.json", index)
        return digest

    def test_independent_manifest_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.tar"
            expected = self.archive(path)
            self.assertEqual(manifest_digest(path), expected)

    def test_tampered_duplicate_and_multiple_manifests_fail(self):
        for kwargs in ({"tamper": True}, {"duplicate": True}, {"multiple": True}, {"tamper_blob": True}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "image.tar"
                self.archive(path, **kwargs)
                with self.assertRaises(ValueError):
                    manifest_digest(path)
