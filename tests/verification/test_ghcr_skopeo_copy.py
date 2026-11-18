import subprocess
from pathlib import Path
from types import SimpleNamespace
import unittest
from tools.verification.ghcr_skopeo_copy import copy_probe


class SkopeoCopyTests(unittest.TestCase):
    def setUp(self):
        self.marker = "skopeo-check-42-1-" + "a" * 32
        self.archive = Path("/isolated/probe.tar")

    def test_only_unique_tag_and_suppressed_output(self):
        calls = []
        def fake(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0)
        copy_probe(self.archive, self.marker, run=fake)
        args, kwargs = calls[0]
        self.assertEqual(args[:3], ["skopeo", "copy", "--preserve-digests"])
        self.assertTrue(args[-1].endswith(":" + self.marker))
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)

    def test_copy_failure_has_fixed_message_without_tool_output(self):
        def denied(*_args, **_kwargs):
            raise RuntimeError("synthetic secret must never be shown")
        with self.assertRaises(RuntimeError) as error:
            copy_probe(self.archive, self.marker, run=denied)
        self.assertNotIn("synthetic secret", str(error.exception))
        self.assertIn("GHCR probe copy failed", str(error.exception))

    def test_invalid_tag_cannot_call_tool(self):
        calls = []
        with self.assertRaises(ValueError):
            copy_probe(self.archive, "latest", run=lambda *args, **kwargs: calls.append(args))
        self.assertEqual(calls, [])
