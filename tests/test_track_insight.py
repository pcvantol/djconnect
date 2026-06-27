from __future__ import annotations

import asyncio
import importlib
import types
import unittest

from tests.test_config_flow_helpers import install_homeassistant_stubs


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

    def test_explicit_track_returns_normalized_insight_and_visual_profile(self) -> None:
        hass = FakeHass(
            '{"summary":"Warm and wide","full_text":"A detailed view",'
            '"genre":"electronic","energy":0.7,"danceability":0.8,'
            '"intensity":0.6,"confidence":0.9,"production_notes":["wide mix"],'
            '"instrumentation":["synth"],"arrangement_notes":["slow build"],'
            '"listening_cues":["pad swell"],"similar_tracks":[]}'
        )
        runtime = Runtime()

        result = asyncio.run(
            self.track_insight.TrackInsightService().async_analyze(
                hass,
                runtime,
                {"title": "Innerbloom", "artist": "RUFUS DU SOL", "album": "Bloom"},
                source="http",
            )
        )

        self.assertEqual(result["source"], "http")
        self.assertEqual(result["track"]["title"], "Innerbloom")
        self.assertEqual(result["analysis"]["summary"], "Warm and wide")
        self.assertEqual(result["analysis"]["energy"], 0.7)
        self.assertFalse(result["cache"]["hit"])
        self.assertEqual(len(result["visual_profile"]["palette"]), 3)
        self.assertIn("music_dna", result)
        self.assertGreaterEqual(result["music_dna"]["match_percent"], 0)
        self.assertLessEqual(result["music_dna"]["match_percent"], 100)

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
        self.assertIn("Music DNA", result["text"])

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


if __name__ == "__main__":
    unittest.main()
