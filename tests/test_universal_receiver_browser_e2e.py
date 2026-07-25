"""Focused privacy and failure-boundary tests for Browser E2E infrastructure."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "djconnect" / "universal_receiver_browser_e2e.py"
RECEIVER_PATH = ROOT / "custom_components" / "djconnect" / "universal_receiver.html"
RELEASE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "home-assistant-release-artifact.yml"


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
            self.assertNotIn(f'"{prohibited}"', self.source.lower())
        self.assertIn('page.includes("localStorage"), false', self.source)

    def test_overlay_is_process_local_and_allowlist_based(self) -> None:
        self.assertIn('overlay.dataset.kind = "read-only-observability"', self.source)
        self.assertIn('elements.set("developer-overlay", overlay)', self.source)
        self.assertIn('Object.keys(observability)', self.source)
        for allowed in (
            '"session"',
            '"planner"',
            '"current_moment"',
            '"session_flow"',
            '"broadcast"',
            '"transport"',
        ):
            self.assertIn(allowed, self.source)
        for forbidden in (
            "start_strategy",
            "persona",
            "capability_policy",
            "registry",
            "renderer_identity",
        ):
            self.assertNotIn(f'"{forbidden}"', self.source)

    def test_receiver_and_release_artifact_have_no_overlay_surface(self) -> None:
        receiver = RECEIVER_PATH.read_text(encoding="utf-8")
        release_workflow = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertNotIn("developer-overlay", receiver)
        self.assertNotIn("read-only-observability", receiver)
        self.assertIn("tar -C custom_components -czf", release_workflow)
