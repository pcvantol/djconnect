from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class DJConnectWebsocketApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        package = types.ModuleType("custom_components.djconnect")
        package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
        sys.modules.setdefault("custom_components.djconnect", package)
        voluptuous = types.ModuleType("voluptuous")
        voluptuous.Required = lambda key: key
        voluptuous.Optional = lambda key, default=None: key
        sys.modules["voluptuous"] = voluptuous
        websocket_api = types.ModuleType("homeassistant.components.websocket_api")
        websocket_api.async_register_command = lambda hass, command: None
        websocket_api.websocket_command = lambda schema: lambda func: func
        websocket_api.async_response = lambda func: func
        homeassistant = types.ModuleType("homeassistant")
        components = types.ModuleType("homeassistant.components")
        components.websocket_api = websocket_api
        homeassistant.components = components
        sys.modules["homeassistant"] = homeassistant
        sys.modules["homeassistant.components"] = components
        sys.modules["homeassistant.components.websocket_api"] = websocket_api
        const = types.ModuleType("custom_components.djconnect.const")
        const.DOMAIN = "djconnect"
        const.VERSION = "3.2.1"
        sys.modules.setdefault("custom_components.djconnect.const", const)
        http = types.ModuleType("custom_components.djconnect.http")

        async def async_handle_command_payload(*args, **kwargs):
            return {"success": True}, 200

        http.async_handle_command_payload = async_handle_command_payload
        http.async_handle_ask_dj_message_payload = async_handle_command_payload
        http.async_handle_ask_dj_history_payload = async_handle_command_payload
        http.async_handle_ask_dj_history_clear_payload = async_handle_command_payload
        http.async_handle_ask_dj_history_state_payload = async_handle_command_payload
        http.async_handle_ask_dj_idle_suggestion_payload = async_handle_command_payload
        http.async_handle_track_insight_payload = async_handle_command_payload
        http.async_handle_music_dna_profile_payload = async_handle_command_payload
        http.async_handle_music_dna_settings_payload = async_handle_command_payload
        http.async_handle_music_dna_clear_payload = async_handle_command_payload
        http.async_handle_music_dna_import_payload = async_handle_command_payload
        http.async_handle_music_dna_export_payload = async_handle_command_payload
        sys.modules.setdefault("custom_components.djconnect.http", http)
        cls.websocket_api = importlib.import_module("custom_components.djconnect.websocket_api")
        cls.websocket_api.websocket_api = websocket_api

    @classmethod
    def tearDownClass(cls) -> None:
        for module_name in (
            "custom_components.djconnect.websocket_api",
            "custom_components.djconnect.http",
            "custom_components.djconnect.const",
            "homeassistant.components.websocket_api",
        ):
            sys.modules.pop(module_name, None)

    def test_registers_commands_once(self) -> None:
        calls = []
        hass = types.SimpleNamespace(data={})
        original = self.websocket_api.websocket_api.async_register_command
        self.websocket_api.websocket_api.async_register_command = lambda hass_arg, command: calls.append(command)
        try:
            self.websocket_api.async_register(hass)
            self.websocket_api.async_register(hass)
        finally:
            self.websocket_api.websocket_api.async_register_command = original
        self.assertEqual(
            [command.__name__ for command in calls],
            [
                "websocket_capabilities",
                "websocket_command",
                "websocket_ask_dj_message",
                "websocket_ask_dj_history",
                "websocket_ask_dj_history_clear",
                "websocket_ask_dj_history_state",
                "websocket_ask_dj_idle_suggestion",
                "websocket_track_insight",
                "websocket_music_dna_profile",
                "websocket_music_dna_settings",
                "websocket_music_dna_clear",
                "websocket_music_dna_import",
                "websocket_music_dna_export",
                "websocket_music_discovery_feed",
                "websocket_music_discovery_refresh",
                "websocket_music_discovery_play",
                "websocket_music_discovery_feedback",
                "websocket_session_broadcast_subscribe",
            ],
        )
        self.assertTrue(hass.data["djconnect"]["websocket_registered"])

    def test_register_is_noop_without_home_assistant_websocket_api(self) -> None:
        hass = types.SimpleNamespace(data={})
        original = self.websocket_api.websocket_api
        self.websocket_api.websocket_api = None
        try:
            self.websocket_api.async_register(hass)
        finally:
            self.websocket_api.websocket_api = original
        self.assertEqual(hass.data, {})

    def test_capabilities_response_advertises_fast_path(self) -> None:
        connection = _Connection()
        asyncio.run(
            self.websocket_api.websocket_capabilities(
                types.SimpleNamespace(data={}),
                connection,
                {"id": 3, "type": self.websocket_api.WS_TYPE_CAPABILITIES},
            )
        )
        self.assertEqual(connection.errors, [])
        msg_id, result = connection.results[0]
        self.assertEqual(msg_id, 3)
        self.assertTrue(result["success"])
        self.assertTrue(result["websocket_supported"])
        self.assertEqual(result["domain"], "djconnect")
        self.assertIn(self.websocket_api.WS_TYPE_COMMAND, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_ASK_DJ_MESSAGE, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_ASK_DJ_HISTORY, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_ASK_DJ_HISTORY_CLEAR, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_ASK_DJ_HISTORY_STATE, result["commands"])
        self.assertNotIn("djconnect/ask_dj/history/export", result["commands"])
        self.assertFalse(hasattr(self.websocket_api, "WS_TYPE_ASK_DJ_HISTORY_EXPORT"))
        self.assertIn(self.websocket_api.WS_TYPE_ASK_DJ_IDLE_SUGGESTION, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_TRACK_INSIGHT, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DNA_PROFILE, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DNA_SETTINGS, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DNA_CLEAR, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DNA_IMPORT, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DNA_EXPORT, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEED, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_REFRESH, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_PLAY, result["commands"])
        self.assertIn(self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEEDBACK, result["commands"])
        self.assertTrue(result["features"]["music_dna"])
        self.assertTrue(result["features"]["music_discovery"])
        self.assertTrue(result["features"]["music_discovery_feedback"])
        self.assertEqual(
            result["fallbacks"]["music_discovery"]["http_paths"]["feed"],
            "/api/djconnect/v1/music_discovery",
        )
        self.assertEqual(
            result["fallbacks"]["music_dna"]["http_paths"]["import"],
            "/api/djconnect/v1/music_dna/import",
        )
        self.assertEqual(
            result["fallbacks"]["music_dna"]["http_paths"]["export"],
            "/api/djconnect/v1/music_dna/export",
        )
        self.assertEqual(
            result["fallbacks"]["music_discovery_feedback"]["missing_behavior"],
            "hide_negative_feedback_controls",
        )
        self.assertEqual(result["transports"], {"http": True, "websocket": True})
        self.assertEqual(
            result["fallbacks"]["session_broadcast_transport"]["http_snapshot_path"],
            "/api/djconnect/v1/session/broadcast/{session_id}",
        )
        self.assertTrue(result["fallbacks"]["session_broadcast_transport"]["snapshot_only"])
        self.assertFalse(result["fallbacks"]["session_broadcast_transport"]["flow_delta"])

    def test_session_broadcast_subscription_sends_snapshot_then_incremental_events(self) -> None:
        calls = []
        cleanup_called = []

        async def subscribe_handler(hass, payload, *, callback, headers=None, user_id=None):
            calls.append((payload, headers, user_id))

            async def activate():
                callback(
                    {
                        "event_type": "session_flow_updated",
                        "session_id": "session-1",
                        "payload": {"session_flow": {"flow_id": "flow-session-1"}},
                    }
                )

            async def cleanup():
                cleanup_called.append(True)

            return {
                "success": True,
                "subscription_id": "subscription-1",
                "session_id": "session-1",
                "snapshot": {"session": {"session_id": "session-1"}},
            }, 200, activate, cleanup

        original = self.websocket_api.async_handle_session_broadcast_subscribe_payload
        self.websocket_api.async_handle_session_broadcast_subscribe_payload = subscribe_handler
        try:
            connection = _Connection(user_id="ha-owner")
            asyncio.run(
                self.websocket_api.websocket_session_broadcast_subscribe(
                    types.SimpleNamespace(data={}, async_create_task=lambda task: task.close()),
                    connection,
                    {
                        "id": 48,
                        "type": self.websocket_api.WS_TYPE_SESSION_BROADCAST_SUBSCRIBE,
                        "session_id": "session-1",
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_session_broadcast_subscribe_payload = original

        self.assertEqual(connection.errors, [])
        self.assertEqual(connection.results[0][1]["snapshot"]["session"]["session_id"], "session-1")
        self.assertEqual(
            connection.events,
            [("djconnect/session/broadcast", {"event_type": "session_flow_updated", "session_id": "session-1", "payload": {"session_flow": {"flow_id": "flow-session-1"}}})],
        )
        self.assertEqual(calls[0][0]["session_id"], "session-1")
        self.assertEqual(calls[0][2], "ha-owner")
        self.assertEqual(len(connection.close_callbacks), 1)
        self.assertEqual(cleanup_called, [])
        self.assertEqual(connection.delivery_order, ["result", "event"])

    def test_session_broadcast_subscription_cleans_up_when_initial_response_fails(self) -> None:
        cleanup_called = []

        async def subscribe_handler(*args, **kwargs):
            async def cleanup():
                cleanup_called.append(True)

            return {
                "success": True,
                "subscription_id": "subscription-1",
                "session_id": "session-1",
                "snapshot": {"session": {"session_id": "session-1"}},
            }, 200, None, cleanup

        original = self.websocket_api.async_handle_session_broadcast_subscribe_payload
        self.websocket_api.async_handle_session_broadcast_subscribe_payload = subscribe_handler
        try:
            connection = _FailingResultConnection(user_id="ha-owner")
            with self.assertRaises(RuntimeError):
                asyncio.run(
                    self.websocket_api.websocket_session_broadcast_subscribe(
                        types.SimpleNamespace(data={}, async_create_task=lambda task: task.close()),
                        connection,
                        {
                            "id": 49,
                            "type": self.websocket_api.WS_TYPE_SESSION_BROADCAST_SUBSCRIBE,
                            "session_id": "session-1",
                            "device_id": "djconnect-ios-ABCDEF123456",
                            "client_type": "ios",
                        },
                    )
                )
        finally:
            self.websocket_api.async_handle_session_broadcast_subscribe_payload = original

        self.assertEqual(cleanup_called, [True])
        self.assertEqual(connection.close_callbacks, [])

    def test_backend_capability_fallbacks_degrade_when_command_is_missing(self) -> None:
        commands = [
            command
            for command in self.websocket_api._supported_websocket_commands()
            if command != self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEEDBACK
        ]

        features = self.websocket_api._feature_capabilities(commands)
        fallbacks = self.websocket_api._capability_fallbacks(commands)

        self.assertTrue(features["music_discovery"])
        self.assertFalse(features["music_discovery_feedback"])
        self.assertEqual(fallbacks["music_discovery_feedback"]["preferred_transport"], "http")
        self.assertEqual(
            fallbacks["music_discovery_feedback"]["http_path"],
            "/api/djconnect/v1/music_discovery/feedback",
        )
        self.assertEqual(
            fallbacks["music_discovery_feedback"]["missing_behavior"],
            "hide_negative_feedback_controls",
        )

    def test_music_discovery_websocket_routes_match_http_contract(self) -> None:
        calls = []

        async def feed_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("feed", payload, headers, user_id))
            return {"success": True, "enabled": True, "sections": []}, 200

        async def play_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("play", payload, headers, user_id))
            return {"success": True, "played": True, "music_dna_feedback_recorded": True}, 200

        async def feedback_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("feedback", payload, headers, user_id))
            return {"success": True, "feedback": payload["feedback"], "music_dna_feedback_recorded": True}, 200

        originals = (
            self.websocket_api.async_handle_music_discovery_feed_payload,
            self.websocket_api.async_handle_music_discovery_play_payload,
            self.websocket_api.async_handle_music_discovery_feedback_payload,
        )
        self.websocket_api.async_handle_music_discovery_feed_payload = feed_handler
        self.websocket_api.async_handle_music_discovery_play_payload = play_handler
        self.websocket_api.async_handle_music_discovery_feedback_payload = feedback_handler
        try:
            connection = _Connection(user_id="user-discovery")
            base = {
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
                "device_token": "device-secret",
                "music_dna_key": "user:ha-user-1",
            }
            asyncio.run(
                self.websocket_api.websocket_music_discovery_feed(
                    types.SimpleNamespace(data={}),
                    connection,
                    {"id": 21, "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEED, **base},
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_discovery_play(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 22,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_PLAY,
                        **base,
                        "section_id": "new_for_you",
                        "discovery_item_id": "disc-1",
                    },
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_discovery_feedback(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 23,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEEDBACK,
                        **base,
                        "section_id": "new_for_you",
                        "discovery_item_id": "disc-1",
                        "feedback": "not_for_me",
                    },
                )
            )
        finally:
            (
                self.websocket_api.async_handle_music_discovery_feed_payload,
                self.websocket_api.async_handle_music_discovery_play_payload,
                self.websocket_api.async_handle_music_discovery_feedback_payload,
            ) = originals

        self.assertEqual(connection.errors, [])
        self.assertEqual([msg_id for msg_id, _ in connection.results], [21, 22, 23])
        self.assertEqual([call[0] for call in calls], ["feed", "play", "feedback"])
        for _, payload, headers, user_id in calls:
            self.assertEqual(payload["device_id"], "djconnect-ios-ABCDEF123456")
            self.assertEqual(payload["client_type"], "ios")
            self.assertEqual(payload["music_dna_key"], "user:ha-user-1")
            self.assertEqual(headers["Authorization"], "Bearer device-secret")
            self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-ios-ABCDEF123456")
            self.assertEqual(user_id, "user-discovery")
        self.assertEqual(calls[1][1]["discovery_item_id"], "disc-1")
        self.assertEqual(calls[2][1]["feedback"], "not_for_me")

    def test_command_uses_device_token_and_device_id_headers(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "command": payload["command"]}, 200

        connection = _Connection(user_id="user-1")
        original = self.websocket_api.async_handle_command_payload
        self.websocket_api.async_handle_command_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_command(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 7,
                        "type": self.websocket_api.WS_TYPE_COMMAND,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "device_token": "device-secret",
                        "command": "next",
                        "client_type": "ios",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_command_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["command"], "next")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-ios-ABCDEF123456")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(user_id, "user-1")
        self.assertEqual(connection.results, [(7, {"success": True, "command": "next"})])
        self.assertEqual(connection.errors, [])

    def test_command_preserves_payload_values_over_top_level_defaults(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers))
            return {"success": True, "value": payload["value"]}, 200

        connection = _Connection()
        original = self.websocket_api.async_handle_command_payload
        self.websocket_api.async_handle_command_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_command(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 9,
                        "type": self.websocket_api.WS_TYPE_COMMAND,
                        "device_id": "djconnect-ios-TOPLEVEL1234",
                        "client_type": "ios",
                        "command": "next",
                        "value": "top-level",
                        "payload": {
                            "device_id": "djconnect-ios-PAYLOAD12345",
                            "client_type": "ios",
                            "command": "set_repeat",
                            "value": "context",
                        },
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_command_payload = original
        payload, headers = calls[0]
        self.assertEqual(payload["device_id"], "djconnect-ios-PAYLOAD12345")
        self.assertEqual(payload["command"], "set_repeat")
        self.assertEqual(payload["value"], "context")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-ios-PAYLOAD12345")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(connection.results, [(9, {"success": True, "value": "context"})])

    def test_command_accepts_existing_bearer_authorization(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append(headers)
            return {"success": True}, 200

        connection = _Connection()
        original = self.websocket_api.async_handle_command_payload
        self.websocket_api.async_handle_command_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_command(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 10,
                        "type": self.websocket_api.WS_TYPE_COMMAND,
                        "payload": {
                            "device_id": "djconnect-windows-ABCDEF123456",
                            "client_type": "windows",
                            "command": "status",
                        },
                        "authorization": "Bearer existing-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_command_payload = original
        self.assertEqual(calls[0]["Authorization"], "Bearer existing-secret")

    def test_command_wraps_plain_authorization_as_bearer(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append(headers)
            return {"success": True}, 200

        connection = _Connection()
        original = self.websocket_api.async_handle_command_payload
        self.websocket_api.async_handle_command_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_command(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 11,
                        "type": self.websocket_api.WS_TYPE_COMMAND,
                        "payload": {
                            "device_id": "djconnect-raspberry-pi-ABCDEF123456",
                            "client_type": "raspberry_pi",
                            "command": "status",
                            "authorization": "plain-secret",
                        },
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_command_payload = original
        self.assertEqual(calls[0]["Authorization"], "Bearer plain-secret")

    def test_command_sends_websocket_error_for_failed_payload(self) -> None:
        async def handler(hass, payload, *, headers=None, user_id=None):
            return {"success": False, "error": "unauthorized", "message": "Nope."}, 401

        connection = _Connection()
        original = self.websocket_api.async_handle_command_payload
        self.websocket_api.async_handle_command_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_command(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 8,
                        "type": self.websocket_api.WS_TYPE_COMMAND,
                        "payload": {"command": "status", "client_type": "ios"},
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_command_payload = original
        self.assertEqual(connection.results, [])
        self.assertEqual(connection.errors, [(8, "unauthorized", "Nope.")])

    def test_command_sends_default_error_when_payload_has_no_message(self) -> None:
        async def handler(hass, payload, *, headers=None, user_id=None):
            return {"success": False, "error": "backend_unavailable"}, 503

        connection = _Connection()
        original = self.websocket_api.async_handle_command_payload
        self.websocket_api.async_handle_command_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_command(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 12,
                        "type": self.websocket_api.WS_TYPE_COMMAND,
                        "payload": {"command": "status", "client_type": "ios"},
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_command_payload = original
        self.assertEqual(connection.results, [])
        self.assertEqual(connection.errors, [(12, "backend_unavailable", "backend_unavailable")])

    def test_ask_dj_message_route_uses_history_sync_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "history_revision": 42}, 200

        connection = _Connection(user_id="user-ask")
        original = self.websocket_api.async_handle_ask_dj_message_payload
        self.websocket_api.async_handle_ask_dj_message_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_ask_dj_message(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 13,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_MESSAGE,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                        "client_message_id": "msg-1",
                        "text": "Wat draait er?",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_ask_dj_message_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["text"], "Wat draait er?")
        self.assertEqual(payload["client_message_id"], "msg-1")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(user_id, "user-ask")
        self.assertEqual(connection.results, [(13, {"success": True, "history_revision": 42})])

    def test_ask_dj_message_route_accepts_nested_identity(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "history_revision": 43}, 200

        connection = _Connection(user_id="user-ask")
        original = self.websocket_api.async_handle_ask_dj_message_payload
        self.websocket_api.async_handle_ask_dj_message_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_ask_dj_message(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 14,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_MESSAGE,
                        "identity": {
                            "device_id": "djconnect-macos-ABCDEF123456",
                            "client_id": "djconnect-macos-ABCDEF123456",
                            "client_type": "macos",
                            "device_name": "DJConnect Mac",
                            "client_token": "device-secret",
                        },
                        "client_message_id": "msg-2",
                        "text": "Wat draait er?",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_ask_dj_message_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["identity"]["client_type"], "macos")
        self.assertEqual(payload["text"], "Wat draait er?")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(user_id, "user-ask")
        self.assertEqual(connection.results, [(14, {"success": True, "history_revision": 43})])

    def test_track_insight_route_uses_websocket_source(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, source="http"):
            calls.append((payload, headers, source))
            return {"success": True, "type": "track_insight"}, 200

        connection = _Connection()
        original = self.websocket_api.async_handle_track_insight_payload
        self.websocket_api.async_handle_track_insight_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_track_insight(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 14,
                        "type": self.websocket_api.WS_TYPE_TRACK_INSIGHT,
                        "payload": {
                            "device_id": "djconnect-macos-ABCDEF123456",
                            "client_type": "macos",
                            "title": "Windowlicker",
                            "artist": "Aphex Twin",
                        },
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_track_insight_payload = original
        payload, headers, source = calls[0]
        self.assertEqual(payload["title"], "Windowlicker")
        self.assertEqual(payload["artist"], "Aphex Twin")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(source, "websocket")
        self.assertEqual(connection.results, [(14, {"success": True, "type": "track_insight"})])

    def test_track_insight_route_preserves_client_track_aliases(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, source="http"):
            calls.append((payload, headers, source))
            return {"success": True, "type": "track_insight"}, 200

        connection = _Connection()
        original = self.websocket_api.async_handle_track_insight_payload
        self.websocket_api.async_handle_track_insight_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_track_insight(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 15,
                        "type": self.websocket_api.WS_TYPE_TRACK_INSIGHT,
                        "device_id": "djconnect-macos-ABCDEF123456",
                        "client_type": "macos",
                        "device_token": "device-secret",
                        "track_name": "Windowlicker",
                        "artist_name": "Aphex Twin",
                        "album_name": "Windowlicker",
                        "backend": "spotify_direct",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_track_insight_payload = original
        payload, headers, source = calls[0]
        self.assertEqual(payload["track_name"], "Windowlicker")
        self.assertEqual(payload["artist_name"], "Aphex Twin")
        self.assertEqual(payload["album_name"], "Windowlicker")
        self.assertEqual(payload["backend"], "spotify_direct")
        self.assertEqual(source, "websocket")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(connection.results, [(15, {"success": True, "type": "track_insight"})])

    def test_track_insight_route_accepts_nested_identity(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, source="http"):
            calls.append((payload, headers, source))
            return {"success": True, "type": "track_insight"}, 200

        connection = _Connection()
        original = self.websocket_api.async_handle_track_insight_payload
        self.websocket_api.async_handle_track_insight_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_track_insight(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 16,
                        "type": self.websocket_api.WS_TYPE_TRACK_INSIGHT,
                        "identity": {
                            "device_id": "djconnect-macos-ABCDEF123456",
                            "client_id": "djconnect-macos-ABCDEF123456",
                            "client_type": "macos",
                            "device_name": "DJConnect Mac",
                            "device_token": "device-secret",
                        },
                        "track_name": "Windowlicker",
                        "artist_name": "Aphex Twin",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_track_insight_payload = original
        payload, headers, source = calls[0]
        self.assertEqual(payload["identity"]["client_type"], "macos")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(source, "websocket")
        self.assertEqual(connection.results, [(16, {"success": True, "type": "track_insight"})])

    def test_ask_dj_history_route_uses_history_sync_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "history_revision": 9, "messages": []}, 200

        connection = _Connection(user_id="user-history")
        original = self.websocket_api.async_handle_ask_dj_history_payload
        self.websocket_api.async_handle_ask_dj_history_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_ask_dj_history(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 15,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_HISTORY,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                        "since_revision": 8,
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_ask_dj_history_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["since_revision"], 8)
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(user_id, "user-history")
        self.assertEqual(connection.results[0][1]["history_revision"], 9)

    def test_ask_dj_history_clear_route_uses_clear_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "clear_revision": 3}, 200

        connection = _Connection(user_id="user-clear")
        original = self.websocket_api.async_handle_ask_dj_history_clear_payload
        self.websocket_api.async_handle_ask_dj_history_clear_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_ask_dj_history_clear(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 16,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_HISTORY_CLEAR,
                        "payload": {
                            "device_id": "djconnect-macos-ABCDEF123456",
                            "client_type": "macos",
                            "client_id": "djconnect-macos-ABCDEF123456",
                            "device_name": "DJConnect Mac",
                        },
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_ask_dj_history_clear_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["client_type"], "macos")
        self.assertEqual(payload["client_id"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(payload["device_name"], "DJConnect Mac")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(user_id, "user-clear")
        self.assertEqual(connection.results, [(16, {"success": True, "clear_revision": 3})])

    def test_ask_dj_history_state_route_uses_state_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "ask_dj_clear_required": True}, 200

        connection = _Connection(user_id="user-state")
        original = self.websocket_api.async_handle_ask_dj_history_state_payload
        self.websocket_api.async_handle_ask_dj_history_state_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_ask_dj_history_state(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 17,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_HISTORY_STATE,
                        "device_id": "djconnect-watchos-ABCDEF123456",
                        "client_type": "watchos",
                        "device_token": "device-secret",
                        "since_revision": 12,
                        "clear_revision": 1,
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_ask_dj_history_state_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["since_revision"], 12)
        self.assertEqual(payload["clear_revision"], 1)
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-watchos-ABCDEF123456")
        self.assertEqual(user_id, "user-state")
        self.assertEqual(connection.results, [(17, {"success": True, "ask_dj_clear_required": True})])

    def test_music_dna_profile_route_uses_profile_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "enabled": True, "profile": {}}, 200

        connection = _Connection(user_id="user-dna")
        original = self.websocket_api.async_handle_music_dna_profile_payload
        self.websocket_api.async_handle_music_dna_profile_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_music_dna_profile(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 18,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_PROFILE,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                        "music_dna_key": "user:ha-user",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_profile_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["music_dna_key"], "user:ha-user")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(user_id, "user-dna")
        self.assertEqual(connection.results, [(18, {"success": True, "enabled": True, "profile": {}})])

    def test_ask_dj_idle_suggestion_route_uses_idle_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "origin": "idle_suggestion"}, 200

        connection = _Connection(user_id="user-idle")
        original = self.websocket_api.async_handle_ask_dj_idle_suggestion_payload
        self.websocket_api.async_handle_ask_dj_idle_suggestion_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_ask_dj_idle_suggestion(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 21,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_IDLE_SUGGESTION,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                        "music_dna_key": "user:ha-user",
                        "mood": 72,
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_ask_dj_idle_suggestion_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["music_dna_key"], "user:ha-user")
        self.assertEqual(payload["mood"], 72)
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(user_id, "user-idle")
        self.assertEqual(connection.results, [(21, {"success": True, "origin": "idle_suggestion"})])

    def test_music_dna_settings_route_uses_settings_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "enabled": bool(payload["enabled"])}, 200

        connection = _Connection(user_id="user-dna")
        original = self.websocket_api.async_handle_music_dna_settings_payload
        self.websocket_api.async_handle_music_dna_settings_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_music_dna_settings(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 19,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_SETTINGS,
                        "payload": {
                            "device_id": "djconnect-macos-ABCDEF123456",
                            "client_type": "macos",
                            "enabled": True,
                        },
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_settings_payload = original
        payload, headers, user_id = calls[0]
        self.assertTrue(payload["enabled"])
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(user_id, "user-dna")
        self.assertEqual(connection.results, [(19, {"success": True, "enabled": True})])

    def test_music_dna_clear_route_uses_clear_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "enabled": False, "profile": {}}, 200

        connection = _Connection(user_id="user-dna")
        original = self.websocket_api.async_handle_music_dna_clear_payload
        self.websocket_api.async_handle_music_dna_clear_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_music_dna_clear(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 20,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_CLEAR,
                        "device_id": "djconnect-watchos-ABCDEF123456",
                        "client_type": "watchos",
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_clear_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["client_type"], "watchos")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-watchos-ABCDEF123456")
        self.assertEqual(user_id, "user-dna")
        self.assertEqual(connection.results, [(20, {"success": True, "enabled": False, "profile": {}})])

    def test_music_dna_import_route_uses_import_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": True, "imported": True, "enabled": True}, 200

        connection = _Connection(user_id="user-dna")
        original = self.websocket_api.async_handle_music_dna_import_payload
        self.websocket_api.async_handle_music_dna_import_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_music_dna_import(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 24,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_IMPORT,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                        "music_dna_key": "user:ha-user",
                        "profile": {
                            "format": "djconnect.music_dna.export",
                            "profile": {"enabled": True},
                        },
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_import_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["music_dna_key"], "user:ha-user")
        self.assertEqual(payload["profile"]["format"], "djconnect.music_dna.export")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-ios-ABCDEF123456")
        self.assertEqual(user_id, "user-dna")
        self.assertEqual(connection.results, [(24, {"success": True, "imported": True, "enabled": True})])

    def test_music_dna_export_route_uses_export_handler(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {
                "success": True,
                "format": "djconnect.music_dna.export",
                "schema_version": 1,
            }, 200

        connection = _Connection(user_id="user-dna")
        original = self.websocket_api.async_handle_music_dna_export_payload
        self.websocket_api.async_handle_music_dna_export_payload = handler
        try:
            asyncio.run(
                self.websocket_api.websocket_music_dna_export(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 25,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_EXPORT,
                        "payload": {
                            "device_id": "djconnect-macos-ABCDEF123456",
                            "client_type": "macos",
                            "music_dna_key": "user:ha-user",
                        },
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_export_payload = original
        payload, headers, user_id = calls[0]
        self.assertEqual(payload["client_type"], "macos")
        self.assertEqual(payload["music_dna_key"], "user:ha-user")
        self.assertEqual(headers["Authorization"], "Bearer device-secret")
        self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-macos-ABCDEF123456")
        self.assertEqual(user_id, "user-dna")
        self.assertEqual(
            connection.results,
            [(25, {"success": True, "format": "djconnect.music_dna.export", "schema_version": 1})],
        )

    def test_music_dna_profile_http_and_websocket_payloads_have_parity(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {
                "success": True,
                "enabled": True,
                "music_dna_key": payload["music_dna_key"],
                "profile": {"summary": "Parity profile"},
            }, 200

        hass = types.SimpleNamespace(data={})
        payload = {
            "device_id": "djconnect-ios-ABCDEF123456",
            "client_type": "ios",
            "music_dna_key": "user:ha-user",
        }
        headers = {
            "Authorization": "Bearer device-secret",
            "X-DJConnect-Device-ID": "djconnect-ios-ABCDEF123456",
        }
        original = self.websocket_api.async_handle_music_dna_profile_payload
        self.websocket_api.async_handle_music_dna_profile_payload = handler
        try:
            http_result, http_status = asyncio.run(
                self.websocket_api.async_handle_music_dna_profile_payload(
                    hass,
                    dict(payload),
                    headers=dict(headers),
                    user_id="user-dna",
                )
            )
            connection = _Connection(user_id="user-dna")
            asyncio.run(
                self.websocket_api.websocket_music_dna_profile(
                    hass,
                    connection,
                    {
                        "id": 31,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_PROFILE,
                        **payload,
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_profile_payload = original

        self.assertEqual(http_status, 200)
        self.assertEqual(connection.errors, [])
        self.assertEqual(connection.results, [(31, http_result)])
        self.assertEqual(calls[0], calls[1])

    def test_music_dna_import_export_http_and_websocket_payloads_have_parity(self) -> None:
        calls = []

        async def import_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("import", payload, headers, user_id))
            return {"success": True, "imported": True, "profile_keys": sorted(payload["profile"])}, 200

        async def export_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("export", payload, headers, user_id))
            return {"success": True, "format": "djconnect.music_dna.export", "music_dna_key": payload["music_dna_key"]}, 200

        hass = types.SimpleNamespace(data={})
        base_payload = {
            "device_id": "djconnect-macos-ABCDEF123456",
            "client_type": "macos",
            "music_dna_key": "user:ha-user",
        }
        headers = {
            "Authorization": "Bearer device-secret",
            "X-DJConnect-Device-ID": "djconnect-macos-ABCDEF123456",
        }
        import_payload = {
            **base_payload,
            "profile": {
                "format": "djconnect.music_dna.export",
                "schema_version": 1,
            },
        }
        originals = (
            self.websocket_api.async_handle_music_dna_import_payload,
            self.websocket_api.async_handle_music_dna_export_payload,
        )
        self.websocket_api.async_handle_music_dna_import_payload = import_handler
        self.websocket_api.async_handle_music_dna_export_payload = export_handler
        try:
            http_import, import_status = asyncio.run(
                self.websocket_api.async_handle_music_dna_import_payload(
                    hass,
                    dict(import_payload),
                    headers=dict(headers),
                    user_id="user-dna",
                )
            )
            http_export, export_status = asyncio.run(
                self.websocket_api.async_handle_music_dna_export_payload(
                    hass,
                    dict(base_payload),
                    headers=dict(headers),
                    user_id="user-dna",
                )
            )
            connection = _Connection(user_id="user-dna")
            asyncio.run(
                self.websocket_api.websocket_music_dna_import(
                    hass,
                    connection,
                    {
                        "id": 32,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_IMPORT,
                        **import_payload,
                        "device_token": "device-secret",
                    },
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_dna_export(
                    hass,
                    connection,
                    {
                        "id": 33,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_EXPORT,
                        "payload": dict(base_payload),
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            (
                self.websocket_api.async_handle_music_dna_import_payload,
                self.websocket_api.async_handle_music_dna_export_payload,
            ) = originals

        self.assertEqual(import_status, 200)
        self.assertEqual(export_status, 200)
        self.assertEqual(connection.errors, [])
        self.assertEqual(connection.results, [(32, http_import), (33, http_export)])
        self.assertEqual(calls[0], calls[2])
        self.assertEqual(calls[1], calls[3])

    def test_music_discovery_http_and_websocket_payloads_have_parity(self) -> None:
        calls = []

        async def feed_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("feed", payload, headers, user_id))
            return {
                "success": True,
                "enabled": True,
                "music_dna_key": payload["music_dna_key"],
                "sections": [{"id": "new_for_you", "title": "Nieuw voor jou", "items": []}],
            }, 200

        async def play_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("play", payload, headers, user_id))
            return {"success": True, "played": True, "discovery_item_id": payload["discovery_item_id"]}, 200

        async def feedback_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("feedback", payload, headers, user_id))
            return {"success": True, "feedback": payload["feedback"], "discovery_item_id": payload["discovery_item_id"]}, 200

        hass = types.SimpleNamespace(data={})
        base_payload = {
            "device_id": "djconnect-ios-ABCDEF123456",
            "client_type": "ios",
            "music_dna_key": "user:ha-user",
        }
        item_payload = {
            **base_payload,
            "section_id": "new_for_you",
            "discovery_item_id": "disc-1",
        }
        feedback_payload = {**item_payload, "feedback": "not_for_me"}
        headers = {
            "Authorization": "Bearer device-secret",
            "X-DJConnect-Device-ID": "djconnect-ios-ABCDEF123456",
        }
        originals = (
            self.websocket_api.async_handle_music_discovery_feed_payload,
            self.websocket_api.async_handle_music_discovery_play_payload,
            self.websocket_api.async_handle_music_discovery_feedback_payload,
        )
        self.websocket_api.async_handle_music_discovery_feed_payload = feed_handler
        self.websocket_api.async_handle_music_discovery_play_payload = play_handler
        self.websocket_api.async_handle_music_discovery_feedback_payload = feedback_handler
        try:
            http_feed, feed_status = asyncio.run(
                self.websocket_api.async_handle_music_discovery_feed_payload(
                    hass,
                    dict(base_payload),
                    headers=dict(headers),
                    user_id="user-discovery",
                )
            )
            http_play, play_status = asyncio.run(
                self.websocket_api.async_handle_music_discovery_play_payload(
                    hass,
                    dict(item_payload),
                    headers=dict(headers),
                    user_id="user-discovery",
                )
            )
            http_feedback, feedback_status = asyncio.run(
                self.websocket_api.async_handle_music_discovery_feedback_payload(
                    hass,
                    dict(feedback_payload),
                    headers=dict(headers),
                    user_id="user-discovery",
                )
            )
            connection = _Connection(user_id="user-discovery")
            asyncio.run(
                self.websocket_api.websocket_music_discovery_feed(
                    hass,
                    connection,
                    {
                        "id": 34,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEED,
                        **base_payload,
                        "device_token": "device-secret",
                    },
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_discovery_play(
                    hass,
                    connection,
                    {
                        "id": 35,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_PLAY,
                        **item_payload,
                        "device_token": "device-secret",
                    },
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_discovery_feedback(
                    hass,
                    connection,
                    {
                        "id": 36,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEEDBACK,
                        **feedback_payload,
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            (
                self.websocket_api.async_handle_music_discovery_feed_payload,
                self.websocket_api.async_handle_music_discovery_play_payload,
                self.websocket_api.async_handle_music_discovery_feedback_payload,
            ) = originals

        self.assertEqual((feed_status, play_status, feedback_status), (200, 200, 200))
        self.assertEqual(connection.errors, [])
        self.assertEqual(connection.results, [(34, http_feed), (35, http_play), (36, http_feedback)])
        self.assertEqual(calls[0], calls[3])
        self.assertEqual(calls[1], calls[4])
        self.assertEqual(calls[2], calls[5])

    def test_music_dna_import_export_websocket_errors_do_not_send_success_results(self) -> None:
        calls = []

        async def import_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("import", payload, headers, user_id))
            return {"success": False, "error": "unauthorized", "message": "No import."}, 401

        async def export_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("export", payload, headers, user_id))
            return {"success": False, "error": "unauthorized", "message": "No export."}, 401

        originals = (
            self.websocket_api.async_handle_music_dna_import_payload,
            self.websocket_api.async_handle_music_dna_export_payload,
        )
        self.websocket_api.async_handle_music_dna_import_payload = import_handler
        self.websocket_api.async_handle_music_dna_export_payload = export_handler
        try:
            connection = _Connection(user_id="user-dna")
            base = {
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
                "music_dna_key": "user:ha-user",
                "device_token": "wrong-token",
            }
            asyncio.run(
                self.websocket_api.websocket_music_dna_import(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 41,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_IMPORT,
                        **base,
                        "profile": {"format": "djconnect.music_dna.export"},
                    },
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_dna_export(
                    types.SimpleNamespace(data={}),
                    connection,
                    {"id": 42, "type": self.websocket_api.WS_TYPE_MUSIC_DNA_EXPORT, **base},
                )
            )
        finally:
            (
                self.websocket_api.async_handle_music_dna_import_payload,
                self.websocket_api.async_handle_music_dna_export_payload,
            ) = originals

        self.assertEqual(connection.results, [])
        self.assertEqual(
            connection.errors,
            [(41, "unauthorized", "No import."), (42, "unauthorized", "No export.")],
        )
        self.assertEqual([call[0] for call in calls], ["import", "export"])

    def test_music_dna_settings_websocket_missing_enabled_returns_error(self) -> None:
        calls = []

        async def handler(hass, payload, *, headers=None, user_id=None):
            calls.append((payload, headers, user_id))
            return {"success": False, "error": "missing_enabled", "message": "Missing enabled."}, 400

        original = self.websocket_api.async_handle_music_dna_settings_payload
        self.websocket_api.async_handle_music_dna_settings_payload = handler
        try:
            connection = _Connection(user_id="user-dna")
            asyncio.run(
                self.websocket_api.websocket_music_dna_settings(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 43,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DNA_SETTINGS,
                        "device_id": "djconnect-ios-ABCDEF123456",
                        "client_type": "ios",
                        "device_token": "device-secret",
                    },
                )
            )
        finally:
            self.websocket_api.async_handle_music_dna_settings_payload = original

        self.assertEqual(connection.results, [])
        self.assertEqual(connection.errors, [(43, "missing_enabled", "Missing enabled.")])
        self.assertNotIn("enabled", calls[0][0])

    def test_music_discovery_mutation_websocket_errors_do_not_send_success_results(self) -> None:
        calls = []

        async def play_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("play", payload, headers, user_id))
            return {"success": False, "reason": "unauthorized", "message": "No play."}, 401

        async def feedback_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("feedback", payload, headers, user_id))
            return {"success": False, "reason": "unsupported_feedback", "message": "No feedback."}, 400

        originals = (
            self.websocket_api.async_handle_music_discovery_play_payload,
            self.websocket_api.async_handle_music_discovery_feedback_payload,
        )
        self.websocket_api.async_handle_music_discovery_play_payload = play_handler
        self.websocket_api.async_handle_music_discovery_feedback_payload = feedback_handler
        try:
            connection = _Connection(user_id="user-discovery")
            base = {
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
                "device_token": "wrong-token",
                "music_dna_key": "user:ha-user",
                "section_id": "new_for_you",
                "discovery_item_id": "disc-1",
            }
            asyncio.run(
                self.websocket_api.websocket_music_discovery_play(
                    types.SimpleNamespace(data={}),
                    connection,
                    {"id": 44, "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_PLAY, **base},
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_discovery_feedback(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 45,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEEDBACK,
                        **base,
                        "feedback": "delete_everything",
                    },
                )
            )
        finally:
            (
                self.websocket_api.async_handle_music_discovery_play_payload,
                self.websocket_api.async_handle_music_discovery_feedback_payload,
            ) = originals

        self.assertEqual(connection.results, [])
        self.assertEqual(
            connection.errors,
            [(44, "djconnect_error", "No play."), (45, "djconnect_error", "No feedback.")],
        )
        self.assertEqual([call[0] for call in calls], ["play", "feedback"])

    def test_top_level_profile_context_fields_reach_websocket_handlers(self) -> None:
        calls = []

        async def ask_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("ask", payload, headers, user_id))
            return {"success": True}, 200

        async def discovery_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("discovery", payload, headers, user_id))
            return {"success": True, "sections": []}, 200

        originals = (
            self.websocket_api.async_handle_ask_dj_message_payload,
            self.websocket_api.async_handle_music_discovery_feed_payload,
        )
        self.websocket_api.async_handle_ask_dj_message_payload = ask_handler
        self.websocket_api.async_handle_music_discovery_feed_payload = discovery_handler
        try:
            connection = _Connection(user_id="ha-user")
            base = {
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
                "device_token": "device-secret",
                "profile_id": "profile-personal",
                "private_session": True,
                "privacy_mode": "private",
            }
            asyncio.run(
                self.websocket_api.websocket_ask_dj_message(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 46,
                        "type": self.websocket_api.WS_TYPE_ASK_DJ_MESSAGE,
                        **base,
                        "text": "Play something",
                    },
                )
            )
            asyncio.run(
                self.websocket_api.websocket_music_discovery_feed(
                    types.SimpleNamespace(data={}),
                    connection,
                    {
                        "id": 47,
                        "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEED,
                        **base,
                    },
                )
            )
        finally:
            (
                self.websocket_api.async_handle_ask_dj_message_payload,
                self.websocket_api.async_handle_music_discovery_feed_payload,
            ) = originals

        self.assertEqual(connection.errors, [])
        self.assertEqual(len(connection.results), 2)
        for _kind, payload, _headers, user_id in calls:
            self.assertEqual(payload["profile_id"], "profile-personal")
            self.assertTrue(payload["private_session"])
            self.assertEqual(payload["privacy_mode"], "private")
            self.assertEqual(user_id, "ha-user")


class _Connection:
    def __init__(self, user_id: str | None = None) -> None:
        self.user = types.SimpleNamespace(id=user_id) if user_id else None
        self.results = []
        self.errors = []
        self.events = []
        self.close_callbacks = []
        self.delivery_order = []

    def send_result(self, msg_id, result) -> None:
        self.results.append((msg_id, result))
        self.delivery_order.append("result")

    def send_error(self, msg_id, code, message) -> None:
        self.errors.append((msg_id, code, message))

    def send_event(self, event_type, data) -> None:
        self.events.append((event_type, data))
        self.delivery_order.append("event")

    def async_on_close(self, callback) -> None:
        self.close_callbacks.append(callback)


class _FailingResultConnection(_Connection):
    def send_result(self, msg_id, result) -> None:
        raise RuntimeError("connection closed")


if __name__ == "__main__":
    unittest.main()
