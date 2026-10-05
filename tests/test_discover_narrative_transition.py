"""Producer and Session behavior for one bounded Discover relationship."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import importlib
import json
import types
import unittest

from tests.test_config_flow_helpers import install_homeassistant_stubs
from tests.test_http_voice_helpers import install_http_stubs
from tests.test_session_intelligence_continuity import _load_runtime_module
from tests.test_spotify_backend import install_backend_stubs
from tests.test_track_insight import FakeHass, Runtime as InsightRuntime


ARTIST = "A" * 22
OTHER = "B" * 22


class DiscoverNarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_homeassistant_stubs()
        install_backend_stubs()
        install_http_stubs()
        cls.spotify = importlib.import_module("custom_components.djconnect.spotify_backend")
        cls.insight = importlib.import_module("custom_components.djconnect.track_insight")
        cls.api = importlib.import_module("custom_components.djconnect.api_handlers")
        cls.core = _load_runtime_module()

    def playback(self, title, number, *, ids=(ARTIST,), genre="ambient", returned=None):
        """Use both real production normalizers with a mocked Spotify response."""
        value = self.spotify._normalize_playback({
            "is_playing": True,
            "item": {
                "uri": f"spotify:track:{number:022d}", "name": title,
                "artists": [{"id": key, "name": "Example Artist"} for key in ids],
                "album": {"name": "Example Album"},
            },
        })
        backend = self.spotify.SpotifyBackend(
            object(), types.SimpleNamespace(backend_cache={})
        )

        async def request(method, path):
            self.assertEqual((method, path), ("GET", f"/artists?ids={','.join(ids)}"))
            return {"artists": [
                {"id": key, "genres": [genre]}
                for key in (ids if returned is None else returned)
            ]}

        backend._request = request
        if ids:
            asyncio.run(backend._enrich_playback_artist_genres(value))
        return value

    def insight_for(self, playback, number, *, evidence=None, analysis_genre="ambient",
                    track_title=None, track_artist=None, related_tracks=None):
        track = self.insight._track_contract(
            playback, types.SimpleNamespace(config={"music_backend": "spotify_direct"}),
            self.insight.TrackInsightRequest(music_backend="spotify_direct"),
        )
        if track_title is not None:
            track["title"] = track_title
        if track_artist is not None:
            track["artist"] = track_artist
        if related_tracks is not None:
            track["related_tracks"] = related_tracks
        private = {
            "source": "spotify_playback_status",
            "backend": "spotify_direct",
            "media_identity": playback["uri"],
            "artist_ids": playback["artist_ids"],
            "genres": playback.get("genres", []),
            "title": playback["title"], "artist": playback["artist"],
            "is_playing": playback["is_playing"],
        }
        private.update(evidence or {})
        return {
            "track": track,
            "analysis": {
                "genre": analysis_genre,
                "summary": f"Observed context {number}.",
                "full_text": f"A bounded explanation for track {number}.",
            },
            "_session_narrative_evidence": private,
        }

    def start(self, *, strategy=None, locale="en", profile="discover-narrative"):
        clock = [100.0]
        manager = self.core.SessionRuntimeManager()
        session = asyncio.run(manager.async_start(
            owner_profile_id=profile, selected_mood="groove",
            dj_persona=self.core.DJPersona.HOME_DJ, locale=locale,
            session_start_strategy=strategy or self.core.SessionStartStrategy.DISCOVER,
            elapsed_time_source=lambda: clock[0],
        ))
        return manager, session, clock

    def event(self, manager, session, clock, playback, number, **changes):
        insight = self.insight_for(playback, number, **changes)

        async def provide():
            return insight

        result = asyncio.run(manager.async_process_track_started(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            media_identity=playback["uri"], insight_provider=provide,
        ))
        clock[0] += 75.0
        return result

    def sequence(self, *, source_evidence=None, target_evidence=None,
                 source_genre="ambient", strategy=None, locale="en"):
        manager, session, clock = self.start(strategy=strategy, locale=locale)
        self.assertIsNone(self.event(manager, session, clock, self.playback("Baseline", 1), 1))
        source = self.event(manager, session, clock, self.playback("First Light", 2), 2,
                            evidence=source_evidence, analysis_genre=source_genre)
        target = self.event(manager, session, clock, self.playback("Second Light", 3), 3,
                            evidence=target_evidence)
        return manager, session, clock, source, target

    def bridges(self, session):
        return [m for m in session.moment_engine.moments
                if m.moment_type is self.core.DJMomentType.TRANSITION]

    def test_producer_checks_artist_id_and_private_evidence_survives_both_cache_orders(self):
        bad = self.playback("First Light", 2, returned=(OTHER,))
        self.assertEqual(bad["artist_ids"], [ARTIST])
        self.assertNotIn("genres", bad)
        current = self.playback("First Light", 2)
        self.assertEqual(current["genres"], ["ambient"])
        self.assertEqual(current["uri"], "spotify:track:0000000000000000000002")
        hass = FakeHass('{"summary":"Context","full_text":"Detail","genre":"ambient"}')

        async def status(_hass, _runtime, command, value=None):
            self.assertEqual(command, "status")
            return {"playback": current}

        original = self.insight.run_music_command
        self.insight.run_music_command = status
        try:
            for order in (("public", "internal"), ("internal", "public")):
                runtime = InsightRuntime()
                service = self.insight.TrackInsightService()
                result = {}
                for kind in order:
                    result[kind] = asyncio.run(service.async_analyze(
                        hass, runtime, {"music_backend": "spotify_direct"},
                        source="session_moment" if kind == "internal" else "http",
                        **({"session_evidence": True} if kind == "internal" else {}),
                    ))
                proof = result["internal"]["_session_narrative_evidence"]
                self.assertEqual(proof["artist_ids"], [ARTIST])
                self.assertEqual(proof["genres"], ["ambient"])
                self.assertEqual(proof["media_identity"], current["uri"])
                self.assertNotIn("_session_narrative_evidence", result["public"])
                self.assertNotIn(ARTIST, str(result["public"]))
                self.assertNotIn(current["uri"], str(result["public"]))
        finally:
            self.insight.run_music_command = original

    def test_valid_observed_genre_to_track_is_a_visible_single_transition(self):
        _, session, _, source, target = self.sequence()
        self.assertEqual(source.moment_type, self.core.DJMomentType.GENRE)
        self.assertEqual(target.moment_type, self.core.DJMomentType.TRACK)
        self.assertEqual(len(self.bridges(session)), 1)
        bridge = self.bridges(session)[0]
        meta = dict(bridge.generation_metadata)
        self.assertEqual(meta["relation"], "discover_same_artist_genre")
        self.assertEqual(meta["transition_from_moment_id"], source.moment_id)
        self.assertEqual(meta["transition_to_moment_id"], target.moment_id)
        for value in ("ambient", "Example Artist", "First Light", "Second Light"):
            self.assertIn(value, bridge.content)
        self.assertNotIn(ARTIST, str(bridge.as_dict()))
        self.assertNotIn("spotify:track:", str(bridge.as_dict()))
        flow = [item.moment_id for item in session.planner.output.session_flow.items if item.moment_id]
        self.assertEqual(flow[-3:], [source.moment_id, target.moment_id, bridge.moment_id])
        self.assertEqual(session.broadcast.as_dict()["dj_moments"][-1]["moment_id"], bridge.moment_id)

    def test_missing_ambiguous_conflicting_or_stale_context_never_bridges(self):
        cases = (
            ({"artist_ids": []}, {}, "ambient"),
            ({"artist_ids": [ARTIST, OTHER]}, {}, "ambient"),
            ({"genres": []}, {}, "ambient"),
            ({"media_identity": "spotify:track:" + "9" * 22}, {}, "ambient"),
            ({"title": "Wrong source"}, {}, "ambient"),
            ({"artist": "Wrong artist"}, {}, "ambient"),
            ({}, {"artist_ids": [OTHER]}, "ambient"),
            ({}, {"genres": ["jazz"]}, "ambient"),
            ({}, {"media_identity": "spotify:track:" + "8" * 22}, "ambient"),
            ({}, {"is_playing": False}, "ambient"),
            ({}, {"title": "Wrong target"}, "ambient"),
            ({}, {"artist": "Wrong artist"}, "ambient"),
            ({}, {}, "jazz"),
        )
        for source_evidence, target_evidence, source_genre in cases:
            with self.subTest(source=source_evidence, target=target_evidence, genre=source_genre):
                _, session, _, _, _ = self.sequence(
                    source_evidence=source_evidence,
                    target_evidence=target_evidence, source_genre=source_genre,
                )
                self.assertEqual(self.bridges(session), [])

    def test_duplicate_unrelated_or_changed_context_abandons_line(self):
        for change in ("duplicate_then_unrelated", "mood", "persona", "direction", "flow"):
            with self.subTest(change=change):
                manager, session, clock = self.start(profile=f"abandon-{change}")
                self.event(manager, session, clock, self.playback("Baseline", 1), 1)
                first = self.playback("First Light", 2)
                source = self.event(manager, session, clock, first, 2)
                self.assertEqual(source.moment_type, self.core.DJMomentType.GENRE)
                if change == "duplicate_then_unrelated":
                    self.assertIsNone(self.event(manager, session, clock, first, 2))
                    unrelated = self.playback("Unrelated", 3, ids=(OTHER,), genre="jazz")
                    self.event(manager, session, clock, unrelated, 3,
                               analysis_genre="jazz")
                    target = self.playback("Later Light", 4)
                    self.event(manager, session, clock, target, 4)
                else:
                    if change == "mood":
                        asyncio.run(manager.async_update_mood(
                            owner_profile_id=session.owner_profile_id,
                            session_id=session.session_id, selected_mood="groove_changed"))
                    elif change == "persona":
                        asyncio.run(manager.async_update_persona(
                            owner_profile_id=session.owner_profile_id,
                            session_id=session.session_id,
                            dj_persona=self.core.DJPersona.RADIO_DJ))
                    elif change == "direction":
                        active = asyncio.run(manager.async_get_active(session.owner_profile_id))
                        manager._active_by_profile[session.owner_profile_id] = replace(
                            active, session_direction=replace(
                                active.session_direction,
                                direction=self.core.SessionDirectionType.RETURNING))
                    else:
                        session.republish_session_flow()
                    self.event(manager, session, clock, self.playback("Second Light", 3), 3)
                self.assertEqual(self.bridges(session), [])

    def test_completed_line_single_use_and_session_end_drops_pending_line(self):
        manager, session, clock, _, _ = self.sequence()
        for number in range(4, 12):
            self.event(manager, session, clock,
                       self.playback(f"Later Light {number}", number), number)
        self.assertEqual(len(self.bridges(session)), 1)
        manager, old, clock = self.start(profile="ended-line")
        self.event(manager, old, clock, self.playback("Baseline", 21), 21)
        self.event(manager, old, clock, self.playback("First Light", 22), 22)
        asyncio.run(manager.async_end(owner_profile_id=old.owner_profile_id))
        new = asyncio.run(manager.async_start(
            owner_profile_id=old.owner_profile_id, selected_mood="groove",
            session_start_strategy=self.core.SessionStartStrategy.DISCOVER,
            elapsed_time_source=lambda: clock[0]))
        self.event(manager, new, clock, self.playback("New baseline", 23), 23)
        self.event(manager, new, clock, self.playback("Second Light", 24), 24)
        self.assertEqual(self.bridges(new), [])

    def test_manual_and_continue_do_not_gain_the_relation(self):
        for strategy in (self.core.SessionStartStrategy.MANUAL,
                         self.core.SessionStartStrategy.CONTINUE):
            with self.subTest(strategy=strategy):
                _, session, _, _, _ = self.sequence(strategy=strategy)
                self.assertFalse(any(dict(m.generation_metadata).get("relation")
                                     == "discover_same_artist_genre"
                                     for m in session.moment_engine.moments))

    def test_real_session_provider_feeds_the_runtime(self):
        manager, session, clock = self.start(profile="real-provider")
        hass, runtime = FakeHass(), InsightRuntime()
        current = {"playback": None}

        async def status(_hass, _runtime, command, value=None):
            self.assertEqual(command, "status")
            return {"playback": current["playback"]}

        original = self.insight.run_music_command
        self.insight.run_music_command = status
        try:
            provider = self.api._session_track_insight_provider(hass, runtime, session)
            results = []
            for number, title in ((1, "Baseline"), (2, "First Light"), (3, "Second Light")):
                playback = self.playback(title, number)
                current["playback"] = playback
                hass.services.response_text = json.dumps({
                    "summary": f"Observed context {number}.",
                    "full_text": f"A bounded explanation for track {number}.",
                    "genre": "ambient",
                })
                results.append(asyncio.run(manager.async_process_track_started(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id, media_identity=playback["uri"],
                    insight_provider=provider)))
                clock[0] += 75.0
        finally:
            self.insight.run_music_command = original
        self.assertIsNone(results[0])
        self.assertEqual(results[1].moment_type, self.core.DJMomentType.GENRE)
        self.assertEqual(results[2].moment_type, self.core.DJMomentType.TRACK)
        self.assertEqual(len(self.bridges(session)), 1)


if __name__ == "__main__":
    unittest.main()
