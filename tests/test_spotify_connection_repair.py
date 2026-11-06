"""Causal recovery tests: fresh OAuth, same current Profile, no donor credentials."""

import importlib
import types
import unittest
from dataclasses import replace

from tests.test_config_flow_helpers import install_homeassistant_stubs


class SpotifyConnectionRepairTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_homeassistant_stubs()
        cls.repair = importlib.import_module(
            "custom_components.djconnect.spotify_connection_repair"
        )
        cls.flow = importlib.import_module("custom_components.djconnect.config_flow")

    async def asyncSetUp(self):
        from custom_components.djconnect.domain.storage import ProfilePlatformStorage, STORE_KEY
        from custom_components.djconnect.domain import BackendProvider
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        self.manager = ProfilePlatformStorage()
        profile = await self.manager.async_create_profile("DEFAULT")
        self.profile = profile.profile_id
        self.device = "djconnect-raspberry-pi-ABCDEFGHIJKL"
        await self.manager.async_upsert_device(
            self.device, "raspberry_pi", linked_profile_id=self.profile
        )
        backend = await self.manager.async_upsert_music_backend(
            "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Spotify"
        )
        account = await self.manager.async_upsert_music_account(
            "account-default",
            "spotify_direct",
            kind=MusicAccountKind.PERSONAL,
            display_name="Spotify",
            linked_profile_ids=frozenset({self.profile}),
            provider_account_id="a" * 32,
        )
        await self.manager.async_bind_device_profile_backend(
            self.device, "raspberry_pi", backend, account=account
        )
        self.entry = types.SimpleNamespace(
            entry_id="paired-pi",
            disabled_by=None,
            data={
                "device_id": self.device,
                "client_type": "raspberry_pi",
                "profile_backend_entry_id": "missing-owner",
                "profile_id": "previous-profile",
                "ha_external_url": "https://ha.example",
                "spotify_refresh_token": "unusable-donor",
            },
            options={},
        )
        self.entries = [self.entry]
        self.hass = types.SimpleNamespace(
            data={"djconnect": {STORE_KEY: self.manager}},
            config_entries=types.SimpleNamespace(
                async_entries=lambda domain: self.entries,
                async_get_entry=lambda key: next(
                    (e for e in self.entries if e.entry_id == key), None
                ),
            ),
            config=types.SimpleNamespace(language="en"),
        )

    def test_candidate_uses_current_profile_not_stale_entry_or_donor_credentials(self):
        result = self.repair.binding(self.hass, self.entry)
        self.assertEqual(result["profile_id"], self.profile)
        self.assertEqual(result["client_id"], "a" * 32)
        self.assertNotIn("unusable-donor", repr(result))
        self.assertIn(
            "spotify_reauthorize", self.flow._options_actions_for_status(self.hass, self.entry.data)
        )

    def test_existing_disabled_original_owner_prevents_takeover(self):
        self.entries.append(types.SimpleNamespace(entry_id="missing-owner", disabled_by="user"))
        self.assertIsNone(self.repair.binding(self.hass, self.entry))

    def test_another_same_profile_owner_prevents_takeover_even_disabled(self):
        self.entries.append(
            types.SimpleNamespace(
                entry_id="another",
                disabled_by="user",
                data={"device_id": self.device, "music_backend": "spotify_direct"},
                options={},
            )
        )
        self.assertIsNone(self.repair.binding(self.hass, self.entry))

    def test_profile_reassignment_during_oauth_rejects_commit(self):
        expected = self.repair.binding(self.hass, self.entry)
        h = self.manager.household
        d = h.devices[self.device]
        self.manager._household = replace(
            h, devices={self.device: replace(d, linked_profile_id="other")}
        )
        with self.assertRaisesRegex(ValueError, "profile_connection_unavailable"):
            self.repair.repaired_config(self.hass, self.entry, expected, "a" * 32)

    def test_owner_appearing_during_oauth_rejects_commit(self):
        expected = self.repair.binding(self.hass, self.entry)
        self.entries.append(types.SimpleNamespace(entry_id="missing-owner"))
        with self.assertRaises(ValueError):
            self.repair.repaired_config(self.hass, self.entry, expected, "a" * 32)

    def test_account_changed_during_oauth_rejects_commit(self):
        expected = self.repair.binding(self.hass, self.entry)
        h = self.manager.household
        a = h.music_accounts["account-default"]
        self.manager._household = replace(
            h, music_accounts={"account-default": replace(a, provider_account_id="b" * 32)}
        )
        with self.assertRaises(ValueError):
            self.repair.repaired_config(self.hass, self.entry, expected, "a" * 32)

    def test_only_exact_fresh_grant_can_commit_and_old_overrides_are_removed(self):
        self.entry.options = {
            "spotify_refresh_token": "old-override",
            "spotify_client_id": "old-app",
            "api_base_url": "keep",
        }
        expected = self.repair.binding(self.hass, self.entry)
        with self.assertRaises(ValueError):
            self.repair.repaired_config(self.hass, self.entry, expected, "b" * 32)
        data, options = self.repair.repaired_config(self.hass, self.entry, expected, "a" * 32)
        self.assertNotIn("profile_backend_entry_id", data)
        self.assertEqual(data["profile_id"], self.profile)
        self.assertEqual(data["music_account_id"], "account-default")
        self.assertEqual(options, {"api_base_url": "keep"})
        self.assertEqual(self.entry.options["spotify_refresh_token"], "old-override")

    async def test_normal_options_flow_stages_identity_only_and_new_pkce_grant(self):
        flow = self.flow.DJConnectOptionsFlow(self.entry)
        flow.hass = self.hass
        flow.flow_id = "repair-flow"
        result = await flow.async_step_spotify_reauth()
        self.assertEqual(result["type"], "external")
        pending = self.hass.data["djconnect"]["spotify_oauth_pending"][flow._oauth["state"]]
        self.assertEqual(
            pending["profile_connection_repair"], self.repair.binding(self.hass, self.entry)
        )
        self.assertEqual(pending["client_id"], "a" * 32)
        self.assertNotIn("unusable-donor", repr(pending))
        self.assertTrue(pending["code_verifier"])
        self.assertEqual(self.entry.data["profile_backend_entry_id"], "missing-owner")

    def test_entry_replacement_and_disabled_client_cannot_repair(self):
        self.entries.clear()
        self.assertIsNone(self.repair.binding(self.hass, self.entry))
        self.entries.append(self.entry)
        self.entry.disabled_by = "user"
        self.assertIsNone(self.repair.binding(self.hass, self.entry))

    async def test_profile_reassignment_and_return_does_not_revive_old_flow(self):
        expected = self.repair.binding(self.hass, self.entry)
        other = await self.manager.async_create_profile("Other")
        await self.manager.async_upsert_device(
            self.device, "raspberry_pi", linked_profile_id=other.profile_id
        )
        await self.manager.async_upsert_device(
            self.device, "raspberry_pi", linked_profile_id=self.profile
        )
        self.assertNotEqual(
            self.repair.binding(self.hass, self.entry)["binding_generation"],
            expected["binding_generation"],
        )
        with self.assertRaises(ValueError):
            self.repair.repaired_config(self.hass, self.entry, expected, "a" * 32)
