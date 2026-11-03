"""Core signed Watch preference request and reconciliation boundaries."""
from dataclasses import replace
import json
import unittest
from unittest.mock import AsyncMock, Mock

from tests.test_persistence_platform import PersistenceService  # noqa: F401
from custom_components.djconnect.watch_preference_client import (
    EnrolledWatchReceiver, WatchPreferenceIntent, update_watch_preference, watch_preference_https,
)


class WatchPreferenceClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.receiver = EnrolledWatchReceiver("lab-api", "install-a", "watch-a", "pair-a", 2, "a" * 64)
        self.intent = WatchPreferenceIntent("opt-out", 3, False, 125)
        self.receipt = dict(incarnation="pair-a", revision=4, operation="opt-out", enabled=0, sealed=0)
        self.guard = Mock(return_value=None)
        self.sign = AsyncMock(return_value=bytes(64))
        self.post = AsyncMock(return_value=self.receipt)

    async def update(self):
        return await update_watch_preference(
            self.receiver, self.intent, require_current=self.guard,
            sign_frame=self.sign, post_signed=self.post, wall=lambda: 100,
        )

    async def test_exact_bound_write(self):
        self.assertEqual(await self.update(), "confirmed")
        body, signature = self.post.await_args.args
        self.assertEqual(json.loads(body), {
            "audience": "lab-api", "action": "preference-write", "installation": "install-a",
            "receiver": "watch-a", "epoch": 2, "key_fingerprint": "a" * 64, "expiry": 125,
            "operation": "opt-out", "incarnation": "pair-a", "expected_version": 3, "enabled": False,
        })
        self.assertEqual(signature, "A" * 86)
        self.assertTrue(self.sign.await_args.args[0].startswith(b"DJC-WATCH-LIFECYCLE-V1\x00"))

    async def test_unknown_write_reconciles_only_by_signed_read(self):
        for uncertain in (TimeoutError(), {"error": "watch_preference_outcome_unknown"}):
            with self.subTest(uncertain=uncertain):
                self.post.reset_mock(side_effect=True)
                self.post.side_effect = [uncertain, self.receipt]
                self.assertEqual(await self.update(), "confirmed")
                write, read = [json.loads(call.args[0]) for call in self.post.await_args_list]
                self.assertEqual([write["action"], read["action"]], ["preference-write", "preference-read"])
                self.assertEqual(read["expiry"], write["expiry"])
                self.assertEqual(read["incarnation"], write["incarnation"])
                self.assertNotEqual(read["operation"], write["operation"])
                self.assertNotIn("expected_version", read)
                self.assertNotIn("enabled", read)

    async def test_stale_authority_during_signing_does_not_send(self):
        self.guard.side_effect = [None, None, PermissionError(), None]
        self.assertEqual(await self.update(), "discarded")
        self.post.assert_not_awaited()

    async def test_late_response_after_pairing_or_intent_changed_is_discarded(self):
        self.guard.side_effect = [None, None, None, PermissionError()]
        self.assertEqual(await self.update(), "discarded")
        self.post.assert_awaited_once()

    async def test_superseded_receipt_never_rebases(self):
        self.post.return_value = self.receipt | {"revision": 5, "operation": "other"}
        self.assertEqual(await self.update(), "superseded")
        self.post.assert_awaited_once()

    async def test_wrong_incarnation_or_invalid_ack_never_confirms(self):
        for changes in ({"incarnation": "other"}, {"enabled": False}, {"operation": "other"}):
            self.post.return_value = self.receipt | changes
            self.assertEqual(await self.update(), "unknown")

    async def test_expired_intent_does_not_sign(self):
        self.intent = replace(self.intent, expiry=100)
        self.assertEqual(await self.update(), "unknown")
        self.sign.assert_not_awaited()
        self.post.assert_not_awaited()


    def test_https_transport_only_accepts_canonical_provisioned_endpoint(self):
        self.assertTrue(callable(watch_preference_https("https://watch.example.test/internal/preference")))
        for endpoint in (
            "http://watch.example.test/internal/preference",
            "https://user@watch.example.test/internal/preference",
            "https://watch.example.test:443/internal/preference",
            "https://watch.example.test/internal/preference?next=other",
            "https://watch.example.test/internal/%70reference",
            "https://watch.example.test/../internal/preference",
            "https://127.0.0.1/internal/preference",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(
                    ValueError, "invalid_watch_preference_endpoint"):
                watch_preference_https(endpoint)
