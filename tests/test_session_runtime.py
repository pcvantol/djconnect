from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load_runtime_module():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault(PACKAGE, package)
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    previous_const = sys.modules.get(f"{PACKAGE}.const")
    sys.modules[f"{PACKAGE}.const"] = const
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.session_runtime",
        ROOT / "custom_components" / "djconnect" / "session_runtime.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, previous_const


class SessionRuntimeManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop(f"{PACKAGE}.session_runtime", None)
        if cls.previous_const is None:
            sys.modules.pop(f"{PACKAGE}.const", None)
        else:
            sys.modules[f"{PACKAGE}.const"] = cls.previous_const

    def test_creates_and_looks_up_active_runtime_for_profile(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-peter",
                room="living-room",
                selected_mood="groove",
                music_backend="spotify_direct",
            )
        )
        reconnected = asyncio.run(manager.async_get_active("profile-peter"))

        self.assertEqual(created, reconnected)
        self.assertIs(created.planner, reconnected.planner)
        self.assertIs(created.broadcast, reconnected.broadcast)
        self.assertEqual(created.runtime_state, self.runtime.SessionRuntimeState.ACTIVE)
        self.assertEqual(created.owner_profile_id, "profile-peter")
        self.assertTrue(created.started_at)

    def test_runtime_creates_one_ephemeral_planner_with_foundation_defaults(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        planner = created.planner
        self.assertEqual(planner.planner_state, self.runtime.PlannerState.READY)
        self.assertEqual(planner.planning_horizon_minutes, 15)
        self.assertEqual(planner.current_direction, self.runtime.MusicalDirection.MAINTAIN)
        self.assertEqual(planner.pending_events, ())
        self.assertIsNone(planner.output.session_flow)
        public_planner = created.as_dict()["planner"]
        self.assertEqual(public_planner["planning_horizon_minutes"], 15)
        self.assertEqual(public_planner["current_direction"], "maintain")
        self.assertEqual(public_planner["output"], {"session_flow": None})

    def test_planner_is_not_shared_between_runtimes_and_is_disposed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        self.assertIsNot(first.planner, second.planner)

    def test_runtime_creates_one_broadcast_engine_with_canonical_empty_state(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(owner_profile_id="profile-peter", selected_mood="groove")
        )

        state = created.broadcast.as_dict()
        self.assertEqual(
            state["session"],
            {
                "session_id": created.session_id,
                "runtime_state": "active",
                "selected_mood": "groove",
            },
        )
        self.assertEqual(
            state["playback"],
            {
                "current_track": None,
                "playback_progress": None,
            },
        )
        self.assertEqual(state["planner"]["planning_horizon_minutes"], 15)
        self.assertEqual(state["planner"]["current_direction"], "maintain")
        self.assertEqual(state["session_flow"], {})
        self.assertEqual(state["audience"], {})
        self.assertTrue(state["broadcast"]["started_at"])
        self.assertEqual(created.as_dict()["broadcast"], state)

    def test_broadcast_engine_is_not_shared_and_is_removed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )

        self.assertEqual(ended.broadcast.as_dict()["session"]["runtime_state"], "ended")
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        self.assertIsNot(first.broadcast, second.broadcast)

    def test_broadcast_event_vocabulary_is_stable(self) -> None:
        self.assertEqual(
            [event.value for event in self.runtime.BroadcastEventType],
            [
                "runtime_created",
                "runtime_ended",
                "playback_changed",
                "playback_progress",
                "planner_updated",
                "mood_changed",
                "track_changed",
                "session_flow_updated",
                "audience_updated",
                "broadcast_started",
                "broadcast_stopped",
            ],
        )

    def test_rejects_second_active_runtime_for_same_profile(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        with self.assertRaises(self.runtime.ActiveSessionExistsError):
            asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

    def test_ends_and_disposes_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id)
        )

        self.assertEqual(ended.runtime_state, self.runtime.SessionRuntimeState.ENDED)
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))


if __name__ == "__main__":
    unittest.main()
