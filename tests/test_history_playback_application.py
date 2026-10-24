"""Real SQLite archive and common paired AskDJ application; synthetic provider boundary."""

import asyncio
from dataclasses import replace
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

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
        self.commands = []
        # Explicit occurrence identities distinguish both repeated recordings.
        self.queue = [("occurrence-a1", "A"), ("occurrence-b", "B"), ("occurrence-a2", "A")]
        self.queue_before = list(self.queue)
        self.no_output = False
        self.before_dispatch = None
        self.before_inventory = None

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def backend(self, hass, runtime, command, value=None, **kwargs):
        self.commands.append(command)
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
            if command == "play":
                self.queue[:] = [("ordinary-play-replacement", value)]
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

    def assert_closed(self, result, status):
        self.assertEqual(status, 409, result)
        self.assertEqual(result.get("error"), "historical_queue_preservation_unavailable")
        self.assertIs(result.get("success"), False)
        self.assertNotIn("playback_actions", result)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.commands, [])
        self.assertEqual(self.queue, self.queue_before)

    async def test_queue_preservation_unavailable_before_any_play_or_output(self):
        self.assert_closed(*(await self.call()))
        self.assertIs(self.f.manager.current_active("profile-a").broadcast, self.current.broadcast)
        stored = await self.f.repo.async_session_record(self.reference["session_id"])
        self.assertEqual(stored["lifecycle_status"], "ENDED")
        row = await self.f.repo.async_entry_record("profile-a", self.reference["session_id"], self.reference["entry_id"])
        self.assertEqual(row["body"], next(r for r in self.rows if r["entry_id"] == self.reference["entry_id"])["body"])

    async def test_duplicate_and_new_client_ids_never_repeat_or_admit(self):
        for client_id in ("same-tap", "same-tap", "different-tap"):
            self.assert_closed(*(await self.call(client_id=client_id)))

    async def test_no_output_does_not_offer_chooser_or_query_devices(self):
        self.no_output = True
        self.assert_closed(*(await self.call()))

    async def test_concurrent_taps_do_not_mutate_occurrence_multiplicity_or_order(self):
        results = await asyncio.gather(self.call("concurrent-a"), self.call("concurrent-b"))
        for result, status in results:
            self.assertFalse(result.get("success"), result)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.commands, [])
        self.assertEqual(self.queue, self.queue_before)

    async def test_caller_claims_cannot_supply_provider_qualification(self):
        for index, extra in enumerate((
            {"queue_preserved": True},
            {"historical_playback_contract_version": 2},
            {"provider_capabilities": {"atomic_queue_insert": True}},
            {"preserve_queue": True, "adapter": "qualified_atomic_provider"},
        )):
            self.assert_closed(*(await self.call(client_id=f"claim-{index}", **extra)))

    async def test_no_generic_play_grant_or_previous_success_replay(self):
        service = importlib.import_module("custom_components.djconnect.ask_dj.service")
        with (
            patch.object(service, "request_effect_grants", side_effect=AssertionError("generic grant issued")),
            patch.object(self.history, "async_saved_exchange", side_effect=AssertionError("legacy success replayed")),
        ):
            self.assert_closed(*(await self.call()))

    async def test_original_ram_success_cannot_bypass_new_historical_denial(self):
        future = asyncio.get_running_loop().create_future()
        future.set_result(({"success": True, "text": "Original V1 successful playback"}, AsyncMock()))
        with patch.object(self.history.dialogue, "reserve", return_value=(future, False)):
            self.assert_closed(*(await self.call()))

    async def test_original_output_saved_success_cannot_bypass_retained_frame_denial(self):
        original = self.history.dialogue.frame
        def retained_frame(*args, **kwargs):
            frame = original(*args, **kwargs)
            frame.result_set = {"result_set_id": "old-output", "items": [],
                                "historical_playback_admission": {"validate": lambda: None}}
            return frame
        saved = AsyncMock(side_effect=AssertionError("old output success was eligible for replay"))
        with (
            patch.object(self.history.dialogue, "frame", retained_frame),
            patch.object(self.history, "async_saved_exchange", saved),
        ):
            self.assert_closed(*(await self.call(command="ask_dj_play_recommendation_on_output",
                value={"device_id": "speaker-original", "recommendation": {"kind": "track", "uri": "spotify:track:" + "A" * 22}})))
        saved.assert_not_awaited()

    async def seed_original_output_receipt(self, *, dependencies, implicit=None, selected=None, command="ask_dj_play_recommendation_on_output"):
        value = {"device_id": "speaker-original", "recommendation": {"kind": "track", "uri": "spotify:track:" + "A" * 22}}
        if command == "ask_dj_play_request_on_output":
            value = {"device_id": "speaker-original", "request": {"text": "play the original recording"}}
        elif command == "ask_dj_message":
            value = {"text": "play", "choice_action": {"result_set_id": "original-output", "action_id": "original-action", "operation": "play"}}
        client_id = "legacy-saved-" + command
        # Capture the real application's normalized digest from a rejected
        # no-offer request, then seed the original persisted receipt shape.
        captured = []
        original_reserve = self.history.dialogue.reserve
        def reserve(frame, identifier, digest, fast):
            captured.append(digest)
            return original_reserve(frame, identifier, digest, fast)
        context = {"selected_entry": selected} if selected is not None else {}
        with patch.object(self.history.dialogue, "reserve", reserve):
            result, status = await self.call(client_id=client_id, command=command, value=value, conversation_context=context)
        self.assertFalse(result.get("success"), result)
        self.assertEqual(len(captured), 1)
        digest = captured[0]
        await self.history.async_append_exchange("profile:profile-a", {**self.identity,
            "client_message_id": client_id, "text": command},
            {"success": True, "text": "Original V1 output dispatch receipt", "action": "spotify_start_recommendation"},
            session_turn={"turn_id": "original-v1-output-turn", "request_digest": digest,
                "profile_id": "profile-a", "context": context, "dependency_entries": dependencies,
                "implicit_playback_entry": implicit, "effective_style": {"language": "en", "persona": "home_dj"}})
        self.history.dialogue.owners.clear()
        self.assertIsNotNone(await self.history.async_saved_exchange("profile:profile-a", client_id))
        return client_id, command, value

    async def test_evicted_frame_original_durable_historical_output_receipt_is_closed(self):
        client_id, command, value = await self.seed_original_output_receipt(dependencies=[self.reference])
        self.assert_closed(*(await self.call(client_id=client_id, command=command, value=value)))

    async def test_ordinary_durable_output_receipt_without_historical_target_stays_deduplicated(self):
        client_id, command, value = await self.seed_original_output_receipt(dependencies=[])
        result, status = await self.call(client_id=client_id, command=command, value=value)
        self.assertEqual(status, 200, result)
        self.assertTrue(result.get("deduplicated"), result)
        self.assertEqual(self.effects, [])

    async def test_ordinary_implicit_current_playback_receipt_stays_deduplicated(self):
        client_id, command, value = await self.seed_original_output_receipt(dependencies=[self.reference], implicit=self.reference)
        result, status = await self.call(client_id=client_id, command=command, value=value)
        self.assertEqual(status, 200, result)
        self.assertTrue(result.get("deduplicated"), result)
        self.assertEqual(self.effects, [])

    async def test_explicit_original_target_does_not_become_implicit_by_extra_reference_fields(self):
        selected = {k: self.reference[k] for k in ("session_id", "entry_id")}
        client_id, command, value = await self.seed_original_output_receipt(
            dependencies=[self.reference], implicit=self.reference, selected=selected)
        self.assert_closed(*(await self.call(client_id=client_id, command=command, value=value,
            conversation_context={"selected_entry": selected})))

    async def test_legacy_request_output_and_play_choice_replays_are_also_closed(self):
        for command in ("ask_dj_play_request_on_output", "ask_dj_message"):
            client_id, command, value = await self.seed_original_output_receipt(dependencies=[self.reference], command=command)
            self.assert_closed(*(await self.call(client_id=client_id, command=command, value=value)))

    async def test_legacy_output_continuation_closes_before_any_await_or_grant(self):
        for admission in ({"validate": lambda: None}, {}, "old-context"):
            turn = SimpleNamespace(frame=SimpleNamespace(result_set={"historical_playback_admission": admission}))
            inventory = AsyncMock(side_effect=AssertionError("output inventory requested"))
            with patch.object(self.core, "run_music_command", inventory):
                for client_id in ("original", "replacement"):
                    with self.assertRaises(self.dialogue.DialogueError) as raised:
                        await self.core._activate_dialogue_output(self.hass, self.runtime, {"client_message_id": client_id},
                            {"command": "ask_dj_play_recommendation_on_output", "device_id": "speaker-original"}, turn, play=True)
                    self.assertEqual(raised.exception.code, "historical_queue_preservation_unavailable")
                inventory.assert_not_awaited()
        self.assertEqual(self.effects, [])

    async def test_ordinary_output_play_continuation_keeps_existing_effect_owner(self):
        turn = SimpleNamespace(frame=SimpleNamespace(result_set={}), guard=AsyncMock())
        action = {"command": "ask_dj_play_recommendation_on_output", "device_id": "speaker-original", "action_id": "ordinary-action",
                  "value": {"recommendation": {"kind": "track", "uri": "spotify:track:" + "A" * 22}}}
        handler = AsyncMock(return_value={"success": True})
        with (
            patch.object(self.core, "run_music_command", self.backend),
            patch.object(self.f.http, "_handle_ask_dj_play_recommendation_on_output", handler),
        ):
            result = await self.core._activate_dialogue_output(self.hass, self.runtime, {}, action, turn, play=True)
        self.assertTrue(result["success"])
        handler.assert_awaited_once()
        self.assertEqual([grant.families for grant in turn.effect_grants], [frozenset({"output"}), frozenset({"play"})])

    async def test_unknown_entry_and_forged_uri_are_closed(self):
        original = self.reference
        for change in ({"entry_id": "other-entry"}, {"session_id": "other-session"}, {"uri": "spotify:track:" + "Z" * 22}):
            self.reference = {**original, **change}
            result, status = await self.call(client_id="bad-" + next(iter(change)))
            self.assertFalse(result.get("success"), result)
            self.assertEqual(self.effects, [])
        self.reference = original

    async def test_deleted_original_is_not_replaced_by_current_playback(self):
        await self.f.repo.async_remove_entry_records("profile-a", [self.reference["entry_id"]])
        result, status = await self.call()
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.commands, [])

    async def test_withdrawn_source_never_admits_effects(self):
        self.source.disabled_by = "user"
        result, status = await self.call()
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.commands, [])

    async def test_original_account_cannot_be_replaced_by_current_source(self):
        account = self.storage.household.music_accounts["source-account"]
        self.storage.household.music_accounts["source-account"] = replace(account, provider_account_id="other-provider")
        result, status = await self.call()
        self.assertFalse(result.get("success"), result)
        self.assertEqual(self.commands, [])

    async def test_capability_and_contract_advertise_closed_v2(self):
        from custom_components.djconnect.capability_contract import _platform_capabilities, _contract_versions
        self.assertIs(_platform_capabilities()["historical_exact_track_playback"], False)
        self.assertEqual(_contract_versions()["historical_exact_track_playback"], 2)

    async def test_history_browsing_legacy_and_v2_keep_readable_original_without_offers(self):
        for version in (None, 1, "1", 2, "2"):
            data = {**self.identity, "session_id": self.reference["session_id"], "history_contract_version": 2}
            if version is not None:
                data["historical_playback_contract_version"] = version
            page, status = await self.f.handlers.async_handle_session_history_payload(self.hass, data, operation="timeline", headers=self.headers)
            self.assertEqual(status, 200, page)
            row = next(e for e in page["entries"] if e["entry_id"] == self.reference["entry_id"])
            self.assertNotIn("playback_actions", row)
            self.assertEqual(self.effects, [])

    async def test_unknown_contract_versions_remain_closed(self):
        for version in (True, False, 0, 3, "3", {}, []):
            page, status = await self.f.handlers.async_handle_session_history_payload(self.hass,
                {**self.identity, "session_id": self.reference["session_id"], "historical_playback_contract_version": version},
                operation="timeline", headers=self.headers)
            self.assertEqual(status, 400, page)
            self.assertEqual(page.get("error"), "unsupported_historical_playback_contract")

    async def test_denial_copy_uses_supported_request_language(self):
        from custom_components.djconnect.historical_playback import UNAVAILABLE_MESSAGES
        for language, message in UNAVAILABLE_MESSAGES.items():
            result, status = await self.call(client_id="language-" + language, language=language)
            self.assert_closed(result, status)
            self.assertEqual(result["message"], message)
