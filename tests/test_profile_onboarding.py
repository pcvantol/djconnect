"""Behavioral regression for explicit household Profile onboarding."""

from __future__ import annotations

import asyncio
import importlib
import types
import unittest

from tests.test_config_flow_helpers import install_homeassistant_stubs


class ProfileOnboardingTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_homeassistant_stubs()
        cls.flow_module = importlib.import_module("custom_components.djconnect.config_flow")

    def flow(self, hass=None, device="djconnect-ios-NEWDEVICE123"):
        flow = self.flow_module.DJConnectConfigFlow()
        flow.hass = hass or types.SimpleNamespace(
            config=types.SimpleNamespace(language="nl"), data={}
        )
        flow._pairing = {"device_id": device, "client_type": "ios", "device_name": "New device"}
        return flow

    async def test_existing_household_gets_choice_before_backend(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        profile = await manager.async_create_profile("Home")
        result = await flow.async_step_profile_choice()
        self.assertEqual(result["step_id"], "profile_choice")
        schema = {m.key: v for m, v in result["data_schema"].schema.items()}
        self.assertIn("profile_id", schema)
        self.assertIn(
            profile.profile_id, [o["value"] for o in schema["profile_id"].config.kwargs["options"]]
        )
        self.assertNotIn("spotify_client_id", schema)

    async def test_duplicate_name_has_field_error_and_no_household_mutation(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        await manager.async_create_profile("Home")
        before = manager.household
        result = await flow.async_step_profile_setup(
            {"profile_name": " home ", "profile_type": "personal", "require_profile": False}
        )
        self.assertEqual(result["errors"], {"profile_name": "profile_name_exists"})
        self.assertEqual(manager.household, before)

    async def test_new_profile_is_only_draft_until_final_confirmation(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        before = await manager.async_load()
        result = await flow.async_step_profile_setup(
            {"profile_name": "New listener", "profile_type": "personal", "require_profile": False}
        )
        self.assertEqual(result["step_id"], "backend")
        self.assertEqual(manager.household, before)

    async def test_manual_reuse_preserves_profile_and_fallback_until_commit(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        profile = await manager.async_create_profile("Shared home")
        await manager.async_upsert_device(
            "djconnect-macos-OLDDEVICE123", "macos", linked_profile_id=profile.profile_id
        )
        before = manager.household
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["step_id"], "voice")
        self.assertEqual(manager.household, before)
        result = await flow.async_step_voice({})
        self.assertEqual(result["type"], "create_entry")
        after = manager.household
        self.assertEqual(after.profiles, before.profiles)
        self.assertEqual(after.fallback, before.fallback)
        self.assertEqual(after.music_accounts, before.music_accounts)
        self.assertEqual(
            after.devices["djconnect-macos-OLDDEVICE123"],
            before.devices["djconnect-macos-OLDDEVICE123"],
        )
        self.assertEqual(
            after.devices["djconnect-ios-NEWDEVICE123"].linked_profile_id, profile.profile_id
        )
        self.assertEqual(result["data"]["profile_id"], profile.profile_id)

    async def test_removed_selection_refreshes_choice_without_mutation(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        result = await flow.async_step_profile_choice({"profile_id": "profile-gone"})
        self.assertEqual(result["errors"], {"profile_id": "profile_unavailable"})
        self.assertFalse(manager.household.profiles)
        self.assertFalse(manager.household.devices)

    async def provider_profile(self, flow, backend="spotify_direct"):
        from custom_components.djconnect.domain.backend import BackendProvider
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.domain.profile import ProfilePreferences

        manager = self.flow_module._profile_storage(flow.hass)
        await manager.async_upsert_music_backend(
            backend, BackendProvider(backend), display_name="Existing connection"
        )
        profile = await manager.async_create_profile(
            "Existing listener", default_backend_id=backend
        )
        account = await manager.async_upsert_music_account(
            "account-existing",
            backend,
            kind=MusicAccountKind.PERSONAL,
            display_name="Existing account",
            linked_profile_ids=frozenset({profile.profile_id}),
        )
        profile = await manager.async_update_profile(
            profile.profile_id,
            preferences=ProfilePreferences(
                default_backend_id=backend, default_music_account_id=account.account_id
            ),
        )
        await manager.async_upsert_device(
            "djconnect-macos-OLDDEVICE123", "macos", linked_profile_id=profile.profile_id
        )
        owner = types.SimpleNamespace(
            entry_id="owner-entry",
            disabled_by=None,
            data={
                "device_id": "djconnect-macos-OLDDEVICE123",
                "profile_id": profile.profile_id,
                "music_account_id": account.account_id,
                "music_backend": backend,
                "spotify_client_id": "synthetic-client",
                "spotify_refresh_token": "synthetic-token",
                "music_assistant_player": "media_player.synthetic",
            },
            options={},
        )
        entries = [owner]
        flow.hass.config_entries = types.SimpleNamespace(async_entries=lambda _: entries)
        flow.hass.data["djconnect"][owner.entry_id] = types.SimpleNamespace(
            entry=owner, config=owner.data
        )
        return manager, profile, owner, entries

    async def test_spotify_reuse_skips_oauth_and_never_copies_credentials(self):
        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        before = manager.household
        owner_before = dict(owner.data)
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["step_id"], "voice")
        self.assertFalse(flow._spotify)
        result = await flow.async_step_voice({})
        self.assertEqual(result["data"]["profile_backend_entry_id"], owner.entry_id)
        self.assertNotIn("spotify_refresh_token", result["data"])
        self.assertNotIn("spotify_client_id", result["data"])
        self.assertEqual(owner.data, owner_before)
        self.assertEqual(manager.household.profiles, before.profiles)
        self.assertEqual(manager.household.music_backends, before.music_backends)
        self.assertEqual(manager.household.music_accounts, before.music_accounts)
        self.assertEqual(manager.household.fallback, before.fallback)

    async def test_music_assistant_reuse_keeps_existing_player_connection(self):
        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow, "music_assistant")
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["step_id"], "voice")
        result = await flow.async_step_voice({})
        self.assertEqual(result["data"]["music_backend"], "music_assistant")
        self.assertEqual(result["data"]["profile_backend_entry_id"], owner.entry_id)
        self.assertNotIn("music_assistant_player", result["data"])

    async def test_provider_reference_resolves_live_owner_and_denies_cross_profile(self):
        from custom_components.djconnect.profile_backend import profile_backend_runtime
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError

        flow = self.flow()
        manager, profile, owner, entries = await self.provider_profile(flow)
        await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        result = await flow.async_step_voice({})
        entry = types.SimpleNamespace(entry_id="new-entry", data=result["data"], options={})
        runtime = types.SimpleNamespace(entry=entry, config=entry.data)
        source = profile_backend_runtime(flow.hass, runtime)
        self.assertIs(source.provider, flow.hass.data["djconnect"]["owner-entry"])
        self.assertIs(source.caller, runtime)
        owner.data["spotify_refresh_token"] = "rotated-synthetic"
        self.assertEqual(
            profile_backend_runtime(flow.hass, runtime).config["spotify_refresh_token"],
            "rotated-synthetic",
        )
        other = await manager.async_create_profile("Other person")
        runtime.profile_context_profile_id = other.profile_id
        with self.assertRaises(ProfileStorageValidationError):
            profile_backend_runtime(flow.hass, runtime)
        del runtime.profile_context_profile_id
        entries.clear()
        with self.assertRaises(ProfileStorageValidationError):
            profile_backend_runtime(flow.hass, runtime)

    async def test_changed_profile_requires_fresh_selection_and_no_mapping(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        profile = await manager.async_create_profile("Home")
        await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        await manager.async_update_profile(profile.profile_id, display_name="Renamed home")
        before = manager.household
        result = await flow.async_step_voice({})
        self.assertEqual(result["step_id"], "profile_choice")
        self.assertEqual(result["errors"], {"profile_id": "profile_unavailable"})
        self.assertEqual(manager.household, before)
        options = next(iter(result["data_schema"].schema.values())).config.kwargs["options"]
        self.assertIn({"value": profile.profile_id, "label": "Renamed home"}, options)

    async def test_concurrent_new_name_only_commits_one_profile(self):
        first = self.flow()
        second = self.flow(first.hass, "djconnect-ios-SECOND123456")
        draft = {"profile_name": "Same name", "profile_type": "personal", "require_profile": False}
        for flow in (first, second):
            await flow.async_step_profile_setup(draft)
            await flow.async_step_backend({"music_backend": "later_manual"})
        results = await asyncio.gather(first.async_step_voice({}), second.async_step_voice({}))
        self.assertEqual(sum(r["type"] == "create_entry" for r in results), 1)
        failed = next(r for r in results if r["type"] == "form")
        self.assertEqual(failed["errors"], {"profile_name": "profile_name_exists"})
        household = self.flow_module._profile_storage(first.hass).household
        self.assertEqual(len(household.profiles), 1)
        self.assertEqual(len(household.devices), 1)

    async def test_duplicate_name_can_recover_to_existing_profile_on_same_form(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        profile = await manager.async_create_profile("Home")
        error = await flow.async_step_profile_setup(
            {"profile_name": "HOME", "profile_type": "personal"}
        )
        self.assertEqual(error["errors"], {"profile_name": "profile_name_exists"})
        result = await flow.async_step_profile_setup(
            {"profile_id": profile.profile_id, "profile_name": "HOME", "profile_type": "personal"}
        )
        self.assertEqual(result["step_id"], "voice")
        result = await flow.async_step_voice({})
        self.assertEqual(result["data"]["profile_id"], profile.profile_id)
        self.assertEqual(len(manager.household.profiles), 1)

    async def test_back_to_new_choice_keeps_cancelled_draft_unpersisted(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        await flow.async_step_profile_setup(
            {"profile_name": "Abandoned", "profile_type": "personal"}
        )
        await flow.async_step_profile_choice({"profile_id": "new"})
        self.assertFalse(manager.household.profiles)
        self.assertFalse(manager.household.music_backends)
        await flow.async_step_profile_setup(
            {"profile_name": "Replacement", "profile_type": "personal"}
        )
        await flow.async_step_backend({"music_backend": "later_manual"})
        await flow.async_step_voice({})
        self.assertEqual(
            [p.display_name for p in manager.household.profiles.values()], ["Replacement"]
        )

    async def test_new_profile_does_not_replace_existing_household_fallback(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        await manager.async_create_profile("Existing fallback")
        before = manager.household.fallback
        await flow.async_step_profile_setup(
            {"profile_name": "Another", "profile_type": "personal", "require_profile": False}
        )
        await flow.async_step_backend({"music_backend": "later_manual"})
        await flow.async_step_voice({})
        self.assertEqual(manager.household.fallback, before)

    async def test_store_failure_retains_exact_household_and_retry_form(self):
        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        before = await manager.async_load()

        class FailingStore:
            async def async_save(self, data):
                raise OSError("synthetic persistence failure")

        manager._store = FailingStore()
        await flow.async_step_profile_setup(
            {"profile_name": "Not committed", "profile_type": "personal"}
        )
        await flow.async_step_backend({"music_backend": "later_manual"})
        result = await flow.async_step_voice({})
        self.assertEqual(result["step_id"], "voice")
        self.assertEqual(result["errors"], {"base": "profile_setup_failed"})
        self.assertEqual(manager.household, before)

    async def test_ambiguous_provider_owner_and_disabled_profile_are_not_reused(self):
        from dataclasses import replace

        flow = self.flow()
        manager, profile, owner, entries = await self.provider_profile(flow)
        entries.append(
            types.SimpleNamespace(
                entry_id="second-owner", disabled_by=None, data=dict(owner.data), options={}
            )
        )
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["errors"], {"profile_id": "profile_connection_unavailable"})
        self.assertNotIn("djconnect-ios-NEWDEVICE123", manager.household.devices)
        from custom_components.djconnect.domain.profile import ProfileState

        manager._household = replace(
            manager.household,
            profiles={profile.profile_id: replace(profile, state=ProfileState.DISABLED)},
        )
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["errors"], {"profile_id": "profile_unavailable"})

    async def test_removed_device_mapping_cannot_revive_stale_entry_profile_id(self):
        from custom_components.djconnect.profile_backend import profile_backend_runtime
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError
        from dataclasses import replace

        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        result = await flow.async_step_voice({})
        entry = types.SimpleNamespace(entry_id="new-entry", data=result["data"], options={})
        runtime = types.SimpleNamespace(entry=entry, config=entry.data)
        devices = dict(manager.household.devices)
        devices.pop(owner.data["device_id"])
        manager._household = replace(manager.household, devices=devices)
        with self.assertRaises(ProfileStorageValidationError):
            profile_backend_runtime(flow.hass, runtime)

    def test_shared_client_options_do_not_offer_separate_spotify_reauthorization(self):
        flow = self.flow()
        choices = self.flow_module._options_actions_for_status(
            flow.hass,
            {"music_backend": "spotify_direct", "profile_backend_entry_id": "owner-entry"},
        )
        self.assertNotIn(self.flow_module.OPTIONS_ACTION_SPOTIFY_REAUTH, choices)
        owner_choices = self.flow_module._options_actions_for_status(
            flow.hass, {"music_backend": "spotify_direct"}
        )
        self.assertIn(self.flow_module.OPTIONS_ACTION_SPOTIFY_REAUTH, owner_choices)

    async def test_provider_view_keeps_caller_context_and_state_but_shares_token_owner(self):
        from custom_components.djconnect.profile_backend import profile_backend_runtime

        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        result = await flow.async_step_voice({})
        entry = types.SimpleNamespace(entry_id="new-entry", data=result["data"], options={})
        caller = types.SimpleNamespace(
            entry=entry,
            config=entry.data,
            profile_context_profile_id=profile.profile_id,
            last_playback={"title": "Caller playback"},
            device_status={"caller": True},
        )
        source = flow.hass.data["djconnect"][owner.entry_id]
        source.profile_context_profile_id = "unrelated-stale-context"
        source.device_status = {"source": True}
        view = profile_backend_runtime(flow.hass, caller)
        self.assertEqual(view.profile_context_profile_id, profile.profile_id)
        self.assertIs(view.device_status, caller.device_status)
        self.assertEqual(view.config["device_id"], entry.data["device_id"])
        self.assertEqual(view.config["spotify_refresh_token"], "synthetic-token")
        view.spotify_access_token = "cached-synthetic"
        self.assertEqual(source.spotify_access_token, "cached-synthetic")
        self.assertFalse(hasattr(caller, "spotify_access_token"))
        view.last_playback = {"title": "Updated caller"}
        self.assertEqual(caller.last_playback, {"title": "Updated caller"})
        self.assertFalse(hasattr(source, "last_playback"))
        self.assertIs(view.entry, owner)
        again = profile_backend_runtime(flow.hass, view)
        self.assertIs(again.caller, caller)
        self.assertIs(again.provider, source)

    async def test_cancel_during_final_write_restores_disk_and_never_exposes_draft(self):
        from custom_components.djconnect.domain.storage import household_to_storage

        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        before = await manager.async_load()
        started = asyncio.Event()
        release = asyncio.Event()

        class DelayedStore:
            def __init__(self):
                self.writes = []

            async def async_save(self, data):
                if not self.writes:
                    started.set()
                    await release.wait()
                self.writes.append(data)

        store = DelayedStore()
        manager._store = store
        await flow.async_step_profile_setup(
            {"profile_name": "Cancelled draft", "profile_type": "personal"}
        )
        await flow.async_step_backend({"music_backend": "later_manual"})
        task = asyncio.create_task(flow.async_step_voice({}))
        await started.wait()
        self.assertEqual(manager.household, before)
        task.cancel()
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(manager.household, before)
        self.assertEqual(store.writes[-1], household_to_storage(before))

    async def test_concurrent_options_edit_survives_aborted_onboarding_commit(self):
        from custom_components.djconnect.domain.storage import household_to_storage

        flow = self.flow()
        manager = self.flow_module._profile_storage(flow.hass)
        original = await manager.async_create_profile("Original")
        started = asyncio.Event()
        release = asyncio.Event()

        class DelayedStore:
            def __init__(self):
                self.writes = []

            async def async_save(self, data):
                if not self.writes:
                    started.set()
                    await release.wait()
                self.writes.append(data)

        store = DelayedStore()
        manager._store = store
        await flow.async_step_profile_setup({"profile_name": "Draft", "profile_type": "personal"})
        await flow.async_step_backend({"music_backend": "later_manual"})
        task = asyncio.create_task(flow.async_step_voice({}))
        await started.wait()
        edit = asyncio.create_task(
            manager.async_update_profile(original.profile_id, display_name="Renamed concurrently")
        )
        await asyncio.sleep(0)
        release.set()
        result = await task
        await edit
        self.assertEqual(result["errors"], {"base": "profile_setup_failed"})
        self.assertEqual(len(manager.household.profiles), 1)
        self.assertEqual(
            manager.household.profiles[original.profile_id].display_name, "Renamed concurrently"
        )
        self.assertFalse(manager.household.devices)
        self.assertEqual(store.writes[-1], household_to_storage(manager.household))

    async def test_retained_provider_view_rejects_unload_replacement_and_disabled_account(self):
        from custom_components.djconnect.profile_backend import profile_backend_runtime
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError
        from custom_components.djconnect.domain.music_account import MusicAccountState
        from dataclasses import replace

        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        result = await flow.async_step_voice({})
        caller = types.SimpleNamespace(
            entry=types.SimpleNamespace(data=result["data"], options={}), config=result["data"]
        )
        source = flow.hass.data["djconnect"][owner.entry_id]
        source.spotify_access_token = "cached-synthetic"
        view = profile_backend_runtime(flow.hass, caller)
        flow.hass.data["djconnect"].pop(owner.entry_id)
        for getter in [lambda: view.config, lambda: view.entry, lambda: view.spotify_access_token]:
            with self.assertRaises(ProfileStorageValidationError):
                getter()
        flow.hass.data["djconnect"][owner.entry_id] = types.SimpleNamespace(
            entry=owner, config=owner.data
        )
        with self.assertRaises(ProfileStorageValidationError):
            _ = view.config
        with self.assertRaises(ProfileStorageValidationError):
            profile_backend_runtime(flow.hass, view)
        flow.hass.data["djconnect"][owner.entry_id] = source
        account = manager.household.music_accounts["account-existing"]
        manager._household = replace(
            manager.household,
            music_accounts={account.account_id: replace(account, state=MusicAccountState.DISABLED)},
        )
        with self.assertRaises(ProfileStorageValidationError):
            _ = view.spotify_access_token

    async def test_legacy_missing_account_id_cannot_bind_other_same_backend_account(self):
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.domain.profile import ProfilePreferences

        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        owner.data.pop("music_account_id")
        other = await manager.async_upsert_music_account(
            "account-other",
            "spotify_direct",
            kind=MusicAccountKind.PERSONAL,
            display_name="Other account",
            linked_profile_ids=frozenset({profile.profile_id}),
        )
        await manager.async_update_profile(
            profile.profile_id,
            preferences=ProfilePreferences(
                default_backend_id="spotify_direct", default_music_account_id=other.account_id
            ),
        )
        before = manager.household
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["errors"], {"profile_id": "profile_connection_unavailable"})
        self.assertEqual(manager.household, before)

    async def test_closed_legacy_assist_account_chain_is_reusable_without_oauth(self):
        from dataclasses import replace

        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        original = manager.household.music_accounts["account-existing"]
        canonical = f"account-spotify_direct-{profile.profile_id}"
        account = replace(original, account_id=canonical, provider_account_id="synthetic-client")
        profile = replace(
            profile, preferences=replace(profile.preferences, default_music_account_id=canonical)
        )
        manager._household = replace(
            manager.household,
            profiles={profile.profile_id: profile},
            music_accounts={canonical: account},
        )
        owner.data.pop("music_account_id")
        result = await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        self.assertEqual(result["step_id"], "voice")
        self.assertFalse(flow._spotify)

    async def test_retained_view_rejects_config_entry_unloading_before_registry_removal(self):
        from custom_components.djconnect.profile_backend import profile_backend_runtime
        from custom_components.djconnect.domain.storage import ProfileStorageValidationError

        flow = self.flow()
        manager, profile, owner, _ = await self.provider_profile(flow)
        await flow.async_step_profile_choice({"profile_id": profile.profile_id})
        result = await flow.async_step_voice({})
        caller = types.SimpleNamespace(
            entry=types.SimpleNamespace(data=result["data"], options={}), config=result["data"]
        )
        view = profile_backend_runtime(flow.hass, caller)
        owner.state = types.SimpleNamespace(value="unload_in_progress")
        with self.assertRaises(ProfileStorageValidationError):
            _ = view.entry
