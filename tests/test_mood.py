from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
import unittest


class MoodZoneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.mood = importlib.import_module("custom_components.djconnect.mood")
        except ModuleNotFoundError:
            path = (
                Path(__file__).resolve().parents[1]
                / "custom_components"
                / "djconnect"
                / "mood.py"
            )
            spec = importlib.util.spec_from_file_location("djconnect_mood_test", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
            cls.mood = module

    def test_watch_mood_zone_boundaries(self) -> None:
        cases = {
            0: "chill",
            24: "chill",
            25: "groove",
            59: "groove",
            60: "energy",
            84: "energy",
            85: "party",
            100: "party",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                zone = self.mood.mood_zone_for_value(value)
                self.assertIsNotNone(zone)
                self.assertEqual(zone.name, expected)

    def test_unknown_mood_stays_unknown(self) -> None:
        self.assertIsNone(self.mood.mood_zone_for_value(None))
        self.assertIsNone(self.mood.mood_zone_for_value("unknown"))

    def test_missing_mood_does_not_add_zone(self) -> None:
        payload = {"text": "Waarom koos je dit?"}
        self.assertEqual(self.mood.enrich_payload_with_mood_zone(payload), payload)

    def test_mood_is_clamped_before_zone_mapping(self) -> None:
        low = self.mood.mood_zone_for_value(-10)
        high = self.mood.mood_zone_for_value(120)

        self.assertEqual(low.value, 0)
        self.assertEqual(low.name, "chill")
        self.assertEqual(high.value, 100)
        self.assertEqual(high.name, "party")

    def test_mood_announcement_style_text_uses_zone(self) -> None:
        style = self.mood.mood_announcement_style_text({"mood": 70})

        self.assertIn("mood=70", style)
        self.assertIn("zone=energy", style)
        self.assertIn("uptempo", style)


if __name__ == "__main__":
    unittest.main()
