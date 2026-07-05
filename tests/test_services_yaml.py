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
            "push_register",
            "push_unregister",
            "music_backend_status",
            "start_spotify_oauth",
            "device_command",
            "queue",
            "playlists",
            "playback_status",
            "playback_devices",
            "playback_command",
            "refresh_device_info",
            "ask_dj",
            "ask_dj_message",
            "ask_dj_idle_suggestion",
            "ask_dj_history",
            "vibecast_feed",
            "music_discovery_feed",
            "refresh_music_discovery",
            "play_music_discovery_item",
            "music_dna_profile",
            "set_music_dna_enabled",
            "clear_music_dna",
            "music_dna_export",
            "music_dna_import",
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
        self.assertIn("APNs push registration", text)
        self.assertIn("/api/djconnect/v1/push/register", text)
        self.assertIn("APNs push unregistration", text)
        self.assertIn("/api/djconnect/v1/push/unregister", text)
        self.assertIn("bootstrap proof", text)
        self.assertIn("selected backend search/playback", compact_text)
        self.assertIn("Music backend status", text)
        self.assertIn("Music Assistant selection", text)
        self.assertIn("Music queue", text)
        self.assertIn("command queue", text)
        self.assertIn("Music playlists", text)
        self.assertIn("command playlists", text)
        self.assertIn("Playback status", text)
        self.assertIn("Playback devices", text)
        self.assertIn("Playback command", text)
        self.assertIn("Ask DJ text request", text)
        self.assertIn("/api/djconnect/v1/track_insight", text)
        self.assertIn("djconnect_track_insight event", text)
        self.assertIn("/api/djconnect/v1/ask_dj/message", text)
        self.assertIn("client_message_id", text)
        self.assertIn("history_revision", text)
        self.assertIn("clear_revision", text)
        self.assertIn("VibeCast feed", text)
        self.assertIn("/api/djconnect/v1/vibecast", text)
        self.assertIn("Music Discovery feed", text)
        self.assertIn("/api/djconnect/v1/music_discovery", text)
        self.assertIn("Music DNA profile", text)
        self.assertIn("/api/djconnect/v1/music_dna/profile", text)
        self.assertIn("/api/djconnect/v1/music_dna/settings", text)
        self.assertIn("/api/djconnect/v1/music_dna/clear", text)
        self.assertIn("Music DNA export", text)
        self.assertIn("/api/djconnect/v1/music_dna/export", text)
        self.assertIn("Music DNA import", text)
        self.assertIn("/api/djconnect/v1/music_dna/import", text)
        self.assertIn("clear local chat cache", compact_text)
        self.assertIn("/api/djconnect/v1/spotify/callback", text)
        self.assertNotIn("/api/djconnect/v1/spotify_callback", text)
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
