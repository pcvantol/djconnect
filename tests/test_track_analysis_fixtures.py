from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [
    ROOT / "examples" / "ask_dj_track_analysis_v2_response.json",
    ROOT / "examples" / "ask_dj_track_analysis_v2_unavailable.json",
]
CONFIDENCE_VALUES = {"low", "medium", "high"}
REQUIRED_TOP_LEVEL_ARRAYS = ("items", "images", "links", "sources", "playback_actions")
REQUIRED_ANALYSIS_ARRAYS = ("sections", "timeline", "dj_tips", "providers", "limitations")


class TrackAnalysisFixtureContractTest(unittest.TestCase):
    def test_track_analysis_v2_fixtures_are_valid_client_contracts(self) -> None:
        for path in FIXTURES:
            with self.subTest(path=path.name):
                response = _load_json(path)
                self.assertTrue(response["success"])
                self.assertEqual(response["action"], "track_analysis")
                self.assertEqual(response["intent"]["category"], "informational")
                self.assertEqual(response["intent"]["intent"], "technical_track_analysis")
                self.assertEqual(response["intent"]["action"], "track_analysis")
                self.assertEqual(response["playback_actions"], [])
                for key in REQUIRED_TOP_LEVEL_ARRAYS:
                    self.assertIsInstance(response.get(key), list, key)

                analysis = response["analysis"]
                self.assertEqual(analysis["contract_version"], 2)
                self.assertIn(analysis["mode"], {"knowledge_plus_metadata", "measured_plus_knowledge", "measured", "unavailable"})
                self.assertIn(analysis["confidence"], CONFIDENCE_VALUES)
                self.assertIsInstance(analysis["measured"], dict)
                self.assertIsInstance(analysis["inferred"], dict)
                for key in REQUIRED_ANALYSIS_ARRAYS:
                    self.assertIsInstance(analysis.get(key), list, key)

                for section in analysis["sections"]:
                    self.assertIsInstance(section.get("id"), str)
                    self.assertIsInstance(section.get("title"), str)
                    self.assertIsInstance(section.get("kind"), str)
                    self.assertIsInstance(section.get("source"), str)
                    self.assertIn(section.get("confidence"), CONFIDENCE_VALUES)
                    self.assertIsInstance(section.get("items", []), list)
                    for item in section.get("items", []):
                        self.assertIsInstance(item.get("label"), str)
                        self.assertIsInstance(item.get("value"), str)
                        self.assertIsInstance(item.get("source"), str)

                for entry in analysis["timeline"]:
                    self.assertEqual(entry.get("kind"), "section")
                    self.assertEqual(entry.get("source"), "measured")
                    self.assertIsInstance(entry.get("label"), str)
                    for key in ("start_ms", "duration_ms", "end_ms"):
                        if key in entry:
                            self.assertIsInstance(entry[key], int)
                    if "start_ms" in entry and "duration_ms" in entry and "end_ms" in entry:
                        self.assertEqual(entry["start_ms"] + entry["duration_ms"], entry["end_ms"])

                for tip in analysis["dj_tips"]:
                    self.assertIsInstance(tip.get("kind"), str)
                    self.assertIsInstance(tip.get("title"), str)
                    self.assertIsInstance(tip.get("text"), str)
                    self.assertIsInstance(tip.get("source"), str)
                    self.assertIn(tip.get("confidence"), CONFIDENCE_VALUES)

                for provider in analysis["providers"]:
                    self.assertIsInstance(provider.get("provider_id"), str)
                    self.assertIsInstance(provider.get("display_name"), str)
                    self.assertIn(provider.get("status"), {"used", "skipped", "unavailable", "error"})
                    self.assertIsInstance(provider.get("requires_config"), bool)
                    if "reason" in provider:
                        self.assertIsInstance(provider["reason"], str)

    def test_happy_path_fixture_contains_renderable_v2_blocks(self) -> None:
        response = _load_json(FIXTURES[0])
        analysis = response["analysis"]
        section_ids = {section["id"] for section in analysis["sections"]}
        self.assertIn("rhythm_bpm", section_ids)
        self.assertIn("energy_curve", section_ids)
        self.assertIn("buildup", section_ids)
        self.assertIn("metadata_context", section_ids)
        self.assertIn("limitations", section_ids)
        self.assertGreaterEqual(len(analysis["timeline"]), 1)
        self.assertTrue(any(tip["kind"] == "mixing" for tip in analysis["dj_tips"]))
        self.assertTrue(any(provider["provider_id"] == "spotify_measured" for provider in analysis["providers"]))
        self.assertTrue(any(provider["provider_id"] == "metabrainz_metadata" for provider in analysis["providers"]))
        self.assertTrue(any(source["source"] == "spotify_audio_analysis" for source in response["sources"]))
        self.assertTrue(any(source["source"] == "metabrainz_metadata" for source in response["sources"]))

    def test_unavailable_fixture_stays_empty_and_explicit(self) -> None:
        response = _load_json(FIXTURES[1])
        analysis = response["analysis"]
        self.assertEqual(analysis["mode"], "unavailable")
        self.assertEqual(analysis["sections"], [])
        self.assertEqual(analysis["timeline"], [])
        self.assertEqual(analysis["dj_tips"], [])
        self.assertTrue(all(provider["status"] == "skipped" for provider in analysis["providers"]))
        self.assertGreaterEqual(len(analysis["limitations"]), 1)
        self.assertEqual(response["items"], [])
        self.assertEqual(response["sources"], [])


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value
