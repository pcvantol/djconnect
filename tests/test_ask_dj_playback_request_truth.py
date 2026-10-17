"""Reported voice/playback failures: Core logic with provider I/O fixtures only."""

import unittest
import json
from unittest.mock import patch
from types import SimpleNamespace

from tests import test_ask_dj_contextual_dialogue as dialogue_tests


class PlaybackRequestTruthTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        dialogue_tests.SharedDialogueTest.setUpClass()
        cls.core = dialogue_tests.SharedDialogueTest.core
        from custom_components.djconnect import spotify_backend, processor, playback_request

        cls.backend_module, cls.processor, cls.receipts = (
            spotify_backend,
            processor,
            playback_request,
        )

    @classmethod
    def tearDownClass(cls):
        dialogue_tests.SharedDialogueTest.tearDownClass()

    def backend(self, *, unrelated_artist=False, only_wrong_tracks=False, returned_artist=None):
        calls = []
        artist = {"id": "A" * 22, "uri": "spotify:artist:" + "A" * 22, "name": "Nirvana"}
        if unrelated_artist:
            artist = {"id": "G" * 22, "uri": "spotify:artist:" + "G" * 22, "name": "Guns N' Roses"}
        if returned_artist is not None:
            artist["name"] = returned_artist
        nirvana = {
            "id": "N" * 22,
            "uri": "spotify:track:" + "N" * 22,
            "name": "Lithium",
            "artists": [{"id": "A" * 22, "name": "Nirvana"}],
            "album": {
                "name": "Nevermind",
                "uri": "spotify:album:" + "B" * 22,
                "images": [
                    {"url": "https://example.test/lithium.jpg", "width": 640, "height": 640}
                ],
            },
        }
        wrong = {
            "id": "W" * 22,
            "uri": "spotify:track:" + "W" * 22,
            "name": "Patience",
            "artists": [{"id": "G" * 22, "name": "Guns N' Roses"}],
            "album": {},
        }

        class Response:
            status = 200
            headers = {}

            def __init__(self, value, status=200):
                self.value, self.status = value, status

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def json(self, **kwargs):
                return self.value

            async def text(self):
                return ""

        class Session:
            def request(self, method, url, **kwargs):
                calls.append((method, url, kwargs.get("json")))
                if "/search?" in url:
                    return Response({"artists": {"items": [artist]}})
                if "/top-tracks?" in url:
                    return Response({"tracks": [wrong] if only_wrong_tracks else [wrong, nirvana]})
                return Response({}, 204)

        b = object.__new__(self.backend_module.SpotifyBackend)
        b.runtime = SimpleNamespace(config={"spotify_market": "NL"}, backend_cache={})
        b.hass, b.session = object(), Session()

        async def token(**kwargs):
            return "FIXTURE_ONLY"

        b._access_token = token
        return b, calls, nirvana

    async def test_positive_listening_requests_execute_but_negations_and_questions_do_not(self):
        for q in (
            "Ik wil Nirvana horen.",
            "I want to hear Nirvana.",
            "Ich möchte Nirvana hören.",
            "Je veux écouter Nirvana.",
            "Quiero escuchar Nirvana.",
        ):
            with self.subTest(question=q):
                result = self.core.classify_ask_dj(q)
                self.assertEqual((result.category, result.play), ("hybrid", True))
        for q in (
            "Speel Nirvana niet.",
            "Ik wil Nirvana niet horen.",
            "Wie is Nirvana?",
            "What happens if I play Nirvana?",
            '"Play Nirvana"',
        ):
            with self.subTest(question=q):
                self.assertFalse(self.core.classify_ask_dj(q).play)
        self.assertTrue(self.core.classify_ask_dj("Play No Doubt").play)
        self.assertFalse(self.core.classify_ask_dj("Ik wil rustige muziek horen.").play)

    async def test_artist_resolution_cannot_play_unrelated_search_result(self):
        backend, calls, _ = self.backend(unrelated_artist=True)
        with self.assertRaises(self.backend_module.SpotifyBackendError):
            await backend.play_artist_top_tracks("Nirvana")
        self.assertFalse(any(method == "PUT" for method, _, _ in calls))

    async def test_artist_collection_excludes_guns_n_roses_and_preserves_selected_art(self):
        backend, calls, track = self.backend()
        selection = await backend.play_artist_top_tracks("Nirvana")
        effects = [body for method, _, body in calls if method == "PUT"]
        self.assertEqual(effects, [{"uris": [track["uri"]]}])
        self.assertEqual(selection["media"]["title"], "Lithium")
        self.assertEqual(selection["media"]["artist"], "Nirvana")
        self.assertEqual(selection["media"]["album_image_url"], "https://example.test/lithium.jpg")
        stale = self.receipts.outcome(
            selection, {"is_playing": True, "uri": "spotify:track:" + "W" * 22}
        )
        self.assertEqual((stale["state"], stale["observed_match"]), ("dispatched", False))
        actual = self.receipts.outcome(selection, {"is_playing": True, "uri": track["uri"]})
        self.assertEqual((actual["state"], actual["observed_match"]), ("observed", True))

    async def test_artist_shuffle_names_and_illustrates_the_actually_observed_admitted_track(self):
        first = "spotify:track:" + "A" * 22
        actual = "spotify:track:" + "B" * 22
        selection = {
            "kind": "artist_tracks",
            "media": {
                "uri": first,
                "title": "Lithium",
                "artist": "Nirvana",
                "album_image_url": "https://example.test/first.jpg",
            },
            "uris": [first, actual],
            "context_uri": None,
        }
        observed = {
            "is_playing": True,
            "uri": actual,
            "track_name": "In Bloom",
            "artist": "Nirvana",
            "album_name": "Nevermind",
            "album_image_url": "https://example.test/observed.jpg",
        }
        receipt = self.receipts.outcome(selection, observed)
        self.assertEqual(receipt["state"], "observed")
        self.assertEqual(receipt["selection"]["media"]["uri"], actual)
        self.assertEqual(receipt["selection"]["media"]["track_name"], "In Bloom")
        self.assertEqual(
            receipt["selection"]["media"]["album_image_url"], observed["album_image_url"]
        )
        bindings, fallback = self.receipts._copy(receipt, "nl")
        self.assertEqual(bindings["{title}"], "In Bloom")
        self.assertNotIn("Lithium", fallback)
        self.assertEqual(selection["media"]["uri"], first)
        self.assertEqual(selection["media"]["title"], "Lithium")

    async def test_no_matching_artist_credit_means_zero_playback(self):
        backend, calls, _ = self.backend(only_wrong_tracks=True)
        with self.assertRaises(self.backend_module.SpotifyBackendError):
            await backend.play_artist_top_tracks("Nirvana")
        self.assertFalse(any(method == "PUT" for method, _, _ in calls))

    async def test_interpretation_cannot_replace_current_request_with_old_track(self):
        result = self.processor._request_bound_music_intent(
            "Speel Nirvana.", {"type": "artist", "artist": "Guns N' Roses", "query": "Patience"}
        )
        self.assertEqual(result["artist"], "Nirvana")
        self.assertEqual(result["spotify_search_query"], "Nirvana")
        result = self.processor._request_bound_music_intent(
            "Speel nummer Lithium van Nirvana.",
            {"type": "track", "title": "Patience", "artist": "Guns N' Roses"},
        )
        self.assertEqual((result["title"], result["artist"]), ("Lithium", "Nirvana"))

    async def test_artist_prefix_or_fuzzy_result_is_not_execution_identity(self):
        for name in ("Nirvana Tribute", "Nirvanna", "Nirvana UK"):
            with self.subTest(returned_artist=name):
                backend, calls, _ = self.backend(returned_artist=name)
                with self.assertRaises(self.backend_module.SpotifyBackendError):
                    await backend.play_artist_top_tracks("Nirvana")
                self.assertFalse(any(method == "PUT" for method, _, _ in calls))

    async def test_output_offer_never_imports_caller_frozen_media(self):
        forged = {
            "media": {"uri": "spotify:track:" + "W" * 22},
            "uris": ["spotify:track:" + "W" * 22],
        }
        actions = self.core._output_device_play_request_actions(
            [{"id": "speaker-B", "name": "Bedroom"}],
            "play One",
            {"_frozen_playback_selection": forged},
        )
        self.assertNotIn("_frozen_playback_selection", actions[0]["value"]["request"])

    async def test_voice_request_and_speaker_choice_keep_exact_artist_and_never_resume_old_queue(
        self,
    ):
        await self._output_choice_scenario()

    async def test_track_choice_is_producer_frozen_despite_injected_selection_and_changed_search(
        self,
    ):
        await self._output_choice_scenario("track", forged=True)

    async def test_album_choice_uses_original_uri_without_second_search(self):
        await self._output_choice_scenario("album")

    async def test_playlist_choice_uses_original_uri_without_second_search(self):
        await self._output_choice_scenario("playlist")

    async def test_duplicate_output_tap_never_repeats_accepted_playback(self):
        await self._output_choice_scenario(duplicate=True)

    async def test_failed_dispatch_never_receives_success_or_art_from_old_playback(self):
        await self._output_choice_scenario(dispatch_failure=True)

    async def test_stale_readback_is_pending_and_never_acknowledged_as_selected_music_playing(self):
        await self._output_choice_scenario(stale=True)

    async def test_compound_speaker_500_is_uncertain_and_single_use_without_music_start(self):
        await self._output_choice_scenario(transfer_failure=500)

    async def test_compound_speaker_timeout_is_uncertain_and_single_use_without_music_start(self):
        await self._output_choice_scenario(transfer_failure="timeout")

    async def test_compound_speaker_404_is_rejected_without_global_outage_or_music_start(self):
        await self._output_choice_scenario(transfer_failure=404)

    async def test_explicit_output_id_never_falls_back_to_active_cached_or_restricted_device(self):
        for devices in (
            [{"id": "old-speaker", "name": "Bedroom", "is_active": True}],
            [{"id": "another-device", "name": "iphone", "is_active": True}],
            [{"id": "iphone", "name": "iPhone", "is_restricted": True}],
            [{"id": "other-1", "name": "same"}, {"id": "other-2", "name": "same"}],
        ):
            with self.subTest(devices=devices):
                backend, calls = self._output_backend(devices)
                backend.runtime.device_status["available_outputs"] = [
                    {"id": "iphone", "name": "iPhone", "cached": True}
                ]
                with self.assertRaises(self.backend_module.SpotifyOutputError):
                    await backend.set_output("same" if len(devices) == 2 else "iphone")
                self.assertEqual(sum(method == "GET" for method, _, _ in calls), 1)
                self.assertFalse(any(method == "PUT" for method, _, _ in calls))

    async def test_output_404_and_500_are_action_local_and_never_disable_the_backend(self):
        f = dialogue_tests.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            for status, code, state in (
                (404, "output_unavailable", "rejected"),
                (500, "output_transfer_failed", "uncertain"),
            ):
                with self.subTest(status=status):
                    backend, calls = self._output_backend(
                        [{"id": "iphone", "name": "iPhone"}], status=status
                    )
                    with self.assertRaises(self.backend_module.SpotifyOutputError) as denied:
                        await backend.set_output("iphone")
                    f.runtime.device_status["backend_available"] = True
                    result, http = f.handlers._unexpected_backend_error_result(
                        f.hass,
                        f.runtime,
                        {"language": "nl"},
                        "set_output",
                        "set_output",
                        denied.exception,
                    )
                    self.assertEqual((http, result["success"], result["error"]), (200, False, code))
                    self.assertEqual(result["error_scope"], "output")
                    self.assertEqual(result["action_outcome"]["state"], state)
                    self.assertFalse(result["action_outcome"]["retry_automatically"])
                    self.assertTrue(f.runtime.device_status["backend_available"])
                    self.assertNotIn("backend_available", result)
                    self.assertEqual(sum(method == "PUT" for method, _, _ in calls), 1)
        finally:
            await f.asyncTearDown()

    async def test_output_dispatch_with_stale_target_readback_is_not_confirmed(self):
        backend, calls = self._output_backend([{"id": "iphone", "name": "iPhone"}])
        result = await self.backend_module._spotify_playback_command(
            backend, "set_output", "iphone", False, "set_output"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["action_outcome"]["state"], "dispatched")
        self.assertFalse(result["action_outcome"]["readback_confirmed"])
        self.assertEqual(result["action_outcome"]["selected_output_id"], "iphone")
        self.assertEqual(
            [body for method, _, body in calls if method == "PUT"],
            [{"device_ids": ["iphone"], "play": False}],
        )

    def _output_backend(self, devices, *, status=204):
        backend, _, _ = self.backend()
        calls = []
        backend.runtime.device_status = {}
        backend.runtime.update = lambda **kwargs: None

        class Response:
            headers = {}

            def __init__(self, data, status):
                self.data, self.status = data, status

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def json(self, **kwargs):
                return self.data

            async def text(self):
                return json.dumps(self.data)

        class Session:
            def request(self, method, url, **kwargs):
                from urllib.parse import urlsplit

                path = urlsplit(url).path
                calls.append((method, path, kwargs.get("json")))
                if path.endswith("/devices"):
                    return Response({"devices": devices}, 200)
                if method == "PUT":
                    return Response({"error": {"message": "device not found"}}, status)
                return Response({"is_playing": False, "device": {"id": "old-speaker"}}, 200)

        backend.session = Session()
        return backend, calls

    async def _output_choice_scenario(
        self,
        kind="artist",
        *,
        forged=False,
        duplicate=False,
        dispatch_failure=False,
        stale=False,
        transfer_failure=None,
    ):
        f = dialogue_tests.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            from dataclasses import replace
            from custom_components.djconnect.domain.backend import BackendProvider
            from custom_components.djconnect.domain.music_account import MusicAccountKind

            storage = f.hass.data["djconnect"]["djconnect_profile_platform"]
            await storage.async_upsert_music_backend(
                "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Provider fixture"
            )
            await storage.async_upsert_music_account(
                "nirvana-account",
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
                    default_music_account_id="nirvana-account",
                ),
            )
            f.runtime.config.update(
                music_backend="spotify_direct", music_account_id="nirvana-account"
            )
            entry = SimpleNamespace(
                entry_id="owner-entry",
                data={**f.runtime.config, "device_token": f.runtime.device_token},
                options={},
                disabled_by=None,
                state=SimpleNamespace(value="loaded"),
            )
            f.runtime.entry = entry
            f.hass.config_entries.async_entries = lambda domain: [entry]
            f.hass.config_entries.async_get_entry = lambda eid: (
                entry if eid == "owner-entry" else None
            )
            f.runtime.update = lambda **fields: [
                setattr(f.runtime, key, value) for key, value in fields.items()
            ]
            sample, calls, track = self.backend()
            original_session = sample.session
            selected, playing = False, False
            search_calls = 0
            selected_uri = (
                track["uri"] if kind in ("artist", "track") else "spotify:" + kind + ":" + "B" * 22
            )
            title = (
                "Lithium"
                if kind in ("artist", "track")
                else "Nevermind"
                if kind == "album"
                else "Nirvana Favorites"
            )
            request_text = {
                "artist": "Ik wil Nirvana horen.",
                "track": "Speel nummer Lithium van Nirvana.",
                "album": "Speel album Nevermind van Nirvana.",
                "playlist": "Speel playlist Nirvana Favorites.",
            }[kind]
            media = {
                "uri": selected_uri,
                "id": "B" * 22,
                "name": title,
                "artists": [{"id": "A" * 22, "name": "Nirvana"}],
                "images": [
                    {"url": "https://example.test/lithium.jpg", "width": 640, "height": 640}
                ],
                "album": track["album"],
            }

            class Response:
                headers = {}

                def __init__(self, data, status=200):
                    self.data, self.status = data, status

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    return None

                async def json(self, **kwargs):
                    return self.data

                async def text(self):
                    return str(self.data)

            class Session:
                def request(self, method, url, **kwargs):
                    nonlocal selected, playing, search_calls
                    from urllib.parse import urlsplit

                    path = urlsplit(url).path
                    if path.endswith("/search"):
                        search_calls += 1
                        if kind != "artist":
                            # A fresh interpretation/search after the offer would
                            # return B. Only the original A is authorised.
                            result = (
                                media
                                if search_calls == 1
                                else {**media, "uri": "spotify:" + kind + ":" + "W" * 22}
                            )
                            return Response({kind + "s": {"items": [result]}})
                    if path.endswith("/me/player/devices"):
                        return Response(
                            {
                                "devices": [
                                    {
                                        "id": "speaker-B",
                                        "name": "Bedroom",
                                        "is_active": selected,
                                        "is_restricted": False,
                                        "type": "Speaker",
                                    }
                                ]
                            }
                        )
                    if path.endswith("/me/player") and method == "GET":
                        return Response(
                            {
                                "is_playing": True,
                                "context": {"uri": selected_uri}
                                if playing and kind in ("album", "playlist")
                                else {},
                                "item": track
                                if playing and not stale
                                else {
                                    "uri": "spotify:track:" + "W" * 22,
                                    "name": "Patience",
                                    "artists": [{"id": "G" * 22, "name": "Guns N’ Roses"}],
                                    "album": {},
                                },
                                "device": {
                                    "id": "speaker-B",
                                    "name": "Bedroom",
                                    "is_active": selected,
                                },
                            }
                        )
                    if path.endswith("/me/player") and method == "PUT":
                        calls.append((method, path, kwargs.get("json")))
                        if transfer_failure == "timeout":
                            raise TimeoutError("provider transfer timeout")
                        if transfer_failure:
                            return Response(
                                {"error": {"message": "transfer rejected"}}, transfer_failure
                            )
                        selected = True
                        return Response({}, 204)
                    if path.endswith("/me/player/play"):
                        if not selected:
                            return Response({"error": {"message": "No active device found"}}, 404)
                        calls.append((method, path, kwargs.get("json")))
                        if dispatch_failure:
                            return Response(
                                {"error": {"message": "Provider rejected playback"}}, 500
                            )
                        playing = True
                        return Response({}, 204)
                    if path.endswith("/me/tracks/contains"):
                        return Response([False])
                    if "/artists/" in path and not path.endswith("/top-tracks"):
                        return Response({"genres": []})
                    return original_session.request(method, url, **kwargs)

            async def token(*args, **kwargs):
                return "FIXTURE_ONLY"

            async def agent(hass, data, **kwargs):
                prompt = data["text"]
                body = json.loads(prompt.split("\nData:\n", 1)[1])
                if "candidate" in body:
                    text = json.dumps({"supported": True, "language_ok": True, "style_ok": True})
                else:
                    text = json.dumps({"text": " · ".join(body["required_placeholders"])})
                return {"response": {"speech": {"plain": {"speech": text}}}}

            with (
                patch.object(
                    self.backend_module, "async_get_clientsession", lambda hass: Session()
                ),
                patch.object(self.backend_module.SpotifyBackend, "_access_token", token),
                patch.object(f.pipeline, "_call_conversation_process_transport", agent),
            ):
                offered, status = await f.handlers.async_handle_ask_dj_message_payload(
                    f.hass,
                    {
                        **f.identity,
                        "text": request_text,
                        "client_message_id": "nirvana-voice-no-output",
                        **(
                            {
                                "_frozen_playback_selection": {
                                    "uris": ["spotify:track:" + "W" * 22],
                                    "media": {"title": "Patience"},
                                }
                            }
                            if forged
                            else {}
                        ),
                        "language": "nl",
                        "audio_response": "never",
                    },
                    headers=f.headers,
                    voice_input=True,
                )
                self.assertEqual(status, 200, offered)
                self.assertEqual(offered.get("action"), "select_output", offered)
                self.assertEqual(
                    offered["assistant_message"]["session_turn"]["input_type"], "voice"
                )
                self.assertFalse(any(path.endswith("/play") for _, path, _ in calls))
                shown = offered["result_set"]
                action = shown["items"][0]
                frozen = action["value"]["request"]["_frozen_playback_selection"]
                self.assertEqual(frozen["media"]["title"], title)
                response, status = await f.request(
                    "Speel hier",
                    identifier="nirvana-exact-output",
                    language="nl",
                    choice_action={
                        "result_set_id": shown["result_set_id"],
                        "action_id": action["action_id"],
                        "operation": "play",
                    },
                )
                self.assertEqual(status, 200, response)
                effects = [body for method, path, body in calls if method == "PUT"]
                if transfer_failure:
                    self.assertEqual(effects, [{"device_ids": ["speaker-B"], "play": False}])
                    self.assertFalse(response["success"])
                    self.assertEqual(
                        response["error"],
                        "output_unavailable"
                        if transfer_failure == 404
                        else "output_transfer_failed",
                    )
                    self.assertEqual(
                        response["action_outcome"]["state"],
                        "rejected" if transfer_failure == 404 else "uncertain",
                    )
                    self.assertNotIn("backend_available", response)
                    self.assertNotIn("playback_outcome", response)
                    await f.request(
                        "Speel hier",
                        identifier="uncertain-transfer-duplicate",
                        language="nl",
                        choice_action={
                            "result_set_id": shown["result_set_id"],
                            "action_id": action["action_id"],
                            "operation": "play",
                        },
                    )
                    self.assertEqual(
                        [body for method, path, body in calls if method == "PUT"], effects
                    )
                    return
                expected = (
                    {"uris": [selected_uri]}
                    if kind in ("artist", "track")
                    else {"context_uri": selected_uri}
                )
                self.assertEqual(effects, [{"device_ids": ["speaker-B"], "play": False}, expected])
                self.assertEqual(search_calls, 1)
                if dispatch_failure:
                    self.assertNotIn("playback_outcome", response)
                    self.assertNotIn("Daar is Nirvana", response.get("text", ""))
                    self.assertFalse(response.get("images"))
                    return
                if duplicate:
                    await f.request(
                        "Speel hier",
                        identifier="nirvana-duplicate-output",
                        language="nl",
                        choice_action={
                            "result_set_id": shown["result_set_id"],
                            "action_id": action["action_id"],
                            "operation": "play",
                        },
                    )
                    self.assertEqual(
                        [body for method, path, body in calls if method == "PUT"], effects
                    )
                if stale:
                    self.assertEqual(response["playback_outcome"]["state"], "dispatched")
                    self.assertIn("nog niet bevestigd", response["text"])
                    return
                self.assertEqual(response["playback_outcome"]["state"], "observed")
                self.assertIn(title, response["text"])
                self.assertIn("Nirvana", response["text"])
                self.assertNotIn("Patience", response["text"])
                self.assertTrue(response["images"])
                self.assertFalse(any("Guns" in str(i) for i in response["images"]))
                self.assertTrue(response["conversation"]["metrics"]["agent_calls"] <= 3)
        finally:
            await f.asyncTearDown()
