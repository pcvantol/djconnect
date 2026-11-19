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
        cls.pipeline = importlib.import_module("custom_components.djconnect.pipeline")

    def test_run_text_command_updates_text_before_processing_result(self) -> None:
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

    def test_run_text_command_falls_back_to_local_spotify_search_when_assist_fails(self) -> None:
        async def assist(hass, user_text, conf):
            raise RuntimeError("HA Assist unavailable")

        seen_intents = []

        async def play(hass, runtime, intent, conf):
            seen_intents.append(intent)
            return {
                "resolved_media": {
                    "type": "artist",
                    "name": "Armin van Buuren",
                    "uri": "spotify:artist:0SfsnGyD8FpIN4U4WCkBZ5",
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
                    "Speel Armin",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(len(seen_intents), 1)
        self.assertEqual(seen_intents[0]["type"], "artist")
        self.assertEqual(seen_intents[0]["artist"], "Armin")
        self.assertEqual(seen_intents[0]["spotify_search_query"], "Armin")
        self.assertEqual(runtime.last_intent["spotify_search_query"], "Armin")
        self.assertEqual(result["playback"]["resolved_media"]["name"], "Armin van Buuren")

    def test_run_text_command_corrects_stt_before_intent_parsing(self) -> None:
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

    def test_run_text_command_preserves_accepted_resolved_track_reply(self) -> None:
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

        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": "Maak een energieke festival-DJ-aankondiging.",
            "tts_language": "nl",
        }

        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    types.SimpleNamespace(),
                    runtime,
                    "ik wil pearl jam starten",
                    play=True,
                    memory_payload={"mood": 70},
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(
            result["dj_text"],
            "Daar is Alive van Pearl Jam.",
        )
        self.assertEqual(result["text_source"], "fallback")
        self.assertFalse(result["is_generated_text"])

    def test_run_text_command_preserves_accepted_resolved_album_reply(self) -> None:
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


        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": (
                "Noem de artiest, het album en het nummer.\n"
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

        self.assertEqual(
            result["dj_text"],
            "Je luistert naar Pearl Jam met hun album Ten.",
        )
        self.assertIn("Pearl Jam met hun album Ten", runtime.last_dj_text)

    def test_album_playback_response_names_album_and_first_track(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "album",
                "artist": "Radiohead",
                "album": "OK Computer",
                "spotify_search_query": "OK Computer Radiohead",
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "played": True,
                "media_content_id": "OK Computer Radiohead",
                "media_content_type": "album",
                "resolved_media": {
                    "type": "album",
                    "album": "OK Computer",
                    "artist": "Radiohead",
                    "uri": "spotify:album:ok-computer",
                },
                "device_response": {
                    "playback": {
                        "track_name": "Airbag",
                        "title": "Airbag",
                        "artist": "Radiohead",
                        "album_name": "OK Computer",
                        "album_image_url": "https://img.example/ok-computer.jpg",
                    }
                },
            }


        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        runtime.config = {"tts_language": "nl"}
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "speel het album OK Computer van Radiohead",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(
            result["dj_text"],
            "Je luistert naar Radiohead met hun album OK Computer. Hier is het eerste nummer op het album, Airbag.",
        )

    def test_run_text_command_adds_current_track_to_artist_dj_response_media(self) -> None:
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


        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
        runtime = Runtime()
        runtime.config = {
            "dj_response_prompt": (
                "Noem de artiest, het album en het nummer.\n"
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

        self.assertEqual(result["dj_text"], "Daar is Pearl Jam, met Soldier of Love. Van Last Kiss.")

    def test_run_text_command_keeps_accepted_reply_without_a_second_generation(self) -> None:
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


        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
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

        self.assertEqual(
            result["dj_text"],
            "Daar is Example Artist.",
        )
        self.assertEqual(result["text_source"], "fallback")
        self.assertFalse(result["is_generated_text"])
        self.assertNotIn("spotify:artist", result["dj_text"])

    def test_run_text_command_does_not_use_stale_device_playback_for_dj_response(self) -> None:
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


        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
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

        self.assertEqual(result["dj_text"], "Daar is Nirvana.")
        self.assertEqual(runtime.last_dj_text, "Daar is Nirvana.")

    def test_clear_multi_word_artist_play_request_uses_local_intent_before_assist(self) -> None:
        async def assist(*args, **kwargs):
            raise AssertionError("clear artist playback request must not use stale Assist intent")

        seen_intents = []

        async def play(hass, runtime, intent, conf):
            seen_intents.append(intent)
            return {
                "played": True,
                "media_content_id": intent["spotify_search_query"],
                "media_content_type": "artist",
                "resolved_media": {
                    "type": "artist",
                    "artist": "DJ Paul Elstak",
                    "name": "DJ Paul Elstak",
                    "image_url": "https://img.example/dj-paul.jpg",
                },
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
                    "speel dj paul elstak",
                    play=True,
                )
            )
        finally:
            self.processor.process_text_with_assist = original_assist
            self.processor.play_from_intent = original_play

        self.assertEqual(seen_intents[0]["type"], "artist")
        self.assertEqual(seen_intents[0]["artist"], "dj paul elstak")
        self.assertEqual(seen_intents[0]["spotify_search_query"], "dj paul elstak")
        self.assertEqual(result["playback"]["resolved_media"]["artist"], "DJ Paul Elstak")

    def test_run_text_command_ignores_conflicting_resolved_media_for_dj_response(self) -> None:
        async def assist(hass, user_text, conf):
            return {
                "type": "artist",
                "artist": "Nirvana",
                "spotify_search_query": "Nirvana",
                "dj_announcement": "Daar gaan we.",
            }

        async def play(hass, runtime, intent, conf):
            return {
                "played": True,
                "media_content_id": "Nirvana",
                "media_content_type": "artist",
                "resolved_media": {
                    "type": "track",
                    "title": "Tangled Up - Lokee Remix",
                    "artist": "Caro Emerald",
                    "album": "The Shocking Miss Emerald (The Remixes)",
                },
            }


        original_assist = self.processor.process_text_with_assist
        original_play = self.processor.play_from_intent
        self.processor.process_text_with_assist = assist
        self.processor.play_from_intent = play
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

        self.assertEqual(result["dj_text"], "Daar is Nirvana.")


    def test_current_track_question_reads_status_without_playback_action(self) -> None:
        calls = []

        async def play(hass, runtime, intent, conf):
            raise AssertionError("current-track question must not start playback")

        async def status(hass, runtime, command, value=None, *, play=None):
            calls.append(command)
            return {
                "success": True,
                "playback": {
                    "has_playback": True,
                    "is_playing": True,
                    "track_name": "Black",
                    "artist": "Pearl Jam",
                    "album_name": "Ten",
                },
            }


        original_play = self.processor.play_from_intent
        original_status = self.processor.run_music_command
        self.processor.play_from_intent = play
        self.processor.run_music_command = status
        runtime = Runtime()
        runtime.config = {"tts_language": "nl"}
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "Welk nummer draait er nu?",
                    play=True,
                )
            )
        finally:
            self.processor.play_from_intent = original_play
            self.processor.run_music_command = original_status

        self.assertEqual(calls, ["status"])
        self.assertEqual(result["intent"]["type"], "current_track")
        self.assertEqual(result["playback"]["track_name"], "Black")
        self.assertEqual(result["dj_text"], "Nu draait Black van Pearl Jam. Van Ten.")
        self.assertEqual(runtime.last_playback["track_name"], "Black")

    def test_current_track_question_answers_when_nothing_is_playing(self) -> None:
        async def status(hass, runtime, command, value=None, *, play=None):
            return {
                "success": True,
                "playback": {
                    "has_playback": False,
                    "is_playing": False,
                },
            }


        original_status = self.processor.run_music_command
        self.processor.run_music_command = status
        runtime = Runtime()
        runtime.config = {"tts_language": "nl"}
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "Wat speelt er?",
                    play=True,
                )
            )
        finally:
            self.processor.run_music_command = original_status

        self.assertEqual(
            result["dj_text"],
            "Er draait nu geen nummer, voor zover ik kan zien.",
        )

    def test_current_track_question_answers_when_spotify_is_unavailable(self) -> None:
        async def status(hass, runtime, command, value=None, *, play=None):
            raise self.processor.SpotifyBackendError("Spotify OAuth is not configured")


        original_status = self.processor.run_music_command
        self.processor.run_music_command = status
        runtime = Runtime()
        runtime.config = {"tts_language": "nl"}
        try:
            result = asyncio.run(
                self.processor.process_text_command(
                    object(),
                    runtime,
                    "Welk nummer speelt er nu?",
                    play=True,
                )
            )
        finally:
            self.processor.run_music_command = original_status

        self.assertEqual(
            result["dj_text"],
            "Ik kan nu niet zien welk nummer er draait.",
        )
        self.assertFalse(result["playback"]["backend_available"])

    def test_playback_control_requests_call_backend_without_music_search(self) -> None:
        cases = [
            ("Stop muziek", "pause", "Ik zet de muziek op pauze."),
            ("Start muziek", "play", "Ik start de muziek weer."),
            ("Volgende nummer", "next", "Ik ga naar het volgende nummer."),
            ("Vorig nummer", "previous", "Ik ga terug naar het vorige nummer."),
        ]
        for text, expected_command, expected_fallback in cases:
            with self.subTest(text=text):
                calls = []

                async def assist(hass, user_text, conf):
                    raise AssertionError("playback control must not run Assist parsing")

                async def play(hass, runtime, intent, conf):
                    raise AssertionError("playback control must not run music search")

                async def command(hass, runtime, command, value=None, *, play=None):
                    calls.append((command, value))
                    return {
                        "success": True,
                        "playback": {
                            "has_playback": True,
                            "is_playing": command != "pause",
                            "track_name": "Black",
                            "artist": "Pearl Jam",
                        },
                    }


                original_assist = self.processor.process_text_with_assist
                original_play = self.processor.play_from_intent
                original_command = self.processor.run_music_command
                self.processor.process_text_with_assist = assist
                self.processor.play_from_intent = play
                self.processor.run_music_command = command
                runtime = Runtime()
                runtime.config = {"tts_language": "nl"}
                try:
                    result = asyncio.run(
                        self.processor.process_text_command(
                            object(),
                            runtime,
                            text,
                            play=True,
                        )
                    )
                finally:
                    self.processor.process_text_with_assist = original_assist
                    self.processor.play_from_intent = original_play
                    self.processor.run_music_command = original_command

                expected_calls = [(expected_command, None)]
                if expected_command in {"next", "previous"}:
                    expected_calls.append(("status", None))
                self.assertEqual(calls, expected_calls)
                self.assertEqual(result["intent"]["action"], expected_command)
                self.assertEqual(result["dj_text"], expected_fallback)

    def test_volume_control_requests_adjust_current_spotify_volume_by_ten(self) -> None:
        cases = [
            ("Zet harder", 30, 40),
            ("Zet zachter", 30, 20),
            ("Zet zachter", 5, 0),
            ("Zet harder", 58, 60),
        ]
        for text, current, expected in cases:
            with self.subTest(text=text, current=current):
                calls = []

                async def command(hass, runtime, command, value=None, *, play=None):
                    calls.append((command, value))
                    if command == "status":
                        return {
                            "success": True,
                            "playback": {
                                "has_playback": True,
                                "is_playing": True,
                                "volume_percent": current,
                            },
                        }
                    return {
                        "success": True,
                        "playback": {
                            "has_playback": True,
                            "is_playing": True,
                            "volume_percent": value,
                        },
                    }


                original_command = self.processor.run_music_command
                self.processor.run_music_command = command
                runtime = Runtime()
                runtime.config = {"tts_language": "nl"}
                try:
                    result = asyncio.run(
                        self.processor.process_text_command(
                            object(),
                            runtime,
                            text,
                            play=True,
                        )
                    )
                finally:
                    self.processor.run_music_command = original_command

                self.assertEqual(calls, [("status", None), ("set_volume", expected)])
                self.assertEqual(result["playback"]["requested_volume_percent"], expected)
                self.assertEqual(result["dj_text"], f"Ik zet het volume op {expected}.")

    def test_command_paths_cannot_start_session_narration_or_unrequested_speech(self):
        from unittest.mock import AsyncMock, patch
        async def play(hass, runtime, intent, conf):
            return {"resolved_media": {"title": "Black", "artist": "Pearl Jam"}}
        async def command(hass, runtime, command, value=None, **kwargs):
            return {"success": True, "playback": {"has_playback": True,
                "is_playing": True, "track_name": "Black", "artist": "Pearl Jam"}}
        class Services:
            async def async_call(self, *args, **kwargs):
                raise AssertionError("No second model/TTS/HA service call for an accepted command")
        narrator = AsyncMock(side_effect=AssertionError("Only Session publication owns narration"))
        with patch.object(self.pipeline, "realize_session_narration", narrator), \
             patch.object(self.processor, "play_from_intent", play), \
             patch.object(self.processor, "run_music_command", command):
            for text in ("Speel Pearl Jam", "Welk nummer draait er nu?", "Stop muziek"):
                with self.subTest(text=text):
                    result = asyncio.run(self.processor.process_text_command(
                        types.SimpleNamespace(services=Services()), Runtime(), text))
                    self.assertTrue(result["dj_text"])
                    self.assertFalse(result["is_generated_text"])
                    self.assertEqual(result["text_source"], "fallback")
        narrator.assert_not_awaited()

    def test_free_model_announcement_never_becomes_an_accepted_command_reply(self):
        from unittest.mock import patch
        async def intent(*args, **kwargs):
            return {"type": "search", "query": "", "spotify_search_query": "",
                    "dj_announcement": "I invented a personal story about your private listening."}
        async def play(*args, **kwargs):
            return {"resolved_media": {}}
        with patch.object(self.processor, "process_text_with_assist", intent), \
             patch.object(self.processor, "play_from_intent", play):
            for execute in (False, True):
                with self.subTest(execute=execute):
                    result = asyncio.run(self.processor.process_text_command(
                        object(), Runtime(), "an unresolved request", play=execute))
                    self.assertEqual(result["dj_text"], "Daar gaan we. Ik zet hem voor je klaar.")
                    self.assertFalse(result["is_generated_text"])
                    self.assertNotIn("private listening", result["dj_text"])

    def test_run_text_command_keeps_intent_when_playback_fails(self) -> None:
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
