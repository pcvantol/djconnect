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

    def test_recent_ask_dj_intents_are_documented_for_clients(self) -> None:
        data = json.loads((ROOT / "examples" / "voice_intents.json").read_text())
        ask = data["ask_dj_intents"]

        artist_items = ask["artist_item_list"]
        self.assertFalse(artist_items["plays_music"])
        self.assertEqual(artist_items["intent"], "artist_item_list")
        self.assertIn("Welke muziek heeft Scooter gemaakt?", artist_items["nl"])
        self.assertIn("What music has Scooter made?", artist_items["en"])
        self.assertIn("Play Now", artist_items["response_shape"]["button_labels"])

        versions = ask["current_track_versions"]
        self.assertFalse(versions["plays_music"])
        self.assertEqual(versions["intent"], "current_track_versions")
        self.assertIn("Heb je een live versie?", versions["nl"])
        self.assertIn("Heb je een akoestische versie?", versions["nl"])
        self.assertIn("Heb je remixes?", versions["nl"])
        self.assertIn("Play Now", versions["response_shape"]["button_labels"])

        save = ask["save_current_track"]
        self.assertFalse(save["plays_music"])
        self.assertEqual(save["action"], "set_current_track_favorite")
        self.assertEqual(save["response_shape"]["images"], [])
        self.assertEqual(save["response_shape"]["playback_actions"], [])
        self.assertIn("Zet huidig nummer in favorieten", save["nl"])
        self.assertIn("Haal huidig nummer uit favorieten", save["nl"])
        self.assertIn("Save this track to liked songs", save["en"])

        seed = ask["seed_playlist_mix"]
        self.assertIn("Heb je meer nummers die hierop lijken?", seed["nl"])
        self.assertIn("Speel vergelijkbare nummers", seed["nl"])
        self.assertIn("Queue similar tracks", seed["en"])

    def test_backend_contract_wording_is_backend_neutral(self) -> None:
        data = json.loads((ROOT / "examples" / "voice_intents.json").read_text())

        playback = data["intents"]["playback_control"]
        self.assertIn("selected DJConnect backend", playback["description"])
        self.assertNotIn("Spotify backend command", playback["description"])

        outputs = data["ask_dj_intents"]["speaker_outputs"]
        self.assertIn("backend output", outputs["description"])
        self.assertNotIn("Spotify output devices", outputs["description"])

        seed = data["ask_dj_intents"]["seed_playlist_mix"]
        self.assertIn("backend-aware Play Now actions", seed["description"])


if __name__ == "__main__":
    unittest.main()
