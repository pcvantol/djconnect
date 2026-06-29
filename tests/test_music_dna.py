from __future__ import annotations

import asyncio
import importlib
import logging
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType("custom_components.djconnect")
package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
sys.modules.setdefault("custom_components.djconnect", package)

memory_module = importlib.import_module("custom_components.djconnect.music_dna")
MusicDNAManager = memory_module.MusicDNAManager
enrich_user_text_with_memory = memory_module.enrich_user_text_with_memory
prompt_context_text = memory_module.prompt_context_text
resolve_music_dna_key = memory_module.resolve_music_dna_key


class FakeStore:
    def __init__(self, initial=None):
        self.data = initial
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data
        self.data = data


def runtime_for(
    *,
    device_id="djconnect-watchos-8F3A2C91B45D",
    client_type="watchos",
    device_name="Apple Watch van Peter",
):
    return types.SimpleNamespace(
        entry=types.SimpleNamespace(entry_id="entry-1"),
        config={},
        pairing_device_id=device_id,
        device_status={
            "device_id": device_id,
            "client_type": client_type,
            "device_name": device_name,
        },
        client_type=lambda: client_type,
    )


class MusicDNAManagerTest(unittest.TestCase):
    def test_watchos_music_dna_key_falls_back_to_device_id(self) -> None:
        runtime = runtime_for()

        key = resolve_music_dna_key(runtime, {"client_type": "watchos"})

        self.assertEqual(key, "djconnect-watchos-8F3A2C91B45D")

    def test_runtime_follow_up_context_is_shared_by_user_id(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        watch = runtime_for()
        mac = runtime_for(
            device_id="djconnect-macos-68B74487726D",
            client_type="macos",
            device_name="Peter Mac",
        )
        asyncio.run(manager.async_set_enabled(watch, True, {"client_type": "watchos"}, user_id="ha-user-1"))

        asyncio.run(
            manager.async_update_last_ask_dj(
                watch,
                input_text="Draai iets rustigers",
                result={
                    "intent": {"intent": "play_similar", "action": "start_track"},
                    "dj_text": "Ik heb iets rustigers gekozen met dezelfde sfeer.",
                    "playback": {
                        "track": {
                            "title": "Nights",
                            "artist": "Frank Ocean",
                            "uri": "spotify:track:123",
                        }
                    },
                },
                payload={"client_type": "watchos"},
                user_id="ha-user-1",
            )
        )

        context = asyncio.run(
            manager.async_context_for_runtime(
                mac,
                {"client_type": "macos"},
                user_id="ha-user-1",
            )
        )

        self.assertEqual(context["music_dna_key"], "user:ha-user-1")
        self.assertIn("Draai iets rustigers", prompt_context_text(context))
        self.assertIn("Frank Ocean", prompt_context_text(context))
        self.assertIn("Ik heb iets rustigers gekozen", prompt_context_text(context))

    def test_store_persistence_loads_and_saves_compact_memory(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        asyncio.run(
            manager.async_update_last_ask_dj(
                runtime,
                input_text="Waarom koos je dit?",
                result={
                    "intent": {"intent": "explain_choice"},
                    "dj_text": "Omdat dit goed aansluit op de vorige track.",
                    "playback": {"track": {"title": "Intro", "artist": "The xx"}},
                },
                payload={
                    "mood": 65,
                    "dj_style": "warm_radio_dj",
                    "device_token": "must-not-persist",
                },
            )
        )

        saved = store.saved
        self.assertEqual(saved["version"], 1)
        memory = saved["memories"]["djconnect-watchos-8F3A2C91B45D"]
        self.assertEqual(memory["mood"], 65)
        self.assertEqual(memory["dj_style"], "warm_radio_dj")
        self.assertIn("listening_time_context", memory)
        self.assertIn("hour", memory["listening_time_context"])
        self.assertIn("weekday", memory["listening_time_context"])
        self.assertIn("is_weekend", memory["listening_time_context"])
        self.assertIn("daypart", memory["listening_time_context"])
        self.assertEqual(memory["listening_time_patterns"][0]["daypart"], memory["listening_time_context"]["daypart"])
        self.assertNotIn("device_token", str(saved))

        reloaded = MusicDNAManager(store=FakeStore(saved))
        context = asyncio.run(reloaded.async_context_for_runtime(runtime))

        self.assertEqual(context["memory"]["mood"], 65)
        self.assertEqual(context["memory"]["last_ask_dj"]["intent"], "explain_choice")
        self.assertIn("listening_time_context", context["memory"])

    def test_blocked_music_preference_is_persisted_and_prompt_safe(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()
        asyncio.run(
            manager.async_set_enabled(
                runtime,
                True,
                {"client_type": "watchos"},
                user_id="ha-user-1",
            )
        )

        asyncio.run(
            manager.async_record_blocked_music_preference(
                runtime,
                {"kind": "artist", "name": "BLØF", "reason": "user_never_wants_to_hear"},
                {"client_type": "watchos"},
                user_id="ha-user-1",
            )
        )

        memory = store.saved["memories"]["user:ha-user-1"]
        self.assertEqual(memory["blocked_artists"][0]["name"], "BLØF")
        self.assertNotIn("spotify:", str(memory))
        context = asyncio.run(
            manager.async_context_for_runtime(
                runtime,
                {"client_type": "watchos"},
                user_id="ha-user-1",
            )
        )
        self.assertIn("Niet meer draaien volgens gebruiker: BLØF", prompt_context_text(context))

    def test_clear_memory_helper_removes_persistent_and_runtime_context(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        asyncio.run(
            manager.async_append_runtime_message(
                runtime,
                "user",
                "Doe nog zoiets",
            )
        )
        asyncio.run(manager.async_clear("djconnect-watchos-8F3A2C91B45D"))

        context = asyncio.run(manager.async_context_for_runtime(runtime))

        self.assertEqual(context["music_dna_key"], "djconnect-watchos-8F3A2C91B45D")
        self.assertEqual(context["session"], [])
        self.assertNotIn("last_ask_dj", context["memory"])

    def test_music_dna_prompt_enrichment_uses_compact_context(self) -> None:
        context = {
            "music_dna_key": "user:1",
            "memory": {
                "mood": 42,
                "listening_time_context": {
                    "hour": 20,
                    "weekday": 4,
                    "weekday_name": "vrijdag",
                    "is_weekend": False,
                    "daypart": "avond",
                },
                "last_ask_dj": {
                    "input": "Draai iets rustigers",
                    "response_text": "Ik heb iets zachts gekozen.",
                    "intent": "play_similar",
                    "track": {"artist": "The xx", "title": "Intro"},
                },
            },
            "session": [{"role": "user", "text": "Doe nog zoiets"}],
        }

        prompt = enrich_user_text_with_memory("Waarom koos je dit?", context)

        self.assertIn("Waarom koos je dit?", prompt)
        self.assertIn("Laatste Ask DJ vraag", prompt)
        self.assertIn("The xx", prompt)
        self.assertIn("Mood/energy: 42/100", prompt)
        self.assertIn("Luistertijdcontext", prompt)
        self.assertIn("avond", prompt)

    def test_music_dna_logs_do_not_include_tokens_or_raw_prompts(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()
        logger = logging.getLogger("custom_components.djconnect.music_dna")
        asyncio.run(manager.async_set_enabled(runtime, True, {"client_type": "watchos"}))

        with self.assertLogs(logger, level="DEBUG") as captured:
            asyncio.run(
                manager.async_update_last_ask_dj(
                    runtime,
                    input_text="RAW VOICE TRANSCRIPT WITH Bearer secret-token",
                    result={
                        "intent": {"intent": "play_music"},
                        "dj_text": "token should not appear",
                        "playback": {"track": {"title": "Safe", "artist": "Artist"}},
                    },
                    payload={
                        "client_type": "watchos",
                        "authorization": "Bearer secret-token",
                    },
                )
            )

        logs = "\n".join(captured.output)
        self.assertIn("DJConnect Music DNA updated", logs)
        self.assertNotIn("secret-token", logs)
        self.assertNotIn("RAW VOICE TRANSCRIPT", logs)
        self.assertNotIn("token should not appear", logs)

    def test_music_dna_requires_opt_in_before_building_knowledge(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()

        asyncio.run(
            manager.async_update_last_ask_dj(
                runtime,
                input_text="Draai iets rustigers",
                result={
                    "intent": {"intent": "play_music"},
                    "dj_text": "Ik kies iets zachts.",
                    "playback": {"track": {"title": "Intro", "artist": "The xx"}},
                },
            )
        )
        disabled_profile = asyncio.run(manager.async_profile(runtime))

        self.assertFalse(disabled_profile["enabled"])
        self.assertEqual(disabled_profile["profile"], {})
        self.assertNotIn("last_ask_dj", store.saved["memories"]["djconnect-watchos-8F3A2C91B45D"])

        asyncio.run(manager.async_set_enabled(runtime, True))
        asyncio.run(
            manager.async_update_last_ask_dj(
                runtime,
                input_text="Draai iets rustigers",
                result={
                    "intent": {"intent": "play_music"},
                    "dj_text": "Ik kies iets zachts.",
                    "playback": {"track": {"title": "Intro", "artist": "The xx"}},
                },
            )
        )
        enabled_profile = asyncio.run(manager.async_profile(runtime))

        self.assertTrue(enabled_profile["enabled"])
        self.assertIn("recent_tracks", enabled_profile["profile"])

    def test_clear_music_dna_preserves_opt_in_and_resets_profile(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()

        asyncio.run(manager.async_set_enabled(runtime, True))
        asyncio.run(
            manager.async_update_last_ask_dj(
                runtime,
                input_text="Draai The xx",
                result={
                    "intent": {"intent": "play_music"},
                    "dj_text": "Komt eraan.",
                    "playback": {"track": {"title": "Intro", "artist": "The xx"}},
                },
            )
        )
        asyncio.run(manager.async_clear("djconnect-watchos-8F3A2C91B45D"))
        profile = asyncio.run(manager.async_profile(runtime))

        self.assertTrue(profile["enabled"])
        self.assertEqual(profile["profile"]["summary"], "Music DNA is ingeschakeld, maar er is nog weinig profieldata opgebouwd.")


if __name__ == "__main__":
    unittest.main()
