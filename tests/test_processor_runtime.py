from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest


from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def install_processor_stubs() -> None:
    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    aiohttp.ClientTimeout = ClientTimeout
    helpers = sys.modules.setdefault(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    aiohttp_client.async_get_clientsession = lambda hass: None
    helpers.aiohttp_client = aiohttp_client
    if "homeassistant.core" not in sys.modules:
        homeassistant = types.ModuleType("homeassistant")
        core = types.ModuleType("homeassistant.core")
        core.HomeAssistant = object
        sys.modules["homeassistant"] = homeassistant
        sys.modules["homeassistant.core"] = core
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)


class Runtime:
    config = {}

    def __init__(self) -> None:
        self.updates = []

    def update(self, **kwargs):
        self.updates.append(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)


class ProcessorRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_processor_stubs()
        cls.processor = importlib.import_module("custom_components.djconnect.processor")

    def test_process_text_command_updates_text_before_processing_result(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "search",
                "spotify_search_query": user_text,
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "resolved_media": {
                    "title": "Black",
                    "artist": "Pearl Jam",
                    "album_name": "Ten",
                }
            }

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "Speel Black",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(
            runtime.updates[0],
            {
                "last_text": "Speel Black",
                "last_stt_text": "Speel Black",
                "last_corrected_text": None,
                "last_error": None,
            },
        )
        self.assertEqual(runtime.last_intent["type"], "search")
        self.assertEqual(
            runtime.last_dj_text,
            "Daar is Pearl Jam, met Black. Van Ten.",
        )
        self.assertEqual(runtime.last_playback["resolved_media"]["title"], "Black")
        self.assertEqual(result["playback"]["resolved_media"]["artist"], "Pearl Jam")

    def test_process_text_command_corrects_stt_before_intent_parsing(self) -> None:
        seen = {}

        async def correct(hass, user_text, conf):
            seen["stt"] = user_text
            return "speel nummer Lithium van Nirvana"

        async def assist(hass, user_text, conf):
            seen["intent_text"] = user_text
            return {
                "type": "track",
                "title": "Lithium",
                "artist": "Nirvana",
                "spotify_search_query": "track:Lithium artist:Nirvana",
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "resolved_media": {
                    "title": intent["title"],
                    "artist": intent["artist"],
                }
            }

        original_correct = self.processor.correct_stt_text_with_assist
        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.correct_stt_text_with_assist = correct
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "speel nummer litiem van nervana",
                    play=True,
                    correct_stt=True,
                )
            )
        finally:
            self.processor.correct_stt_text_with_assist = original_correct
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(seen["stt"], "speel nummer litiem van nervana")
        self.assertEqual(seen["intent_text"], "speel nummer Lithium van Nirvana")
        self.assertEqual(runtime.last_stt_text, "speel nummer litiem van nervana")
        self.assertEqual(runtime.last_text, "speel nummer Lithium van Nirvana")
        self.assertEqual(runtime.last_corrected_text, "speel nummer Lithium van Nirvana")
        self.assertEqual(result["stt_text"], "speel nummer litiem van nervana")
        self.assertEqual(result["corrected_text"], "speel nummer Lithium van Nirvana")

    def test_process_text_command_uses_generated_dj_response_for_resolved_track(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "search",
                "spotify_search_query": user_text,
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "device_response": {
                    "playback": {
                        "track_name": "Alive",
                        "artist": "Pearl Jam",
                    }
                }
            }

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        async def generated_dj_response(hass, *, media, fallback_text, conf, debug=None):
            self.assertEqual(media["track_name"], "Alive")
            self.assertEqual(media["artist"], "Pearl Jam")
            self.assertIn("festival", conf["dj_response_prompt"])
            if debug is not None:
                debug["fallback_used"] = False
            return "Pearl Jam komt binnen alsof de festivalweide net wakker wordt."

        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        original_dj_response = self.processor.generate_dj_response_with_assist
        self.processor.generate_dj_response_with_assist = generated_dj_response
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": "Maak een energieke festival-DJ-aankondiging.",
            "tts_language": "nl",
        }
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "ik wil pearl jam starten",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play
            self.processor.generate_dj_response_with_assist = original_dj_response

        self.assertEqual(
            result["dj_text"],
            "Pearl Jam komt binnen alsof de festivalweide net wakker wordt.",
        )

    def test_process_text_command_uses_generated_dj_response_for_resolved_album(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "album",
                "artist": "Pearl Jam",
                "album": "Ten",
                "spotify_search_query": "Ten Pearl Jam",
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "resolved_media": {
                    "type": "album",
                    "album": "Ten",
                    "artist": "Pearl Jam",
                    "uri": "spotify:album:abc",
                }
            }

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent

        async def generated_dj_response(hass, *, media, fallback_text, conf, debug=None):
            self.assertEqual(media["type"], "album")
            self.assertEqual(media["album"], "Ten")
            self.assertEqual(media["artist"], "Pearl Jam")
            self.assertIn("Geef een leuk feitje", conf["dj_response_prompt"])
            self.assertEqual(fallback_text, "Daar is Ten van Pearl Jam.")
            if debug is not None:
                debug["fallback_used"] = False
            return (
                "Ten van Pearl Jam staat klaar. Wist je dat Pearl Jam begin "
                "jaren negentig uit Seattle doorbrak?"
            )

        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        original_dj_response = self.processor.generate_dj_response_with_assist
        self.processor.generate_dj_response_with_assist = generated_dj_response
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": (
                "Noem de artiest en het nummer.\n"
                "Geef een leuk feitje over de artiest.\n"
                "Klink warm en persoonlijk."
            ),
            "tts_language": "nl",
        }
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "speel het album ten van pearl jam",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play
            self.processor.generate_dj_response_with_assist = original_dj_response

        self.assertEqual(
            result["dj_text"],
            "Ten van Pearl Jam staat klaar. Wist je dat Pearl Jam begin "
            "jaren negentig uit Seattle doorbrak?",
        )
        self.assertIn("Ten van Pearl Jam", runtime.last_dj_text)

    def test_process_text_command_adds_current_track_to_artist_dj_response_media(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "artist",
                "artist": "Pearl Jam",
                "spotify_search_query": "Pearl Jam",
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "resolved_media": {
                    "type": "artist",
                    "artist": "Pearl Jam",
                    "artist_name": "Pearl Jam",
                    "track_name": "",
                    "title": "",
                    "uri": "spotify:artist:abc",
                },
                "device_response": {
                    "playback": {
                        "track_name": "Soldier of Love",
                        "title": "Soldier of Love",
                        "artist": "Pearl Jam",
                        "album_name": "Last Kiss",
                    }
                },
            }

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent

        async def generated_dj_response(hass, *, media, fallback_text, conf, debug=None):
            self.assertEqual(media["type"], "artist")
            self.assertEqual(media["artist"], "Pearl Jam")
            self.assertEqual(media["track_name"], "Soldier of Love")
            self.assertEqual(media["album_name"], "Last Kiss")
            self.assertIn("Noem de artiest en het nummer", conf["dj_response_prompt"])
            if debug is not None:
                debug["fallback_used"] = False
            return "Pearl Jam met Soldier of Love staat klaar."

        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        original_dj_response = self.processor.generate_dj_response_with_assist
        self.processor.generate_dj_response_with_assist = generated_dj_response
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": (
                "Noem de artiest en het nummer.\n"
                "Geef een leuk feitje over de artiest.\n"
                "Klink warm en persoonlijk."
            ),
            "tts_language": "nl",
        }
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "speel pearl jam",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play
            self.processor.generate_dj_response_with_assist = original_dj_response

        self.assertEqual(result["dj_text"], "Pearl Jam met Soldier of Love staat klaar.")

    def test_process_text_command_uses_plain_fallback_when_assist_generation_fails(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "search",
                "spotify_search_query": user_text,
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "resolved_media": {
                    "artist": "Example Artist",
                    "uri": "spotify:artist:abc",
                }
            }

        async def bad_dj_response(hass, *, media, fallback_text, conf, debug=None):
            if debug is not None:
                debug.update({"fallback_used": True, "block_reason": "test"})
            return fallback_text

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        original_dj_response = self.processor.generate_dj_response_with_assist
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        self.processor.generate_dj_response_with_assist = bad_dj_response
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": "gebruik twee zinnen en klink als een warme radio-DJ",
            "tts_language": "nl",
        }
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "start Example Artist",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play
            self.processor.generate_dj_response_with_assist = original_dj_response

        self.assertEqual(
            result["dj_text"],
            "Daar is Example Artist.",
        )
        self.assertNotIn("spotify:artist", result["dj_text"])

    def test_process_text_command_does_not_use_stale_device_playback_for_dj_response(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "search",
                "artist": "Nirvana",
                "spotify_search_query": "Nirvana",
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "played": True,
                "media_content_id": "Nirvana",
                "media_content_type": "artist",
                "resolved_media": None,
                "device_response": {
                    "playback": {
                        "type": "artist",
                        "artist": "Red Hot Chili Peppers",
                        "artist_name": "Red Hot Chili Peppers",
                    }
                },
            }

        async def generated_dj_response(hass, *, media, fallback_text, conf, debug=None):
            self.assertEqual(media["artist"], "Nirvana")
            self.assertNotIn("artist_name", media)
            self.assertNotIn("track_name", media)
            self.assertNotIn("title", media)
            self.assertNotIn("Red Hot Chili Peppers", fallback_text)
            if debug is not None:
                debug["fallback_used"] = False
            return f"Generated for {media['artist']}"

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        original_dj_response = self.processor.generate_dj_response_with_assist
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        self.processor.generate_dj_response_with_assist = generated_dj_response
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": "Noem de artiest.",
            "tts_language": "nl",
        }
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "speel Nirvana",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play
            self.processor.generate_dj_response_with_assist = original_dj_response

        self.assertEqual(result["dj_text"], "Generated for Nirvana")
        self.assertEqual(runtime.last_dj_text, "Generated for Nirvana")

    def test_process_text_command_keeps_intent_when_playback_fails(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "search",
                "spotify_search_query": user_text,
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            raise RuntimeError("Spotify failed")

        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        try:
            with self.assertRaisesRegex(RuntimeError, "Spotify failed"):
                asyncio.run(
                    self.processor.process_text_command(
                        object(),
                        runtime,
                        "ik wil pearl jam starten",
                        play=True,
                    )
                )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(runtime.last_text, "ik wil pearl jam starten")
        self.assertEqual(runtime.last_intent["type"], "search")
        self.assertEqual(
            runtime.last_intent["spotify_search_query"],
            "ik wil pearl jam starten",
        )


if __name__ == "__main__":
    unittest.main()
