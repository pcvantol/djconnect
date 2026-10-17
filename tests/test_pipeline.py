from __future__ import annotations

import importlib
import asyncio
from pathlib import Path
import sys
import types
import unittest


def install_pipeline_stubs() -> None:
    if "homeassistant.core" in sys.modules:
        return
    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = core
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [
        str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")
    ]
    sys.modules["custom_components.djconnect"] = package


class AssistPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_pipeline_stubs()
        cls.pipeline = importlib.import_module("custom_components.djconnect.pipeline")

    def test_unqualified_media_or_memory_cannot_start_an_independent_announcer(self):
        class Services:
            async def async_call(self,*args,**kwargs):
                raise AssertionError('Unqualified command response must not call a model')
        debug = {}
        text = asyncio.run(self.pipeline.realize_session_narration(
            types.SimpleNamespace(services=Services()), narration={'artist':'Private catalog artist'}, admission=lambda:None,
            fallback_text='Accepted command answer.', conf={}, debug=debug))
        self.assertEqual(text,'Accepted command answer.')
        self.assertEqual(debug['block_reason'],'narration_unavailable')
        self.assertNotIn('prompt',debug)
        self.assertNotIn('Private',str(debug))

    def test_intent_from_assist_response_uses_djconnect_data(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "action_done",
                    "data": {
                        "djconnect": {
                            "type": "track",
                            "title": "Black",
                            "artist": "Pearl Jam",
                            "spotify_search_query": "Pearl Jam Black",
                            "dj_announcement": "Pearl Jam staat klaar.",
                        }
                    },
                }
            },
            "Speel Black van Pearl Jam",
        )

        self.assertEqual(intent["type"], "track")
        self.assertEqual(intent["artist"], "Pearl Jam")
        self.assertEqual(intent["spotify_search_query"], "Pearl Jam Black")
        self.assertNotIn("dj_announcement", intent)

    def test_djconnect_assist_prompt_focuses_on_command_parsing(self) -> None:
        prompt = self.pipeline._djconnect_assist_prompt(
            "Speel Black van Pearl Jam",
            "nl-NL",
        )

        self.assertIn("Bepaal de artiest", prompt)
        self.assertIn("track, album of playlist", prompt)
        self.assertIn("ik wil Zombie horen", prompt)
        self.assertIn("wat heb je nog meer van Scala", prompt)
        self.assertIn("artiest", prompt)
        self.assertIn("Speel Black van Pearl Jam", prompt)
        self.assertNotIn("Noem waar mogelijk", prompt)
        self.assertNotIn("leuk feitje", prompt)

    def test_djconnect_assist_prompt_does_not_include_custom_response_prompt(self) -> None:
        prompt = self.pipeline._djconnect_assist_prompt(
            "Play Pearl Jam",
            "en",
        )

        self.assertNotIn("DJ response prompt", prompt)
        self.assertIn("Play Pearl Jam", prompt)

    def test_command_assist_prompt_is_debug_logged(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {"response": {"response_type": "action_done", "data": {}}}

        hass = types.SimpleNamespace(services=Services())
        with self.assertLogs("custom_components.djconnect", level="DEBUG") as logs:
            asyncio.run(
                self.pipeline._conversation_process(
                    hass,
                    "Speel Pearl Jam",
                    {
                        "language": "nl-NL",
                        "agent_id": "conversation.openai",
                        "pipeline_id": "preferred",
                    },
                )
            )

        self.assertIn("Speel Pearl Jam", calls[0]["text"])
        self.assertTrue(
            any("DJConnect Assist command prompt" in line for line in logs.output)
        )
        self.assertFalse(any("Speel Pearl Jam" in line for line in logs.output))

    def test_correct_stt_text_with_assist_returns_corrected_text(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {
                    "response": {
                        "speech": {
                            "plain": {"speech": "speel nummer Lithium van Nirvana"}
                        }
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.correct_stt_text_with_assist(
                hass,
                "speel nummer litiem van nervana",
                {
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
            )
        )

        self.assertEqual(text, "speel nummer Lithium van Nirvana")
        self.assertIn("Transcript: speel nummer litiem van nervana", calls[0]["text"])
        self.assertEqual(calls[0]["pipeline_id"], "conversation.openai")
        self.assertNotIn("agent_id", calls[0])

    def test_correct_stt_text_with_assist_ignores_prompt_leak(self) -> None:
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Sorry, ik kan Corrigeer alleen spraak-naar-tekst "
                                    "Transcript Nirvana niet vinden"
                                )
                            }
                        }
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.correct_stt_text_with_assist(
                hass,
                "speel nervana",
                {
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
            )
        )

        self.assertEqual(text, "speel nervana")

    def test_correct_stt_text_with_assist_uses_default_conversation_agent(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {
                    "response": {
                        "speech": {"plain": {"speech": "speel Nirvana"}}
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.correct_stt_text_with_assist(
                hass,
                "speel nervana",
                {"tts_language": "nl-NL"},
            )
        )

        self.assertEqual(text, "speel Nirvana")
        self.assertEqual(calls[0]["language"], "nl-NL")
        self.assertNotIn("agent_id", calls[0])


    def test_voice_profile_mapping_follows_all_mood_zones(self) -> None:
        voice_profiles = importlib.import_module("custom_components.djconnect.voice_profiles")

        cases = {
            0: "late_night",
            25: "classic_radio",
            60: "energy",
            85: "clean_host",
        }
        for mood, expected in cases.items():
            with self.subTest(mood=mood):
                self.assertEqual(
                    voice_profiles.voice_profile_for_mood_or_config(
                        {"voice_profile": "late_night"},
                        {"mood": mood},
                    ),
                    expected,
                )

        self.assertEqual(
            voice_profiles.voice_profile_for_mood_or_config(
                {"voice_profile": "clean_host"},
                {},
            ),
            "clean_host",
        )



    def test_intent_parser_does_not_promote_agent_speech_to_dj_response(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "query_answer",
                    "speech": {"plain": {"speech": "Ik zet Pearl Jam voor je klaar."}},
                    "data": {"djconnect": {"type": "search"}},
                }
            },
            "Speel Pearl Jam",
        )

        self.assertEqual(intent["type"], "artist")
        self.assertEqual(intent["artist"], "Pearl Jam")
        self.assertEqual(intent["spotify_search_query"], "Pearl Jam")
        self.assertNotIn("dj_announcement", intent)

    def test_local_artist_request_overrides_stale_assist_artist(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "query_answer",
                    "speech": {
                        "plain": {
                            "speech": "Ik zet Red Hot Chili Peppers voor je klaar."
                        }
                    },
                    "data": {
                        "djconnect": {
                            "type": "artist",
                            "artist": "Red Hot Chili Peppers",
                            "spotify_search_query": "Red Hot Chili Peppers",
                        }
                    },
                }
            },
            "speel Nirvana",
        )

        self.assertEqual(intent["type"], "artist")
        self.assertEqual(intent["artist"], "Nirvana")
        self.assertEqual(intent["spotify_search_query"], "Nirvana")
        self.assertNotIn("dj_announcement", intent)
        self.assertEqual(intent["assist_intent"]["artist"], "Red Hot Chili Peppers")

    def test_local_artist_request_overrides_stale_assist_track(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "query_answer",
                    "data": {
                        "djconnect": {
                            "type": "track",
                            "title": "Californication",
                            "artist": "Red Hot Chili Peppers",
                            "spotify_search_query": "Californication Red Hot Chili Peppers",
                        }
                    },
                }
            },
            "speel Nirvana",
        )

        self.assertEqual(intent["type"], "artist")
        self.assertEqual(intent["artist"], "Nirvana")
        self.assertEqual(intent["spotify_search_query"], "Nirvana")
        self.assertEqual(intent["assist_intent"]["title"], "Californication")

    def test_generic_assist_music_refusal_is_not_used_as_dj_response(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "query_answer",
                    "speech": {
                        "plain": {
                            "speech": (
                                "Ik kan geen muziek afspelen. Ik kan alleen apparaten "
                                "in je huis bedienen, zoals lampen, gordijnen en sensoren."
                            )
                        }
                    },
                    "data": {},
                }
            },
            "Speel Pearl Jam",
        )

        self.assertEqual(intent["type"], "artist")
        self.assertEqual(intent["artist"], "Pearl Jam")
        self.assertEqual(intent["spotify_search_query"], "Pearl Jam")
        self.assertNotIn("dj_announcement", intent)

    def test_intent_from_assist_response_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Niet begrepen"):
            self.pipeline._intent_from_assist_response(
                {
                    "response": {
                        "response_type": "error",
                        "speech": {"plain": {"speech": "Niet begrepen"}},
                    }
                },
                "Speel iets",
            )

    def test_assist_prompt_device_lookup_error_falls_back_to_search_intent(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "error",
                    "speech": {
                        "plain": {
                            "speech": (
                                "Sorry, ik kan geen apparaat vinden met de naam "
                                "Verwerk deze DJConnect muziekopdracht en maak waar mogelijk "
                                "djconnect intentdata"
                            )
                        }
                    },
                }
            },
            "Speel Black van Pearl Jam",
        )

        self.assertEqual(intent["intent"], "play_music")
        self.assertEqual(intent["type"], "track")
        self.assertEqual(intent["title"], "Black")
        self.assertEqual(intent["artist"], "Pearl Jam")
        self.assertEqual(intent["spotify_search_query"], "Black Pearl Jam")
        self.assertNotIn("dj_announcement", intent)

    def test_assist_prompt_area_lookup_error_falls_back_to_search_intent(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "error",
                    "speech": {
                        "plain": {
                            "speech": (
                                "Sorry, I am not aware of any area called Analyze only "
                                "this DJConnect music request Determine"
                            )
                        }
                    },
                }
            },
            "Speel Black van Pearl Jam",
        )

        self.assertEqual(intent["intent"], "play_music")
        self.assertEqual(intent["type"], "track")
        self.assertEqual(intent["title"], "Black")
        self.assertEqual(intent["artist"], "Pearl Jam")
        self.assertEqual(intent["spotify_search_query"], "Black Pearl Jam")

    def test_prompt_leak_device_lookup_error_falls_back_to_original_command(self) -> None:
        intent = self.pipeline._intent_from_assist_response(
            {
                "response": {
                    "response_type": "error",
                    "speech": {
                        "plain": {
                            "speech": (
                                "Sorry, ik kan Nederlands Noem waar mogelijk de artiest "
                                "en/of het nummer Opdracht Metallica niet vinden"
                            )
                        }
                    },
                }
            },
            "Metallica",
        )

        self.assertEqual(intent["type"], "artist")
        self.assertEqual(intent["artist"], "Metallica")
        self.assertEqual(intent["spotify_search_query"], "Metallica")


if __name__ == "__main__":
    unittest.main()
