"""Bounded shared HTTP/WSS reservation accounting, without transport mocks."""
import importlib
from types import SimpleNamespace
import unittest

from tests import test_display_admission  # noqa: F401


class DisplayDeliveryBudgetTests(unittest.TestCase):
    def setUp(self):
        # Import through the namespace fixture without loading the HA integration.
        from tests.test_session_conversation_history import SessionConversationHistoryTest
        SessionConversationHistoryTest.setUpClass()
        self.addCleanup(SessionConversationHistoryTest.tearDownClass)
        self.module = importlib.import_module("custom_components.djconnect.display_delivery")
        self.hub = self.module.display_live_hub(SimpleNamespace())

    def test_preauth_global_and_per_transport_source_capacity_never_evicts(self):
        self.hub.reserve_preauth("same")
        self.hub.reserve_preauth("same")
        with self.assertRaises(self.module.DisplayAdmissionError):
            self.hub.reserve_preauth("same")
        for n in range(14):
            self.hub.reserve_preauth(str(n))
        with self.assertRaises(self.module.DisplayAdmissionError):
            self.hub.reserve_preauth("overflow")
        self.assertEqual(self.hub.preauth, 16)
        self.hub.release_preauth("same")
        self.hub.release_preauth("same")
        for n in range(14):
            self.hub.release_preauth(str(n))
        self.assertEqual(self.hub.preauth, 0)
        self.assertFalse(self.hub.sources)

    def test_one_projection_per_display_eight_global_idempotent_release(self):
        releases = [self.hub.reserve_projection(str(n)) for n in range(8)]
        self.assertEqual(self.hub.projections, 8)
        self.assertLessEqual(self.hub.reserved_bytes, 4 * 1024 * 1024)
        for identity in ("0", "ninth"):
            with self.assertRaises(self.module.DisplayAdmissionError):
                self.hub.reserve_projection(identity)
        releases[0]()
        releases[0]()
        self.assertEqual(self.hub.projections, 7)
        replacement = self.hub.reserve_projection("0")
        releases[0]()
        self.assertEqual(self.hub.projections, 8)
        replacement()
        for release in releases[1:]:
            release()
        self.assertEqual(self.hub.reserved_bytes, 0)
        self.assertFalse(self.hub.projecting)
