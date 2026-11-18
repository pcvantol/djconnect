import hashlib
import json
import unittest
from tools.verification.ghcr_write_scope_probe import BASE_DIGEST, build_manifest


class GHCRWriteProbeTests(unittest.TestCase):
    def test_unique_markers_produce_separate_manifests_without_changing_blobs(self):
        original = {"schemaVersion": 2, "config": {"digest": "sha256:" + "a" * 64},
                    "layers": [{"digest": "sha256:" + "b" * 64,
                                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip"}]}
        a = build_manifest(original, "rights-check-10-1-" + "a" * 32)
        b = build_manifest(original, "rights-check-10-1-" + "b" * 32)
        decoded = json.loads(a)
        self.assertNotEqual(a, b)
        self.assertNotEqual("sha256:" + hashlib.sha256(a).hexdigest(), BASE_DIGEST)
        self.assertEqual(decoded["config"]["digest"], original["config"]["digest"])
        self.assertEqual(decoded["layers"][0]["digest"], original["layers"][0]["digest"])
        self.assertNotIn("annotations", original)

    def test_rejects_unexpected_marker_and_layer(self):
        for marker in ("latest", "1.1.0", "rights-check-1-1-abc"):
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                build_manifest({}, marker)
        with self.assertRaises(ValueError):
            build_manifest({"schemaVersion": 2, "config": {}, "layers": [{"mediaType": "other"}]},
                           "rights-check-1-1-" + "a" * 32)

class GHCRWriteProbeFlowTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        from tools.verification import ghcr_write_scope_probe as probe
        self.probe = probe
        self.marker = "rights-check-10-1-" + "a" * 32
        self.raw = json.dumps({"schemaVersion": 2, "config": {"digest": "sha256:" + "a" * 64},
            "layers": [{"digest": "sha256:" + "b" * 64,
                        "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip"}]}).encode()
        self.base = "sha256:" + hashlib.sha256(self.raw).hexdigest()
        self.patch = patch.object(probe, "BASE_DIGEST", self.base)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def opener(self, mode="ok"):
        import io
        import urllib.error
        outer = self
        class Response(io.BytesIO):
            def __init__(self, raw, status, digest=None):
                super().__init__(raw)
                self.status = status
                self.headers = {"Docker-Content-Digest": digest} if digest else {}
        class Opener:
            def __init__(self):
                self.calls = []
                self.manifest = None
            def open(self, request, timeout):
                method, url = request.get_method(), request.full_url
                self.calls.append((method, url))
                if "/token?" in url:
                    if mode == "token_error":
                        raise urllib.error.HTTPError(url, 403, "denied", {}, None)
                    return Response(b'{"token":"opaque"}', 200)
                tag = url.rsplit("/", 1)[-1]
                if tag in outer.probe.BASE_TAGS:
                    digest = "sha256:" + "f" * 64 if mode == "baseline" else outer.base
                    return Response(outer.raw, 200, digest)
                if method == "PUT":
                    if mode == "put_denied":
                        raise urllib.error.HTTPError(url, 403, "denied", {}, None)
                    self.manifest = request.data
                    return Response(b"", 201, "sha256:" + hashlib.sha256(self.manifest).hexdigest())
                if tag == outer.marker and self.manifest is None:
                    if mode == "exists":
                        return Response(b"existing", 200, "sha256:existing")
                    raise urllib.error.HTTPError(url, 404, "not found", {}, None)
                if tag == outer.marker:
                    data = b"tampered" if mode == "tamper" else self.manifest
                    return Response(data, 200, "sha256:" + hashlib.sha256(self.manifest).hexdigest())
                raise AssertionError("unexpected request")
        return Opener()

    def run_case(self, opener):
        return self.probe.run_probe(opener, actor="owner", secret="fixture", run_id="10", attempt="1", nonce="a" * 32)

    def test_write_happens_once_after_all_five_baselines_and_absence_check(self):
        opener = self.opener()
        marker, digest = self.run_case(opener)
        self.assertEqual(marker, self.marker)
        self.assertEqual(digest, "sha256:" + hashlib.sha256(opener.manifest).hexdigest())
        calls = opener.calls
        puts = [index for index, (method, _) in enumerate(calls) if method == "PUT"]
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0], 8)  # token, five baseline tags, baseline bytes, missing probe tag
        self.assertTrue(calls[puts[0]][1].endswith("/" + self.marker))
        self.assertEqual(sum(url.endswith("/" + self.marker) for _, url in calls), 3)
        self.assertTrue(all(method in ("GET", "PUT") for method, _ in calls))

    def test_bad_baseline_or_existing_tag_never_puts(self):
        for mode in ("baseline", "exists"):
            opener = self.opener(mode)
            with self.subTest(mode=mode), self.assertRaises(SystemExit):
                self.run_case(opener)
            self.assertFalse(any(method == "PUT" for method, _ in opener.calls))

    def test_readback_bytes_mismatch_fails_even_when_digest_header_matches(self):
        opener = self.opener("tamper")
        with self.assertRaises(SystemExit):
            self.run_case(opener)
        self.assertEqual(sum(method == "PUT" for method, _ in opener.calls), 1)

    def test_missing_identity_stops_before_network(self):
        opener = self.opener()
        with self.assertRaises(SystemExit):
            self.probe.run_probe(opener, actor="", secret="", run_id="10", attempt="1", nonce="a" * 32)
        self.assertEqual(opener.calls, [])

    def test_token_denial_has_no_write_and_put_denial_stops(self):
        for mode, expected in (("token_error", 0), ("put_denied", 1)):
            opener = self.opener(mode)
            with self.subTest(mode=mode), self.assertRaises(SystemExit):
                self.run_case(opener)
            self.assertEqual(sum(method == "PUT" for method, _ in opener.calls), expected)
