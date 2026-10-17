"""Purpose fences with ordinary unit pairing fixtures, not live HA acceptance."""
import importlib
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures


class DisplayOwnerPurposeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()
        cls.module = importlib.import_module("custom_components.djconnect.display_authority")

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass, self.runtime, _history, self.identity, self.headers = await self.fixture.transport_fixture()
        self.manager = self.fixture.manager
        self.entry = SimpleNamespace(entry_id="owner-entry", data={**self.identity,
            "device_token": self.runtime.device_token}, options={}, disabled_by=None, state="loaded")
        self.runtime.entry = self.entry
        self.runtime._receiver_end_generation = 0
        self.hass.config_entries.async_get_entry = lambda entry_id: self.entry if entry_id == self.entry.entry_id else None
        self.storage = self.hass.data["djconnect"]["djconnect_profile_platform"]
        self.active = await self.manager.async_start(owner_profile_id="profile-a")

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def owner(self, **changes):
        return await self.module.resolve_display_owner(self.hass, self.identity, self.headers, self.manager,
                                                      session_id=changes.get("session_id", self.active.session_id))

    async def test_actual_request_helpers_accept_pairing_without_private_history_access(self):
        from custom_components.djconnect.domain import ProfilePrivacyMode
        await self.storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.SHARED)
        with patch("custom_components.djconnect.session_conversation.async_history_grant_revision",
                   side_effect=AssertionError("B must not read private history grant")):
            context, binding = await self.owner()
        self.assertFalse(context.privacy_policy.allow_personal_read)
        self.assertTrue(binding.valid())
        self.assertNotIn(self.runtime.device_token, repr(binding))

    async def test_bad_pairing_and_client_profile_override_fail_closed(self):
        for identity, headers in [(self.identity, {}), (self.identity, {"Authorization": "Bearer djcd_fake"}),
                                  (self.identity | {"profile_id": "other"}, self.headers),
                                  (self.identity | {"client_type": "watchos"}, self.headers)]:
            with self.subTest(identity=identity), self.assertRaises(self.module.DisplayAdmissionError):
                await self.module.resolve_display_owner(self.hass, identity, headers, self.manager,
                                                       session_id=self.active.session_id)

    async def test_wrong_session_cannot_obtain_owner_stamp(self):
        with self.assertRaises(self.module.DisplayAdmissionError):
            await self.owner(session_id="not-owned")

    async def test_token_rotation_entry_generation_and_unload_revoke_old_stamp(self):
        _context, binding = await self.owner()
        self.runtime.device_token = "rotated-synthetic-token"
        self.entry.data["device_token"] = self.runtime.device_token
        self.assertFalse(binding.valid())
        self.runtime.device_token = "synthetic-fixture-token"
        self.entry.data["device_token"] = self.runtime.device_token
        await self.manager.async_invalidate_receiver_entry("owner-entry")
        self.assertFalse(binding.valid())
        self.manager._receiver_entry_generations["owner-entry"] = 0  # Independent branch unit only.
        self.hass.data["djconnect"].pop("owner-entry")
        self.assertFalse(binding.valid())

    async def test_profile_reassignment_back_does_not_resurrect_generation(self):
        _context, binding = await self.owner()
        await self.storage.async_create_profile("Other", profile_id="profile-b", default_backend_id="later_manual")
        await self.storage.async_upsert_device(self.identity["device_id"], "ios", linked_profile_id="profile-b")
        self.assertFalse(binding.valid())
        await self.storage.async_upsert_device(self.identity["device_id"], "ios", linked_profile_id="profile-a")
        self.assertFalse(binding.valid())

    async def test_source_and_privacy_changes_are_separate_from_history_consent(self):
        from custom_components.djconnect.domain import ProfilePrivacyMode
        _context, binding = await self.owner()
        profile = self.storage.household.profiles["profile-a"]
        await self.storage.async_update_profile("profile-a", preferences=replace(profile.preferences,
            default_backend_id="source-spotify", default_music_account_id="source-account"))
        self.assertFalse(binding.valid())
        _context, current = await self.owner()
        self.assertTrue(current.valid())
        await self.storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.PRIVATE)
        self.assertFalse(current.valid())

    async def test_awaited_profile_resolution_rechecks_pairing_before_commit(self):
        from custom_components.djconnect import profile_context
        original = profile_context.async_resolve_device_bound_request_context
        async def changed(*args, **kwargs):
            result = await original(*args, **kwargs)
            self.entry.disabled_by = "synthetic-disabled"
            return result
        with patch.object(profile_context, "async_resolve_device_bound_request_context", changed):
            with self.assertRaises(self.module.DisplayAdmissionError):
                await self.owner()

    async def test_original_token_cannot_inherit_repair_during_profile_await(self):
        from custom_components.djconnect import profile_context
        original = profile_context.async_resolve_device_bound_request_context
        async def repaired(*args, **kwargs):
            result = await original(*args, **kwargs)
            self.runtime.device_token = "new-pairing-synthetic-token"
            self.entry.data["device_token"] = self.runtime.device_token
            return result
        with patch.object(profile_context, "async_resolve_device_bound_request_context", repaired):
            with self.assertRaises(self.module.DisplayAdmissionError):
                await self.owner()

    async def test_privacy_and_source_aba_without_intermediate_read_are_terminal(self):
        from custom_components.djconnect.domain import ProfilePrivacyMode
        _context, binding = await self.owner()
        await self.storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.PRIVATE)
        await self.storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.NORMAL)
        self.assertFalse(binding.valid())
        _context, binding = await self.owner()
        original = self.storage.household.profiles["profile-a"].preferences
        await self.storage.async_update_profile("profile-a", preferences=replace(original,
            default_backend_id="source-spotify", default_music_account_id="source-account"))
        await self.storage.async_update_profile("profile-a", preferences=original)
        self.assertFalse(binding.valid())

    async def test_observed_authority_failure_latches_even_if_runtime_fields_revert(self):
        _context, binding = await self.owner()
        token = self.runtime.device_token
        self.runtime.device_token = "synthetic-rotated-token"
        self.entry.data["device_token"] = self.runtime.device_token
        self.assertFalse(binding.valid())
        self.runtime.device_token = token
        self.entry.data["device_token"] = token
        self.assertFalse(binding.valid())

    async def test_session_end_invalidates_stamp_without_stopping_other_sessions(self):
        _context, binding = await self.owner()
        await self.manager.async_start(owner_profile_id="other-profile")
        await self.manager.async_end(owner_profile_id="profile-a", session_id=self.active.session_id)
        self.assertFalse(binding.valid())
        self.assertIsNotNone(self.manager.current_active("other-profile"))
