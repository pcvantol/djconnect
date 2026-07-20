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
        self.assertEqual(planner.output.session_flow.planning_horizon_minutes, 15)
        public_planner = created.as_dict()["planner"]
        self.assertEqual(public_planner["planning_horizon_minutes"], 15)
        self.assertEqual(public_planner["current_direction"], "maintain")
        self.assertEqual(
            public_planner["output"]["session_flow"]["flow_id"],
            f"flow-{created.session_id}",
        )

    def test_planner_is_not_shared_between_runtimes_and_is_disposed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        self.assertIsNot(first.planner, second.planner)

    def test_runtime_creates_one_broadcast_engine_with_canonical_state(self) -> None:
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
        self.assertEqual(
            state["session_flow"],
            created.planner.output.session_flow.as_dict(),
        )
        self.assertEqual(state["audience"], {})
        self.assertTrue(state["broadcast"]["started_at"])
        self.assertEqual(created.as_dict()["broadcast"], state)

    def test_planner_creates_and_republishes_its_canonical_session_flow(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        flow = created.planner.output.session_flow
        self.assertEqual(flow.flow_id, f"flow-{created.session_id}")
        self.assertEqual(flow.planning_horizon_minutes, 15)
        self.assertEqual(
            [(item.position.value, item.item_type.value) for item in flow.items],
            [
                ("now", "current_track"),
                ("next", "planning_horizon"),
                ("next", "maintain_direction"),
                ("later", "future_direction"),
                ("later", "future_placeholder"),
            ],
        )

        republished = created.republish_session_flow()

        self.assertIs(created.planner.output.session_flow, republished)
        self.assertEqual(created.broadcast.as_dict()["session_flow"], republished.as_dict())
        self.assertTrue(created.planner.last_replan_at)

    def test_session_flow_is_not_shared_and_is_removed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))

        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        self.assertIsNot(
            first.planner.output.session_flow,
            second.planner.output.session_flow,
        )
        self.assertEqual(
            ended.broadcast.as_dict()["session_flow"]["flow_id"],
            first.planner.output.session_flow.flow_id,
        )

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

    def test_broadcast_subscription_receives_snapshot_incremental_events_and_cleanup(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        received: list[dict] = []

        subscribed = asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=received.append,
            )
        )

        self.assertIsNotNone(subscribed)
        subscription_id, snapshot = subscribed
        self.assertEqual(snapshot, created.broadcast.as_dict())
        self.assertEqual(created.broadcast.subscriber_count, 1)

        created.republish_session_flow()
        self.assertEqual(
            [event["event_type"] for event in received],
            ["planner_updated", "session_flow_updated"],
        )
        self.assertEqual(received[-1]["payload"]["session_flow"], created.broadcast.as_dict()["session_flow"])

        asyncio.run(
            manager.async_unsubscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                subscription_id=subscription_id,
            )
        )
        self.assertEqual(created.broadcast.subscriber_count, 0)

    def test_broadcast_runtime_termination_notifies_and_releases_subscriptions(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        received: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=received.append,
            )
        )

        asyncio.run(manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id))

        self.assertEqual(
            [event["event_type"] for event in received],
            ["runtime_ended", "broadcast_stopped"],
        )
        self.assertEqual(created.broadcast.subscriber_count, 0)

    def test_profile_owned_runtime_terminates_every_bound_device_subscription(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        first_events: list[dict] = []
        second_events: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=first_events.append,
            )
        )
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=second_events.append,
            )
        )

        asyncio.run(manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id))

        self.assertEqual(created.broadcast.subscriber_count, 0)
        self.assertEqual(
            [event["event_type"] for event in first_events],
            ["runtime_ended", "broadcast_stopped"],
        )
        self.assertEqual(
            [event["event_type"] for event in second_events],
            ["runtime_ended", "broadcast_stopped"],
        )

    def test_subscription_is_rejected_when_requested_runtime_belongs_to_another_profile(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-owner"))

        subscribed = asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-other",
                session_id=created.session_id,
                callback=lambda event: None,
            )
        )

        self.assertIsNone(subscribed)

    def test_broadcast_token_is_read_only_runtime_scoped_and_invalid_after_end(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-b"))
        contract = asyncio.run(
            manager.async_broadcast_token_for_owner(
                owner_profile_id="profile-a", session_id=first.session_id
            )
        )
        assert contract is not None
        token = contract["broadcast_token"]
        self.assertEqual(
            contract["capabilities"],
            {"view_broadcast": True, "like": False, "audience_signals": False, "ask_dj": False, "owner_controls": False},
        )
        self.assertNotIn("profile", contract)

        received: list[dict] = []
        self.assertIsNotNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=first.session_id, broadcast_token=token, callback=received.append
                )
            )
        )
        self.assertIsNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=second.session_id, broadcast_token=token, callback=received.append
                )
            )
        )
        self.assertIsNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=first.session_id, broadcast_token=f"{token}changed", callback=received.append
                )
            )
        )

        asyncio.run(manager.async_end(owner_profile_id="profile-a", session_id=first.session_id))
        self.assertIsNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=first.session_id, broadcast_token=token, callback=received.append
                )
            )
        )

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
