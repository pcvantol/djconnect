from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "custom_components" / "djconnect" / "services.yaml"


class ServicesYamlTest(unittest.TestCase):
    def test_developer_actions_are_documented(self) -> None:
        text = SERVICES.read_text()
        compact_text = " ".join(text.split())

        for service in (
            "test_parse",
            "test_tts",
            "test_command",
            "test_ptt_text",
            "test_apns_push",
            "music_backend_status",
            "start_spotify_oauth",
            "device_command",
            "refresh_device_info",
            "ask_dj",
            "clear_ask_dj_history",
            "ask_dj_history_state",
        ):
            with self.subTest(service=service):
                self.assertIn(f"{service}:", text)

        self.assertIn("Developer test", text)
        self.assertIn("Developer helper", text)
        self.assertIn("temporary WAV or MP3 audio_url", text)
        self.assertIn("start exactly after STT conversion", compact_text)
        self.assertIn("APNs push readiness", text)
        self.assertIn("diagnostic dry-run", text)
        self.assertIn("selected backend search/playback", compact_text)
        self.assertIn("Music backend status", text)
        self.assertIn("Music Assistant selection", text)
        self.assertIn("Ask DJ text request", text)
        self.assertIn("clear local Ask DJ chat history", compact_text)
        self.assertIn("/api/djconnect/spotify/callback", text)
        self.assertNotIn("/api/djconnect/spotify_callback", text)
        self.assertNotIn("stuur", text.lower())
        self.assertNotIn("zonder Spotify playback", text)

    def test_test_command_documents_play_flag(self) -> None:
        text = SERVICES.read_text()
        test_command_text = text.split("\ntest_ptt_text:", 1)[0]

        self.assertIn("command_text:", text)
        self.assertIn("dj_response_text:", text)
        self.assertNotIn("\n    text:\n      name:", test_command_text)
        self.assertIn("play:", text)
        self.assertIn("Start playback", text)
        self.assertIn("without starting playback on the selected backend", text)


if __name__ == "__main__":
    unittest.main()
