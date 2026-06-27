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
        http.async_handle_track_insight_payload = async_handle_command_payload
        sys.modules.setdefault("custom_components.djconnect.http", http)
        cls.websocket_api = importlib.import_module("custom_components.djconnect.websocket_api")
        cls.websocket_api.websocket_api = websocket_api

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
                "websocket_track_insight",
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
        self.assertIn(self.websocket_api.WS_TYPE_TRACK_INSIGHT, result["commands"])
        self.assertEqual(result["transports"], {"http": True, "websocket": True})

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


class _Connection:
    def __init__(self, user_id: str | None = None) -> None:
        self.user = types.SimpleNamespace(id=user_id) if user_id else None
        self.results = []
        self.errors = []

    def send_result(self, msg_id, result) -> None:
        self.results.append((msg_id, result))

    def send_error(self, msg_id, code, message) -> None:
        self.errors.append((msg_id, code, message))


if __name__ == "__main__":
    unittest.main()
