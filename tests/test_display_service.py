"""B adapter unit chain with normal request helpers; not live HA proof."""
import importlib
import secrets
import unittest
from unittest.mock import patch

from tests import test_display_authority as authority_tests


class DisplayServiceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        authority_tests.DisplayOwnerPurposeTests.setUpClass()
        cls.module = importlib.import_module("custom_components.djconnect.display_service")

    @classmethod
    def tearDownClass(cls):
        authority_tests.DisplayOwnerPurposeTests.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = authority_tests.DisplayOwnerPurposeTests()
        await self.fixture.asyncSetUp()
        self.manager = self.fixture.manager
        self.service = self.module.DisplayAdmissionService(self.fixture.hass, self.manager)
        self.origin = "https://ha.example.net"
        self.origin_patch = patch.object(self.module, "selected_ha_origin", side_effect=lambda _: self.origin)
        self.origin_patch.start()

    async def asyncTearDown(self):
        self.origin_patch.stop()
        await self.fixture.asyncTearDown()

    async def call(self, action, data=None, *, origins=None, headers=None):
        body = {"contract_version": 1, **(data or {})}
        if action.startswith("owner/"):
            body["identity"] = self.fixture.identity
        return await self.service.post(action, body,
            headers=self.fixture.headers if headers is None else headers,
            origins=[self.origin] if origins is None else origins, source="unit-peer")

    async def admitted(self):
        nonce = secrets.token_urlsafe(32)
        claim = (await self.call("claim", {"browser_nonce": nonce})).payload
        owner_fields = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "code")}
        await self.call("owner/approve", owner_fields | {"session_id": self.fixture.active.session_id,
            "share": {"mode": "create", "consent": True}})
        binding = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "claim_secret")}
        result = await self.call("collect", binding | {"browser_nonce": nonce})
        return result

    async def test_owner_context_absent_origin_requires_real_pairing_and_is_pure(self):
        result = await self.call("owner/context", origins=[])
        self.assertEqual(result.payload["session_id"], self.fixture.active.session_id)
        self.assertFalse(self.manager._display_admission._shares)
        with self.assertRaises(self.module.DisplayAdmissionError):
            await self.call("owner/context", origins=[], headers={})

    async def test_closed_shapes_versions_and_nested_owner_identity(self):
        for action, data in [("claim", {"browser_nonce": secrets.token_urlsafe(32), "profile_id": "other"}),
                             ("claim", {"contract_version": True, "browser_nonce": "x"}),
                             ("owner/resolve", {"code": "１２３４５６"}),
                             ("snapshot", {}), ("session_end", {})]:
            with self.subTest(action=action, data=data), self.assertRaises(self.module.DisplayAdmissionError):
                await self.call(action, data)
        self.assertFalse(self.manager._display_admission._claims)

    async def test_nested_share_malformed_types_are_errors_without_reservations(self):
        nonce = secrets.token_urlsafe(32)
        claim = (await self.call("claim", {"browser_nonce": nonce})).payload
        fields = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "code")}
        for share in ({"mode": []}, {"mode": {}}, {"mode": 1}, {"mode": "create", "consent": 1},
                      {"mode": "existing", "share_id": [], "share_generation": 1}):
            with self.subTest(share=share), self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("owner/approve", fields | {"session_id": self.fixture.active.session_id, "share": share})
        self.assertFalse(self.manager._display_admission._shares)
        self.assertFalse(self.manager._display_admission._displays)

    async def test_display_origin_absent_null_foreign_duplicate_denied(self):
        for origins in ([], ["null"], ["https://other.example.net"], [self.origin, self.origin]):
            with self.subTest(origins=origins), self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("claim", {"browser_nonce": secrets.token_urlsafe(32)}, origins=origins)
        self.assertFalse(self.manager._display_admission._claims)

    async def test_real_unit_pairing_chain_and_renew_read_only_grant(self):
        result = await self.admitted()
        result.release()
        payload = result.payload
        self.assertIn("lease_expires_at", payload)
        self.assertNotIn("profile_id", payload)
        self.assertFalse(payload["capabilities"]["owner_controls"])
        binding = {key: payload[key] for key in ("issuer_epoch", "display_id")}
        headers = {"Authorization": "Bearer " + payload["grant_token"]}
        renewed = await self.call("renew", binding | {"renew_sequence": 1}, headers=headers)
        repeated = await self.call("renew", binding | {"renew_sequence": 1}, headers=headers)
        self.assertEqual(renewed.payload["lease_revision"], repeated.payload["lease_revision"])
        with self.assertRaises(self.module.DisplayAdmissionError):
            await self.call("owner/context", headers=headers)
        await self.call("leave", binding, headers=headers)
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()
        self.assertIsNotNone(self.manager.current_active("profile-a"))

    async def test_origin_change_clears_old_grants_and_never_reuses_epoch(self):
        result = await self.admitted()
        epoch = result.payload["issuer_epoch"]
        self.origin = "https://new.example.net"
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()
        await self.call("owner/context")
        self.assertNotEqual(self.manager._display_admission.issuer_epoch, epoch)
        self.assertFalse(self.manager._display_admission._displays)

    async def test_unavailable_external_origin_fails_closed_and_clears_authority(self):
        await self.admitted()
        self.origin = None
        with self.assertRaises(self.module.DisplayAdmissionError) as failure:
            await self.call("owner/context", origins=[])
        self.assertEqual(failure.exception.code, "display_external_url_unavailable")
        self.assertFalse(self.manager._display_admission._displays)

    async def test_pairing_rotates_between_commit_and_delivery_no_credential_release(self):
        result = await self.admitted()
        self.fixture.runtime.device_token = "rotated-unit"
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()

    async def test_session_ends_between_commit_and_delivery(self):
        result = await self.admitted()
        await self.manager.async_end(owner_profile_id="profile-a", session_id=self.fixture.active.session_id)
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()

    async def test_owner_can_revoke_approved_uncollected_reservation(self):
        nonce = secrets.token_urlsafe(32)
        claim = (await self.call("claim", {"browser_nonce": nonce})).payload
        fields = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "code")}
        approved = await self.call("owner/approve", fields | {"session_id": self.fixture.active.session_id,
            "share": {"mode": "create", "consent": True}})
        await self.call("owner/revoke", {"session_id": self.fixture.active.session_id,
            "share_id": approved.payload["share_id"], "display_id": approved.payload["display_id"]})
        with self.assertRaises(self.module.DisplayAdmissionError):
            approved.release()
        self.assertFalse(self.manager._display_admission._claims)
        self.assertEqual(len(self.manager._display_admission._shares), 1)
