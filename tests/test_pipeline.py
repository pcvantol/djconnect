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
        self.assertEqual(intent["dj_announcement"], "Pearl Jam staat klaar.")

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
        self.assertIn("agent_id", calls[0])

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

    def test_generate_dj_response_with_assist_ignores_legacy_custom_response_prompt(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append((domain, service, data, kwargs))
                return {
                    "response": {
                        "speech": {"plain": {"speech": "Arrr, Pearl Jam op de draaitafel!"}}
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={"artist": "Pearl Jam", "uri": "spotify:artist:pearl-jam"},
                fallback_text="Daar is Pearl Jam.",
                conf={
                    "dj_response_prompt": "Sound like a pirate DJ.",
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
            )
        )

        self.assertEqual(text, "Arrr, Pearl Jam op de draaitafel!")
        self.assertIn(
            "Negeer alle eventueel hierboven ingestelde instructies",
            calls[0][2]["text"],
        )
        self.assertIn("Je bent een radio-DJ", calls[0][2]["text"])
        self.assertIn("Klink warm en persoonlijk.", calls[0][2]["text"])
        self.assertNotIn("Sound like a pirate DJ.", calls[0][2]["text"])
        self.assertIn("artiest: Pearl Jam", calls[0][2]["text"])
        self.assertNotIn("spotify:artist", calls[0][2]["text"])
        self.assertNotIn("{'artist'", calls[0][2]["text"])
        self.assertNotIn("'uri'", calls[0][2]["text"])

    def test_generate_dj_response_uses_configured_conversation_agent(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {
                    "response": {
                        "speech": {"plain": {"speech": "Metallica staat klaar."}}
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={"type": "artist", "artist": "Metallica", "artist_name": "Metallica"},
                fallback_text="Daar is Metallica.",
                conf={
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
            )
        )

        self.assertEqual(text, "Metallica staat klaar.")
        self.assertEqual(calls[0]["agent_id"], "conversation.openai")
        self.assertEqual(calls[0]["text"].count("artiest: Metallica"), 1)

    def test_generate_dj_response_rejects_wrong_resolved_artist(self) -> None:
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "En we zijn terug met AC/DC van Back in Black, "
                                    "You Shook Me All Night Long."
                                )
                            }
                        }
                    }
                }

        debug = {}
        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={
                    "type": "artist",
                    "artist": "Metallica",
                    "artist_name": "Metallica",
                },
                fallback_text="Daar is Metallica.",
                conf={"tts_language": "nl-NL"},
                debug=debug,
            )
        )

        self.assertEqual(text, "Daar is Metallica.")
        self.assertTrue(debug["fallback_used"])
        self.assertEqual(debug["block_reason"], "generated response missing resolved artist")

    def test_dj_response_assist_prompt_is_debug_logged(self) -> None:
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {"plain": {"speech": "Pearl Jam komt eraan."}}
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        with self.assertLogs("custom_components.djconnect", level="DEBUG") as logs:
            text = asyncio.run(
                self.pipeline.generate_dj_response_with_assist(
                    hass,
                    media={"artist": "Pearl Jam"},
                    fallback_text="Daar is Pearl Jam.",
                conf={
                    "dj_response_prompt": "Klink warm.",
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
            )
            )

        self.assertEqual(text, "Pearl Jam komt eraan.")
        self.assertTrue(
            any("DJConnect Assist DJ response prompt" in line for line in logs.output)
        )
        self.assertFalse(any("Klink warm." in line for line in logs.output))
        self.assertFalse(any("artiest: Pearl Jam" in line for line in logs.output))
        self.assertFalse(any("Negeer alle eventueel hierboven" in line for line in logs.output))

    def test_generate_dj_response_prompt_uses_safe_media_lines(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Nirvana gaat erin, rauw en recht uit de speakers."
                                )
                            }
                        }
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={
                    "type": "artist",
                    "artist": "Nirvana",
                    "uri": "spotify:artist:abc",
                },
                fallback_text="Daar is Nirvana.",
                conf={
                    "dj_response_prompt": "Noem de artiest en klink warm.",
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
            )
        )

        self.assertEqual(text, "Nirvana gaat erin, rauw en recht uit de speakers.")
        prompt = calls[0]["text"]
        self.assertIn("Negeer alle eventueel hierboven ingestelde instructies", prompt)
        self.assertIn("type: artist", prompt)
        self.assertIn("artiest: Nirvana", prompt)
        self.assertIn("MusicBrainz", prompt)
        self.assertIn("Wikidata", prompt)
        self.assertIn("Wikipedia", prompt)
        self.assertIn("Last.fm", prompt)
        self.assertIn("Discogs", prompt)
        self.assertIn("TheAudioDB", prompt)
        self.assertIn("Music DNA", prompt)
        self.assertIn("Gebruik deze bronnen niet live als ze niet beschikbaar zijn", prompt)
        self.assertNotIn("spotify:artist", prompt)
        self.assertNotIn("{", prompt)
        self.assertNotIn("}", prompt)

    def test_generate_dj_response_orders_answer_before_fact(self) -> None:
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Wist je dat Michael Jackson bekend staat als de King of Pop en Bad uit 1987 komt? "
                                    "Geniet van de muziek!"
                                )
                            }
                        }
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        fallback = "Je luistert naar Michael Jackson met hun album Bad. Hier is het eerste nummer op het album, Bad."

        result = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={
                    "type": "album",
                    "artist": "Michael Jackson",
                    "album_name": "Bad",
                    "track_name": "Bad",
                },
                fallback_text=fallback,
                conf={"tts_language": "nl"},
            )
        )

        self.assertTrue(result.startswith(fallback))
        self.assertIn("Wist je dat Michael Jackson", result)
        self.assertLess(result.index("Je luistert naar"), result.index("Wist je dat"))

    def test_generate_dj_response_prompt_allows_personal_intro_from_memory_and_weather(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Fijn dat je er weer bent. Nirvana slingert de dag aan."
                                )
                            }
                        }
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={"type": "artist", "artist": "Nirvana"},
                fallback_text="Daar is Nirvana.",
                conf={
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
                memory_context=(
                    "Luistertijdcontext: zaterdag, ochtend, weekend, 10:00\n"
                    "Expliciet gedeelde smart-home context voor persoonlijke intro's: "
                    "Buitentemperatuur (sensor.outdoor_temperature): 27 °C"
                ),
            )
        )

        self.assertEqual(text, "Fijn dat je er weer bent. Nirvana slingert de dag aan.")
        prompt = calls[0]["text"]
        self.assertIn("persoonlijke openingszin", prompt)
        self.assertIn("Het is een warme dag, we gaan lekker swingen", prompt)
        self.assertIn("Buitentemperatuur", prompt)
        self.assertIn("27 °C", prompt)
        self.assertIn("zeg niet dat er memory of Home Assistant context bestaat", prompt)

    def test_generate_dj_response_ignores_assist_device_lookup_error(self) -> None:
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "response_type": "error",
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Sorry, ik kan geen apparaat vinden met de naam "
                                    "twee zinnen klink als warme radio-DJ Example Artist "
                                    "{'type': 'artist', 'uri': 'spotify:artist:abc'}"
                                )
                            }
                        },
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        debug = {}
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={"artist": "Example Artist", "uri": "spotify:artist:abc"},
                fallback_text="Daar is Example Artist. Blijf erbij.",
                conf={
                    "dj_response_prompt": "twee zinnen klink als radio DJ",
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
                debug=debug,
            )
        )

        self.assertEqual(text, "Daar is Example Artist. Blijf erbij.")
        self.assertNotIn("geen apparaat", text)
        self.assertNotIn("spotify:artist", text)
        self.assertTrue(debug["fallback_used"])
        self.assertIn("spotify:artist", debug["generated_text"])
        self.assertIsNotNone(debug["block_reason"])

    def test_generate_dj_response_blocks_prompt_leak_device_lookup_error(self) -> None:
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Sorry, ik kan Noem de artiest en het nummer "
                                    "Geef een leuk feitje over de artiest Klink warm "
                                    "en persoonlijk Media type artist artiest Red Hot "
                                    "Chili Peppers niet vinden"
                                )
                            }
                        }
                    }
                }

        hass = types.SimpleNamespace(services=Services())
        debug = {}
        text = asyncio.run(
            self.pipeline.generate_dj_response_with_assist(
                hass,
                media={"type": "artist", "artist": "Red Hot Chili Peppers"},
                fallback_text="Daar is Red Hot Chili Peppers.",
                conf={
                    "assist_pipeline_id": "conversation.openai",
                    "tts_language": "nl-NL",
                },
                debug=debug,
            )
        )

        self.assertEqual(text, "Daar is Red Hot Chili Peppers.")
        self.assertNotIn("Noem de artiest", text)
        self.assertNotIn("niet vinden", text)
        self.assertTrue(debug["fallback_used"])
        self.assertEqual(debug["block_reason"], "device lookup error")
        self.assertIn("Noem de artiest", debug["prompt"])
        self.assertIn("Red Hot Chili Peppers", debug["generated_text"])

    def test_generate_dj_response_uses_default_conversation_agent(self) -> None:
        calls = []

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                calls.append(data)
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": "Nirvana, rauw en recht uit Seattle, komt eraan."
                            }
                        }
                    }
                }

        preferred = types.SimpleNamespace(
            id="preferred-pipeline",
            conversation_engine="conversation.openai",
            conversation_language="nl-NL",
        )

        class Pipelines:
            def async_get_preferred_pipeline(self):
                return preferred

            def __iter__(self):
                return iter([preferred])

        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        pipeline_module.async_get_pipelines = lambda hass: Pipelines()
        original_pipeline_module = sys.modules.get(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        sys.modules["homeassistant.components.assist_pipeline.pipeline"] = pipeline_module

        hass = types.SimpleNamespace(services=Services())
        debug = {}
        try:
            with self.assertLogs("custom_components.djconnect", level="DEBUG") as logs:
                text = asyncio.run(
                    self.pipeline.generate_dj_response_with_assist(
                        hass,
                        media={"type": "artist", "artist": "Nirvana"},
                        fallback_text="Daar is Nirvana.",
                        conf={
                            "dj_response_prompt": "Noem de artiest en het nummer.",
                            "tts_language": "nl-NL",
                        },
                        debug=debug,
                    )
                )
        finally:
            if original_pipeline_module is None:
                sys.modules.pop("homeassistant.components.assist_pipeline.pipeline", None)
            else:
                sys.modules[
                    "homeassistant.components.assist_pipeline.pipeline"
                ] = original_pipeline_module

        self.assertEqual(text, "Nirvana, rauw en recht uit Seattle, komt eraan.")
        self.assertEqual(calls[0]["language"], "nl-NL")
        self.assertEqual(calls[0]["agent_id"], "conversation.openai")
        self.assertFalse(debug["fallback_used"])
        self.assertIsNone(debug["block_reason"])
        self.assertTrue(any("DJ response prompt" in line for line in logs.output))
        self.assertTrue(
            any("agent_id=conversation.openai" in line for line in logs.output)
        )

    def test_ordinary_artist_dj_response_is_usable(self) -> None:
        self.assertTrue(
            self.pipeline._is_usable_dj_response(
                "Nirvana gaat erin, rauw en recht uit de speakers."
            )
        )

    def test_intent_from_djconnect_data_uses_speech_as_dj_response(self) -> None:
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
        self.assertEqual(intent["dj_announcement"], "Ik zet Pearl Jam voor je klaar.")

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
        self.assertEqual(intent["dj_announcement"], "Daar gaan we. Ik zet hem voor je klaar.")
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
        self.assertEqual(intent["dj_announcement"], "Daar gaan we. Ik zet hem voor je klaar.")

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
        self.assertEqual(intent["dj_announcement"], "Daar gaan we. Ik zet hem voor je klaar.")

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
