"""Operational Golden conversations, not catalog presence or prose-only tests."""

import unittest
from unittest.mock import patch
from tests import test_ask_dj_contextual_dialogue as dialogue_tests


class GoldenConversationChains(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        dialogue_tests.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        dialogue_tests.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = dialogue_tests.SharedDialogueTest()
        await self.f.asyncSetUp()
        from dataclasses import replace
        from types import SimpleNamespace
        from custom_components.djconnect.domain.backend import BackendProvider
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        storage = self.f.handlers.profile_storage(self.f.hass)
        await storage.async_upsert_music_backend(
            "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Provider fixture"
        )
        await storage.async_upsert_music_account(
            "golden-account",
            "spotify_direct",
            kind=MusicAccountKind.PERSONAL,
            display_name="Provider fixture",
            linked_profile_ids=frozenset({"profile-a"}),
        )
        await storage.async_update_profile(
            "profile-a",
            preferences=replace(
                storage.household.profiles["profile-a"].preferences,
                default_backend_id="spotify_direct",
                default_music_account_id="golden-account",
            ),
        )
        self.f.runtime.config.update(
            music_backend="spotify_direct",
            music_account_id="golden-account",
            spotify_client_id="TEST_CLIENT_ID_NOT_A_SECRET",
            spotify_refresh_token="TEST_REFRESH_NOT_A_SECRET",
        )
        entry = SimpleNamespace(
            entry_id="owner-entry",
            data={**self.f.runtime.config, "device_token": self.f.runtime.device_token},
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.f.runtime.entry = entry
        self.f.hass.config_entries.async_entries = lambda domain: [entry]
        self.f.hass.config_entries.async_get_entry = lambda eid: (
            entry if eid == "owner-entry" else None
        )
        self.f.runtime.update = lambda **fields: [
            setattr(self.f.runtime, key, value) for key, value in fields.items()
        ]

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    def catalogue_provider(self, *, empty=False):
        """Only external Spotify reads are fixtures; ordinary Ask DJ owns delivery."""
        calls = []
        albums = [{"uri": "spotify:album:" + char * 22, "title": f"Album {i}",
                   "artist": "Metallica", "album_image_url": f"https://img.example/album-{i}.jpg"}
                  for i, char in enumerate("ABCDE", 1)]
        playlists = [{"uri": "spotify:playlist:" + char * 22, "title": f"Playlist {i}",
                      "owner": "Catalogue curator", "image_url": f"https://img.example/playlist-{i}.jpg"}
                     for i, char in enumerate("FGHIJ", 1)]

        async def provider(hass, runtime, command, value=None, **kwargs):
            calls.append(command)
            if command == "status":
                return {"success": True, "playback": {}}
            if command == "search_albums":
                return {"success": True, "albums": [] if empty else albums}
            if command == "search_playlists":
                return {"success": True, "playlists": [] if empty else playlists}
            raise AssertionError("Offering a catalogue must not start music: " + command)
        return provider, calls

    async def test_metallica_options_are_one_playable_list_with_short_intro_in_five_languages(self):
        f = self.f
        for language in ("en", "nl", "de", "fr", "es"):
            with self.subTest(language=language):
                provider, calls = self.catalogue_provider()
                with patch.object(f.core, "run_music_command", provider):
                    answer, status = await f.request("Speel iets van Metallica.",
                        identifier="metallica-list-" + language, language=language)
                self.assertEqual(status, 200, answer)
                self.assertEqual(answer["items"], [])
                self.assertEqual(answer["assistant_message"]["items"], [])
                self.assertEqual(answer["text"], answer["assistant_message"]["text"])
                self.assertLess(len(answer["text"]), 240)
                self.assertNotIn("1.", answer["text"])
                actions = answer["playback_actions"]
                self.assertEqual(len(actions), 10)
                self.assertEqual({a["kind"] for a in actions}, {"album", "playlist"})
                self.assertEqual(len({a["uri"] for a in actions}), 10)
                self.assertTrue(all(a["label"] == "Play Now" and a["image_url"].startswith(
                    "/api/djconnect/v1/image_proxy/") for a in actions))
                self.assertEqual(answer["result_set"]["items"], actions)
                self.assertEqual(answer["assistant_message"]["playback_actions"], actions)
                for action in actions:
                    self.assertNotIn(action["title"], answer["text"])
                self.assertEqual(calls, ["status", "search_albums", "search_playlists"])
        self.assertEqual(f.prompts, [])

    async def test_catalogue_options_speak_exact_intro_and_serve_private_audio_without_repeating_search(self):
        from custom_components.djconnect import session_speech
        f = self.f
        provider, catalogue_calls = self.catalogue_provider()
        with patch.object(f.core, "run_music_command", provider):
            answer, status = await f.request("Speel iets van Metallica.",
                identifier="metallica-speech", audio_response="always", speech_contract_version=1)
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["items"], [])
        stack, entity, pipeline, synthesis_calls, processor = f.generic_tts()
        with stack:
            payload = {**f.identity, "contract_version": 1,
                       "reference": answer["session_speech"]["reference"],
                       "processor": "ha_configured", "voice_preference": "default"}
            prepared, status = await session_speech.async_handle_prepare(f.hass, payload, headers=f.headers)
            self.assertEqual(status, 200, prepared)
            speech = prepared["session_speech"]
            self.assertEqual(speech["audio_state"], "ready")
            self.assertEqual("".join(s["text"] for s in speech["segments"]), answer["text"])
            self.assertEqual(synthesis_calls[0][0], answer["text"])
            repeated, _ = await session_speech.async_handle_prepare(f.hass, payload, headers=f.headers)
            self.assertEqual(repeated["session_speech"]["audio_reference"], speech["audio_reference"])
            asset_payload = {**f.identity, "contract_version": 1,
                             "asset_id": speech["audio_reference"]["asset_id"]}
            audio, status = await session_speech.async_handle_audio(f.hass, asset_payload, headers=f.headers)
            self.assertEqual((status, audio.content_type), (200, "audio/mpeg"))
            self.assertTrue(processor._valid_mp3(audio.data))
            self.assertEqual(len(synthesis_calls), 1)
        self.assertEqual(catalogue_calls, ["status", "search_albums", "search_playlists"])
        self.assertEqual(f.prompts, [])

    async def test_catalogue_speech_provider_failure_preserves_playable_choices_and_safe_notice(self):
        from custom_components.djconnect import session_speech
        f = self.f
        provider, catalogue_calls = self.catalogue_provider()
        with patch.object(f.core, "run_music_command", provider):
            answer, _ = await f.request("Speel iets van Metallica.", identifier="metallica-tts-failure")
        stack, entity, pipeline, synthesis_calls, processor = f.generic_tts()
        attempts = []
        async def failed(*args):
            attempts.append(True)
            raise RuntimeError("PRIVATE_PROVIDER_EXCEPTION")
        entity.async_get_tts_audio = failed
        payload = {**f.identity, "contract_version": 1,
                   "reference": answer["session_speech"]["reference"],
                   "processor": "ha_configured", "voice_preference": "default"}
        with stack:
            for index in range(2):
                prepared, status = await session_speech.async_handle_prepare(f.hass, payload, headers=f.headers)
                self.assertEqual(status, 200, prepared)
                self.assertEqual(prepared["session_speech"]["state"], "unavailable")
                self.assertEqual(prepared["session_speech"]["notification"]["code"],
                    "tts_preparation_failed")
                self.assertEqual(prepared["session_speech"]["reason"],
                    "speech_preparation_failed" if index == 0 else "speech_retry_backoff")
                self.assertNotIn("PRIVATE_PROVIDER_EXCEPTION", str(prepared))
        self.assertEqual(attempts, [True])
        self.assertEqual(len(answer["playback_actions"]), 10)
        self.assertEqual(catalogue_calls, ["status", "search_albums", "search_playlists"])

    async def test_empty_and_populated_options_keep_one_collection_and_localized_intro(self):
        f = self.f
        texts = set()
        for language in ("en", "nl", "de", "fr", "es"):
            for empty in (False, True):
                with self.subTest(language=language, empty=empty):
                    provider, calls = self.catalogue_provider(empty=empty)
                    with patch.object(f.core, "run_music_command", provider):
                        answer, status = await f.request("Speel iets van Metallica.",
                            identifier=f"options-{language}-{empty}", language=language)
                    self.assertEqual(status, 200, answer)
                    self.assertEqual(answer["items"], [])
                    self.assertEqual(len(answer["playback_actions"]), 0 if empty else 10)
                    self.assertIn("metallica", answer["text"].lower())
                    self.assertNotIn("Album 1", answer["text"])
                    self.assertEqual(calls, ["status", "search_albums", "search_playlists"])
                    if not empty:
                        texts.add(answer["text"])
        self.assertEqual(len(texts), 5)
        self.assertEqual(f.prompts, [])

    async def test_catalogue_intro_shared_settings_speech3_keeps_identity_and_current_voice(self):
        from datetime import UTC, datetime
        from custom_components.djconnect import profile_settings, session_speech
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        from tests.test_profile_dj_settings_persistence import operation
        f = self.f
        f.fixture.manager._settings_repository = ProfileDJSettingsRepository(f.fixture.service)
        stack, entity, pipeline, synthesis_calls, processor = f.generic_tts()
        with stack:
            before, status = await profile_settings.async_handle_settings(f.hass,
                {**f.identity, "contract_version": 3}, headers=f.headers)
            self.assertEqual(status, 200, before)
            accepted, status = await profile_settings.async_handle_settings(f.hass,
                {**f.identity, "contract_version": 3, "binding": before["binding"],
                 "operation_id": operation(int(datetime.now(UTC).timestamp() * 1000)),
                 "expected_defaults_revision": before["snapshot"]["defaults_revision"],
                 "expected_session": None, "patch": {"announcement_output": "client_device",
                     "voice": {"kind": "provider_voice", "provider_id": pipeline.tts_engine,
                               "voice_id": "marin"}}}, headers=f.headers, write=True)
            self.assertEqual(status, 200, accepted)
            provider, catalogue_calls = self.catalogue_provider()
            with patch.object(f.core, "run_music_command", provider):
                answer, status = await f.request("Speel iets van Metallica.",
                    identifier="metallica-settings3", speech_contract_version=3)
            self.assertEqual(status, 200, answer)
            payload = {**f.identity, "contract_version": 3,
                       "reference": answer["session_speech"]["reference"],
                       "processor": "ha_configured", "intent": "manual", "target": "local"}
            prepared, status = await session_speech.async_handle_prepare(f.hass, payload, headers=f.headers)
            self.assertEqual(status, 200, prepared)
            speech = prepared["session_speech"]
            self.assertEqual(speech["audio_state"], "ready")
            self.assertEqual(speech["effective_voice"]["voice_id"], "marin")
            self.assertEqual(speech["effective_voice"]["engine"], pipeline.tts_engine)
            for key in ("reference", "text_revision", "presentation_revision", "persona",
                        "persona_revision", "locale", "attribution"):
                self.assertEqual(speech[key], answer["session_speech"][key], key)
            self.assertEqual(synthesis_calls[0][0], answer["text"])
            self.assertEqual(answer["items"], [])
            self.assertEqual(len(answer["playback_actions"]), 10)
            after, _ = await profile_settings.async_handle_settings(f.hass,
                {**f.identity, "contract_version": 3}, headers=f.headers)
            self.assertEqual(after["snapshot"], accepted["snapshot"])
        self.assertEqual(catalogue_calls, ["status", "search_albums", "search_playlists"])
        self.assertEqual(f.prompts, [])

    async def test_current_prince_album_period_refinement_keeps_real_titles_and_original_expiry(
        self,
    ):
        f = self.f
        calls = []

        async def provider(hass, runtime, command, value=None, **kwargs):
            calls.append(command)
            if command == "artist_albums":
                return {
                    "success": True,
                    "artist": "Prince",
                    "albums": [
                        {
                            "name": "Prince",
                            "uri": "spotify:album:" + "A" * 22,
                            "release_date": "1979-10-19",
                        },
                        {
                            "name": "1999",
                            "uri": "spotify:album:" + "B" * 22,
                            "release_date": "1982-10-27",
                        },
                        {
                            "name": "Purple Rain",
                            "uri": "spotify:album:" + "C" * 22,
                            "release_date": "1984-06-25",
                        },
                        {"name": "Unqualified date", "uri": "spotify:album:" + "D" * 22},
                    ],
                }
            if command == "status":
                return {"success": True, "playback": {}}
            raise AssertionError(
                "Period refinement cannot mutate playback or refetch unrelated data: " + command
            )

        with patch.object(f.core, "run_music_command", provider):
            initial, status = await f.request(
                "Welke albums heeft Prince?", identifier="prince-albums", language="nl"
            )
            self.assertEqual(status, 200, initial)
            self.assertIn("Purple Rain", initial["text"])
            frame = f.history.dialogue.owners["profile:profile-a"]["default"]
            deadline = frame.result_set["deadline"]
            refined, status = await f.request(
                "Alleen tussen 1980 en 1990", identifier="prince-period", language="nl"
            )
            self.assertEqual(status, 200, refined)
            self.assertEqual(
                [item["title"] for item in refined["result_set"]["items"]], ["1999", "Purple Rain"]
            )
            self.assertEqual(
                [item["uri"] for item in refined["result_set"]["items"]],
                ["spotify:album:" + "B" * 22, "spotify:album:" + "C" * 22],
            )
            self.assertLessEqual(frame.result_set["deadline"], deadline)
            self.assertEqual(refined["filtering_coverage"]["missing_date"], 1)
            listed, status = await f.request(
                "Welke titels?", identifier="prince-titles", language="nl"
            )
            self.assertEqual(status, 200, listed)
            self.assertIn("1999", listed["text"])
            self.assertIn("Purple Rain", listed["text"])
            self.assertEqual(
                listed["result_set"]["result_set_id"], refined["result_set"]["result_set_id"]
            )
        self.assertEqual(calls.count("artist_albums"), 1)
        self.assertEqual(f.prompts, [])

    async def test_period_empty_result_replaces_old_offer_and_cannot_revive_old_album(self):
        f = self.f

        async def provider(hass, runtime, command, value=None, **kwargs):
            if command == "artist_albums":
                return {
                    "success": True,
                    "artist": "Prince",
                    "albums": [
                        {
                            "name": "Prince",
                            "uri": "spotify:album:" + "A" * 22,
                            "release_date": "1979",
                        }
                    ],
                }
            if command == "status":
                return {"success": True, "playback": {}}
            raise AssertionError("No playback effect allowed")

        with patch.object(f.core, "run_music_command", provider):
            initial, status = await f.request(
                "Welke albums heeft Prince?", identifier="prince-empty-seed", language="nl"
            )
            self.assertEqual(status, 200, initial)
            shown = initial["result_set"]
            refined, status = await f.request(
                "Alleen tussen 1980 en 1990", identifier="prince-empty-filter", language="nl"
            )
            self.assertEqual(status, 200, refined)
            self.assertEqual(refined["items"], [])
            played, status = await f.request(
                "Speel die",
                identifier="prince-empty-old",
                language="nl",
                choice_action={
                    "result_set_id": shown["result_set_id"],
                    "action_id": shown["items"][0]["action_id"],
                    "operation": "play",
                },
            )
            self.assertEqual(status, 409, played)
        self.assertEqual(f.prompts, [])

    async def test_morning_no_new_proposal_yes_and_sleep_are_one_owner_conversation(self):
        from custom_components.djconnect import http

        f = self.f
        effects = []
        playing = False
        target = "spotify:track:" + "M" * 22

        async def provider(hass, runtime, command, value=None, **kwargs):
            nonlocal playing
            if command == "status":
                return {
                    "success": True,
                    "playback": {
                        "has_playback": playing,
                        "is_playing": playing,
                        "uri": target if playing else "",
                    },
                }
            if command == "listening_profile":
                return {
                    "success": True,
                    "profile": {
                        "top_tracks_by_range": {
                            "short_term": [
                                {
                                    "uri": target,
                                    "track_name": "Morning fixture",
                                    "artist": "Fixture artist",
                                }
                            ]
                        },
                        "sources": ["spotify_top_tracks_short_term"],
                    },
                }

            async def dispatch():
                nonlocal playing
                if command == "play":
                    await f.dialogue.guard_effect_dispatch(
                        method="PUT", path="/me/player/play", body={"uris": [value]}
                    )
                    playing = True
                elif command == "pause":
                    await f.dialogue.guard_effect_dispatch(
                        method="PUT", path="/me/player/pause", body=None
                    )
                    playing = False
                else:
                    raise AssertionError("Unexpected morning effect: " + command)
                effects.append((command, value))

            result = await f.external_effect_probe(command, value, dispatch)
            return {**result, "playback": {"is_playing": playing, "uri": target}}

        with (
            patch.object(f.core, "run_music_command", provider),
            patch.object(http, "run_music_command", provider),
        ):
            first, status = await f.request("Goedemorgen", identifier="morning-1", language="nl")
            self.assertEqual(status, 200, first)
            self.assertTrue(first.get("confirmation_actions"), first)
            frame = f.history.dialogue.owners["profile:profile-a"]["default"]
            first_pending = frame.pending
            self.assertIsNotNone(first_pending, first)
            no, status = await f.request("Nee", identifier="morning-no", language="nl")
            self.assertEqual(status, 200, no)
            self.assertIsNone(frame.pending)
            self.assertEqual(effects, [])
            second, status = await f.request("Goedemorgen", identifier="morning-2", language="nl")
            self.assertEqual(status, 200, second)
            self.assertIsNot(frame.pending, first_pending)
            yes, status = await f.request("Ja", identifier="morning-yes", language="nl")
            self.assertEqual(status, 200, yes)
            self.assertTrue(yes["success"], yes)
            self.assertEqual(effects, [("play", target)])
            self.assertIsNone(frame.pending)
            slept, status = await f.request(
                "Ik ga slapen", identifier="morning-sleep", language="nl"
            )
            self.assertEqual(status, 200, slept)
            self.assertTrue(slept["success"], slept)
            self.assertEqual(effects, [("play", target), ("pause", None)])
            self.assertFalse(playing)

    async def test_search_live_titles_choice_volume_and_play_keep_one_exact_result(self):
        import json
        from custom_components.djconnect import http

        f = self.f
        queries = []
        effects = []
        observed_uri = ""

        async def search(hass, runtime, query, **kwargs):
            queries.append(query)
            return {
                "success": True,
                "tracks": [
                    {
                        "uri": "spotify:track:" + letter * 22,
                        "title": title,
                        "artist": "Within Temptation",
                    }
                    for letter, title in (
                        ("A", "First original" if len(queries) == 1 else "First live"),
                        ("B", "Second original" if len(queries) == 1 else "Second live"),
                    )
                ],
            }

        async def provider(hass, runtime, command, value=None, **kwargs):
            if command == "status":
                return {
                    "success": True,
                    "playback": {
                        "volume_percent": 40,
                        "is_playing": bool(observed_uri),
                        "uri": observed_uri,
                    },
                }

            async def dispatch():
                nonlocal observed_uri
                if command == "set_volume":
                    await f.dialogue.guard_effect_dispatch(
                        method="PUT", path=f"/me/player/volume?volume_percent={value}", body=None
                    )
                elif command == "play":
                    await f.dialogue.guard_effect_dispatch(
                        method="PUT", path="/me/player/play", body={"uris": [value]}
                    )
                    observed_uri = value
                else:
                    raise AssertionError("Unexpected chain effect: " + command)
                effects.append((command, value))

            return await f.external_effect_probe(command, value, dispatch)

        with (
            patch.object(f.core, "_spotify_track_search", search),
            patch.object(f.core, "run_music_command", provider),
            patch.object(http, "run_music_command", provider),
        ):
            f.reply = json.dumps({"intent": "lookup", "query": "Within Temptation"})
            initial, status = await f.request(
                "Wat heb je van Within Temptation?", identifier="chain-search", language="nl"
            )
            self.assertEqual(status, 200, initial)
            f.reply = json.dumps({"intent": "refine", "query": "Within Temptation live"})
            refined, status = await f.request("Liever live", identifier="chain-live", language="nl")
            self.assertEqual(status, 200, refined)
            self.assertIn("result_set", initial, initial)
            self.assertIn("result_set", refined, refined)
            self.assertNotEqual(
                initial["result_set"]["result_set_id"], refined["result_set"]["result_set_id"]
            )
            listed, status = await f.request("Welke dan?", identifier="chain-list", language="nl")
            self.assertEqual(status, 200, listed)
            self.assertIn("First live", listed["text"])
            self.assertIn("Second live", listed["text"])
            chosen, status = await f.request("De tweede", identifier="chain-select", language="nl")
            self.assertEqual(status, 200, chosen)
            self.assertEqual(effects, [])
            quiet, status = await f.request("Zachter", identifier="chain-volume", language="nl")
            self.assertEqual(status, 200, quiet)
            self.assertEqual(effects, [("set_volume", 30)])
            played, status = await f.request("Speel die", identifier="chain-play", language="nl")
            self.assertEqual(status, 200, played)
            self.assertTrue(played["success"], played)
            self.assertEqual(observed_uri, "spotify:track:" + "B" * 22)
            self.assertEqual(
                played["action_outcome"], {"state": "confirmed", "readback_confirmed": True}
            )
            self.assertEqual(played["selected_action_id"], chosen["selected_action_id"])
            self.assertEqual(effects, [("set_volume", 30), ("play", "spotify:track:" + "B" * 22)])
        self.assertEqual(queries, ["Within Temptation", "Within Temptation live"])

    async def test_resume_shuffle_repeat_use_actual_typed_effect_grants(self):
        f = self.f
        effects = []

        async def provider(hass, runtime, command, value=None, **kwargs):
            if command == "status":
                return {"success": True, "playback": {"is_playing": False}}

            async def dispatch():
                paths = {
                    "play": "/me/player/play",
                    "set_shuffle": "/me/player/shuffle?state=true",
                    "set_repeat": "/me/player/repeat?state=off",
                }
                await f.dialogue.guard_effect_dispatch(method="PUT", path=paths[command], body=None)
                effects.append((command, value))

            return await f.external_effect_probe(command, value, dispatch)

        with patch.object(f.core, "run_music_command", provider):
            for i, text in enumerate(("Hervat muziek", "Zet shuffle aan", "Zet repeat uit")):
                result, status = await f.request(
                    text, identifier="golden-control-" + str(i), language="nl"
                )
                self.assertEqual(status, 200, result)
                self.assertTrue(result["success"], result)
        self.assertEqual(effects, [("play", None), ("set_shuffle", True), ("set_repeat", "off")])
        self.assertEqual(f.prompts, [])

    async def test_taste_surprise_select_then_play_keeps_the_actual_recommendation(self):
        from custom_components.djconnect import http

        f = self.f
        played = []
        tracks = [
            {
                "uri": "spotify:track:" + letter * 22,
                "track_name": "Fixture " + letter,
                "artist": "Artist " + letter,
            }
            for letter in "ABCDE"
        ]

        async def provider(hass, runtime, command, value=None, **kwargs):
            if command == "status":
                return {"success": True, "playback": {"is_playing": False}}
            if command == "listening_profile":
                return {
                    "success": True,
                    "profile": {
                        "top_tracks_by_range": {"short_term": tracks},
                        "top_artists_by_range": {
                            "short_term": [
                                {
                                    "uri": "spotify:artist:" + "Z" * 22,
                                    "name": "Fixture Artist",
                                    "genres": ["rock"],
                                }
                            ]
                        },
                        "sources": [
                            "spotify_top_tracks_short_term",
                            "spotify_top_artists_short_term",
                        ],
                    },
                }

            async def dispatch():
                self.assertEqual(command, "play")
                await f.dialogue.guard_effect_dispatch(
                    method="PUT", path="/me/player/play", body={"uris": [value]}
                )
                played.append(value)

            return await f.external_effect_probe(command, value, dispatch)

        with (
            patch.object(f.core, "run_music_command", provider),
            patch.object(http, "run_music_command", provider),
        ):
            taste, status = await f.request(
                "Welke artiesten passen bij mijn smaak?", identifier="golden-taste", language="nl"
            )
            self.assertEqual(status, 200, taste)
            self.assertTrue(taste.get("items") or taste.get("playback_actions"), taste)
            surprise, status = await f.request(
                "Verras me", identifier="golden-surprise", language="nl"
            )
            self.assertEqual(status, 200, surprise)
            shown = surprise["result_set"]
            target = shown["items"][1]["uri"]
            selected, status = await f.request(
                "De tweede", identifier="golden-surprise-select", language="nl"
            )
            self.assertEqual(status, 200, selected)
            self.assertEqual(played, [])
            result, status = await f.request(
                "Speel die", identifier="golden-surprise-play", language="nl"
            )
            self.assertEqual(status, 200, result)
            self.assertTrue(result["success"], result)
            self.assertEqual(played, [target])
