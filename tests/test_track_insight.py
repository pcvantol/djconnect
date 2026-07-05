from __future__ import annotations

import asyncio
import importlib
import logging
import types
import unittest

from tests.test_config_flow_helpers import install_homeassistant_stubs
from tests.test_http_voice_helpers import install_http_stubs


class FakeServices:
    def __init__(self, response_text: str | None = None) -> None:
        self.calls: list[dict] = []
        self.response_text = response_text

    async def async_call(self, domain, service, data, *, blocking=False, return_response=False):
        self.calls.append(
            {
                "domain": domain,
                "service": service,
                "data": data,
                "blocking": blocking,
                "return_response": return_response,
            }
        )
        if self.response_text is None:
            return {"response": {"speech": {"plain": {"speech": ""}}}}
        return {"response": {"speech": {"plain": {"speech": self.response_text}}}}


class FakeBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def async_fire(self, event_type, event_data):
        self.events.append((event_type, event_data))


class FakeHass:
    def __init__(self, response_text: str | None = None) -> None:
        self.services = FakeServices(response_text)
        self.bus = FakeBus()
        self.states = types.SimpleNamespace(get=lambda _entity_id: None)


class Runtime:
    def __init__(self) -> None:
        self.config = {"music_backend": "spotify_direct", "device_language": "en"}
        self.device_status = {}
        self.last_playback = {}


class TrackInsightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_homeassistant_stubs()
        cls.track_insight = importlib.import_module("custom_components.djconnect.track_insight")

    def test_prompt_builder_requests_json_only(self) -> None:
        prompt = self.track_insight.TrackInsightPromptBuilder().build(
            {"title": "Innerbloom", "artist": "RUFUS DU SOL", "album": "Bloom"},
            "en",
        )

        self.assertIn("Return JSON only", prompt)
        self.assertIn("Innerbloom", prompt)
        self.assertIn("energy", prompt)

    def test_prompt_builder_includes_realtime_mood_context(self) -> None:
        prompt = self.track_insight.TrackInsightPromptBuilder().build(
            {"title": "Innerbloom", "artist": "RUFUS DU SOL", "album": "Bloom"},
            "en",
            "70/100 (energy: duidelijk meer drive, uptempo, actief)",
        )

        self.assertIn("Realtime client mood", prompt)
        self.assertIn("70/100", prompt)
        self.assertIn("visual energy", prompt)

    def test_explicit_track_returns_normalized_insight_and_visual_profile(self) -> None:
        hass = FakeHass(
            '{"summary":"Warm and wide","full_text":"A detailed view",'
            '"genre":"electronic","energy":0.7,"danceability":0.8,'
            '"intensity":0.6,"confidence":0.9,"production_notes":["wide mix"],'
            '"instrumentation":["synth"],"arrangement_notes":["slow build"],'
            '"listening_cues":["pad swell"],"similar_tracks":[]}'
        )
        runtime = Runtime()

        previous = self.track_insight._LOGGER.level
        self.track_insight._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(self.track_insight._LOGGER, level="DEBUG") as captured:
                result = asyncio.run(
                    self.track_insight.TrackInsightService().async_analyze(
                        hass,
                        runtime,
                        {"title": "Innerbloom", "artist": "RUFUS DU SOL", "album": "Bloom"},
                        source="http",
                    )
                )
        finally:
            self.track_insight._LOGGER.setLevel(previous)

        self.assertEqual(result["source"], "http")
        self.assertEqual(result["track"]["title"], "Innerbloom")
        self.assertEqual(result["analysis"]["summary"], "Warm and wide")
        self.assertEqual(result["analysis"]["energy"], 0.7)
        self.assertFalse(result["cache"]["hit"])
        self.assertEqual(len(result["visual_profile"]["palette"]), 3)
        self.assertNotIn("music_dna", result)
        self.assert_no_music_dna_match_fields(result)
        logs = "\n".join(captured.output)
        self.assertIn("Track Insight analyzed", logs)
        self.assertNotIn("Innerbloom", logs)
        self.assertNotIn("RUFUS DU SOL", logs)

    def test_track_insight_records_energy_signal_in_music_dna(self) -> None:
        class Memory:
            def __init__(self) -> None:
                self.signals = []
                self.saved = 0

            def update_track_insight_energy(self, key, track, analysis):
                self.signals.append((key, dict(track), dict(analysis)))

            async def async_save(self):
                self.saved += 1

        hass = FakeHass(
            '{"summary":"Warm and wide","full_text":"A detailed view",'
            '"genre":"electronic","energy":0.81,"danceability":0.62,'
            '"intensity":0.74,"confidence":0.9}'
        )
        runtime = Runtime()
        runtime.memory = Memory()

        result = asyncio.run(
            self.track_insight.TrackInsightService().async_analyze(
                hass,
                runtime,
                {
                    "title": "Sewing Machine",
                    "artist": "Onur Yalcinsory",
                    "album": "Scala",
                    "music_dna_key": "user:peter",
                },
                source="http",
            )
        )

        self.assertEqual(result["analysis"]["energy"], 0.81)
        self.assertEqual(runtime.memory.signals[0][0], "user:peter")
        self.assertEqual(runtime.memory.signals[0][1]["title"], "Sewing Machine")
        self.assertEqual(runtime.memory.signals[0][2]["energy"], 0.81)
        self.assertEqual(runtime.memory.saved, 1)

    def test_explicit_track_accepts_client_playback_aliases(self) -> None:
        hass = FakeHass('{"summary":"Alias ok","full_text":"Detailed","confidence":0.8}')
        runtime = Runtime()

        result = asyncio.run(
            self.track_insight.TrackInsightService().async_analyze(
                hass,
                runtime,
                {
                    "playback": {
                        "track_name": "Windowlicker",
                        "artist_name": "Aphex Twin",
                        "album_name": "Windowlicker",
                    },
                    "backend": "spotify_direct",
                },
                source="websocket",
            )
        )

        self.assertEqual(result["source"], "websocket")
        self.assertEqual(result["track"]["title"], "Windowlicker")
        self.assertEqual(result["track"]["artist"], "Aphex Twin")
        self.assertEqual(result["track"]["album"], "Windowlicker")

    def test_track_insight_uses_playback_artist_genres_when_analysis_omits_genre(self) -> None:
        hass = FakeHass('{"summary":"Genre from playback","full_text":"Detailed","confidence":0.8}')
        runtime = Runtime()

        async def fake_run_music_command(_hass, _runtime, command, value=None):
            self.assertEqual(command, "status")
            return {
                "playback": {
                    "title": "Dream On",
                    "artist": "Scala & Kolacny Brothers",
                    "album": "Dream On",
                    "genres": ["belgian choir", "pop choir"],
                    "backend": "spotify_direct",
                }
            }

        original = self.track_insight.run_music_command
        self.track_insight.run_music_command = fake_run_music_command
        try:
            result = asyncio.run(self.track_insight.TrackInsightService().async_analyze(hass, runtime, {}, source="http"))
        finally:
            self.track_insight.run_music_command = original

        self.assertEqual(result["track"]["genres"], ["belgian choir", "pop choir"])
        self.assertEqual(result["analysis"]["genre"], "belgian choir")
        self.assertEqual(result["analysis"]["subgenre"], "pop choir")
        self.assertIn("Known artist genres: belgian choir, pop choir", hass.services.calls[0]["data"]["text"])

    def test_track_insight_fetches_artist_profile_genres_for_explicit_track(self) -> None:
        hass = FakeHass('{"summary":"Genre from artist","full_text":"Detailed","confidence":0.8}')
        runtime = Runtime()
        calls = []

        async def fake_run_music_command(_hass, _runtime, command, value=None):
            calls.append((command, value))
            if command == "artist_profile":
                return {"success": True, "artist": {"name": "Massive Attack", "genres": ["trip hop", "downtempo"]}}
            return {}

        original = self.track_insight.run_music_command
        self.track_insight.run_music_command = fake_run_music_command
        try:
            result = asyncio.run(
                self.track_insight.TrackInsightService().async_analyze(
                    hass,
                    runtime,
                    {"title": "Teardrop", "artist": "Massive Attack"},
                    source="http",
                )
            )
        finally:
            self.track_insight.run_music_command = original

        self.assertEqual(calls, [("artist_profile", {"artist": "Massive Attack"})])
        self.assertEqual(result["track"]["genres"], ["trip hop", "downtempo"])
        self.assertEqual(result["analysis"]["genre"], "trip hop")
        self.assertEqual(result["analysis"]["subgenre"], "downtempo")

    def test_cache_avoids_repeated_conversation_calls(self) -> None:
        hass = FakeHass('{"summary":"One","full_text":"One","confidence":0.8}')
        runtime = Runtime()
        service = self.track_insight.TrackInsightService()

        first = asyncio.run(
            service.async_analyze(
                hass,
                runtime,
                {"title": "Song", "artist": "Artist"},
                source="http",
            )
        )
        second = asyncio.run(
            service.async_analyze(
                hass,
                runtime,
                {"title": "Song", "artist": "Artist"},
                source="http",
            )
        )

        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(len(hass.services.calls), 1)
        self.assert_no_music_dna_match_fields(second)

    def test_cache_is_scoped_by_language(self) -> None:
        hass = FakeHass()
        runtime = Runtime()
        service = self.track_insight.TrackInsightService()

        english = asyncio.run(
            service.async_analyze(
                hass,
                runtime,
                {"title": "Run", "artist": "Floor Jansen", "language": "en"},
                source="http",
            )
        )
        dutch = asyncio.run(
            service.async_analyze(
                hass,
                runtime,
                {"title": "Run", "artist": "Floor Jansen", "language": "nl"},
                source="http",
            )
        )

        self.assertNotEqual(english["cache"]["key"], dutch["cache"]["key"])
        self.assertEqual(english["language"], "en")
        self.assertEqual(dutch["language"], "nl")
        self.assertIn("Run by Floor Jansen", english["analysis"]["summary"])
        self.assertIn("Run van Floor Jansen", dutch["analysis"]["summary"])
        self.assertIn("Luister", dutch["analysis"]["full_text"])

    def test_cache_is_scoped_by_realtime_mood(self) -> None:
        hass = FakeHass('{"summary":"Mood aware","full_text":"Detailed","confidence":0.8}')
        runtime = Runtime()
        service = self.track_insight.TrackInsightService()

        chill = asyncio.run(
            service.async_analyze(
                hass,
                runtime,
                {"title": "Run", "artist": "Floor Jansen", "language": "nl", "mood": 10},
                source="http",
            )
        )
        energy = asyncio.run(
            service.async_analyze(
                hass,
                runtime,
                {"title": "Run", "artist": "Floor Jansen", "language": "nl", "mood": 70},
                source="http",
            )
        )

        self.assertNotEqual(chill["cache"]["key"], energy["cache"]["key"])
        self.assertEqual(chill["mood_context"]["zone"], "chill")
        self.assertEqual(energy["mood_context"]["zone"], "energy")
        self.assertEqual(len(hass.services.calls), 2)
        self.assertIn("10/100", hass.services.calls[0]["data"]["text"])
        self.assertIn("70/100", hass.services.calls[1]["data"]["text"])

    def test_track_insight_handler_uses_language_headers(self) -> None:
        install_http_stubs()
        api_handlers = importlib.import_module("custom_components.djconnect.api_handlers")
        const = importlib.import_module("custom_components.djconnect.const")

        class RuntimeWithAuth(Runtime):
            device_token = "device-token"

            def __init__(self) -> None:
                super().__init__()
                self.device_status = {"device_id": "djconnect-ios-68B74487726D"}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

        runtime = RuntimeWithAuth()
        hass = FakeHass()
        hass.data = {const.DOMAIN: {"runtime": runtime}}

        previous = api_handlers._LOGGER.level
        api_handlers._LOGGER.setLevel(logging.DEBUG)
        try:
            with self.assertLogs(api_handlers._LOGGER, level="DEBUG") as captured:
                result, status = asyncio.run(
                    api_handlers.async_handle_track_insight_payload(
                        hass,
                        {
                            "device_id": "djconnect-ios-68B74487726D",
                            "client_type": "ios",
                            "title": "Run",
                            "artist": "Floor Jansen",
                        },
                        headers={
                            "Authorization": "Bearer device-token",
                            "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
                            "X-DJConnect-Language": "nl",
                            "X-DJConnect-Locale": "nl",
                            "Accept-Language": "nl",
                        },
                        source="http",
                    )
                )
        finally:
            api_handlers._LOGGER.setLevel(previous)

        self.assertEqual(status, 200)
        self.assertEqual(result["language"], "nl")
        self.assertIn("Run van Floor Jansen", result["analysis"]["summary"])
        self.assertEqual(hass.services.calls[0]["data"]["language"], "nl")
        logs = "\n".join(captured.output)
        self.assertIn("Track Insight http request", logs)
        self.assertIn("Track Insight http result", logs)
        self.assertIn("title_present=True", logs)
        self.assertNotIn("Floor Jansen", logs)
        self.assertNotIn("Bearer device-token", logs)

    def test_track_insight_handler_uses_mood_header(self) -> None:
        install_http_stubs()
        api_handlers = importlib.import_module("custom_components.djconnect.api_handlers")
        const = importlib.import_module("custom_components.djconnect.const")

        class RuntimeWithAuth(Runtime):
            device_token = "device-token"

            def __init__(self) -> None:
                super().__init__()
                self.device_status = {"device_id": "djconnect-ios-68B74487726D"}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

        runtime = RuntimeWithAuth()
        hass = FakeHass()
        hass.data = {const.DOMAIN: {"runtime": runtime}}

        result, status = asyncio.run(
            api_handlers.async_handle_track_insight_payload(
                hass,
                {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "title": "Run",
                    "artist": "Floor Jansen",
                    "language": "nl",
                },
                headers={
                    "Authorization": "Bearer device-token",
                    "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
                    "X-DJConnect-Mood": "85",
                },
                source="http",
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["mood_context"]["value"], 85)
        self.assertEqual(result["mood_context"]["zone"], "party")
        self.assertIn("85/100", hass.services.calls[0]["data"]["text"])

    def test_cache_strips_legacy_music_dna_match_fields(self) -> None:
        runtime = Runtime()
        key = self.track_insight._cache_key(
            {
                "title": "Song",
                "artist": "Artist",
                "album": None,
                "backend": "spotify_direct",
                "duration_ms": 0,
            }
        )
        runtime.track_insight_cache = {
            key: {
                "_cached_at": 9999999999,
                "response": {
                    "track": {"title": "Song", "artist": "Artist"},
                    "analysis": {"summary": "Cached"},
                    "music" + "_dna": {
                        "match" + "_percent": 91,
                        "label": "matches" + "_music_dna",
                    },
                },
            }
        }

        result = self.track_insight.TrackInsightCache(runtime).get(key)

        self.assertIsNotNone(result)
        self.assert_no_music_dna_match_fields(result)

    def test_missing_track_returns_structured_error(self) -> None:
        hass = FakeHass()
        runtime = Runtime()

        with self.assertRaises(self.track_insight.TrackInsightError) as err:
            asyncio.run(self.track_insight.TrackInsightService().async_analyze(hass, runtime, {}, source="http"))

        self.assertEqual(err.exception.code, "no_track_playing")
        self.assertEqual(err.exception.status, 404)

    def test_ask_dj_intent_handler_returns_track_insight_envelope(self) -> None:
        hass = FakeHass('{"summary":"Big emotion","full_text":"Detailed","confidence":0.8}')
        runtime = Runtime()

        result = asyncio.run(
            self.track_insight.TrackInsightIntentHandler().async_handle(
                hass,
                runtime,
                {"title": "Song", "artist": "Artist"},
            )
        )

        self.assertEqual(result["type"], "track_insight")
        self.assertEqual(result["open_screen"], "track_insight")
        self.assertEqual(result["track_insight"]["track"]["artist"], "Artist")
        self.assertNotIn("Music DNA", result["text"])
        self.assert_no_music_dna_match_fields(result)

    def test_hass_service_fires_event(self) -> None:
        hass = FakeHass('{"summary":"Ready","full_text":"Detailed","confidence":0.8}')
        runtime = Runtime()

        result = asyncio.run(
            self.track_insight.TrackInsightHassService().async_handle(
                hass,
                runtime,
                {"title": "Song", "artist": "Artist"},
            )
        )

        self.assertEqual(result["track"]["title"], "Song")
        self.assertEqual(hass.bus.events[0][0], self.track_insight.TRACK_INSIGHT_EVENT)

    def test_text_classifier_matches_track_insight_requests(self) -> None:
        self.assertTrue(self.track_insight.is_track_insight_request("Tell me about this track"))
        self.assertTrue(self.track_insight.is_track_insight_request("Give me Track Insight"))
        self.assertFalse(self.track_insight.is_track_insight_request("play something else"))

    def assert_no_music_dna_match_fields(self, value) -> None:
        forbidden = {
            "music" + "_dna",
            "match" + "_percent",
            "match" + "_reason",
        }
        if isinstance(value, dict):
            self.assertTrue(
                forbidden.isdisjoint(value),
                f"Track Insight response contains forbidden Music DNA match field(s): {forbidden & set(value)}",
            )
            if value.get("label") in {
                "matches" + "_music_dna",
                "expands" + "_music_dna",
                "outside" + "_music_dna",
            }:
                self.fail("Track Insight response contains a Music DNA match label")
            for child in value.values():
                self.assert_no_music_dna_match_fields(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_no_music_dna_match_fields(child)


if __name__ == "__main__":
    unittest.main()
