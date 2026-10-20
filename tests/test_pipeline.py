from __future__ import annotations

import importlib
import asyncio
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


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
        self.assertNotIn("pipeline_id", calls[0])
        self.assertNotIn("agent_id", calls[0])

    def test_activity_json_speech_uses_the_selected_agent_and_preserves_semantic_playlist(self):
        calls = []
        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                self_outer.assertEqual(set(data), {'text','language','agent_id'})
                calls.append(data)
                return {'response': {'speech': {'plain': {'speech':
                    '{"intent":"play_music","type":"playlist","query":"cooking jazz","playlist":"cooking jazz"}'}}}}
        self_outer = self
        result = asyncio.run(self.pipeline._conversation_process(
            types.SimpleNamespace(services=Services()), 'Play something for cooking',
            {'pipeline_id':'chosen-pipeline','agent_id':'conversation.chosen','language':'en'}))
        self.assertEqual(calls[0]['agent_id'],'conversation.chosen')
        self.assertEqual(result['pipeline_id'],'chosen-pipeline')  # Internal trace only.
        intent = self.pipeline._intent_from_assist_response(result,'Play something for cooking')
        self.assertEqual((intent['type'],intent['spotify_search_query']),('playlist','cooking jazz'))
        # A literal named artist keeps the existing stale-target fence.
        named = self.pipeline._intent_from_assist_response(result,'Play The National')
        self.assertEqual((named['type'],named['artist']),('artist','The National'))

    def test_spoken_intent_json_is_bounded_closed_and_duplicate_safe(self):
        for speech in ('{"type":"playlist","type":"artist","query":"cooking"}',
            '{"type":"playlist","query":"cooking","command":"play"}',
            '{"type":"playlist","query":"https://private.invalid"}',
            '{"type":"playlist","query":true}', 'x'*4097,
            '{"type":[],"query":"cooking"}', '{"type":"playlist"}',
            '```json\n{"type":"playlist","query":"cooking"}\n```'):
            self.assertEqual(self.pipeline._speech_intent_data({'speech':{'plain':{'speech':speech}}}), {})

    def test_playback_frame_can_restore_only_unambiguous_core_kind_not_catalog_names(self):
        import time
        from custom_components.djconnect.playback_request import PlaybackRequestBrief, PlaybackAcceptance
        from custom_components.djconnect.narration_brief import candidate
        brief=PlaybackRequestBrief(PlaybackAcceptance('synthetic',time.monotonic()+30),
            'en','radio_dj','groove','seed',('{media_kind}','{title}','{status}'),
            'accepted request','accepted receipt',
            (('{media_kind}','playlist'),('{title}','Private actual title'),('{status}','Confirmed.')),
            selection_kind='playlist')
        frame='Your playlist is {title}. {status}'
        self.assertEqual(candidate(brief,frame),'Your {media_kind} is {title}. {status}')
        for wrong in ('Your album is {title}. {status}',
            'Your playlist is Private actual title. {status}',
            'Your playlist is {title}, the playlist. {status}'):
            self.assertIsNone(candidate(brief,wrong),wrong)

    def test_localized_playlist_kind_is_core_owned_but_catalog_and_ambiguity_are_not(self):
        import time
        from custom_components.djconnect.playback_request import PlaybackRequestBrief, PlaybackAcceptance
        from custom_components.djconnect.narration_brief import candidate
        brief=PlaybackRequestBrief(PlaybackAcceptance('synthetic',time.monotonic()+30),
            'es','radio_dj','groove','seed',('{media_kind}','{title}','{status}'),
            'accepted request','accepted receipt',
            (('{media_kind}','playlist'),('{title}','Private actual title'),('{status}','Confirmed.')),
            selection_kind='playlist')
        for noun in ('playlist', 'lista de reproducción'):
            self.assertEqual(candidate(brief,'Aquí tienes la '+noun+' {title}; disfrútala a tu ritmo. {status}'),
                'Aquí tienes la {media_kind} {title}; disfrútala a tu ritmo. {status}')
        for wrong in ('Aquí tienes la playlist y la lista de reproducción {title}. {status}',
                      'Aquí tienes el álbum {title}. {status}',
                      'Aquí tienes la lista de reproducción Private actual title. {status}'):
            self.assertIsNone(candidate(brief,wrong),wrong)
        self.assertNotIn('Private actual title',brief.prompt())
        from dataclasses import replace
        dutch=replace(brief,locale='nl')
        self.assertEqual(candidate(dutch,'Ik geef je de afspeellijst {title} mee. {status}'),
            'Ik geef je de {media_kind} {title} mee. {status}')
        self.assertIsNone(candidate(dutch,'De playlist en afspeellijst {title}. {status}'))
        self.assertIsNone(candidate(brief,'Ik geef je de afspeellijst {title} mee. {status}'))

    def test_longer_narration_deadline_is_only_for_an_already_accepted_playback_effect(self):
        import time
        from unittest.mock import patch
        from custom_components.djconnect.playback_request import PlaybackRequestBrief, PlaybackAcceptance
        from custom_components.djconnect.ask_dj.dialogue import current_turn
        brief=PlaybackRequestBrief(PlaybackAcceptance('synthetic',time.monotonic()+60),
            'en','radio_dj','groove','seed',('{media_kind}','{title}','{status}'),
            'accepted request','accepted receipt',
            (('{media_kind}','playlist'),('{title}','Actual title'),('{status}','Confirmed.')),
            selection_kind='playlist')
        async def scenario(effect,accepted):
            seconds=[]
            calls=[]
            original_timeout=asyncio.timeout
            def timeout(value):
                seconds.append(value)
                return original_timeout(value)
            async def model(*args,**kwargs):
                calls.append(True)
                text=('{"text":"{media_kind}: {title}. {status}"}' if len(calls)==1 else
                      '{"supported":true,"language_ok":true,"style_ok":true}')
                return {'response':{'speech':{'plain':{'speech':text}}}}
            turn=types.SimpleNamespace(effect_started=effect,accepted_playback_narration=accepted)
            token=current_turn.set(turn)
            try:
                with patch.object(asyncio,'timeout',timeout), patch.object(self.pipeline,'_assist_context',return_value={'agent_id':'fixture'}), patch.object(self.pipeline,'call_conversation_process_with_agent_retry',model):
                    answer=await self.pipeline.realize_session_narration(object(),narration=brief,
                        admission=lambda:None,fallback_text='Fallback',conf={})
                self.assertIn('Actual title',answer)
                self.assertEqual(len(calls),2)
                self.assertEqual(seconds,[20 if effect and accepted else 12])
            finally:
                current_turn.reset(token)
        for effect,accepted in ((True,True),(True,False),(False,True),(False,False)):
            asyncio.run(scenario(effect,accepted))

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
        # Explicitly exercise unavailable pipeline/default-agent fallback;
        # unrelated config-flow fixtures must not choose this test's pipeline.
        with patch.object(self.pipeline, '_get_default_assist_pipeline', return_value=None):
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
