"""Real SQLite archive and common paired AskDJ application; synthetic provider boundary."""

import asyncio
from dataclasses import replace
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures


class HistoricalPlaybackApplicationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()
        cls.core = importlib.import_module("custom_components.djconnect.ask_dj")
        cls.dialogue = importlib.import_module("custom_components.djconnect.ask_dj.dialogue")
        cls.pipeline = importlib.import_module("custom_components.djconnect.pipeline")

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = fixtures.SessionConversationHistoryTest()
        await self.f.asyncSetUp()
        (
            self.hass,
            self.runtime,
            self.history,
            self.identity,
            self.headers,
        ) = await self.f.transport_fixture()
        self.storage = self.hass.data["djconnect"]["djconnect_profile_platform"]
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        await self.storage.async_upsert_music_account(
            "source-account",
            "source-spotify",
            kind=MusicAccountKind.PERSONAL,
            display_name="Synthetic original account",
            linked_profile_ids=frozenset({"profile-a"}),
            provider_account_id="provider-original",
        )
        await self.storage.async_update_profile(
            "profile-a",
            preferences=replace(
                self.storage.household.profiles["profile-a"].preferences,
                default_backend_id="source-spotify",
                default_music_account_id="source-account",
            ),
        )
        self.source = SimpleNamespace(
            entry_id="source-entry",
            data={
                "music_backend": "source-spotify",
                "music_account_id": "source-account",
                "profile_id": "profile-a",
                "spotify_refresh_token": "synthetic-no-network",
            },
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.owner = SimpleNamespace(
            entry_id="owner-entry",
            data={
                **self.identity,
                "device_token": self.runtime.device_token,
                "profile_backend_entry_id": "source-entry",
                "music_account_id": "source-account",
                "music_backend": "source-spotify",
            },
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.provider = SimpleNamespace(
            entry=self.source,
            config={"music_backend": "spotify_direct", "music_account_id": "source-account"},
            _receiver_end_generation=0,
        )
        self.runtime.entry = self.owner
        self.runtime._receiver_end_generation = 0
        self.hass.data["djconnect"]["source-entry"] = self.provider
        entries = {"source-entry": self.source, "owner-entry": self.owner}
        self.hass.config_entries.async_entries = lambda domain: list(entries.values())
        self.hass.config_entries.async_get_entry = entries.get
        self.runtime.config.update(
            music_backend="spotify_direct", music_account_id="source-account"
        )
        self.runtime.update = lambda **kw: [setattr(self.runtime, k, v) for k, v in kw.items()]
        source = {
            "backend_id": "source-spotify",
            "music_account_id": "source-account",
            "provider_entry_id": "source-entry",
            "provider_account_id": "provider-original",
        }
        old = await self.f.manager.async_start(
            owner_profile_id="profile-a",
            music_backend="spotify_direct",
            history_source_context=source,
        )
        await self.f.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=old.session_id,
            state="playing",
            media_identity="spotify:track:" + "A" * 22,
            title="Synthetic original recording",
            artist="Synthetic original artist",
            album="Synthetic original edition",
            album_uri="spotify:album:" + "B" * 22,
        )
        self.rows = await self.f.repo.async_entry_records("profile-a", old.session_id)
        row = next(r for r in self.rows if r["kind"] == "playback_observed")
        self.reference = {
            "schema_version": 1,
            "session_id": old.session_id,
            "entry_id": row["entry_id"],
        }
        await self.f.manager.async_end(owner_profile_id="profile-a", session_id=old.session_id)
        self.current = await self.f.manager.async_start(
            owner_profile_id="profile-a",
            music_backend="spotify_direct",
            history_source_context=source,
        )
        await self.f.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=self.current.session_id,
            state="playing",
            media_identity="spotify:track:" + "Z" * 22,
            title="Different current recording",
            artist="Different artist",
        )
        self.effects = []
        self.no_output = False
        self.before_dispatch = None
        self.before_inventory = None

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def backend(self, hass, runtime, command, value=None, **kwargs):
        turn = self.dialogue.current_turn.get()
        if command in {"play", "set_output"}:
            if self.before_dispatch:
                await self.before_dispatch()
            await turn.guard()
            if command == "play":
                turn.require_effect("play", media=(value,), output_id=turn.play_output_id)
                if self.no_output:
                    # Other owning fixtures reload the provider module. Raise the
                    # exact class owned by the real HTTP adapter being exercised.
                    raise self.f.http.SpotifyBackendError("No active device found", http_status=404)
            if not turn.effect_started:
                await turn.before_effect()
            self.effects.append((command, value))
            return {
                "success": True,
                "playback": {
                    "uri": "spotify:track:" + "A" * 22,
                    "is_playing": True,
                    "device": {"id": "speaker-original"},
                },
            }
        if command == "status":
            return {
                "success": True,
                "playback": {"uri": "spotify:track:" + "Z" * 22, "is_playing": True},
            }
        if command == "devices":
            if self.before_inventory:
                await self.before_inventory()
            return {
                "success": True,
                "devices": [
                    {
                        "id": "speaker-original",
                        "name": "Synthetic output",
                        "is_active": False,
                        "is_restricted": False,
                    }
                ],
            }
        self.fail("Unexpected provider command: " + command)

    async def call(self, client_id="history-tap", **extra):
        async def local_reply(*args, **kw):
            return kw.get("fallback_text", "Synthetic accepted request")

        with (
            patch.object(self.f.http, "run_music_command", self.backend),
            patch.object(self.core, "run_music_command", self.backend),
            patch.object(self.pipeline, "realize_session_narration", local_reply),
        ):
            return await self.f.handlers.async_handle_command_payload(
                self.hass,
                {
                    **self.identity,
                    "client_message_id": client_id,
                    "command": "play_history_item",
                    "value": self.reference,
                    **extra,
                },
                headers=self.headers,
            )

    async def test_tap_plays_only_original_recording_and_duplicate_does_not_repeat(self):
        result, status = await self.call()
        self.assertEqual(status, 200, result)
        self.assertTrue(result["success"], result)
        self.assertEqual(self.effects, [("play", "spotify:track:" + "A" * 22)])
        again, status = await self.call()
        self.assertEqual(status, 200, again)
        self.assertEqual(self.effects, [("play", "spotify:track:" + "A" * 22)])
        self.assertIs(self.f.manager.current_active("profile-a").broadcast, self.current.broadcast)
        stored = await self.f.repo.async_session_record(self.reference["session_id"])
        self.assertEqual(stored["lifecycle_status"], "ENDED")
        self.assertEqual(
            (
                await self.f.repo.async_entry_record(
                    "profile-a", self.reference["session_id"], self.reference["entry_id"]
                )
            )["body"],
            next(r for r in self.rows if r["entry_id"] == self.reference["entry_id"])["body"],
        )

    async def test_source_withdrawal_before_effect_prevents_dispatch(self):
        async def withdraw():
            self.source.disabled_by = "user"

        self.before_dispatch = withdraw
        result, status = await self.call()
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_unknown_owner_entry_and_forged_uri_are_closed(self):
        for change in (
            {"entry_id": "other-entry"},
            {"session_id": "other-session"},
            {"uri": "spotify:track:" + "Z" * 22},
        ):
            original = self.reference
            self.reference = {**original, **change}
            result, status = await self.call(client_id="bad-" + next(iter(change)))
            self.assertFalse(result.get("success"), result)
            self.assertEqual(self.effects, [])
            self.reference = original

    async def test_unknown_output_uses_existing_chooser_then_exact_item_and_no_duplicate(self):
        self.no_output = True
        first, status = await self.call()
        self.assertEqual(status, 200, first)
        self.assertEqual(first.get("action"), "select_output", first)
        self.assertEqual(self.effects, [])
        action = first["playback_actions"][0]
        self.no_output = False
        result, status = await self.call(
            client_id="choose-output", command=action["command"], value=action["value"]
        )
        self.assertEqual(status, 200, result)
        self.assertTrue(result["success"], result)
        self.assertEqual(
            self.effects,
            [("set_output", "speaker-original"), ("play", "spotify:track:" + "A" * 22)],
        )
        duplicate, status = await self.call(
            client_id="choose-output", command=action["command"], value=action["value"]
        )
        self.assertEqual(status, 200, duplicate)
        self.assertEqual(len(self.effects), 2)

    async def historical_output_offer(self):
        self.no_output = True
        first, status = await self.call()
        self.assertEqual(status, 200, first)
        self.assertEqual(first.get("action"), "select_output", first)
        self.no_output = False
        return first["playback_actions"][0]

    async def choose(self, action, client_id):
        return await self.call(
            client_id=client_id, command=action["command"], value=action["value"]
        )

    async def test_output_offer_is_single_use_with_a_different_client_id(self):
        action = await self.historical_output_offer()
        result, status = await self.choose(action, "first-choice")
        self.assertTrue(result.get("success"), result)
        result, status = await self.choose(action, "new-id-same-choice")
        self.assertFalse(result.get("success"), result)
        self.assertEqual(len(self.effects), 2)

    async def test_output_choice_retains_original_source_authority(self):
        action = await self.historical_output_offer()
        account = self.storage.household.music_accounts["source-account"]
        self.storage.household.music_accounts["source-account"] = replace(
            account, provider_account_id="replacement"
        )
        result, status = await self.choose(action, "changed-source-choice")
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_changed_default_account_cannot_retarget_output_offer(self):
        action = await self.historical_output_offer()
        # The original account remains linked and readable; only the selected
        # current account changes. It must never inherit the original tap.
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        await self.storage.async_upsert_music_account(
            "another-account",
            "source-spotify",
            kind=MusicAccountKind.PERSONAL,
            display_name="Synthetic replacement account",
            linked_profile_ids=frozenset({"profile-a"}),
            provider_account_id="provider-other",
        )
        await self.storage.async_update_profile(
            "profile-a",
            preferences=replace(
                self.storage.household.profiles["profile-a"].preferences,
                default_music_account_id="another-account",
            ),
        )
        result, status = await self.choose(action, "different-default")
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_uncertain_output_attempt_cannot_be_replayed_by_new_id(self):
        action = await self.historical_output_offer()
        original = self.backend

        # Keep the normal inventory/status fixture and fail only the first effect.
        async def dispatch(hass, runtime, command, value=None, **kwargs):
            if command == "set_output":
                self.effects.append((command, value))
                raise TimeoutError("synthetic uncertain dispatch")
            return await original(hass, runtime, command, value, **kwargs)

        with patch.object(self, "backend", dispatch):
            result, status = await self.choose(action, "uncertain-first")
        self.assertFalse(result.get("success"), result)
        result, status = await self.choose(action, "uncertain-new-id")
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [("set_output", "speaker-original")])

    async def test_source_withdrawn_during_output_inventory_cannot_dispatch(self):
        action = await self.historical_output_offer()

        async def withdraw():
            self.source.disabled_by = "user"

        self.before_inventory = withdraw
        result, status = await self.choose(action, "withdrawn-choice")
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_deleted_original_during_output_inventory_cannot_dispatch(self):
        action = await self.historical_output_offer()

        async def remove():
            await self.f.repo.async_remove_entry_records("profile-a", [self.reference["entry_id"]])

        self.before_inventory = remove
        result, status = await self.choose(action, "deleted-during-choice")
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_concurrent_output_choices_cannot_repeat_effects(self):
        action = await self.historical_output_offer()
        entered, release = asyncio.Event(), asyncio.Event()

        async def hold():
            entered.set()
            await release.wait()

        self.before_inventory = hold
        first = asyncio.create_task(self.choose(action, "concurrent-first"))
        await asyncio.wait_for(entered.wait(), 5)
        second = asyncio.create_task(self.choose(action, "concurrent-second"))
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.gather(first, second)
        self.assertEqual(sum(bool(result.get("success")) for result, status in results), 1, results)
        self.assertEqual(len(self.effects), 2)

    async def test_removed_original_entry_during_provider_await_never_dispatches(self):
        async def remove():
            self.before_dispatch = None
            await self.f.repo.async_remove_entry_records("profile-a", [self.reference["entry_id"]])

        self.before_dispatch = remove
        result, status = await self.call()
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_original_account_cannot_be_replaced_by_another_current_source(self):
        account = self.storage.household.music_accounts["source-account"]
        self.storage.household.music_accounts["source-account"] = replace(
            account, provider_account_id="other-provider"
        )
        result, status = await self.call()
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])

    async def test_history_read_only_offers_are_opt_in_and_never_play(self):
        data = {
            **self.identity,
            "session_id": self.reference["session_id"],
            "history_contract_version": 2,
            "historical_playback_contract_version": 1,
        }
        page, status = await self.f.handlers.async_handle_session_history_payload(
            self.hass, data, operation="timeline", headers=self.headers
        )
        self.assertEqual(status, 200, page)
        row = next(e for e in page["entries"] if e["entry_id"] == self.reference["entry_id"])
        self.assertEqual(row["playback_actions"][0]["value"], self.reference)
        self.assertEqual(self.effects, [])
