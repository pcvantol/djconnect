from __future__ import annotations

import asyncio
import importlib
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


install_http_stubs()
api_handlers = importlib.import_module("custom_components.djconnect.api_handlers")
http = importlib.import_module("custom_components.djconnect.http")


class OwnerBroadcastSnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = types.SimpleNamespace()
        self.context = types.SimpleNamespace(profile_id="profile-owner")
        self.snapshot = {
            "session": {"session_id": "session-1", "runtime_state": "active"},
            "planner": {"session_direction": {"direction": "exploring"}},
            "session_flow": {"flow_id": "flow-session-1", "items": []},
            "dj_moments": [
                {
                    "moment_id": "moment-1",
                    "moment_type": "recommendation",
                    "presentation_intent": {"source_session_mood": "groove"},
                }
            ],
        }
        self.snapshot_calls = 0
        self.active = types.SimpleNamespace(
            session_id="session-1",
            broadcast=types.SimpleNamespace(as_dict=self._snapshot),
        )
        self.manager = types.SimpleNamespace(
            async_get_active=self._active,
            async_subscribe=self._subscribe,
            async_register_subscription=self._register_subscription,
            async_register_pending_subscription=self._register_pending_subscription,
            async_activate_subscription=self._activate_subscription,
            async_unsubscribe=self._unsubscribe,
        )
        self.get_active_calls = 0
        self.subscribe_calls = 0
        self.register_calls = 0
        self.pending_register_calls = 0
        self.activate_calls = 0
        self.unsubscribe_calls = 0
        self.registered_callback = None
        self.pending_events = []
        self.emit_during_snapshot = None
        self.registration_result = "subscription-1"
        self.originals = {
            "resolve_runtime": api_handlers.resolve_runtime,
            "authorize": api_handlers.authorize_runtime_device_request,
            "resolve_context": api_handlers.async_resolve_device_bound_request_context,
            "manager": api_handlers.session_runtime_manager,
        }
        api_handlers.resolve_runtime = lambda *args, **kwargs: self.runtime
        api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: True
        api_handlers.async_resolve_device_bound_request_context = self._context
        api_handlers.session_runtime_manager = lambda hass: self.manager

    def tearDown(self) -> None:
        api_handlers.resolve_runtime = self.originals["resolve_runtime"]
        api_handlers.authorize_runtime_device_request = self.originals["authorize"]
        api_handlers.async_resolve_device_bound_request_context = self.originals["resolve_context"]
        api_handlers.session_runtime_manager = self.originals["manager"]

    async def _active(self, profile_id: str):
        self.get_active_calls += 1
        return self.active if profile_id == "profile-owner" else None

    async def _subscribe(self, **kwargs):
        self.subscribe_calls += 1
        return "subscription-1", self.snapshot

    async def _register_subscription(self, *, callback, **kwargs):
        self.register_calls += 1
        if self.registration_result is None:
            return None
        self.registered_callback = callback
        return self.registration_result

    async def _register_pending_subscription(self, *, callback, **kwargs):
        self.pending_register_calls += 1
        if self.registration_result is None:
            return None
        self.registered_callback = callback
        return self.registration_result

    async def _activate_subscription(self, **kwargs):
        self.activate_calls += 1
        assert self.registered_callback is not None
        for event in self.pending_events:
            self.registered_callback(event)
        self.pending_events.clear()

    async def _unsubscribe(self, **kwargs):
        self.unsubscribe_calls += 1
        self.registered_callback = None
        self.pending_events.clear()
        return None

    def _snapshot(self):
        self.snapshot_calls += 1
        if self.emit_during_snapshot is not None:
            self.pending_events.append(self.emit_during_snapshot)
        return self.snapshot

    async def _context(self, *args, **kwargs):
        return self.context

    @staticmethod
    def _payload(session_id: str = "session-1") -> dict[str, str]:
        return {
            "session_id": session_id,
            "device_id": "djconnect-ios-ABCDEFGHIJKL",
            "client_type": "ios",
        }

    def test_owner_http_snapshot_reuses_broadcast_projection_without_subscription(self) -> None:
        result, status = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(
                object(), self._payload()
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual(result, {"success": True, "session_id": "session-1", "snapshot": self.snapshot})
        self.assertEqual(self.subscribe_calls, 0)
        self.assertEqual(self.register_calls, 0)
        self.assertEqual(self.get_active_calls, 2)
        self.assertNotIn("owner_profile_id", result["snapshot"])
        self.assertNotIn("performance_memory", result["snapshot"])

    def test_http_view_maps_the_exact_session_to_the_owner_snapshot_handler(self) -> None:
        request = types.SimpleNamespace(
            query={
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
            },
            headers={},
            app={"hass": object()},
            context=types.SimpleNamespace(user_id="ha-owner"),
        )
        result = asyncio.run(
            http.DJConnectSessionBroadcastSnapshotView(object()).get(request, "session-1")
        )

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["payload"]["snapshot"], self.snapshot)
        self.assertEqual(self.subscribe_calls, 0)
        self.assertEqual(self.register_calls, 0)

    def test_http_and_websocket_initial_snapshots_are_equivalent(self) -> None:
        http_result, http_status = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(
                object(), self._payload()
            )
        )

        received = []
        websocket_result, websocket_status, activate, cleanup = asyncio.run(
            api_handlers.async_handle_session_broadcast_subscribe_payload(
                object(), self._payload(), callback=received.append
            )
        )

        self.assertEqual(http_status, 200)
        self.assertEqual(websocket_status, 200)
        self.assertEqual(http_result["snapshot"], websocket_result["snapshot"])
        self.assertEqual(self.subscribe_calls, 0)
        self.assertEqual(self.pending_register_calls, 1)
        self.assertEqual(received, [])
        assert activate is not None
        asyncio.run(activate())
        self.assertEqual(self.activate_calls, 1)
        assert cleanup is not None
        asyncio.run(cleanup())
        self.assertEqual(self.unsubscribe_calls, 1)

    def test_websocket_constructs_one_snapshot_and_registers_live_delivery_once(self) -> None:
        received = []
        self.emit_during_snapshot = {
            "event_type": "session_flow_updated",
            "session_id": "session-1",
        }
        result, status, activate, cleanup = asyncio.run(
            api_handlers.async_handle_session_broadcast_subscribe_payload(
                object(), self._payload(), callback=received.append
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual(result["snapshot"], self.snapshot)
        self.assertEqual(self.snapshot_calls, 1)
        self.assertEqual(self.subscribe_calls, 0)
        self.assertEqual(self.pending_register_calls, 1)
        assert self.registered_callback is not None
        self.assertEqual(received, [])
        assert activate is not None
        asyncio.run(activate())
        self.assertEqual(received, [self.emit_during_snapshot])
        assert cleanup is not None
        asyncio.run(cleanup())
        asyncio.run(cleanup())
        self.assertEqual(self.unsubscribe_calls, 2)

    def test_snapshot_rejects_unknown_or_unauthorized_or_inactive_requests(self) -> None:
        api_handlers.resolve_runtime = lambda *args, **kwargs: None
        result, status = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(object(), self._payload())
        )
        self.assertEqual((result["error"], status), ("not_configured", 503))

        api_handlers.resolve_runtime = lambda *args, **kwargs: self.runtime
        api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: False
        result, status = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(object(), self._payload())
        )
        self.assertEqual((result["error"], status), ("unauthorized", 401))

        api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: True
        result, status = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(
                object(), self._payload("other-session")
            )
        )
        self.assertEqual((result["error"], status), ("active_session_not_found", 404))

        result, status, activate, cleanup = asyncio.run(
            api_handlers.async_handle_session_broadcast_subscribe_payload(
                object(), self._payload("other-session"), callback=lambda event: None
            )
        )
        self.assertEqual((result["error"], status, activate, cleanup), ("active_session_not_found", 404, None, None))
        self.assertEqual(self.pending_register_calls, 0)

        api_handlers.authorize_runtime_device_request = lambda *args, **kwargs: False
        result, status, activate, cleanup = asyncio.run(
            api_handlers.async_handle_session_broadcast_subscribe_payload(
                object(), self._payload(), callback=lambda event: None
            )
        )
        self.assertEqual((result["error"], status, activate, cleanup), ("unauthorized", 401, None, None))
        self.assertEqual(self.pending_register_calls, 0)

    def test_snapshot_query_or_registration_failure_never_retains_a_callback(self) -> None:
        def unavailable_snapshot():
            raise RuntimeError("unavailable")

        self.active.broadcast.as_dict = unavailable_snapshot
        result, status, activate, cleanup = asyncio.run(
            api_handlers.async_handle_session_broadcast_subscribe_payload(
                object(), self._payload(), callback=lambda event: None
            )
        )
        self.assertEqual((result["error"], status, activate, cleanup), ("broadcast_snapshot_unavailable", 500, None, None))
        self.assertEqual(self.pending_register_calls, 1)
        self.assertEqual(self.unsubscribe_calls, 1)
        self.assertIsNone(self.registered_callback)

        self.active.broadcast.as_dict = self._snapshot
        self.registration_result = None
        result, status, activate, cleanup = asyncio.run(
            api_handlers.async_handle_session_broadcast_subscribe_payload(
                object(), self._payload(), callback=lambda event: None
            )
        )
        self.assertEqual((result["error"], status, activate, cleanup), ("active_session_not_found", 404, None, None))
        self.assertEqual(self.pending_register_calls, 2)
        self.assertIsNone(self.registered_callback)

    def test_repeated_http_snapshot_requests_are_side_effect_free(self) -> None:
        first = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(object(), self._payload())
        )
        second = asyncio.run(
            api_handlers.async_handle_session_broadcast_snapshot_payload(object(), self._payload())
        )

        self.assertEqual(first, second)
        self.assertEqual(self.subscribe_calls, 0)
        self.assertEqual(self.register_calls, 0)
        self.assertEqual(self.snapshot["session_flow"]["items"], [])
