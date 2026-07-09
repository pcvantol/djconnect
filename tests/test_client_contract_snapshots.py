from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "examples" / "client_contracts"
SOURCE_MANIFEST = "contract_manifest.json"


def _load_snapshot(name: str) -> dict:
    return json.loads((SNAPSHOT_DIR / name).read_text(encoding="utf-8"))


class ClientContractSnapshotsTest(unittest.TestCase):
    def test_manifest_lists_all_exported_contract_fixtures(self) -> None:
        manifest = _load_snapshot(SOURCE_MANIFEST)
        fixture_files = {entry["file"] for entry in manifest["fixtures"]}
        actual_files = {
            path.name
            for path in SNAPSHOT_DIR.glob("*.json")
            if path.name != SOURCE_MANIFEST
        }

        self.assertEqual(manifest["format"], "djconnect.client_contract_fixtures")
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(fixture_files, actual_files)
        for entry in manifest["fixtures"]:
            self.assertLessEqual({"id", "file", "transport", "contract"}, set(entry))
            self.assertTrue((SNAPSHOT_DIR / entry["file"]).is_file())

    def test_capabilities_snapshot_matches_websocket_contract(self) -> None:
        websocket_api = _load_websocket_api()
        snapshot = _load_snapshot("capabilities.websocket.json")

        commands = websocket_api._supported_websocket_commands()
        generated = {
            "success": True,
            "domain": "djconnect",
            "websocket_supported": True,
            "commands": commands,
            "features": websocket_api._feature_capabilities(commands),
            "fallbacks": {
                key: websocket_api._capability_fallbacks(commands)[key]
                for key in ("music_dna", "music_discovery", "music_discovery_feedback")
            },
            "capabilities": websocket_api._platform_capabilities(),
            "contract_versions": websocket_api._contract_versions(),
            "transports": {
                "http": True,
                "websocket": True,
            },
        }

        self.assertEqual(snapshot, generated)
        self.assertTrue(snapshot["capabilities"]["profiles"])
        self.assertTrue(snapshot["capabilities"]["explicit_profile_selection"])
        self.assertEqual(snapshot["contract_versions"]["profile_context"], 1)

    def test_music_dna_profile_snapshots_cover_disabled_empty_and_rich_states(self) -> None:
        disabled = _load_snapshot("music_dna.profile.disabled.json")
        empty = _load_snapshot("music_dna.profile.empty.json")
        rich = _load_snapshot("music_dna.profile.rich.json")

        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["profile"], {})

        self.assertTrue(empty["enabled"])
        self.assertIn("summary", empty["profile"])
        self.assertIn("privacy_dashboard", empty["profile"])
        self.assertNotIn("recent_tracks", empty["profile"])
        self.assertNotIn("snapshot_history", empty["profile"])

        profile = rich["profile"]
        self.assertLessEqual(
            {
                "summary",
                "favorite_genres",
                "recent_tracks",
                "top_tracks_by_range",
                "top_artists_by_range",
                "snapshot_history",
                "discovery_feedback",
                "privacy_dashboard",
            },
            set(profile),
        )
        self.assertEqual(profile["snapshot_history"][0]["captured_at"], "2026-07-09T10:00:00+00:00")
        self.assertEqual(profile["discovery_feedback"]["accepted_items"][0]["quality_band"], "high")
        self._assert_privacy_dashboard(profile["privacy_dashboard"])

    def test_music_discovery_feed_snapshot_is_client_rendering_contract(self) -> None:
        snapshot = _load_snapshot("music_discovery.feed.json")

        self.assertTrue(snapshot["enabled"])
        self.assertEqual(snapshot["source"], "music_dna")
        self.assertEqual(snapshot["cache"], {"hit": False})
        self.assertTrue(snapshot["sections"])
        section = snapshot["sections"][0]
        self.assertEqual(set(section), {"id", "title", "items"})
        item = section["items"][0]
        self.assertLessEqual(
            {
                "id",
                "kind",
                "title",
                "subtitle",
                "uri",
                "image_url",
                "reason",
                "reason_sources",
                "confidence",
                "quality_score",
                "quality_band",
                "quality_factors",
            },
            set(item),
        )
        self.assertTrue(item["uri"].startswith("spotify:"))
        self.assertEqual(item["quality_band"], "high")
        self.assertNotIn("playback_actions", item)
        self.assertNotIn("command", item)

    def test_ask_dj_recently_played_snapshot_is_informational_list_contract(self) -> None:
        snapshot = _load_snapshot("ask_dj.recently_played_history.json")

        self.assertTrue(snapshot["success"])
        self.assertEqual(snapshot["action"], "none")
        self.assertEqual(snapshot["intent"]["category"], "informational")
        self.assertEqual(snapshot["intent"]["intent"], "recently_played_history")
        self.assertEqual(snapshot["intent"]["item_type"], "tracks")
        self.assertEqual(snapshot["playback_actions"], [])
        self.assertEqual(snapshot["confirmation_actions"], [])
        self.assertEqual(snapshot["links"], [])
        self.assertEqual(snapshot["sources"][0]["source"], "spotify_recently_played")
        self.assertEqual(snapshot["images"][0]["source"], "spotify_recently_played")
        self.assertEqual(snapshot["items"][0]["image_url"], snapshot["images"][0]["url"])

    def test_profile_context_request_fixture_covers_client_classes(self) -> None:
        snapshot = _load_snapshot("profile_context.requests.json")
        requests = snapshot["requests"]

        self.assertEqual(snapshot["contract_version"], 1)
        for key in (
            "apple_explicit_profile",
            "windows_device_mapped",
            "pi_shared_ambient",
            "esp32_ptt",
            "ha_voice_derived",
            "private_session",
        ):
            self.assertIn(key, requests)
        self.assertEqual(requests["apple_explicit_profile"]["client_type"], "ios")
        self.assertEqual(requests["windows_device_mapped"]["client_type"], "windows")
        self.assertEqual(requests["pi_shared_ambient"]["client_type"], "raspberry_pi")
        self.assertEqual(requests["esp32_ptt"]["client_type"], "esp32")
        self.assertNotIn("device_id", requests["ha_voice_derived"])
        self.assertIn("server_context", requests["ha_voice_derived"])
        self.assertTrue(requests["private_session"]["private_session"])

    def test_profile_context_response_fixture_is_minimal_and_privacy_safe(self) -> None:
        snapshot = _load_snapshot("profile_context.responses.json")
        responses = snapshot["responses"]

        personal = responses["personal_profile"]
        self.assertEqual(personal["resolved_profile"]["id"], personal["profile_id"])
        self.assertEqual(personal["resolution"]["source"], "device_mapping")
        self.assertNotIn("music_dna", personal["resolved_profile"])
        self.assertNotIn("history", json.dumps(personal).casefold())

        shared = responses["shared_profile"]
        self.assertEqual(shared["resolved_profile"]["privacy_mode"], "shared")
        self.assertEqual(shared["resolution"]["source"], "area_mapping")

        private = responses["private_session"]
        self.assertTrue(private["profile_privacy"]["private_session"])
        self.assertFalse(private["profile_privacy"]["allow_history"])
        self.assertFalse(private["profile_privacy"]["allow_music_dna_updates"])

    def test_profile_context_error_fixture_defines_stable_codes(self) -> None:
        snapshot = _load_snapshot("profile_context.errors.json")
        errors = snapshot["errors"]

        expected = {
            "profile_required",
            "profile_not_found",
            "device_not_mapped",
            "backend_not_configured",
            "music_account_not_configured",
            "backend_account_mismatch",
            "profile_access_denied",
            "private_session_restriction",
            "invalid_client_type",
            "invalid_request_context",
        }
        self.assertEqual(set(errors), expected)
        for error in errors.values():
            self.assertFalse(error["retryable"])
            self.assertIn("error", error)
            self.assertIn("http_status", error)
            self.assertIn("client_behavior", error)
        self.assertEqual(errors["profile_required"]["http_status"], 428)
        self.assertEqual(errors["profile_not_found"]["error"], "invalid_profile")
        self.assertEqual(errors["device_not_mapped"]["http_status"], 409)

    def test_snapshots_do_not_contain_secrets_or_raw_audio(self) -> None:
        forbidden = (
            "access_token",
            "refresh_token",
            "authorization",
            "bearer ",
            "client_secret",
        )
        for path in sorted(SNAPSHOT_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").casefold()
                for value in forbidden:
                    self.assertNotIn(value, text)
                payload = json.loads(path.read_text(encoding="utf-8"))
                self._assert_no_raw_audio_values(payload)

    def _assert_privacy_dashboard(self, privacy: dict) -> None:
        self.assertTrue(privacy["enabled"])
        self.assertIsInstance(privacy["data_sources"], list)
        self.assertTrue(privacy["controls"]["clear_supported"])
        for source in privacy["data_sources"]:
            self.assertLessEqual({"id", "label", "enabled"}, set(source))
        self.assertFalse(privacy["stores_raw_audio"])
        self.assertFalse(privacy["stores_oauth_tokens"])
        self.assertFalse(privacy["stores_full_prompts"])

    def _assert_no_raw_audio_values(self, value) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "stores_raw_audio":
                    self.assertFalse(item)
                    continue
                self._assert_no_raw_audio_values(item)
            return
        if isinstance(value, list):
            for item in value:
                self._assert_no_raw_audio_values(item)
            return
        if isinstance(value, str):
            self.assertNotIn("raw_audio", value.casefold())

    def test_export_script_copies_complete_fixture_set(self) -> None:
        output = ROOT / ".tmp_client_contract_export"
        if output.exists():
            for path in output.iterdir():
                if path.is_file():
                    path.unlink()
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "export_client_contracts.py"),
                "--output",
                str(output),
                "--clean",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            self.assertIn("Exported", result.stdout)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            expected = {"manifest.json", "README.md", *(entry["file"] for entry in manifest["fixtures"])}
            self.assertEqual({path.name for path in output.iterdir() if path.is_file()}, expected)
        finally:
            if output.exists():
                for path in output.iterdir():
                    if path.is_file():
                        path.unlink()
                output.rmdir()


def _load_websocket_api():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))
    voluptuous.Required = lambda key: key
    voluptuous.Optional = lambda key, default=None: key
    websocket_stub = types.ModuleType("homeassistant.components.websocket_api")
    websocket_stub.async_register_command = lambda hass, command: None
    websocket_stub.websocket_command = lambda schema: lambda func: func
    websocket_stub.async_response = lambda func: func
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    components = sys.modules.setdefault("homeassistant.components", types.ModuleType("homeassistant.components"))
    components.websocket_api = websocket_stub
    homeassistant.components = components
    sys.modules["homeassistant.components.websocket_api"] = websocket_stub
    sys.modules.pop("custom_components.djconnect.websocket_api", None)
    return importlib.import_module("custom_components.djconnect.websocket_api")


if __name__ == "__main__":
    unittest.main()
