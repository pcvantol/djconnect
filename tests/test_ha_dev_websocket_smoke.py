from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class HADevWebsocketSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        package = types.ModuleType("custom_components.djconnect")
        package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
        sys.modules.setdefault("custom_components.djconnect", package)

        voluptuous = types.ModuleType("voluptuous")
        voluptuous.Required = lambda key: key
        voluptuous.Optional = lambda key, default=None: key
        sys.modules["voluptuous"] = voluptuous

        cls.registry = {}
        websocket_api = types.ModuleType("homeassistant.components.websocket_api")
        websocket_api.async_register_command = (
            lambda hass, command: cls.registry.__setitem__(
                getattr(command, "_djconnect_ws_type", _command_type_from_name(command.__name__)),
                command,
            )
        )

        def websocket_command(schema):
            command_type = schema.get("type") if isinstance(schema, dict) else None

            def decorate(func):
                func._djconnect_ws_type = command_type
                return func

            return decorate

        websocket_api.websocket_command = websocket_command
        websocket_api.async_response = lambda func: func

        homeassistant = types.ModuleType("homeassistant")
        components = types.ModuleType("homeassistant.components")
        components.websocket_api = websocket_api
        homeassistant.components = components
        sys.modules["homeassistant"] = homeassistant
        sys.modules["homeassistant.components"] = components
        sys.modules["homeassistant.components.websocket_api"] = websocket_api

        sys.modules.pop("custom_components.djconnect.const", None)
        sys.modules.pop("custom_components.djconnect.websocket_api", None)
        cls.websocket_api = importlib.import_module("custom_components.djconnect.websocket_api")
        cls.websocket_api.websocket_api = websocket_api

    @classmethod
    def tearDownClass(cls) -> None:
        for module_name in (
            "custom_components.djconnect.websocket_api",
            "custom_components.djconnect.const",
            "homeassistant.components.websocket_api",
        ):
            sys.modules.pop(module_name, None)

    def setUp(self) -> None:
        self.registry.clear()
        self.hass = types.SimpleNamespace(data={})
        self.websocket_api.async_register(self.hass)

    def test_mocked_ha_websocket_smoke_covers_capabilities_music_dna_and_discovery(self) -> None:
        calls = []

        async def profile_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("profile", payload, headers, user_id))
            return {
                "success": True,
                "enabled": True,
                "music_dna_key": "user:ha-smoke",
                "profile": {
                    "summary": "Smoke profile",
                    "privacy_dashboard": {
                        "enabled": True,
                        "data_sources": [{"id": "recent_tracks", "label": "Recent tracks", "enabled": True}],
                        "controls": {"clear_supported": True},
                        "stores_raw_audio": False,
                        "stores_oauth_tokens": False,
                        "stores_full_prompts": False,
                    },
                },
            }, 200

        async def discovery_handler(hass, payload, *, headers=None, user_id=None):
            calls.append(("discovery", payload, headers, user_id))
            return {
                "success": True,
                "enabled": True,
                "sections": [
                    {
                        "id": "new_for_you",
                        "title": "Nieuw voor jou",
                        "items": [
                            {
                                "id": "disc-smoke",
                                "kind": "track",
                                "title": "Smoke Track",
                                "subtitle": "Smoke Artist",
                                "uri": "spotify:track:smoke",
                                "reason": "Past bij je Music DNA.",
                                "reason_sources": ["djconnect_music_dna"],
                                "confidence": "medium",
                                "quality_score": 82,
                                "quality_band": "high",
                                "quality_factors": ["smoke"],
                            }
                        ],
                    }
                ],
            }, 200

        original_profile = self.websocket_api.async_handle_music_dna_profile_payload
        original_discovery = self.websocket_api.async_handle_music_discovery_feed_payload
        self.websocket_api.async_handle_music_dna_profile_payload = profile_handler
        self.websocket_api.async_handle_music_discovery_feed_payload = discovery_handler
        try:
            session = _MockHAWebsocketSession(
                self.hass,
                self.registry,
                valid_token="ha-dev-token",
                user_id="ha-smoke",
            )
            self.assertEqual(session.receive(), {"type": "auth_required"})
            session.send({"type": "auth", "access_token": "ha-dev-token"})
            self.assertEqual(session.receive(), {"type": "auth_ok"})

            session.send({"id": 1, "type": self.websocket_api.WS_TYPE_CAPABILITIES})
            capabilities = session.receive()
            self.assertEqual(capabilities["type"], "result")
            self.assertTrue(capabilities["success"])
            self.assertTrue(capabilities["result"]["features"]["music_dna"])
            self.assertTrue(capabilities["result"]["features"]["music_discovery"])

            identity = {
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
                "device_token": "device-secret",
                "music_dna_key": "user:ha-smoke",
            }
            session.send({"id": 2, "type": self.websocket_api.WS_TYPE_MUSIC_DNA_PROFILE, **identity})
            profile = session.receive()
            self.assertEqual(profile["type"], "result")
            self.assertTrue(profile["result"]["enabled"])
            self.assertFalse(profile["result"]["profile"]["privacy_dashboard"]["stores_oauth_tokens"])

            session.send({"id": 3, "type": self.websocket_api.WS_TYPE_MUSIC_DISCOVERY_FEED, **identity})
            feed = session.receive()
            self.assertEqual(feed["type"], "result")
            self.assertEqual(feed["result"]["sections"][0]["items"][0]["quality_band"], "high")
        finally:
            self.websocket_api.async_handle_music_dna_profile_payload = original_profile
            self.websocket_api.async_handle_music_discovery_feed_payload = original_discovery

        self.assertEqual([call[0] for call in calls], ["profile", "discovery"])
        for _, payload, headers, user_id in calls:
            self.assertEqual(payload["device_id"], "djconnect-ios-ABCDEF123456")
            self.assertEqual(payload["client_type"], "ios")
            self.assertEqual(payload["music_dna_key"], "user:ha-smoke")
            self.assertEqual(headers["Authorization"], "Bearer device-secret")
            self.assertEqual(headers["X-DJConnect-Device-ID"], "djconnect-ios-ABCDEF123456")
            self.assertEqual(user_id, "ha-smoke")

    def test_mocked_ha_websocket_smoke_rejects_bad_auth_before_dispatch(self) -> None:
        session = _MockHAWebsocketSession(
            self.hass,
            self.registry,
            valid_token="ha-dev-token",
            user_id="ha-smoke",
        )

        self.assertEqual(session.receive(), {"type": "auth_required"})
        session.send({"type": "auth", "access_token": "wrong"})
        self.assertEqual(session.receive(), {"type": "auth_invalid", "message": "Invalid access token"})
        session.send({"id": 1, "type": self.websocket_api.WS_TYPE_CAPABILITIES})
        self.assertEqual(
            session.receive(),
            {"id": 1, "type": "error", "success": False, "error": {"code": "unauthorized", "message": "Authenticate first."}},
        )


class _MockHAWebsocketSession:
    def __init__(self, hass, registry, *, valid_token: str, user_id: str) -> None:
        self.hass = hass
        self.registry = registry
        self.valid_token = valid_token
        self.user_id = user_id
        self.authenticated = False
        self.outbox = [{"type": "auth_required"}]

    def send(self, message: dict) -> None:
        if message.get("type") == "auth":
            if message.get("access_token") == self.valid_token:
                self.authenticated = True
                self.outbox.append({"type": "auth_ok"})
            else:
                self.outbox.append({"type": "auth_invalid", "message": "Invalid access token"})
            return
        if not self.authenticated:
            self.outbox.append(
                {
                    "id": message.get("id"),
                    "type": "error",
                    "success": False,
                    "error": {"code": "unauthorized", "message": "Authenticate first."},
                }
            )
            return
        command = self.registry.get(message.get("type"))
        if command is None:
            self.outbox.append(
                {
                    "id": message.get("id"),
                    "type": "error",
                    "success": False,
                    "error": {"code": "unknown_command", "message": "Unknown command."},
                }
            )
            return
        connection = _SmokeConnection(user_id=self.user_id, outbox=self.outbox)
        asyncio.run(command(self.hass, connection, message))

    def receive(self) -> dict:
        return self.outbox.pop(0)


class _SmokeConnection:
    def __init__(self, *, user_id: str, outbox: list[dict]) -> None:
        self.user = types.SimpleNamespace(id=user_id)
        self.outbox = outbox

    def send_result(self, msg_id, result) -> None:
        self.outbox.append({"id": msg_id, "type": "result", "success": True, "result": result})

    def send_error(self, msg_id, code, message) -> None:
        self.outbox.append(
            {
                "id": msg_id,
                "type": "error",
                "success": False,
                "error": {"code": code, "message": message},
            }
        )


def _command_type_from_name(name: str) -> str:
    return {
        "websocket_capabilities": "djconnect/capabilities",
        "websocket_command": "djconnect/command",
        "websocket_ask_dj_message": "djconnect/ask_dj/message",
        "websocket_ask_dj_history": "djconnect/ask_dj/history",
        "websocket_ask_dj_history_clear": "djconnect/ask_dj/history/clear",
        "websocket_ask_dj_history_state": "djconnect/ask_dj/history/state",
        "websocket_ask_dj_idle_suggestion": "djconnect/ask_dj/idle_suggestion",
        "websocket_track_insight": "djconnect/track_insight",
        "websocket_music_dna_profile": "djconnect/music_dna/profile",
        "websocket_music_dna_settings": "djconnect/music_dna/settings",
        "websocket_music_dna_clear": "djconnect/music_dna/clear",
        "websocket_music_dna_import": "djconnect/music_dna/import",
        "websocket_music_dna_export": "djconnect/music_dna/export",
        "websocket_music_discovery_feed": "djconnect/music_discovery/feed",
        "websocket_music_discovery_refresh": "djconnect/music_discovery/refresh",
        "websocket_music_discovery_play": "djconnect/music_discovery/play",
        "websocket_music_discovery_feedback": "djconnect/music_discovery/feedback",
    }.get(name, name)


if __name__ == "__main__":
    unittest.main()
