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


def _load_snapshot(name: str) -> dict:
    return json.loads((SNAPSHOT_DIR / name).read_text(encoding="utf-8"))


class ClientContractSnapshotsTest(unittest.TestCase):
    def test_manifest_lists_all_exported_contract_fixtures(self) -> None:
        manifest = _load_snapshot("manifest.json")
        fixture_files = {entry["file"] for entry in manifest["fixtures"]}
        actual_files = {
            path.name
            for path in SNAPSHOT_DIR.glob("*.json")
            if path.name != "manifest.json"
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
            "transports": {
                "http": True,
                "websocket": True,
            },
        }

        self.assertEqual(snapshot, generated)

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
