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

    def test_listening_profile_snapshots_are_compact_and_bounded(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for(client_type="ios", device_id="djconnect-ios-ABCDEF123456")
        asyncio.run(manager.async_set_enabled(runtime, True, {"client_type": "ios"}, user_id="ha-user-1"))

        for index in range(14):
            asyncio.run(
                manager.async_update_listening_profile(
                    runtime,
                    {
                        "recent_tracks": [
                            {
                                "track_name": f"Recent {index}",
                                "artist": "Artist",
                                "uri": f"spotify:track:recent-{index}",
                            }
                        ],
                        "top_tracks_by_range": {
                            "short_term": [
                                {
                                    "track_name": f"Top {index}",
                                    "artist": "Artist",
                                    "uri": f"spotify:track:top-{index}",
                                }
                            ]
                        },
                        "top_artists_by_range": {
                            "short_term": [
                                {
                                    "name": f"Artist {index}",
                                    "uri": f"spotify:artist:{index}",
                                    "genres": ["indie"],
                                }
                            ]
                        },
                        "inferred_genres": ["indie", "ambient"],
                        "sources": ["spotify_recently_played", "spotify_top_tracks_short_term"],
                        "last_profile_refresh": f"2026-07-09T{index:02d}:00:00+00:00",
                    },
                    {"client_type": "ios"},
                    user_id="ha-user-1",
                )
            )

        profile = asyncio.run(manager.async_profile(runtime, {"client_type": "ios"}, user_id="ha-user-1"))["profile"]
        snapshots = profile["snapshot_history"]
        self.assertEqual(len(snapshots), 12)
        self.assertEqual(snapshots[0]["captured_at"], "2026-07-09T13:00:00+00:00")
        self.assertEqual(snapshots[-1]["captured_at"], "2026-07-09T02:00:00+00:00")
        self.assertEqual(snapshots[0]["top_tracks"][0]["title"], "Top 13")
        self.assertEqual(snapshots[0]["top_artists"][0]["name"], "Artist 13")
        self.assertNotIn("recent_tracks", snapshots[0])

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

    def test_recent_playback_track_genres_feed_profile_favorite_genres(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        manager.update_recent_tracks(
            resolve_music_dna_key(runtime),
            {
                "title": "Innerbloom",
                "artist": "RUFUS DU SOL",
                "album": "Bloom",
                "uri": "spotify:track:innerbloom",
                "genres": ["australian dance", "indietronica"],
            },
        )
        manager.update_recent_tracks(
            resolve_music_dna_key(runtime),
            {
                "title": "Innerbloom",
                "artist": "RUFUS DU SOL",
                "album": "Bloom",
                "uri": "spotify:track:innerbloom",
                "genres": ["australian dance", "indietronica"],
            },
        )
        manager.update_recent_tracks(
            resolve_music_dna_key(runtime),
            {
                "title": "On My Knees",
                "artist": "RUFUS DU SOL",
                "album": "Surrender",
                "uri": "spotify:track:on-my-knees",
                "genres": ["australian dance"],
            },
        )
        manager.update_recent_tracks(
            resolve_music_dna_key(runtime),
            {
                "title": "Midnight City",
                "artist": "M83",
                "album": "Hurry Up, We're Dreaming",
                "uri": "spotify:track:midnight-city",
                "genres": ["indietronica"],
            },
        )
        profile = asyncio.run(manager.async_profile(runtime))

        self.assertEqual(
            set(item["name"] for item in profile["profile"]["favorite_genres"][:2]),
            {"australian dance", "indietronica"},
        )
        self.assertEqual(
            profile["profile"]["recent_tracks"][0]["genres"],
            ["indietronica"],
        )
        self.assertEqual(len(profile["profile"]["recent_tracks"]), 3)
        self.assertEqual(profile["profile"]["favorite_artists"][0]["name"], "RUFUS DU SOL")
        self.assertEqual(profile["profile"]["favorite_artists"][0]["play_count"], 2)
        self.assertEqual(profile["profile"]["favorite_artists"][1]["name"], "M83")
        self.assertEqual(profile["profile"]["favorite_artists"][1]["play_count"], 1)
        self.assertIn("3 recente track(s)", profile["profile"]["summary"])
        self.assertIn("2 artiest(en)", profile["profile"]["summary"])

    def test_current_track_favorite_records_bounded_recent_favorite_tracks(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True, {"client_type": "ios"}, user_id="ha-user-1"))

        asyncio.run(
            manager.async_record_current_track_favorite(
                runtime,
                {
                    "track_name": "Far Behind",
                    "artist": "Candlebox",
                    "album_name": "Candlebox",
                    "uri": "spotify:track:far-behind",
                    "device_token": "must-not-persist",
                },
                {"client_type": "ios"},
                user_id="ha-user-1",
            )
        )
        asyncio.run(
            manager.async_record_current_track_favorite(
                runtime,
                {
                    "track_name": "Far Behind",
                    "artist": "Candlebox",
                    "album_name": "Candlebox",
                    "uri": "spotify:track:far-behind",
                },
                {"client_type": "ios"},
                user_id="ha-user-1",
            )
        )

        profile = asyncio.run(manager.async_profile(runtime, {"client_type": "ios"}, user_id="ha-user-1"))
        favorites = profile["profile"]["recent_favorite_tracks"]

        self.assertEqual(len(favorites), 1)
        self.assertEqual(favorites[0]["track_name"], "Far Behind")
        self.assertEqual(favorites[0]["artist"], "Candlebox")
        self.assertNotIn("device_token", str(profile))
        self.assertEqual(
            manager.data["memories"]["user:ha-user-1"]["recent_favorite_tracks"][0]["source"],
            "ask_dj_current_track_favorite",
        )

    def test_playtime_profile_tracks_total_hours_and_top_three_artists(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        key = resolve_music_dna_key(runtime)
        asyncio.run(manager.async_set_enabled(runtime, True))

        for track in (
            {"track_name": "One", "artist": "Artist A", "album": "Album A", "uri": "spotify:track:1", "duration_ms": 30 * 60 * 1000},
            {"track_name": "Two", "artist": "Artist B", "album": "Album B", "uri": "spotify:track:2", "duration_ms": 20 * 60 * 1000},
            {"track_name": "Three", "artist": "Artist A", "album": "Album A", "uri": "spotify:track:3", "duration_ms": 15 * 60 * 1000},
            {"track_name": "Four", "artist": "Artist C", "album": "Album C", "uri": "spotify:track:4", "duration_ms": 10 * 60 * 1000},
            {"track_name": "Five", "artist": "Artist D", "album": "Album D", "uri": "spotify:track:5", "duration_ms": 5 * 60 * 1000},
        ):
            manager.update_recent_tracks(key, track)

        profile = asyncio.run(manager.async_profile(runtime))
        playtime = profile["profile"]["playtime"]

        self.assertEqual(playtime["total_seconds"], 80 * 60)
        self.assertEqual(playtime["total_hours"], 1.33)
        self.assertEqual(playtime["formatted_total"], "1u 20m")
        self.assertEqual(
            [(item["name"], item["formatted"]) for item in playtime["top_artists"]],
            [("Artist A", "45m"), ("Artist B", "20m"), ("Artist C", "10m")],
        )
        self.assertEqual(
            [(item["name"], item["formatted"]) for item in playtime["top_albums"]],
            [("Album A", "45m"), ("Album B", "20m"), ("Album C", "10m")],
        )
        self.assertIn("1u 20m luistertijd", profile["profile"]["summary"])
        self.assertEqual(manager.data["memories"][key]["artist_play_seconds"]["Artist A"], 45 * 60)
        self.assertEqual(manager.data["memories"][key]["album_play_seconds"]["Album A"], 45 * 60)

    def test_listening_rhythm_profile_exposes_dayparts_and_weekdays(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        key = resolve_music_dna_key(runtime)
        asyncio.run(manager.async_set_enabled(runtime, True))
        manager.data["memories"][key]["listening_time_signals"] = {
            "count": 6,
            "dayparts": {"avond": 4, "middag": 2},
            "weekdays": {"vrijdag": 3, "zaterdag": 2, "maandag": 1},
        }

        rhythm = asyncio.run(manager.async_profile(runtime))["profile"]["listening_rhythm"]

        self.assertGreaterEqual(rhythm["sample_count"], 6)
        self.assertEqual(rhythm["top_daypart"], "avond")
        self.assertEqual(rhythm["top_weekday"], "vrijdag")
        self.assertEqual(rhythm["dayparts"][0]["daypart"], "avond")
        self.assertGreaterEqual(rhythm["dayparts"][0]["count"], 4)
        self.assertEqual(rhythm["weekdays"][0]["weekday"], "vrijdag")
        self.assertGreaterEqual(rhythm["weekdays"][0]["count"], 3)

    def test_conditional_music_dna_blocks_use_reliable_signals(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        key = resolve_music_dna_key(runtime)
        asyncio.run(manager.async_set_enabled(runtime, True))

        sparse_profile = asyncio.run(manager.async_profile(runtime))["profile"]
        self.assertFalse(sparse_profile["repeat_magnets"]["eligible"])
        self.assertFalse(sparse_profile["explicit_positives"]["eligible"])
        self.assertFalse(sparse_profile["taste_anchors"]["eligible"])

        for track in (
            {"track_name": "One", "artist": "Artist A", "album": "Album A", "uri": "spotify:track:1", "genres": ["indie"], "duration_ms": 30 * 60 * 1000},
            {"track_name": "Two", "artist": "Artist A", "album": "Album A", "uri": "spotify:track:2", "genres": ["indie"], "duration_ms": 30 * 60 * 1000},
            {"track_name": "Three", "artist": "Artist B", "album": "Album B", "uri": "spotify:track:3", "genres": ["ambient"], "duration_ms": 20 * 60 * 1000},
            {"track_name": "Four", "artist": "Artist B", "album": "Album B", "uri": "spotify:track:4", "genres": ["ambient"], "duration_ms": 20 * 60 * 1000},
        ):
            manager.update_recent_tracks(key, track)
        asyncio.run(
            manager.async_record_current_track_favorite(
                runtime,
                {"track_name": "One", "artist": "Artist A", "uri": "spotify:track:1"},
            )
        )
        asyncio.run(
            manager.async_record_recommendation_play(
                runtime,
                {"title": "Recommended Track", "subtitle": "Artist C", "uri": "spotify:track:recommended"},
            )
        )

        profile = asyncio.run(manager.async_profile(runtime))["profile"]

        self.assertTrue(profile["repeat_magnets"]["eligible"])
        self.assertEqual(profile["repeat_magnets"]["items"][0]["name"], "Artist A")
        self.assertTrue(profile["explicit_positives"]["eligible"])
        self.assertEqual(profile["explicit_positives"]["favorite_tracks"][0]["title"], "One")
        self.assertEqual(profile["explicit_positives"]["accepted_recommendations"][0]["title"], "Recommended Track")
        self.assertTrue(profile["taste_anchors"]["eligible"])
        self.assertIn(
            ("artist", "Artist A"),
            [(item["kind"], item["name"]) for item in profile["taste_anchors"]["items"]],
        )
        self.assertIn(
            ("genre", "ambient"),
            [(item["kind"], item["name"]) for item in profile["taste_anchors"]["items"]],
        )

    def test_track_insight_energy_signals_feed_profile_energy_profile(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        manager.update_track_insight_energy(
            resolve_music_dna_key(runtime),
            {"title": "Sewing Machine", "artist": "Onur Yalcinsory", "album": "Scala"},
            {"energy": 0.81, "danceability": 0.62, "intensity": 0.74, "confidence": 0.9},
        )
        manager.update_track_insight_energy(
            resolve_music_dna_key(runtime),
            {"title": "Dream On", "artist": "Scala & Kolacny Brothers", "album": "Dream On"},
            {"energy": 0.59, "danceability": 0.45, "intensity": 0.5, "confidence": 0.8},
        )

        profile = asyncio.run(manager.async_profile(runtime))["profile"]

        self.assertEqual(profile["energy_profile"]["sample_count"], 2)
        self.assertEqual(profile["energy_profile"]["energy_percent"], 70)
        self.assertEqual(profile["energy_profile"]["zone"], "energy")
        self.assertEqual(profile["energy_profile"]["danceability_percent"], 54)
        self.assertEqual(profile["energy_profile"]["intensity_percent"], 62)
        self.assertEqual(profile["energy_profile"]["recent_signals"][0]["title"], "Dream On")

    def test_client_mood_signals_feed_profile_mood_average(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 10}))
        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 70}))
        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 90}))

        profile = asyncio.run(manager.async_profile(runtime))["profile"]

        self.assertEqual(profile["mood"]["value"], 90)
        self.assertEqual(profile["mood"]["zone"], "party")
        self.assertEqual(profile["mood"]["sample_count"], 3)
        self.assertEqual(profile["mood"]["average"], 57)
        self.assertEqual(profile["mood"]["average_zone"], "groove")
        self.assertEqual(profile["mood"]["zone_counts"]["chill"], 1)
        self.assertEqual(profile["mood"]["zone_counts"]["energy"], 1)
        self.assertEqual(profile["mood"]["zone_counts"]["party"], 1)
        self.assertEqual(profile["mood_mix"]["sample_count"], 3)
        self.assertEqual(profile["mood_mix"]["top_zone"], "chill")
        self.assertEqual(
            profile["mood_mix"]["zones"],
            [
                {"zone": "chill", "count": 1, "percent": 33.3},
                {"zone": "energy", "count": 1, "percent": 33.3},
                {"zone": "party", "count": 1, "percent": 33.3},
            ],
        )

    def test_repeated_client_mood_refresh_does_not_inflate_signal_count(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 99}))
        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 99}))
        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 99}))
        asyncio.run(manager.async_update_client_metadata(runtime, {"mood": 70}))

        profile = asyncio.run(manager.async_profile(runtime))["profile"]

        self.assertEqual(profile["mood"]["value"], 70)
        self.assertEqual(profile["mood"]["sample_count"], 2)
        self.assertEqual(profile["mood"]["average"], 84)
        self.assertEqual(profile["mood"]["average_zone"], "energy")
        self.assertEqual(profile["mood"]["zone_counts"]["party"], 1)
        self.assertEqual(profile["mood"]["zone_counts"]["energy"], 1)

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

    def test_removed_favorite_track_is_persisted_as_blocked_item(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True, {"client_type": "ios"}, user_id="ha-user-1"))

        asyncio.run(
            manager.async_record_blocked_music_preference(
                runtime,
                {
                    "kind": "track",
                    "name": "Radiohead - Karma Police",
                    "title": "Karma Police",
                    "artist": "Radiohead",
                    "uri": "spotify:track:karma-police",
                    "reason": "removed_from_favorites",
                    "device_token": "must-not-persist",
                },
                {"client_type": "ios"},
                user_id="ha-user-1",
            )
        )

        memory = store.saved["memories"]["user:ha-user-1"]
        self.assertEqual(memory["blocked_items"][0]["kind"], "track")
        self.assertEqual(memory["blocked_items"][0]["name"], "Radiohead - Karma Police")
        self.assertEqual(memory["blocked_items"][0]["reason"], "removed_from_favorites")
        self.assertNotIn("device_token", str(memory))

        context = asyncio.run(
            manager.async_context_for_runtime(
                runtime,
                {"client_type": "ios"},
                user_id="ha-user-1",
            )
        )
        self.assertIn("Discover negatieve feedback: Radiohead - Karma Police", prompt_context_text(context))
        profile = asyncio.run(manager.async_profile(runtime, {"client_type": "ios"}, user_id="ha-user-1"))["profile"]
        self.assertEqual(profile["discovery_feedback"]["blocked_items"][0]["name"], "Radiohead - Karma Police")

    def test_discover_feedback_is_available_to_ask_dj_context(self) -> None:
        store = FakeStore()
        manager = MusicDNAManager(store=store)
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True, user_id="ha-user-1"))

        asyncio.run(
            manager.async_record_discovery_play(
                runtime,
                {
                    "id": "track:1",
                    "kind": "track",
                    "uri": "spotify:track:1",
                    "title": "Midnight City",
                    "subtitle": "M83",
                    "reason": "past bij je recente synthpop",
                    "quality_score": 91,
                    "quality_band": "high",
                },
                {"section_id": "new_for_you"},
                user_id="ha-user-1",
            )
        )
        asyncio.run(
            manager.async_record_blocked_music_preference(
                runtime,
                {"kind": "artist", "name": "Coldplay", "reason": "hide_artist"},
                user_id="ha-user-1",
            )
        )

        context = asyncio.run(manager.async_context_for_runtime(runtime, user_id="ha-user-1"))
        prompt_text = prompt_context_text(context)
        self.assertIn("Discover gekozen door gebruiker: Midnight City - M83, kwaliteit 91", prompt_text)
        self.assertIn("reden: past bij je recente synthpop", prompt_text)
        self.assertIn("Discover negatieve feedback: artiest Coldplay", prompt_text)

        profile = asyncio.run(manager.async_profile(runtime, user_id="ha-user-1"))["profile"]
        feedback = profile["discovery_feedback"]
        self.assertTrue(feedback["eligible"])
        self.assertEqual(feedback["accepted_items"][0]["title"], "Midnight City")
        self.assertEqual(feedback["accepted_items"][0]["quality_score"], 91)
        self.assertEqual(feedback["blocked_artists"][0]["name"], "Coldplay")

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
        self.assertNotIn("recent_tracks", profile["profile"])
        self.assertNotIn("playtime", profile["profile"])

    def test_empty_optional_dashboard_blocks_are_omitted(self) -> None:
        manager = MusicDNAManager(store=FakeStore())
        runtime = runtime_for()
        asyncio.run(manager.async_set_enabled(runtime, True))

        profile = asyncio.run(manager.async_profile(runtime))["profile"]

        self.assertEqual(profile["summary"], "Music DNA is ingeschakeld, maar er is nog weinig profieldata opgebouwd.")
        for key in (
            "favorite_genres",
            "favorite_artists",
            "recent_tracks",
            "recent_favorite_tracks",
            "playtime",
            "listening_rhythm",
            "mood_mix",
            "energy_profile",
            "time_patterns",
            "recommendation_signals",
            "blocked_artists",
            "blocked_items",
            "discovery_feedback",
        ):
            self.assertNotIn(key, profile)
        self.assertFalse(profile["repeat_magnets"]["eligible"])
        self.assertFalse(profile["explicit_positives"]["eligible"])
        self.assertFalse(profile["taste_anchors"]["eligible"])


if __name__ == "__main__":
    unittest.main()
