"""First-play state/effect owner with real Runtime and explicit external seams."""
import asyncio
import hashlib
import importlib
import time
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from tests import test_current_track_insight_runtime_identity as runtime_fixture


class FirstPlayTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await runtime_fixture.CurrentRuntimeValueTests.asyncSetUp(self)
        self.steering = importlib.import_module("custom_components.djconnect.mood_music_steering")
        self.dialogue = importlib.import_module("custom_components.djconnect.ask_dj.dialogue")
        self.spotify = importlib.import_module("custom_components.djconnect.spotify_backend")
        self.use_cases = importlib.import_module("custom_components.djconnect.use_cases")
        self.allowed = True
        self.grant = "synthetic-grant"
        seam = patch("custom_components.djconnect.session_conversation.history_grant_revision", side_effect=lambda *_: self.grant)
        seam.start()
        self.addCleanup(seam.stop)
        self.effects, self.reads, self.reservations = [], [], []
        self.devices = [{"id": "synthetic-output", "name": "Synthetic speaker", "is_active": True}]
        self.observed = SimpleNamespace(state="idle", media_identity="")
        self.queue = {"queue": [], "currently_playing": None}
        self.unavailable_genre = ""
        test = self
        class Backend:
            conf = {"spotify_market": "NL"}
            def __init__(self, *_):
                pass
            async def devices(self, *, fresh=False):
                test.assertTrue(fresh)
                test.reads.append("devices")
                return test.devices
            async def async_observe_current_playback(self):
                test.reads.append("playback")
                return test.observed
            async def _request(self, method, path):
                test.assertEqual(method, "GET")
                test.reads.append(path)
                if path == "/me/player/queue":
                    return test.queue
                query = parse_qs(urlsplit(path).query)
                genre = query["q"][0].split(":", 1)[1]
                tracks = [] if genre == test.unavailable_genre else [
                    {"uri": "spotify:track:"+hashlib.sha256((genre+str(i)).encode()).hexdigest()[:22],
                     "is_playable": True, "is_local": False, "name": "Synthetic track"} for i in range(3)]
                return {"tracks": {"items": tracks}}
        self.backend = Backend()
        seam = patch.object(self.spotify, "SpotifyBackend", Backend)
        seam.start()
        self.addCleanup(seam.stop)
        await self.new_session()
        async def reserve(*args):
            self.reservations.append(args)
        self.history = SimpleNamespace(dialogue=self.dialogue.DialogueState(), async_reserve_dialogue_effect=reserve)
        self.new_turn("first-request")
        async def effect(hass, runtime, command, value=None, *, play=None):
            family = "play" if command == "play_uris" else "output"
            token = self.dialogue.current_effect.set(self.dialogue.CommandEffect(family, command, value, play))
            try:
                body = {"uris": value} if family == "play" else {"device_ids": [value], "play": False}
                path = "/me/player/play?device_id=synthetic-output" if family == "play" else "/me/player"
                await self.dialogue.guard_effect_dispatch(method="PUT", path=path, body=body)
                self.effects.append((command, value, play))
                if command == "set_output":
                    self.devices = [{**d, "is_active": d["id"] == value} for d in self.devices]
                    return {"success": True, "playback": {"device": {"id": value}}}
                self.observed = SimpleNamespace(state="playing", media_identity=value[0])
                await self.manager.async_update_playback_projection(owner_profile_id="synthetic-owner",
                    session_id=self.active.session_id, state="playing", media_identity=value[0], title="Synthetic track")
                return {"success": True, "playback": {"uri": value[0], "is_playing": True,
                                                       "device": {"id": "synthetic-output"}}}
            finally:
                self.dialogue.current_effect.reset(token)
        seam = patch.object(self.use_cases, "run_music_command", effect)
        seam.start()
        self.addCleanup(seam.stop)

    async def new_session(self, mood="groove", locale="en"):
        old = self.manager.current_active("synthetic-owner")
        if old:
            await self.manager.async_end(owner_profile_id="synthetic-owner", session_id=old.session_id)
        self.active = await self.manager.async_start(owner_profile_id="synthetic-owner", selected_mood=mood,
            locale=locale, music_backend="spotify_direct", history_source_context=self.source)

    def new_turn(self, identifier, locale="en"):
        frame = getattr(self, "frame", None)
        if frame is None:
            frame = self.frame = self.dialogue.DialogueFrame(time.monotonic(), "original-generation")
        async def owner():
            if not self.allowed:
                raise self.dialogue.DialogueError("synthetic-owner-withdrawn", 403)
        self.turn = self.dialogue.DialogueTurn(frame, "profile:synthetic-owner", "default", identifier,
            "synthetic-digest-"+identifier, frame.generation, owner, self.history,
            style={"language": locale}, session_id=self.active.session_id,
            reply_source_context=self.source, reply_source_authority=lambda: self.allowed)
        token = self.dialogue.current_turn.set(self.turn)
        self.addCleanup(self.dialogue.current_turn.reset, token)

    async def offer(self):
        result = await self.steering.first_play_response(self.hass, self.runtime)
        self.history.dialogue.complete(self.turn, result)
        return result

    async def choose(self, index=0, identifier="selection"):
        shown = self.frame.result_set
        action = shown["items"][index]
        self.new_turn(identifier)
        result = await self.steering.first_play_choose(self.hass, self.runtime, action, shown, self.turn)
        self.history.dialogue.complete(self.turn, result)
        return result

    async def test_all_four_moods_five_languages_return_exact_three_backed_genres_without_effect(self):
        for mood in self.steering.FIRST_PLAY_GENRES:
            for locale in self.steering.FIRST_PLAY_COPY:
                with self.subTest(mood=mood, locale=locale):
                    await self.new_session(mood, locale)
                    self.frame = None
                    self.new_turn(mood+locale, locale)
                    result = await self.offer()
                    self.assertEqual(result["first_play"]["state"], "genres")
                    actions = result["result_set"]["items"]
                    self.assertEqual(tuple(a["genre"] for a in actions), self.steering.FIRST_PLAY_GENRES[mood])
                    self.assertEqual(len({a["action_id"] for a in actions}), 3)
                    self.assertTrue(all(len(a["uris"]) >= 2 for a in actions))
                    self.assertEqual(result["text"], self.steering.FIRST_PLAY_COPY[locale][3])
                    self.assertEqual(self.effects, [])
                    self.assertEqual(self.reservations, [])

    async def test_genre_tap_is_single_exact_ordered_play_without_more_play_now(self):
        offered = await self.offer()
        exact = offered["result_set"]["items"][1]["uris"]
        result = await self.choose(1)
        self.assertEqual(self.effects, [("play_uris", exact, True)])
        self.assertEqual(len(self.reservations), 1)
        self.assertTrue(result["action_outcome"]["readback_confirmed"])
        self.assertFalse(result["playback_actions"])
        self.assertEqual(self.active.broadcast.first_play_state, "closed")
        self.assertTrue(self.active.broadcast.first_play_observed)
        with self.assertRaises(self.dialogue.DialogueError):
            await self.choose(1, "new-id-cannot-repeat")
        self.assertEqual(len(self.effects), 1)

    async def test_output_choice_resumes_original_three_genres_and_never_autoplays(self):
        self.devices[0]["is_active"] = False
        output = await self.offer()
        self.assertEqual(output["first_play"]["state"], "output")
        admission = self.turn.first_play_admission
        original_deadline = admission.deadline
        self.assertFalse(any(path.startswith("/search") for path in self.reads))
        genres = await self.choose()
        self.assertEqual(self.effects, [("set_output", "synthetic-output", False)])
        self.assertEqual(genres["first_play"]["state"], "genres")
        self.assertEqual(len(genres["result_set"]["items"]), 3)
        self.assertIs(self.frame.result_set["first_play_admission"], admission)
        self.assertEqual(admission.deadline, original_deadline)
        self.assertNotIn("selected_action_id", genres)
        await self.choose(0, "genre-after-output")
        self.assertEqual([effect[0] for effect in self.effects], ["set_output", "play_uris"])

    async def test_fewer_than_three_mix_sources_produces_no_genre_button(self):
        self.unavailable_genre = "jazz"
        result = await self.offer()
        self.assertFalse(result["success"])
        self.assertEqual(result["first_play"]["reason"], "fewer_than_three_playable_mixes")
        self.assertFalse(result["playback_actions"])
        self.assertEqual(self.effects, [])

    async def test_paused_or_nonempty_queue_is_never_overwritten(self):
        for current in ({"state": "paused", "media_identity": "spotify:track:"+"A"*22},):
            self.observed = SimpleNamespace(**current)
            with self.assertRaises(self.dialogue.DialogueError):
                await self.offer()
        self.assertFalse(self.effects)

    async def test_queue_added_after_offer_blocks_genre_play(self):
        await self.offer()
        self.queue = {"queue": [{"uri": "spotify:track:"+"A"*22}], "currently_playing": None}
        with self.assertRaises(self.dialogue.DialogueError):
            await self.choose()
        self.assertFalse(self.effects)

    async def test_original_source_history_and_expiry_cannot_rearm(self):
        for mutation in ("source", "history", "expiry"):
            await self.new_session()
            self.frame = None
            self.new_turn(mutation)
            await self.offer()
            admission = self.turn.first_play_admission
            if mutation == "source":
                admission.source["provider_account_id"] = "changed"
            elif mutation == "history":
                self.grant = "withdrawn"
            else:
                admission.deadline = admission.clock()-1
            with self.assertRaises(self.dialogue.DialogueError):
                admission.guard()
            admission.source.update(self.source)
            self.grant = "synthetic-grant"
            admission.deadline = admission.clock()+60
            with self.assertRaises(self.dialogue.DialogueError):
                admission.guard()
        self.assertFalse(self.effects)

    async def test_silence_after_playback_does_not_restore_first_play(self):
        await self.manager.async_update_playback_projection(owner_profile_id="synthetic-owner",
            session_id=self.active.session_id, state="paused", media_identity="spotify:track:"+"A"*22)
        await self.manager.async_update_playback_projection(owner_profile_id="synthetic-owner",
            session_id=self.active.session_id, state="idle")
        self.assertFalse(self.steering._first_play_empty(self.active))
        result = await self.offer()
        self.assertFalse(result["success"])
        self.assertFalse(self.effects)

    async def test_explicit_no_play_and_questions_cannot_start_offered_genre(self):
        await self.offer()
        core = importlib.import_module("custom_components.djconnect.ask_dj")
        for index, text in enumerate(("play the first without playing", "speel de eerste zonder te spelen",
                                     "spiele das erste ohne abzuspielen", "joue le premier sans jouer",
                                     "reproduce el primero sin reproducir", "what is the first genre?")):
            self.new_turn("explicit-no-play-"+str(index))
            with self.assertRaises(self.dialogue.DialogueError):
                await core._dialogue_choice_response(self.hass, self.runtime, {}, text, index=0)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.reservations, [])

    async def test_held_original_output_reservation_cannot_be_stolen_or_cancelled(self):
        self.devices = [{"id": "synthetic-output", "name": "First", "is_active": False},
                        {"id": "second-output", "name": "Second", "is_active": False}]
        await self.offer()
        shown = self.frame.result_set
        entered, release = asyncio.Event(), asyncio.Event()
        async def reserve(*args):
            self.reservations.append(args)
            entered.set()
            await release.wait()
        self.history.async_reserve_dialogue_effect = reserve
        self.new_turn("original-output")
        original = self.turn
        first = asyncio.create_task(self.steering.first_play_choose(
            self.hass, self.runtime, shown["items"][0], shown, original))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            self.new_turn("competing-output")
            with self.assertRaises(self.dialogue.DialogueError):
                await self.steering.first_play_choose(self.hass, self.runtime, shown["items"][1], shown, self.turn)
            self.assertIs(shown["first_play_admission"].execution_turn, original)
            self.assertFalse(shown["first_play_admission"].withdrawn)
        finally:
            release.set()
        result = await asyncio.wait_for(first, 1)
        self.assertEqual(result["first_play"]["state"], "genres")
        self.assertEqual([effect[1] for effect in self.effects], ["synthetic-output"])

    async def test_unknown_engine_and_no_original_source_remain_unavailable(self):
        self.active.broadcast.first_play_state = "unknown"
        result = await self.offer()
        self.assertFalse(result["success"])
        self.assertEqual(self.reads, [])
        await self.new_session()
        self.new_turn("missing-source")
        self.turn.reply_source_authority = None
        result = await self.offer()
        self.assertFalse(result["success"])
        self.assertEqual(self.reads, [])

    async def test_one_adapter_dispatch_does_not_allow_a_second_send(self):
        await self.offer()
        shown = self.frame.result_set
        self.new_turn("genre-single-dispatch")
        result = await self.steering.first_play_choose(self.hass, self.runtime, shown["items"][0], shown, self.turn)
        admission = self.turn.first_play_admission
        self.assertTrue(result["action_outcome"]["readback_confirmed"])
        with self.assertRaises(self.dialogue.DialogueError):
            admission.before_dispatch("play", admission.selected_media, admission.output_id)
        self.assertEqual(len(self.effects), 1)

    async def test_changed_mood_revision_cannot_restore_original_offer(self):
        from dataclasses import replace
        await self.offer()
        admission = self.turn.first_play_admission
        original = self.manager.current_active("synthetic-owner")
        self.manager._active_by_profile["synthetic-owner"] = replace(original,
            selected_mood="party", mood_revision=original.mood_revision+1)
        with self.assertRaises(self.dialogue.DialogueError):
            admission.guard()
        self.manager._active_by_profile["synthetic-owner"] = original
        with self.assertRaises(self.dialogue.DialogueError):
            admission.guard()
        self.assertFalse(self.effects)

    async def test_output_changed_after_offer_cannot_start_on_another_device(self):
        await self.offer()
        self.devices = [{"id": "other-output", "name": "Other", "is_active": True}]
        with self.assertRaises(self.dialogue.DialogueError):
            await self.choose()
        self.assertFalse(self.effects)

    async def test_cached_restricted_and_zero_outputs_have_no_genre_offer(self):
        for value in ([], [{"id": "old", "name": "Old", "cached": True}],
                      [{"id": "restricted", "name": "Other", "is_restricted": True}]):
            self.devices = value
            self.new_turn("empty-output-"+str(len(self.reads)))
            result = await self.offer()
            self.assertFalse(result["success"])
            self.assertFalse(result["playback_actions"])
        self.assertFalse(any(path.startswith("/search") for path in self.reads))
        self.assertFalse(self.effects)

    async def test_missing_queue_evidence_is_not_known_empty(self):
        self.queue = {"queue": []}
        with self.assertRaises(self.dialogue.DialogueError):
            await self.offer()
        self.assertFalse(self.effects)

    async def test_missing_playability_is_not_a_qualified_mix(self):
        original = self.backend._request
        async def missing(*args):
            result = await original(*args)
            if args[1].startswith("/search"):
                for track in result["tracks"]["items"]:
                    track.pop("is_playable")
            return result
        # Constructor is replaced by a real declared external-fixture instance,
        # not a different authority or a fabricated provider readiness boolean.
        with patch.object(self.spotify, "SpotifyBackend", return_value=self.backend), \
                patch.object(self.backend, "_request", missing):
            result = await self.offer()
        self.assertFalse(result["success"])
        self.assertFalse(result["playback_actions"])
        self.assertFalse(self.effects)

    async def test_lost_dispatch_ack_never_reissues_or_rearms_first_play(self):
        await self.offer()
        original = self.use_cases.run_music_command
        async def lost(*args, **kwargs):
            await original(*args, **kwargs)
            raise self.spotify.SpotifyBackendError("synthetic lost acknowledgement", http_status=503)
        with patch.object(self.use_cases, "run_music_command", lost):
            result = await self.choose()
        self.assertEqual(result["action_outcome"]["state"], "uncertain")
        self.assertEqual(len(self.effects), 1)
        self.assertFalse(result["playback_actions"])
        self.new_turn("new-cta-after-lost-ack")
        again = await self.offer()
        self.assertFalse(again["success"])
        self.assertEqual(len(self.effects), 1)

    async def test_cancellation_during_original_reservation_never_rearms(self):
        await self.offer()
        shown = self.frame.result_set
        started = asyncio.Event()
        async def held(*args):
            started.set()
            await asyncio.Event().wait()
        self.history.async_reserve_dialogue_effect = held
        self.new_turn("cancelled-original-genre")
        original = self.turn
        task = asyncio.create_task(self.steering.first_play_choose(
            self.hass, self.runtime, shown["items"][0], shown, original))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.effects)
        self.assertEqual(self.active.broadcast.first_play_state, "attempted")
        self.new_turn("new-after-reservation-cancel")
        with self.assertRaises(self.dialogue.DialogueError):
            await self.steering.first_play_choose(self.hass, self.runtime, shown["items"][0], shown, self.turn)
        self.assertFalse(self.effects)

    async def test_informational_speaker_question_has_no_output_effect(self):
        self.devices[0]["is_active"] = False
        await self.offer()
        self.new_turn("speaker-question")
        core = importlib.import_module("custom_components.djconnect.ask_dj")
        try:
            await core._dialogue_choice_response(self.hass, self.runtime, {}, "Which speaker is the first?", index=0)
        except self.dialogue.DialogueError:
            pass
        self.assertFalse(self.effects)

    async def test_explicit_speaker_selection_without_playing_stays_output_only(self):
        self.devices[0]["is_active"] = False
        await self.offer()
        self.new_turn("speaker-without-play")
        core = importlib.import_module("custom_components.djconnect.ask_dj")
        result = await core._dialogue_choice_response(self.hass, self.runtime, {}, "Activate the first without playing", index=0)
        self.assertEqual(result["first_play"]["state"], "genres")
        self.assertEqual(self.effects, [("set_output", "synthetic-output", False)])

    async def test_genre_activate_operation_is_not_a_play_grant(self):
        await self.offer()
        action = self.frame.result_set["items"][0]
        self.new_turn("invalid-genre-activate")
        core = importlib.import_module("custom_components.djconnect.ask_dj")
        with self.assertRaises(self.dialogue.DialogueError):
            await core._dialogue_choice_response(self.hass, self.runtime,
                {"choice_action": {"result_set_id": action["result_set_id"],
                 "action_id": action["action_id"], "operation": "activate"}}, "activate")
        self.assertFalse(self.effects)

    async def test_genre_activate_text_is_not_a_play_grant(self):
        await self.offer()
        self.new_turn("invalid-genre-activate-text")
        core = importlib.import_module("custom_components.djconnect.ask_dj")
        with self.assertRaises(self.dialogue.DialogueError):
            await core._dialogue_choice_response(self.hass, self.runtime, {}, "activate first", index=0)
        self.assertFalse(self.effects)


class FirstPlayWireEvidenceTests(IsolatedAsyncioTestCase):
    async def test_actual_source_fixture_binds_all_products_and_original_harness(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'examples/client_contracts/session_first_play_v1/actual-ha-wire.json').read_text())
        self.assertEqual(len(fixture['source_pins']), 302)
        for name, digest in fixture['source_pins'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest, name)
        for name, digest in fixture['original_common_harness_source_pins'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((root/fixture['harness']).read_bytes()).hexdigest(), fixture['harness_sha256'])
        self.assertEqual((fixture['model_provider_calls'], fixture['real_provider_calls']), (0, 0))
        self.assertTrue(fixture['all302_before_inside_after_equal'])
        self.assertTrue(fixture['own_container_verified_absent'])
        self.assertEqual(set(fixture['cases'].values()), {'PASS'})
        self.assertGreaterEqual(len(fixture['cases']), 24)

    async def test_actual_original_flow_has_three_genres_and_no_extra_play_now(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'examples/client_contracts/session_first_play_v1/actual-ha-wire.json').read_text())
        example = fixture['examples'][0]
        self.assertTrue(example['catalogue_before']['available'])
        self.assertFalse(example['catalogue_after']['available'])
        self.assertEqual(set(example['catalogue_before']['localizations']), {'en','nl','de','fr','es'})
        self.assertEqual(example['output']['first_play']['state'], 'output')
        self.assertEqual({item['kind'] for item in example['output']['result_set']['items']}, {'output'})
        choices = example['genres']['result_set']['items']
        self.assertEqual(len(choices), 3)
        self.assertEqual(len({item['genre'] for item in choices}), 3)
        self.assertTrue(all(item['kind']=='track_mix' and len(item['uris'])>=2 for item in choices))
        self.assertEqual(example['played']['first_play']['state'], 'requested')
        self.assertTrue(example['played']['action_outcome']['readback_confirmed'])
        self.assertFalse(example['played']['action_outcome']['retry_automatically'])
        self.assertEqual(example['played']['playback_actions'], [])
