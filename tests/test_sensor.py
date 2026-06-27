from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install_sensor_stubs() -> None:
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    components = sys.modules.setdefault(
        "homeassistant.components",
        types.ModuleType("homeassistant.components"),
    )
    sensor = types.ModuleType("homeassistant.components.sensor")
    config_entries = types.ModuleType("homeassistant.config_entries")
    const = types.ModuleType("homeassistant.const")
    core = types.ModuleType("homeassistant.core")
    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")

    class SensorEntity:
        def async_write_ha_state(self):
            self.write_count = getattr(self, "write_count", 0) + 1
            self.wrote_state = True

    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    aiohttp.ClientTimeout = ClientTimeout
    sensor.SensorEntity = SensorEntity
    sensor.SensorDeviceClass = types.SimpleNamespace(BATTERY="battery", SIGNAL_STRENGTH="signal_strength")
    sensor.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
    config_entries.ConfigEntry = object
    const.EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
    const.PERCENTAGE = "%"
    const.SIGNAL_STRENGTH_DECIBELS_MILLIWATT = "dBm"
    core.HomeAssistant = object
    core.callback = lambda func: func
    device_registry.DeviceInfo = dict
    entity_platform.AddEntitiesCallback = object
    aiohttp_client.async_get_clientsession = lambda hass: None
    components.sensor = sensor
    helpers.device_registry = device_registry
    helpers.entity_platform = entity_platform
    helpers.aiohttp_client = aiohttp_client
    homeassistant.components = components
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules["custom_components.djconnect"] = package

    sys.modules["homeassistant.components.sensor"] = sensor
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers.device_registry"] = device_registry
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client


class DJConnectSensorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_sensor_stubs()
        cls.sensor = importlib.import_module("custom_components.djconnect.sensor")

    def test_pairing_status_is_pending_until_device_confirms(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={},
            listeners=[],
        )
        entity = self.sensor.DJConnectPairingStatusSensor(runtime)

        self.assertEqual(entity.native_value, "pending")
        runtime.device_status["ha_pairing_status"] = "paired"
        self.assertEqual(entity.native_value, "paired")

    def test_pairing_status_is_paired_for_app_client_with_device_token(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={"client_type": "ios", "device_id": "djconnect-ios-ABCDEFGHIJKL"},
            listeners=[],
            client_type=lambda: "ios",
        )
        entity = self.sensor.DJConnectPairingStatusSensor(runtime)

        self.assertEqual(entity.native_value, "paired")

    def test_app_client_backend_sensors_prefer_playback_and_keep_unknown_unknown(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={"client_type": "ios"},
            last_playback={
                "has_playback": True,
                "is_playing": True,
                "device": {"name": "Woonkamer"},
            },
            listeners=[],
            client_type=lambda: "ios",
        )

        self.assertEqual(self.sensor.DJConnectSoundOutputSensor(runtime).native_value, "Woonkamer")
        self.assertEqual(self.sensor.DJConnectSpotifyStatusSensor(runtime).native_value, "playing")
        self.assertTrue(self.sensor.DJConnectPlaybackAvailableSensor(runtime).native_value)
        self.assertIsNone(self.sensor.DJConnectQueueSensor(runtime).native_value)
        self.assertIsNone(self.sensor.DJConnectPlaylistsSensor(runtime).native_value)
        self.assertEqual(self.sensor.DJConnectOutputsSensor(runtime).native_value, 1)

        runtime.device_status["queue"] = {"items": []}
        runtime.device_status["playlists"] = []
        runtime.device_status["available_outputs"] = []

        self.assertEqual(self.sensor.DJConnectQueueSensor(runtime).native_value, 0)
        self.assertEqual(self.sensor.DJConnectPlaylistsSensor(runtime).native_value, 0)
        self.assertEqual(self.sensor.DJConnectOutputsSensor(runtime).native_value, 1)

    def test_backend_sensors_poll_spotify_state_and_collections(self) -> None:
        calls = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={"client_type": "macos"},
            last_playback={},
            listeners=[],
            client_type=lambda: "macos",
        )

        async def fake_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append(command)
            if command == "status":
                runtime_arg.last_playback = {
                    "has_playback": True,
                    "is_playing": False,
                    "device": {"id": "dev-1", "name": "MacBook Pro"},
                    "queue_context": "spotify:playlist:abc",
                }
                return {"success": True, "playback": runtime_arg.last_playback}
            if command == "devices":
                runtime_arg.device_status["available_outputs"] = [
                    {"id": "dev-1", "name": "MacBook Pro"}
                ]
                return {"success": True, "devices": runtime_arg.device_status["available_outputs"]}
            if command == "queue":
                runtime_arg.device_status["queue"] = {
                    "items": [{"title": "Next up"}],
                    "context_uri": "spotify:playlist:abc",
                }
                return {"success": True, "queue": runtime_arg.device_status["queue"]["items"]}
            if command == "playlists":
                runtime_arg.device_status["playlists"] = [{"name": "Roadtrip"}]
                return {"success": True, "playlists": runtime_arg.device_status["playlists"]}
            return {"success": True}

        original = self.sensor.run_music_command
        self.sensor.run_music_command = fake_handler
        try:
            playback_available = self.sensor.DJConnectPlaybackAvailableSensor(runtime, object())
            sound_output = self.sensor.DJConnectSoundOutputSensor(runtime, object())
            outputs = self.sensor.DJConnectOutputsSensor(runtime, object())
            queue = self.sensor.DJConnectQueueSensor(runtime, object())
            playlists = self.sensor.DJConnectPlaylistsSensor(runtime, object())

            self.assertFalse(playback_available._attr_should_poll)
            self.assertFalse(sound_output._attr_should_poll)
            self.assertFalse(outputs._attr_should_poll)
            self.assertFalse(queue._attr_should_poll)
            self.assertFalse(playlists._attr_should_poll)

            asyncio.run(playback_available.async_update())
            asyncio.run(sound_output.async_update())
            asyncio.run(outputs.async_update())
            asyncio.run(queue.async_update())
            asyncio.run(playlists.async_update())
        finally:
            self.sensor.run_music_command = original

        self.assertIn("status", calls)
        self.assertIn("devices", calls)
        self.assertIn("queue", calls)
        self.assertIn("playlists", calls)
        self.assertTrue(playback_available.native_value)
        self.assertEqual(sound_output.native_value, "MacBook Pro")
        self.assertEqual(outputs.native_value, 1)
        self.assertEqual(outputs.extra_state_attributes["items"][0]["name"], "MacBook Pro")
        self.assertEqual(queue.native_value, 1)
        self.assertEqual(queue.extra_state_attributes["context"], "spotify:playlist:abc")
        self.assertEqual(playlists.native_value, 1)
        self.assertEqual(playlists.extra_state_attributes["items"][0]["name"], "Roadtrip")

    def test_backend_sensors_read_nested_status_playback_without_live_poll(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={
                "client_type": "macos",
                "playback": {
                    "has_playback": True,
                    "is_playing": True,
                    "device": {"id": "dev-1", "name": "MacBook Pro"},
                    "queue_context": "spotify:playlist:def",
                },
            },
            last_playback=None,
            listeners=[],
            client_type=lambda: "macos",
        )

        self.assertEqual(self.sensor.DJConnectSpotifyStatusSensor(runtime).native_value, "playing")
        self.assertTrue(self.sensor.DJConnectPlaybackAvailableSensor(runtime).native_value)
        self.assertEqual(self.sensor.DJConnectSoundOutputSensor(runtime).native_value, "MacBook Pro")
        self.assertEqual(self.sensor.DJConnectOutputsSensor(runtime).native_value, 1)
        self.assertEqual(
            self.sensor.DJConnectQueueSensor(runtime).extra_state_attributes["context"],
            "spotify:playlist:def",
        )

    def test_music_sensors_keep_last_known_values_when_snapshot_is_sparse(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={
                "client_type": "macos",
                "queue": {"items": [{"title": "Next up"}]},
                "playlists": [{"name": "Roadtrip"}],
                "available_outputs": [{"id": "dev-1", "name": "MacBook Pro"}],
            },
            last_playback={
                "has_playback": True,
                "is_playing": True,
                "track_name": "Alive",
                "device": {"id": "dev-1", "name": "MacBook Pro"},
            },
            listeners=[],
            client_type=lambda: "macos",
        )

        track = self.sensor.DJConnectLastTrackSensor(runtime)
        spotify_status = self.sensor.DJConnectSpotifyStatusSensor(runtime)
        playback_available = self.sensor.DJConnectPlaybackAvailableSensor(runtime)
        sound_output = self.sensor.DJConnectSoundOutputSensor(runtime)
        queue = self.sensor.DJConnectQueueSensor(runtime)
        playlists = self.sensor.DJConnectPlaylistsSensor(runtime)
        outputs = self.sensor.DJConnectOutputsSensor(runtime)

        self.assertEqual(track.native_value, "Alive")
        self.assertEqual(spotify_status.native_value, "playing")
        self.assertTrue(playback_available.native_value)
        self.assertEqual(sound_output.native_value, "MacBook Pro")
        self.assertEqual(queue.native_value, 1)
        self.assertEqual(playlists.native_value, 1)
        self.assertEqual(outputs.native_value, 1)

        runtime.last_playback = {}
        runtime.device_status.pop("queue")
        runtime.device_status.pop("playlists")
        runtime.device_status.pop("available_outputs")

        self.assertEqual(track.native_value, "Alive")
        self.assertEqual(spotify_status.native_value, "playing")
        self.assertTrue(playback_available.native_value)
        self.assertEqual(sound_output.native_value, "MacBook Pro")
        self.assertEqual(queue.native_value, 1)
        self.assertEqual(playlists.native_value, 1)
        self.assertEqual(outputs.native_value, 1)

    def test_sensor_unique_ids_are_scoped_to_config_entry(self) -> None:
        runtime_a = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-a"),
            device_status={},
            last_playback=None,
            listeners=[],
        )
        runtime_b = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-b"),
            device_status={},
            last_playback=None,
            listeners=[],
        )

        queue_a = self.sensor.DJConnectQueueSensor(runtime_a)
        queue_b = self.sensor.DJConnectQueueSensor(runtime_b)

        self.assertEqual(queue_a._attr_unique_id, "djconnect_entry-a_queue")
        self.assertEqual(queue_b._attr_unique_id, "djconnect_entry-b_queue")
        self.assertNotEqual(queue_a._attr_unique_id, queue_b._attr_unique_id)

    def test_hardware_sensors_are_skipped_for_app_like_clients(self) -> None:
        added = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={"client_type": "ios"},
            last_error=None,
            last_playback=None,
            last_text=None,
            last_stt_text=None,
            last_dj_text=None,
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            ota_in_progress=False,
            ota_last_error=None,
            listeners=[],
            client_type=lambda: "ios",
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": runtime}})
        entry = types.SimpleNamespace(entry_id="entry-1")

        asyncio.run(
            self.sensor.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
        )

        keys = {entity._attr_translation_key for entity in added}
        self.assertIn("apns_registration", keys)
        self.assertNotIn("battery", keys)
        self.assertNotIn("wifi_rssi", keys)
        self.assertNotIn("screen_state", keys)
        self.assertNotIn("led_state", keys)
        self.assertIn("status", keys)
        self.assertIn("last_corrected_stt", keys)
        self.assertIn("queue", keys)
        self.assertIn("playback_available", keys)

    def test_hardware_sensors_are_added_for_esp32_clients(self) -> None:
        added = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_token="device-token",
            device_status={"client_type": "esp32"},
            last_error=None,
            last_playback=None,
            last_text=None,
            last_stt_text=None,
            last_dj_text=None,
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            ota_in_progress=False,
            ota_last_error=None,
            listeners=[],
            client_type=lambda: "esp32",
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": runtime}})
        entry = types.SimpleNamespace(entry_id="entry-1")

        asyncio.run(
            self.sensor.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
        )

        keys = {entity._attr_translation_key for entity in added}
        self.assertIn("apns_registration", keys)
        self.assertIn("battery", keys)
        self.assertIn("wifi_rssi", keys)
        self.assertIn("screen_state", keys)
        self.assertIn("led_state", keys)

    def test_screen_and_led_state_sensors_read_status_payload(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={"screen_state": "on", "led_state": "off"},
            listeners=[],
        )

        screen = self.sensor.DJConnectScreenStateSensor(runtime)
        led = self.sensor.DJConnectLedStateSensor(runtime)

        self.assertEqual(screen.native_value, "on")
        self.assertEqual(led.native_value, "off")

    def test_hardware_sensors_keep_cached_values_after_sparse_status_sync(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={
                "battery_percent": 82,
                "wifi_rssi": -61,
                "screen_state": "on",
                "led_state": "off",
            },
            listeners=[],
        )
        battery = self.sensor.DJConnectBatterySensor(runtime)
        wifi = self.sensor.DJConnectWifiSensor(runtime)
        screen = self.sensor.DJConnectScreenStateSensor(runtime)
        led = self.sensor.DJConnectLedStateSensor(runtime)

        self.assertEqual(battery.native_value, 82)
        self.assertEqual(wifi.native_value, -61)
        self.assertEqual(screen.native_value, "on")
        self.assertEqual(led.native_value, "off")

        runtime.device_status = {
            "battery_percent": None,
            "wifi_rssi": "unknown",
            "screen_state": "",
            "led_state": "unavailable",
        }

        self.assertEqual(battery.native_value, 82)
        self.assertEqual(wifi.native_value, -61)
        self.assertEqual(screen.native_value, "on")
        self.assertEqual(led.native_value, "off")

        runtime.device_status = {
            "battery_percent": 0,
            "wifi_rssi": -70,
            "screen_state": "off",
            "led_state": "on",
        }

        self.assertEqual(battery.native_value, 0)
        self.assertEqual(wifi.native_value, -70)
        self.assertEqual(screen.native_value, "off")
        self.assertEqual(led.native_value, "on")

    def test_conversation_agent_only_adds_apns_diagnostic_sensor(self) -> None:
        added = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            config={"client_type": "conversation_agent"},
            device_status={"client_type": "conversation_agent"},
            push_status={},
            listeners=[],
            client_type=lambda: "conversation_agent",
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": runtime}})
        entry = types.SimpleNamespace(entry_id="entry-1")

        asyncio.run(
            self.sensor.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
        )

        self.assertEqual([entity._attr_translation_key for entity in added], ["apns_registration"])
        self.assertEqual(added[0].native_value, "not_applicable")
        self.assertEqual(added[0]._attr_entity_category, "diagnostic")

    def test_apns_registration_sensor_reports_registered_app_client(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            config={
                "client_type": "ios",
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "djconnect_install_token": "djci_token",
            },
            device_status={"client_type": "ios", "device_id": "djconnect-ios-ABCDEFGHIJKL"},
            push_status={
                "djconnect-ios-ABCDEFGHIJKL|ios": {
                    "push_registered": True,
                    "push_environment": "production",
                    "last_push_error": None,
                }
            },
            listeners=[],
            client_type=lambda: "ios",
        )
        entity = self.sensor.DJConnectApnsRegistrationSensor(runtime)

        self.assertEqual(entity.native_value, "registered")
        self.assertEqual(entity.extra_state_attributes["registered_count"], 1)
        self.assertEqual(entity.extra_state_attributes["push_environment"], "production")
        self.assertNotIn("push_token", str(entity.extra_state_attributes))

    def test_apns_registration_sensor_reports_error_before_disabled(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            config={
                "client_type": "macos",
                "device_id": "djconnect-macos-ABCDEFGHIJKL",
            },
            device_status={"client_type": "macos", "device_id": "djconnect-macos-ABCDEFGHIJKL"},
            push_status={
                "djconnect-macos-ABCDEFGHIJKL|macos": {
                    "push_registered": False,
                    "push_environment": None,
                    "last_push_error": "missing_bootstrap_proof",
                }
            },
            listeners=[],
            client_type=lambda: "macos",
        )
        entity = self.sensor.DJConnectApnsRegistrationSensor(runtime)

        self.assertEqual(entity.native_value, "error")
        self.assertFalse(entity.extra_state_attributes["central_api_configured"])
        self.assertEqual(entity.extra_state_attributes["last_push_error"], "missing_bootstrap_proof")

    def test_apns_registration_sensor_reports_unsupported_device_client(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            config={"client_type": "esp32"},
            device_status={"client_type": "esp32"},
            push_status={},
            listeners=[],
            client_type=lambda: "esp32",
        )
        entity = self.sensor.DJConnectApnsRegistrationSensor(runtime)

        self.assertEqual(entity.native_value, "unsupported")
        self.assertFalse(entity.extra_state_attributes["push_supported"])

    def test_last_track_sensor_reads_backend_and_device_aliases(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={"last_track": "Device Track"},
            last_playback={"track_name": "Backend Track"},
            last_resolved_media={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTrackSensor(runtime)

        self.assertEqual(entity.native_value, "Backend Track")
        runtime.last_playback = {}
        self.assertEqual(entity.native_value, "Device Track")
        runtime.device_status = {"track": "Firmware Track"}
        self.assertEqual(entity.native_value, "Firmware Track")

    def test_last_track_sensor_keeps_cached_value_when_runtime_becomes_empty(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={"last_track": "Alive"},
            last_playback={},
            last_resolved_media={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTrackSensor(runtime)

        self.assertTrue(entity.available)
        self.assertEqual(entity.native_value, "Alive")
        runtime.device_status = {}
        runtime.last_playback = {}
        runtime.last_resolved_media = {}
        self.assertEqual(entity.native_value, "Alive")

        runtime.last_resolved_media = {"artist": "Pearl Jam"}
        self.assertEqual(entity.native_value, "Pearl Jam")

    def test_last_track_sensor_is_push_only_and_writes_only_on_change(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={"last_track": "Alive"},
            last_playback={},
            last_resolved_media={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTrackSensor(runtime)

        self.assertFalse(entity._attr_should_poll)

        entity._handle_runtime_update()
        entity._handle_runtime_update()
        runtime.device_status["last_track"] = "Black"
        entity._handle_runtime_update()

        self.assertEqual(entity.write_count, 2)

    def test_last_command_sensor_reads_runtime_last_text(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text="Speel Pearl Jam",
            last_stt_text="ik wil pearl jam starten",
            last_dj_text="Daar is Pearl Jam",
            last_intent={"action": "play"},
            last_spotify_search={
                "query": "ik wil pearl jam starten",
                "selected": {"title": "Alive", "artist": "Pearl Jam"},
            },
            last_resolved_media={"title": "Alive", "artist": "Pearl Jam"},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTextSensor(runtime)

        self.assertTrue(entity.available)
        self.assertEqual(entity.native_value, "Daar is Pearl Jam")
        self.assertEqual(entity.extra_state_attributes["last_text"], "Speel Pearl Jam")
        self.assertEqual(entity.extra_state_attributes["last_dj_text"], "Daar is Pearl Jam")
        self.assertEqual(entity.extra_state_attributes["last_stt_text"], "ik wil pearl jam starten")
        self.assertEqual(entity.extra_state_attributes["last_intent"], {"action": "play"})
        self.assertEqual(
            entity.extra_state_attributes["last_spotify_search"]["selected"]["title"],
            "Alive",
        )
        self.assertEqual(
            entity.extra_state_attributes["last_resolved_media"]["artist"],
            "Pearl Jam",
        )

    def test_last_command_sensor_keeps_cached_value_when_runtime_becomes_empty(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text="ik wil pearl jam starten",
            last_stt_text="ik wil pearl jam starten",
            last_dj_text="Daar is Pearl Jam",
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            device_status={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTextSensor(runtime)

        self.assertEqual(entity.native_value, "Daar is Pearl Jam")
        runtime.last_text = None
        runtime.last_stt_text = None
        runtime.last_dj_text = None
        self.assertEqual(entity.native_value, "Daar is Pearl Jam")
        self.assertEqual(
            entity.extra_state_attributes["last_stt_text"],
            "Daar is Pearl Jam",
        )

    def test_last_command_sensor_is_push_only_and_writes_only_on_change(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text="ik wil pearl jam starten",
            last_stt_text="ik wil pearl jam starten",
            last_dj_text="Daar is Pearl Jam",
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            device_status={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTextSensor(runtime)

        self.assertFalse(entity._attr_should_poll)

        entity._handle_runtime_update()
        entity._handle_runtime_update()
        runtime.last_dj_text = "Pearl Jam staat klaar."
        entity._handle_runtime_update()

        self.assertEqual(entity.write_count, 2)

    def test_last_corrected_stt_sensor_keeps_cached_value_when_runtime_becomes_empty(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text="speel nummer Lithium van Nirvana",
            last_stt_text="speel nummer litiem van nervana",
            last_corrected_text="speel nummer Lithium van Nirvana",
            listeners=[],
        )
        entity = self.sensor.DJConnectLastCorrectedSttSensor(runtime)

        self.assertTrue(entity.available)
        self.assertEqual(entity.native_value, "speel nummer Lithium van Nirvana")
        self.assertEqual(
            entity.extra_state_attributes["last_stt_text"],
            "speel nummer litiem van nervana",
        )

        runtime.last_corrected_text = None
        runtime.last_stt_text = None
        runtime.last_text = None

        self.assertEqual(entity.native_value, "speel nummer Lithium van Nirvana")
        self.assertEqual(
            entity.extra_state_attributes["full_value"],
            "speel nummer Lithium van Nirvana",
        )

    def test_last_command_sensor_restores_persisted_dj_response_text(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text=None,
            last_stt_text=None,
            last_dj_text=None,
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            device_status={
                "last_command": "ik wil pearl jam starten",
                "last_dj_text": "Daar is Pearl Jam",
            },
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTextSensor(runtime)

        self.assertEqual(entity.native_value, "Daar is Pearl Jam")
        self.assertEqual(entity.extra_state_attributes["last_dj_text"], "Daar is Pearl Jam")

    def test_last_command_sensor_skips_assist_prompt_leak_error(self) -> None:
        leaked = (
            "Sorry, ik kan Gebruik deze DJ response prompt als stijl-/inhoudsinstructie "
            "Maak een korte gesproken DJ-aankondiging in het Nederlands Media type artist "
            "artiest Red Hot Chili Peppers Antwoord alleen met de tekst die uitgesproken "
            "moet worden Geen JSON geen uitleg geen URI niet vinden"
        )
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text="zet red hot chili peppers op",
            last_stt_text="zet red hot chili peppers op",
            last_dj_text=leaked,
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            device_status={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTextSensor(runtime)

        self.assertEqual(entity.native_value, "zet red hot chili peppers op")
        self.assertEqual(entity.extra_state_attributes["full_value"], leaked)
        self.assertTrue(entity.extra_state_attributes["state_prompt_leak_ignored"])
        self.assertEqual(entity.extra_state_attributes["last_dj_text"], leaked)

    def test_last_command_sensor_truncates_long_state_text(self) -> None:
        long_text = "x" * 300
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_text=None,
            last_stt_text=None,
            last_dj_text=long_text,
            last_intent=None,
            last_spotify_search=None,
            last_resolved_media=None,
            device_status={},
            listeners=[],
        )
        entity = self.sensor.DJConnectLastTextSensor(runtime)

        self.assertEqual(len(entity.native_value), 255)
        self.assertTrue(entity.native_value.endswith("…"))
        self.assertEqual(entity.extra_state_attributes["full_value"], long_text)
        self.assertTrue(entity.extra_state_attributes["state_truncated"])

    def test_status_sensor_exposes_voice_and_spotify_debug_attributes(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            last_error=None,
            last_stt_text="ik wil pearl jam starten",
            last_spotify_search={"query": "pearl jam", "returned": 1},
            last_resolved_media={"title": "Alive"},
            last_dj_text="Daar is Pearl Jam",
            last_dj_response_debug={"fallback_used": True, "block_reason": "test"},
            last_playback={
                "has_playback": True,
                "is_playing": False,
                "device": {"name": "Woonkamer"},
            },
            device_status={
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "firmware": "3.1.83",
                "queue": {"items": [{"title": "Noisy"}]},
            },
            ota_in_progress=False,
            ota_last_error=None,
            listeners=[],
        )
        entity = self.sensor.DJConnectStatusSensor(runtime)

        attrs = entity.extra_state_attributes
        self.assertEqual(attrs["last_stt_text"], "ik wil pearl jam starten")
        self.assertEqual(attrs["last_spotify_search"]["query"], "pearl jam")
        self.assertEqual(attrs["last_resolved_media"]["title"], "Alive")
        self.assertTrue(attrs["last_dj_response_debug"]["fallback_used"])
        self.assertEqual(attrs["playback_state"], "idle")
        self.assertEqual(attrs["playback_device"], "Woonkamer")
        self.assertNotIn("device_status", attrs)
        self.assertNotIn("last_playback", attrs)

    def test_app_version_sensor_prefers_app_version_for_apple_clients(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={
                "client_type": "macos",
                "app_version": "3.1.46",
                "version": "3.1.46",
                "firmware": "3.1.43",
            },
            listeners=[],
        )
        entity = self.sensor.DJConnectFirmwareSensor(runtime)

        self.assertEqual(entity.native_value, "3.1.46")

    def test_version_sensor_keeps_cached_value_after_sparse_status_sync(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={
                "client_type": "windows",
                "app_version": "3.2.0",
                "version": "3.2.0",
            },
            listeners=[],
        )
        entity = self.sensor.DJConnectFirmwareSensor(runtime)

        self.assertEqual(entity.native_value, "3.2.0")
        runtime.device_status = {"client_type": "windows", "app_version": "", "version": "unknown"}
        self.assertEqual(entity.native_value, "3.2.0")

        runtime.device_status = {"client_type": "windows", "app_version": "3.2.1"}
        self.assertEqual(entity.native_value, "3.2.1")

    def test_app_version_sensor_falls_back_to_legacy_firmware(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={"client_type": "esp32", "firmware": "3.1.85"},
            listeners=[],
        )
        entity = self.sensor.DJConnectFirmwareSensor(runtime)

        self.assertEqual(entity.native_value, "3.1.85")

    def test_queue_sensor_reads_dict_items_and_context(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={
                "queue": {
                    "items": [{"title": "Song"}],
                    "context": {"uri": "spotify:playlist:abc"},
                    "currently_playing": {"title": "Current"},
                }
            },
            last_playback={},
            listeners=[],
        )
        entity = self.sensor.DJConnectQueueSensor(runtime)

        self.assertEqual(entity.native_value, 1)
        self.assertEqual(entity.extra_state_attributes["items"], [{"title": "Song"}])
        self.assertEqual(
            entity.extra_state_attributes["context"],
            {"uri": "spotify:playlist:abc"},
        )
        self.assertEqual(
            entity.extra_state_attributes["currently_playing"],
            {"title": "Current"},
        )

    def test_queue_sensor_falls_back_to_playback_context(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            device_status={},
            last_playback={"queue_context": "spotify:playlist:def"},
            listeners=[],
        )
        entity = self.sensor.DJConnectQueueSensor(runtime)

        self.assertIsNone(entity.native_value)
        self.assertEqual(entity.extra_state_attributes["context"], "spotify:playlist:def")

        runtime.device_status["queue"] = []
        self.assertEqual(entity.native_value, 0)


if __name__ == "__main__":
    unittest.main()
