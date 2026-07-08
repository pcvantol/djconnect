from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def install_button_stubs() -> None:
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    components = sys.modules.setdefault("homeassistant.components", types.ModuleType("homeassistant.components"))
    button = types.ModuleType("homeassistant.components.button")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")

    class ButtonEntity:
        pass

    button.ButtonEntity = ButtonEntity
    config_entries.ConfigEntry = object
    core.HomeAssistant = object
    device_registry.DeviceInfo = dict
    entity_registry.async_get = lambda hass: getattr(hass, "entity_registry", None)
    entity_platform.AddEntitiesCallback = object
    components.button = button
    helpers.device_registry = device_registry
    helpers.entity_registry = entity_registry
    helpers.entity_platform = entity_platform
    homeassistant.components = components

    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    package.DEFAULT_TEST_TTS_TEXT = "test"

    async def async_speak_dj_test(*args, **kwargs):
        return None

    package.async_speak_dj_test = async_speak_dj_test
    sys.modules["custom_components.djconnect"] = package
    spotify_backend = types.ModuleType("custom_components.djconnect.spotify_backend")

    class SpotifyBackendError(Exception):
        pass

    async def handle_spotify_command(*args, **kwargs):
        return {}

    spotify_backend.SpotifyBackendError = SpotifyBackendError
    spotify_backend.handle_spotify_command = handle_spotify_command
    sys.modules["custom_components.djconnect.spotify_backend"] = spotify_backend
    push = types.ModuleType("custom_components.djconnect.push")
    push.EVENT_ASK_DJ_CONFIRM = "ask_dj_confirm"
    push.calls = []

    async def async_send_event(*args, **kwargs):
        push.calls.append((args, kwargs))
        return {"success": True, "sent": 1}

    push.async_send_event = async_send_event
    sys.modules["custom_components.djconnect.push"] = push
    sys.modules["homeassistant.components.button"] = button
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers.device_registry"] = device_registry
    sys.modules["homeassistant.helpers.entity_registry"] = entity_registry
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform


class DJConnectButtonEntityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_button_stubs()
        cls.button = importlib.import_module("custom_components.djconnect.button")

    @classmethod
    def tearDownClass(cls) -> None:
        for module in (
            "custom_components.djconnect.button",
            "custom_components.djconnect.spotify_backend",
            "custom_components.djconnect.push",
            "custom_components.djconnect.entity_ids",
            "custom_components.djconnect.const",
            "custom_components.djconnect",
        ):
            sys.modules.pop(module, None)

    def test_reboot_button_is_skipped_for_app_clients(self) -> None:
        added = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            client_type=lambda: "macos",
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": runtime}})
        entry = types.SimpleNamespace(entry_id="entry-1")

        asyncio.run(
            self.button.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
        )

        translation_keys = {entity._attr_translation_key for entity in added}
        self.assertNotIn("reboot_device", translation_keys)
        self.assertNotIn("test_dj_response", translation_keys)
        self.assertIn("test_push_message", translation_keys)

    def test_test_push_button_is_added_for_apple_clients_only(self) -> None:
        for client_type in ("ios", "macos", "watchos"):
            with self.subTest(client_type=client_type):
                added = []
                runtime = types.SimpleNamespace(
                    entry=types.SimpleNamespace(entry_id=f"entry-{client_type}"),
                    client_type=lambda client_type=client_type: client_type,
                )
                hass = types.SimpleNamespace(data={"djconnect": {runtime.entry.entry_id: runtime}})
                entry = types.SimpleNamespace(entry_id=runtime.entry.entry_id)

                asyncio.run(
                    self.button.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
                )

                translation_keys = {entity._attr_translation_key for entity in added}
                self.assertIn("test_push_message", translation_keys)
                self.assertNotIn("test_dj_response", translation_keys)

        for client_type in ("esp32", "raspberry_pi", "windows"):
            with self.subTest(client_type=client_type):
                added = []
                runtime = types.SimpleNamespace(
                    entry=types.SimpleNamespace(entry_id=f"entry-{client_type}"),
                    client_type=lambda client_type=client_type: client_type,
                )
                hass = types.SimpleNamespace(data={"djconnect": {runtime.entry.entry_id: runtime}})
                entry = types.SimpleNamespace(entry_id=runtime.entry.entry_id)

                asyncio.run(
                    self.button.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
                )

                translation_keys = {entity._attr_translation_key for entity in added}
                self.assertNotIn("test_push_message", translation_keys)
                if client_type != "esp32":
                    self.assertNotIn("test_dj_response", translation_keys)

    def test_test_push_button_sends_ask_dj_attention_event(self) -> None:
        push = importlib.import_module("custom_components.djconnect.push")
        push.calls.clear()
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={
                "device_id": "djconnect-macos-ABCDEFGHIJKL",
                "client_type": "macos",
            },
            config={},
        )
        hass = object()

        asyncio.run(self.button.DJConnectTestPushButton(runtime, hass).async_press())

        args, kwargs = push.calls[0]
        self.assertIs(args[0], hass)
        self.assertIs(args[1], runtime)
        self.assertEqual(kwargs["event_type"], "ask_dj_confirm")
        self.assertEqual(kwargs["source_device_id"], "djconnect-macos-ABCDEFGHIJKL")
        self.assertEqual(kwargs["client_type"], "macos")
        self.assertTrue(kwargs["explicit_user_request"])

    def test_test_push_button_records_readable_failure_reason(self) -> None:
        errors = []

        async def send_push(*args, **kwargs):
            return {
                "success": False,
                "sent": 0,
                "errors": 1,
                "disabled": True,
                "error": "missing_bootstrap_proof",
            }

        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={
                "device_id": "djconnect-macos-ABCDEFGHIJKL",
                "client_type": "macos",
            },
            config={},
            update=lambda **kwargs: errors.append(kwargs["last_error"]),
        )
        original = self.button.async_send_push_event
        self.button.async_send_push_event = send_push
        try:
            with self.assertLogs("custom_components.djconnect.button", level="WARNING") as logs:
                asyncio.run(self.button.DJConnectTestPushButton(runtime, object()).async_press())
        finally:
            self.button.async_send_push_event = original

        self.assertIn("missing_bootstrap_proof", logs.output[0])
        self.assertEqual(
            errors,
            ["DJConnect test push was not sent: missing_bootstrap_proof"],
        )

    def test_pi_power_buttons_are_added_for_raspberry_pi_clients(self) -> None:
        added = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            client_type=lambda: "raspberry_pi",
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": runtime}})
        entry = types.SimpleNamespace(entry_id="entry-1")

        asyncio.run(
            self.button.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
        )

        translation_keys = {entity._attr_translation_key for entity in added}
        self.assertNotIn("reboot_device", translation_keys)
        self.assertNotIn("test_dj_response", translation_keys)
        self.assertIn("restart_device", translation_keys)
        self.assertIn("shutdown_device", translation_keys)

    def test_pi_power_buttons_call_pi_device_endpoints(self) -> None:
        calls = []

        async def async_device_post(hass, path):
            calls.append(path)
            return {"success": True}

        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            async_device_post=async_device_post,
        )
        hass = object()

        asyncio.run(self.button.DJConnectPiRestartButton(runtime, hass).async_press())
        asyncio.run(self.button.DJConnectPiShutdownButton(runtime, hass).async_press())

        self.assertEqual(calls, ["/api/device/restart", "/api/device/shutdown"])

    def test_reboot_button_is_added_for_esp32_clients(self) -> None:
        added = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            client_type=lambda: "esp32",
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": runtime}})
        entry = types.SimpleNamespace(entry_id="entry-1")

        asyncio.run(
            self.button.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
        )

        translation_keys = {entity._attr_translation_key for entity in added}
        self.assertIn("test_dj_response", translation_keys)
        self.assertIn("reboot_device", translation_keys)


if __name__ == "__main__":
    unittest.main()
