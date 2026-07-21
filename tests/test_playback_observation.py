from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load_modules():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules[PACKAGE] = package

    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    const.MUSIC_BACKEND_SPOTIFY_DIRECT = "spotify_direct"
    sys.modules[f"{PACKAGE}.const"] = const

    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    event = types.ModuleType("homeassistant.helpers.event")
    scheduled: list[dict] = []

    def track_interval(hass, callback, interval):
        item = {"callback": callback, "interval": interval, "removed": False}
        scheduled.append(item)

        def remove():
            item["removed"] = True

        return remove

    event.async_track_time_interval = track_interval
    helpers.event = event
    sys.modules["homeassistant.helpers.event"] = event

    spotify = types.ModuleType(f"{PACKAGE}.spotify_backend")

    class SpotifyBackendError(RuntimeError):
        pass

    class SpotifyBackend:
        responses: list[object] = []
        calls = 0

        def __init__(self, hass, runtime):
            self.hass = hass
            self.runtime = runtime

        async def async_observe_current_playback(self):
            type(self).calls += 1
            response = type(self).responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    spotify.SpotifyBackend = SpotifyBackend
    spotify.SpotifyBackendError = SpotifyBackendError
    sys.modules[f"{PACKAGE}.spotify_backend"] = spotify

    runtime_spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.session_runtime",
        ROOT / "custom_components" / "djconnect" / "session_runtime.py",
    )
    runtime = importlib.util.module_from_spec(runtime_spec)
    sys.modules[runtime_spec.name] = runtime
    assert runtime_spec.loader is not None
    runtime_spec.loader.exec_module(runtime)

    observation_spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.playback_observation",
        ROOT / "custom_components" / "djconnect" / "playback_observation.py",
    )
    observation = importlib.util.module_from_spec(observation_spec)
    sys.modules[observation_spec.name] = observation
    assert observation_spec.loader is not None
    observation_spec.loader.exec_module(observation)
    return runtime, observation, spotify, scheduled


class PlaybackObservationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.observation, cls.spotify, cls.scheduled = _load_modules()

    @classmethod
    def tearDownClass(cls) -> None:
        for name in (
            f"{PACKAGE}.playback_observation",
            f"{PACKAGE}.session_runtime",
            f"{PACKAGE}.spotify_backend",
            f"{PACKAGE}.const",
        ):
            sys.modules.pop(name, None)

    def setUp(self) -> None:
        self.scheduled.clear()
        self.spotify.SpotifyBackend.responses = []
        self.spotify.SpotifyBackend.calls = 0
        self.hass = types.SimpleNamespace(data={})
        self.manager = self.runtime.session_runtime_manager(self.hass)
        self.observer = self.observation.playback_observation_manager(self.hass)

    def _observation(self, uri: str = "", *, playing: bool = True):
        return types.SimpleNamespace(is_playing=playing, media_identity=uri)

    async def _insight(self):
        return {
            "track": {"title": "Observed Track", "artists": ["Observed Artist"]},
            "analysis": {"summary": "Observed context."},
        }

    def _start(self, strategy=None):
        return asyncio.run(
            self.manager.async_start(
                owner_profile_id="profile-a",
                music_backend="spotify_direct",
                session_start_strategy=(strategy or self.runtime.SessionStartStrategy.MANUAL),
            )
        )

    def test_stage_one_baselines_then_processes_one_changed_uri(self) -> None:
        session = self._start()
        self.spotify.SpotifyBackend.responses = [
            self._observation("spotify:track:a"),
            self._observation("spotify:track:b"),
            self._observation("spotify:track:b"),
        ]

        asyncio.run(
            self.observer.async_start_spotify(
                integration_runtime=object(), session=session, insight_provider=self._insight
            )
        )
        active = asyncio.run(self.manager.async_get_active("profile-a"))
        self.assertEqual(active.last_accepted_media_identity, "spotify:track:a")
        self.assertEqual(len(active.moment_engine.moments), 0)

        asyncio.run(self.scheduled[0]["callback"](None))
        active = asyncio.run(self.manager.async_get_active("profile-a"))
        self.assertEqual(active.last_accepted_media_identity, "spotify:track:b")
        self.assertEqual(len(active.moment_engine.moments), 1)
        self.assertEqual(
            len(
                [
                    item
                    for item in active.planner.output.session_flow.items
                    if item.item_type is self.runtime.SessionFlowItemType.DJ_MOMENT
                ]
            ),
            1,
        )
        self.assertEqual(len(active.broadcast.state.dj_moments), 1)

        asyncio.run(self.scheduled[0]["callback"](None))
        active = asyncio.run(self.manager.async_get_active("profile-a"))
        self.assertEqual(len(active.moment_engine.moments), 1)

    def test_all_active_start_strategies_are_eligible(self) -> None:
        for strategy in self.runtime.SessionStartStrategy:
            self.setUp()
            session = self._start(strategy)
            self.spotify.SpotifyBackend.responses = [
                self._observation(f"spotify:track:{strategy.value}")
            ]
            asyncio.run(
                self.observer.async_start_spotify(
                    integration_runtime=object(), session=session, insight_provider=self._insight
                )
            )
            self.assertEqual(len(self.scheduled), 1)

    def test_no_active_or_non_spotify_session_does_not_schedule_observation(self) -> None:
        session = asyncio.run(
            self.manager.async_start(
                owner_profile_id="profile-a", music_backend="music_assistant"
            )
        )
        asyncio.run(
            self.observer.async_start_spotify(
                integration_runtime=object(), session=session, insight_provider=self._insight
            )
        )
        self.assertEqual(self.scheduled, [])
        self.assertEqual(self.spotify.SpotifyBackend.calls, 0)

    def test_pause_absence_failure_and_session_end_do_not_publish(self) -> None:
        session = self._start()
        self.spotify.SpotifyBackend.responses = [
            self._observation("spotify:track:a"),
            self._observation("spotify:track:a", playing=False),
            self.spotify.SpotifyBackendError("temporary"),
            self._observation("spotify:track:b"),
        ]
        asyncio.run(
            self.observer.async_start_spotify(
                integration_runtime=object(), session=session, insight_provider=self._insight
            )
        )
        asyncio.run(self.scheduled[0]["callback"](None))
        asyncio.run(self.scheduled[0]["callback"](None))
        active = asyncio.run(self.manager.async_get_active("profile-a"))
        self.assertEqual(active.last_accepted_media_identity, "spotify:track:a")
        self.assertEqual(len(active.moment_engine.moments), 0)

        asyncio.run(self.observer.async_stop("profile-a", session.session_id))
        asyncio.run(self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id))
        asyncio.run(self.scheduled[0]["callback"](None))
        self.assertTrue(self.scheduled[0]["removed"])
        self.assertIsNone(asyncio.run(self.manager.async_get_active("profile-a")))

    def test_overlapping_poll_is_suppressed(self) -> None:
        session = self._start()
        self.spotify.SpotifyBackend.responses = [self._observation("spotify:track:a")]
        asyncio.run(
            self.observer.async_start_spotify(
                integration_runtime=object(), session=session, insight_provider=self._insight
            )
        )
        observed = self.observer._spotify_sessions["profile-a"]

        async def poll_while_locked():
            await observed.poll_lock.acquire()
            try:
                await self.observer._async_poll_spotify(observed)
            finally:
                observed.poll_lock.release()

        asyncio.run(poll_while_locked())
        self.assertEqual(self.spotify.SpotifyBackend.calls, 1)

    def test_rolling_records_reconcile_pr_292_before_next_production_capability(self) -> None:
        for name in (
            "ENGINEERING_STATUS.md",
            "REPOSITORY_STATUS.md",
            "MANAGEMENT_SUMMARY.md",
            "PROMPT_INDEX.md",
        ):
            contents = (ROOT / name).read_text()
            self.assertIn("PR [#292]", contents)
            self.assertIn("3abc24e4b2f77f160b4b8adbc47e14e48dbc9c78", contents)

    def test_media_identity_never_enters_public_runtime_representation(self) -> None:
        session = self._start()
        self.spotify.SpotifyBackend.responses = [self._observation("spotify:track:a")]
        asyncio.run(
            self.observer.async_start_spotify(
                integration_runtime=object(), session=session, insight_provider=self._insight
            )
        )
        active = asyncio.run(self.manager.async_get_active("profile-a"))
        self.assertNotIn("last_accepted_media_identity", active.as_dict())
