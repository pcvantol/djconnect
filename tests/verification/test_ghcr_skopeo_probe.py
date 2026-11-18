import unittest
from tools.verification.ghcr_skopeo_probe import BASE_TAGS, HISTORICAL_DIGEST, check


class SkopeoProbeTests(unittest.TestCase):
    def setUp(self):
        self.marker = "skopeo-check-42-1-" + "a" * 32
        self.digest = "sha256:" + "b" * 64
        self.state = {tag: (200, HISTORICAL_DIGEST) for tag in BASE_TAGS}

    def probe(self, tag):
        return self.state.get(tag, (404, None))

    def test_before_and_after(self):
        check(self.probe, self.marker)
        self.state[self.marker] = (200, self.digest)
        check(self.probe, self.marker, self.digest)

    def test_existing_probe_or_bad_baseline_or_wrong_digest_fails(self):
        self.state[self.marker] = (200, self.digest)
        with self.assertRaises(ValueError):
            check(self.probe, self.marker)
        with self.assertRaises(ValueError):
            check(self.probe, self.marker, "sha256:" + "c" * 64)
        self.state["latest"] = (200, "sha256:" + "d" * 64)
        with self.assertRaises(ValueError):
            check(self.probe, self.marker, self.digest)

    def test_invalid_identity_and_inaccessible_registry_fail(self):
        with self.assertRaises(ValueError):
            check(self.probe, "latest")
        with self.assertRaises(ValueError):
            check(lambda _: (403, None), self.marker)

    def test_readback_rejects_changed_bytes_and_headers(self):
        import hashlib
        import io
        from unittest.mock import patch
        from tools.verification.ghcr_skopeo_probe import readback_bytes

        raw = b'{"schemaVersion":2}'
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()

        class Response(io.BytesIO):
            def __init__(self, data, header=None):
                super().__init__(data)
                self.headers = {"Docker-Content-Digest": header} if header else {}

        class Opener:
            def __init__(self, body, header):
                self.body, self.header = body, header
            def open(self, request, timeout):
                if isinstance(request, str):
                    return Response(b'{"token":"synthetic"}')
                return Response(self.body, self.header)

        for body, header, succeeds in ((raw, digest, True), (b"tampered", digest, False),
                                       (raw, "sha256:" + "f" * 64, False)):
            with self.subTest(succeeds=succeeds), patch(
                "tools.verification.ghcr_skopeo_probe.urllib.request.build_opener",
                return_value=Opener(body, header),
            ):
                if succeeds:
                    readback_bytes(self.marker, digest)
                else:
                    with self.assertRaises(ValueError):
                        readback_bytes(self.marker, digest)
