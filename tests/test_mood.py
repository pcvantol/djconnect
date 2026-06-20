from __future__ import annotations

import importlib
import unittest


class MoodZoneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mood = importlib.import_module("custom_components.djconnect.mood")

    def test_watch_mood_zone_boundaries(self) -> None:
        cases = {
            0: "Chill",
            24: "Chill",
            25: "Groove",
            59: "Groove",
            60: "Energy",
            84: "Energy",
            85: "Party",
            100: "Party",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                zone = self.mood.mood_zone_for_value(value)
                self.assertIsNotNone(zone)
                self.assertEqual(zone.name, expected)

    def test_unknown_mood_stays_unknown(self) -> None:
        self.assertIsNone(self.mood.mood_zone_for_value(None))
        self.assertIsNone(self.mood.mood_zone_for_value("unknown"))


if __name__ == "__main__":
    unittest.main()
