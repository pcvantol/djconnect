from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class VoiceIntentDataTest(unittest.TestCase):
    def test_personal_memory_summary_intent_is_documented(self) -> None:
        data = json.loads((ROOT / "examples" / "voice_intents.json").read_text())
        intent = data["ask_dj_intents"]["personal_memory_summary"]

        self.assertFalse(intent["plays_music"])
        self.assertEqual(intent["intent"], "personal_memory_summary")
        self.assertEqual(intent["action"], "memory_summary")
        self.assertEqual(intent["response_shape"]["images"], [])
        self.assertEqual(intent["response_shape"]["playback_actions"], [])
        self.assertEqual(intent["response_shape"]["sources"], ["djconnect_memory"])
        self.assertIn("Wat weet je nu over mij?", intent["nl"])
        self.assertIn("What do you know about me?", intent["en"])


if __name__ == "__main__":
    unittest.main()
