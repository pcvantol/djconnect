"""Focused privacy and failure-boundary tests for Browser E2E infrastructure."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "djconnect" / "universal_receiver_browser_e2e.py"


class UniversalReceiverBrowserE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        cls.source = source

    def test_browser_runner_never_passes_the_real_token_to_node(self) -> None:
        self.assertIn("broadcast_token=str(contract[\"broadcast_token\"])", self.source)
        self.assertIn("broadcast_token=ephemeral", self.source)
        self.assertNotIn('"broadcast_token": contract', self.source)
        self.assertIn("capture_output=True", self.source)

    def test_browser_runner_rejects_failures_without_emitting_node_output(self) -> None:
        self.assertIn('UniversalReceiverBrowserE2EError("headless_receiver_assertion_failed")', self.source)
        self.assertNotIn("completed.stderr", self.source)
        self.assertNotIn("completed.stdout", self.source)

    def test_prohibited_browser_artifacts_are_not_introduced(self) -> None:
        for prohibited in ("screenshot", "trace", "har", "video"):
            self.assertNotIn(prohibited, self.source.lower())
        self.assertIn('page.includes("localStorage"), false', self.source)
