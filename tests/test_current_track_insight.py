"""Current recording regressions with external HTTP and causal lifecycle interleavings."""
from __future__ import annotations

import importlib
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from tests.test_track_insight import FakeHass, Runtime
from tests.test_config_flow_helpers import install_homeassistant_stubs
from tests.test_spotify_backend import install_backend_stubs

CURRENT = {"track_insight_subject": {"schema_version": 1, "mode": "current"}}
URI_A = "spotify:track:" + "a" * 22
URI_B = "spotify:track:" + "b" * 22


def provider_payload(uri=URI_A, *, playing=True, position=10000):
    return {"is_playing": playing, "progress_ms": position,
            "device": {"id": "synthetic-output", "name": "Synthetic output"},
            "item": {"uri": uri, "name": "Same title", "artists": [{"name": "Same artist"}],
                     "duration_ms": 180000, "album": {"name": "Synthetic album"}}}


class CurrentTrackInsightTests(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_homeassistant_stubs()
        install_backend_stubs()
        cls.package = importlib.import_module("custom_components.djconnect")
        cls.had_runtime_attribute = hasattr(cls.package, "session_runtime")
        cls.previous_runtime_attribute = getattr(cls.package, "session_runtime", None)
        cls.module = importlib.import_module("custom_components.djconnect.track_insight")
        cls.spotify = importlib.import_module("custom_components.djconnect.spotify_backend")

    @classmethod
    def tearDownClass(cls):
        # The repository's synthetic Runtime loader replaces sys.modules without
        # updating the parent package. Do not leave our first ordinary import as
        # a stale parent alias for a later real lifecycle fixture.
        if cls.had_runtime_attribute:
            cls.package.session_runtime = cls.previous_runtime_attribute
        elif hasattr(cls.package, "session_runtime"):
            delattr(cls.package, "session_runtime")

    async def asyncSetUp(self):
        self.hass, self.runtime = FakeHass(), Runtime()
        self.hass.data = {"djconnect": {}}
        self.value = provider_payload()
        self.calls = []
        async def request(_backend, method, path, **kwargs):
            self.calls.append((method, path))
            self.assertEqual((method, path), ("GET", "/me/player"))
            return self.value
        self.edge = patch.object(self.spotify.SpotifyBackend, "_request", request)
        self.edge.start()
        self.addCleanup(self.edge.stop)

    async def analyze(self, payload=None, **kwargs):
        return await self.module.TrackInsightService().async_analyze(
            self.hass, self.runtime, CURRENT if payload is None else payload, **kwargs)

    async def test_current_without_session_is_exact_unmeasured_and_has_no_model_or_history_write(self):
        result = await self.analyze()
        self.assertEqual(result["subject"]["mode"], "current")
        self.assertEqual(result["subject"]["media_identity"], URI_A)
        self.assertTrue(result["subject"]["observation_id"])
        self.assertGreater(result["subject"]["expires_in"], 0)
        self.assertLessEqual(result["subject"]["expires_in"], 30)
        self.assertEqual(result["analysis"]["basis"], "unmeasured_metadata_only_v1")
        self.assertFalse(self.hass.services.calls)
        self.assertEqual(self.runtime.last_playback, {})
        self.assertFalse(self.hass.bus.events)
        self.assertEqual(self.calls, [("GET", "/me/player"), ("GET", "/me/player")])

    async def test_closed_selector_and_mixed_authorities_are_rejected_before_provider(self):
        for subject in (None, {}, {"schema_version": True, "mode": "current"},
                        {"schema_version": 1, "mode": "latest"},
                        {"schema_version": 1, "mode": "current", "uri": URI_A}):
            with self.subTest(subject=subject):
                with self.assertRaises(self.module.TrackInsightError) as raised:
                    await self.analyze({"track_insight_subject": subject})
                self.assertEqual(raised.exception.code, "invalid_track_insight_subject")
        for key in ("title", "artist", "album", "track", "entity_id", "player_id", "music_backend",
                    "track_insight_target", "conversation_context", "playback", "media", "track_name", "media_title",
                    "name", "artist_name", "media_artist", "artists", "album_name", "media_album_name",
                    "media_album", "backend", "provider", "uri", "media_identity"):
            with self.subTest(key=key):
                with self.assertRaises(self.module.TrackInsightError) as raised:
                    await self.analyze({**CURRENT, key: "untrusted"})
                self.assertEqual(raised.exception.code, "invalid_track_insight_subject")
        self.assertFalse(self.calls)

    async def test_no_exact_recording_or_idle_never_uses_stale_runtime_track(self):
        self.runtime.last_playback = {"uri": URI_A, "track_name": "Stale", "artist_name": "Stale"}
        for uri in ("", "spotify:episode:" + "a" * 22, "spotify:track:invalid"):
            self.value = provider_payload(uri)
            with self.assertRaises(self.module.TrackInsightError) as raised:
                await self.analyze()
            self.assertEqual(raised.exception.code, "current_track_unavailable")
        self.assertFalse(self.hass.services.calls)

    async def test_same_name_different_recordings_have_distinct_subject_and_cache(self):
        a = await self.analyze()
        self.value = provider_payload(URI_B)
        b = await self.analyze()
        self.assertEqual(a["track"]["title"], b["track"]["title"])
        self.assertNotEqual(a["subject"]["media_identity"], b["subject"]["media_identity"])
        self.assertNotEqual(a["subject"]["observation_id"], b["subject"]["observation_id"])
        self.assertNotEqual(a["cache"]["key"], b["cache"]["key"])

    async def test_final_provider_read_rejects_change_before_cache(self):
        original = self.module.TrackInsightAnalyzer.analyze
        async def analyze(analyzer, *args, **kwargs):
            result = await original(analyzer, *args, **kwargs)
            self.value = provider_payload(URI_B)
            return result
        with patch.object(self.module.TrackInsightAnalyzer, "analyze", analyze):
            with self.assertRaises(self.module.TrackInsightError) as raised:
                await self.analyze()
        self.assertEqual(raised.exception.code, "track_insight_context_changed")
        self.assertFalse(getattr(self.runtime, "track_insight_cache", {}))

    async def test_owner_guard_covers_initial_and_final_provider_awaits(self):
        allowed = True
        def owner_guard():
            if not allowed:
                raise self.module.TrackInsightError("unauthorized", "Withdrawn", status=401)
        async def request(_backend, method, path, **kwargs):
            nonlocal allowed
            allowed = False
            return self.value
        with patch.object(self.spotify.SpotifyBackend, "_request", request):
            with self.assertRaises(self.module.TrackInsightError) as raised:
                await self.analyze(commit_guard=owner_guard)
        self.assertEqual(raised.exception.code, "unauthorized")
        self.assertFalse(getattr(self.runtime, "track_insight_cache", {}))

    async def test_cache_hit_revalidates_provider_and_does_not_renew_original_observation(self):
        a = await self.analyze()
        b = await self.analyze()
        self.assertEqual(a["subject"]["observation_id"], b["subject"]["observation_id"])
        self.assertTrue(b["cache"]["hit"])
        self.assertEqual(a["subject"]["expires_at"], b["subject"]["expires_at"])
        self.assertLessEqual(b["subject"]["expires_in"], a["subject"]["expires_in"])
        self.assertEqual(len(self.calls), 4)
        self.assertFalse(self.hass.services.calls)

    async def test_runtime_aba_during_generation_is_not_same_occurrence(self):
        current = importlib.import_module("custom_components.djconnect.current_track_insight")
        original = self.module.TrackInsightAnalyzer.analyze
        async def analyze(analyzer, *args, **kwargs):
            result = await original(analyzer, *args, **kwargs)
            current.observe(self.runtime, URI_B, "playing", 10000, "Synthetic output")
            current.observe(self.runtime, URI_A, "playing", 10000, "Synthetic output")
            return result
        with patch.object(self.module.TrackInsightAnalyzer, "analyze", analyze):
            with self.assertRaises(self.module.TrackInsightError) as raised:
                await self.analyze()
        self.assertEqual(raised.exception.code, "track_insight_context_changed")
        self.assertFalse(getattr(self.runtime, "track_insight_cache", {}))

    async def test_pause_and_seek_fence_but_normal_progress_does_not(self):
        current = importlib.import_module("custom_components.djconnect.current_track_insight")
        a = await self.analyze()
        self.value = provider_payload(position=12000)
        b = await self.analyze()
        self.assertEqual(a["subject"]["observation_id"], b["subject"]["observation_id"])
        self.assertEqual(b["track"]["progress_ms"], 12000)
        current.observe(self.runtime, URI_A, "paused", 12000, "Synthetic output")
        self.value = provider_payload(playing=False, position=12000)
        c = await self.analyze()
        self.assertNotEqual(b["subject"]["observation_id"], c["subject"]["observation_id"])
        self.value = provider_payload(playing=False, position=0)
        d = await self.analyze()
        self.assertNotEqual(c["subject"]["observation_id"], d["subject"]["observation_id"])

    async def test_provider_failure_never_falls_back_to_last_playback(self):
        async def request(*args, **kwargs):
            raise self.spotify.SpotifyBackendError("Synthetic unavailable")
        self.runtime.last_playback = {"uri": URI_A, "track_name": "Stale", "artist_name": "Stale"}
        with patch.object(self.spotify.SpotifyBackend, "_request", request):
            with self.assertRaises(self.module.TrackInsightError) as raised:
                await self.analyze()
        self.assertEqual(raised.exception.code, "current_track_unavailable")

    async def test_unsupported_backend_does_not_query_spotify(self):
        self.runtime.config["music_backend"] = "music_assistant"
        with self.assertRaises(self.module.TrackInsightError) as raised:
            await self.analyze()
        self.assertEqual(raised.exception.code, "current_track_unavailable")
        self.assertFalse(self.calls)

    async def test_unrelated_runtime_notification_cannot_reobserve_stale_last_playback(self):
        current = importlib.import_module("custom_components.djconnect.current_track_insight")
        self.runtime.last_playback = {"uri": URI_B, "is_playing": True, "progress_ms": 5000}
        original = self.module.TrackInsightAnalyzer.analyze
        async def analyze(analyzer, *args, **kwargs):
            current.observe_runtime_playback(self.runtime)
            return await original(analyzer, *args, **kwargs)
        with patch.object(self.module.TrackInsightAnalyzer, "analyze", analyze):
            result = await self.analyze()
        self.assertEqual(result["subject"]["media_identity"], URI_A)

    async def test_runtime_normal_status_aba_invalidates_pending_request(self):
        current = importlib.import_module("custom_components.djconnect.current_track_insight")
        original = self.module.TrackInsightAnalyzer.analyze
        async def analyze(analyzer, *args, **kwargs):
            for uri in (URI_B, URI_A):
                self.runtime.last_playback = {"uri": uri, "is_playing": True, "progress_ms": 10000}
                current.observe_runtime_playback(self.runtime)
            return await original(analyzer, *args, **kwargs)
        with patch.object(self.module.TrackInsightAnalyzer, "analyze", analyze):
            with self.assertRaises(self.module.TrackInsightError):
                await self.analyze()
        self.assertFalse(self.runtime.track_insight_cache)

    async def test_expiry_during_analysis_prevents_cache_commit(self):
        current = importlib.import_module("custom_components.djconnect.current_track_insight")
        import time
        clock = time.monotonic
        original = self.module.TrackInsightAnalyzer.analyze
        async def analyze(analyzer, *args, **kwargs):
            result = await original(analyzer, *args, **kwargs)
            self.clock_patch = patch.object(current.time, "monotonic", return_value=clock() + 31)
            self.clock_patch.start()
            return result
        try:
            with patch.object(self.module.TrackInsightAnalyzer, "analyze", analyze):
                with self.assertRaises(self.module.TrackInsightError) as raised:
                    await self.analyze()
            self.assertEqual(raised.exception.code, "track_insight_context_changed")
            self.assertFalse(self.runtime.track_insight_cache)
        finally:
            if hasattr(self, "clock_patch"):
                self.clock_patch.stop()

    async def test_artist_genres_are_exact_display_metadata_without_a_model_grant(self):
        artist_id = "c" * 22
        value = provider_payload()
        value["item"]["artists"][0]["id"] = artist_id
        calls = []
        async def request(_backend, method, path, **kwargs):
            calls.append((method, path))
            self.assertEqual(method, "GET")
            if path == "/me/player":
                return value
            self.assertEqual(path, "/artists?ids=" + artist_id)
            return {"artists": [{"id": artist_id, "genres": ["synthpop"]}]}
        with patch.object(self.spotify.SpotifyBackend, "_request", request):
            result = await self.analyze()
        self.assertEqual(result["track"]["genres"], ["synthpop"])
        self.assertEqual(result["analysis"]["basis"], "unmeasured_metadata_only_v1")
        self.assertIsNone(result["analysis"]["energy"])
        self.assertFalse(self.hass.services.calls)
        self.assertEqual(len(calls), 3)

    async def test_account_rebinding_during_genre_read_prevents_response_and_cache(self):
        artist_id = "c" * 22
        value = provider_payload()
        value["item"]["artists"][0]["id"] = artist_id
        async def request(_backend, method, path, **kwargs):
            if path.startswith("/artists"):
                self.runtime.profile_context_music_account_id = "replacement-account"
                return {"artists": [{"id": artist_id, "genres": ["synthpop"]}]}
            return value
        with patch.object(self.spotify.SpotifyBackend, "_request", request):
            with self.assertRaises(self.module.TrackInsightError) as raised:
                await self.analyze()
        self.assertEqual(raised.exception.code, "track_insight_context_changed")
        self.assertFalse(getattr(self.runtime, "track_insight_cache", {}))

    async def test_current_errors_and_capability_cover_supported_languages(self):
        current = importlib.import_module("custom_components.djconnect.current_track_insight")
        from custom_components.djconnect.capability_contract import _platform_capabilities, _contract_versions
        self.assertTrue(_platform_capabilities()["current_track_insight_subject_v1"])
        self.assertEqual(_contract_versions()["current_track_insight_subject"], 1)
        for code, labels in current._MESSAGES.items():
            self.assertEqual(set(labels), {"en", "nl", "de", "fr", "es"})
            for language, text in labels.items():
                self.assertEqual(current._error(code, language + "-region", 409).message, text)
                self.assertTrue(text.strip())

    async def test_actual_ha_current_fixture_binds_current_source_without_install_or_model_claim(self):
        import hashlib
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / "examples/client_contracts/track_insight/current-subject-v1-history-reply-artwork-20261022.json").read_text())
        for relative, digest in fixture["source_pins"].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest, relative)
        self.assertEqual(hashlib.sha256((root / fixture["harness"]).read_bytes()).hexdigest(), fixture["harness_sha256"])
        self.assertTrue(fixture["source_unchanged"])
        self.assertEqual(fixture["model_reply_fixture_calls"], 2)
        self.assertEqual((fixture["installed"], fixture["native"], fixture["model_provider_calls"], fixture["playback_mutations"]),
                         ("NOT_RUN", "NOT_RUN", 0, 0))
        self.assertEqual(set(fixture["cases"].values()), {"PASS"})
        self.assertGreaterEqual(len(fixture["cases"]), 8)

    async def test_new_account_same_recording_gets_new_source_epoch_without_transferring_nonce(self):
        first = await self.analyze()
        self.runtime.profile_context_music_account_id = "replacement-account"
        second = await self.analyze()
        self.assertEqual(first["subject"]["media_identity"], second["subject"]["media_identity"])
        self.assertNotEqual(first["subject"]["observation_id"], second["subject"]["observation_id"])
        self.assertEqual(second["source"], "current_detail")
        self.assertTrue(second["cache"]["hit"])
        self.assertFalse(self.hass.services.calls)
