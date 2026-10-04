"""VibeCast's owner-approved browser handoff stays ephemeral and bounded."""

from __future__ import annotations

import asyncio
import importlib
import types
import unittest
from unittest.mock import patch

from tests.test_http_voice_helpers import install_http_stubs


install_http_stubs()
handoff = importlib.import_module("custom_components.djconnect.broadcast_handoff")
handlers = importlib.import_module("custom_components.djconnect.api_handlers")


class BroadcastHandoffManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = handoff.BroadcastHandoffManager()

    def test_claim_is_secret_bound_one_use_and_never_exposes_token_early(self) -> None:
        claim = asyncio.run(self.manager.create("192.0.2.10"))
        self.assertIsNotNone(claim)
        claim_id = claim["claim_id"]
        secret = claim["claim_secret"]
        self.assertNotEqual(secret, claim["code"])
        self.assertEqual(len(claim["code"]), 6)
        self.assertEqual(asyncio.run(self.manager.collect(claim_id, "wrong")), ("not_found", None))
        self.assertEqual(asyncio.run(self.manager.collect(claim_id, secret))[0], "pending")
        self.assertTrue(
            asyncio.run(
                self.manager.approve(
                    claim["code"],
                    owner_profile_id="owner",
                    session_id="session-1",
                    broadcast_token="runtime-token",
                )
            )
        )
        self.assertFalse(
            asyncio.run(
                self.manager.approve(
                    claim["code"],
                    owner_profile_id="owner",
                    session_id="session-2",
                    broadcast_token="other",
                )
            )
        )
        state, result = asyncio.run(self.manager.collect(claim_id, secret))
        self.assertEqual(state, "approved")
        self.assertEqual(result["session_id"], "session-1")
        self.assertEqual(result["broadcast_token"], "runtime-token")
        self.assertEqual(asyncio.run(self.manager.collect(claim_id, secret)), ("not_found", None))

    def test_expiry_and_per_source_limit_fail_closed(self) -> None:
        with patch.object(handoff.time, "monotonic", return_value=100.0):
            claims = [asyncio.run(self.manager.create("192.0.2.10")) for _ in range(3)]
            self.assertTrue(all(claims))
            self.assertIsNone(asyncio.run(self.manager.create("192.0.2.10")))
            self.assertIsNotNone(asyncio.run(self.manager.create("192.0.2.11")))
        with patch.object(
            handoff.time, "monotonic", return_value=100.0 + handoff.HANDOFF_TTL_SECONDS
        ):
            self.assertEqual(
                asyncio.run(self.manager.collect(claims[0]["claim_id"], claims[0]["claim_secret"])),
                ("not_found", None),
            )
            self.assertFalse(
                asyncio.run(
                    self.manager.approve(
                        claims[0]["code"],
                        owner_profile_id="owner",
                        session_id="session-1",
                        broadcast_token="token",
                    )
                )
            )
            self.assertIsNotNone(asyncio.run(self.manager.create("192.0.2.10")))

    def test_code_must_be_six_ascii_digits(self) -> None:
        for code in ("", "12345", "1234567", "１２３４５６", "ABCDEF"):
            self.assertFalse(
                asyncio.run(
                    self.manager.approve(
                        code, owner_profile_id="owner", session_id="s", broadcast_token="t"
                    )
                )
            )

    def test_clearing_claims_revokes_uncollected_handoff(self) -> None:
        claim = asyncio.run(self.manager.create("192.0.2.10"))
        self.assertTrue(
            asyncio.run(
                self.manager.approve(
                    claim["code"], owner_profile_id="owner", session_id="s", broadcast_token="t"
                )
            )
        )
        asyncio.run(self.manager.clear())
        self.assertEqual(
            asyncio.run(self.manager.collect(claim["claim_id"], claim["claim_secret"])),
            ("not_found", None),
        )

    def test_wrong_code_guesses_are_bounded_per_authenticated_owner(self) -> None:
        with patch.object(handoff.time, "monotonic", return_value=100.0):
            claim = asyncio.run(self.manager.create("192.0.2.10"))
            wrong = "000000"
            for _ in range(handoff.MAX_APPROVAL_ATTEMPTS_PER_OWNER):
                self.assertFalse(
                    asyncio.run(
                        self.manager.approve(
                            wrong, owner_profile_id="owner", session_id="s", broadcast_token="t"
                        )
                    )
                )
            self.assertFalse(
                asyncio.run(
                    self.manager.approve(
                        claim["code"], owner_profile_id="owner", session_id="s", broadcast_token="t"
                    )
                )
            )
            self.assertTrue(
                asyncio.run(
                    self.manager.approve(
                        claim["code"],
                        owner_profile_id="different-owner",
                        session_id="s",
                        broadcast_token="t",
                    )
                )
            )


class BroadcastHandoffOwnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.hass = types.SimpleNamespace(data={})
        self.manager = handoff.broadcast_handoff_manager(self.hass)
        self.claim = asyncio.run(self.manager.create("192.0.2.10"))

    def test_only_exact_active_owner_can_approve_and_owner_never_receives_token(self) -> None:
        payload = {
            "device_id": "djconnect-ios-ABCDEFGHIJKL",
            "client_type": "ios",
            "session_id": "session-1",
            "code": self.claim["code"],
        }
        owner = types.SimpleNamespace(profile_id="profile-owner")
        runtime_manager = types.SimpleNamespace(
            async_broadcast_token_for_owner=lambda **kwargs: self._owner_token(kwargs)
        )

        async def context(*args, **kwargs):
            return object(), owner, None, None

        async def unauthorized(*args, **kwargs):
            return None, None, {"success": False, "error": "unauthorized"}, 401

        with patch.object(handlers, "_session_profile_context", unauthorized):
            result, status = asyncio.run(
                handlers.async_handle_session_broadcast_handoff_approve_payload(self.hass, payload)
            )
            self.assertEqual(status, 401)
            self.assertEqual(result["error"], "unauthorized")
        self.assertEqual(
            asyncio.run(self.manager.collect(self.claim["claim_id"], self.claim["claim_secret"]))[
                0
            ],
            "pending",
        )

        with (
            patch.object(handlers, "_session_profile_context", context),
            patch.object(handlers, "session_runtime_manager", return_value=runtime_manager),
        ):
            result, status = asyncio.run(
                handlers.async_handle_session_broadcast_handoff_approve_payload(self.hass, payload)
            )
            self.assertEqual(status, 200)
            self.assertEqual(
                result, {"success": True, "session_id": "session-1", "handoff": "approved"}
            )
            self.assertNotIn("broadcast_token", result)
            result, status = asyncio.run(
                handlers.async_handle_session_broadcast_handoff_approve_payload(self.hass, payload)
            )
            self.assertEqual(status, 404)
        self.assertEqual(
            asyncio.run(self.manager.collect(self.claim["claim_id"], self.claim["claim_secret"]))[
                1
            ]["broadcast_token"],
            "runtime-token",
        )

    @staticmethod
    async def _owner_token(kwargs):
        if kwargs != {"owner_profile_id": "profile-owner", "session_id": "session-1"}:
            return None
        return {"broadcast_token": "runtime-token"}


if __name__ == "__main__":
    unittest.main()
