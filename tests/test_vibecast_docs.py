from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VibeCastDocsTest(unittest.TestCase):
    def test_api_contract_documents_vibecast_parity_and_response_contract(self) -> None:
        text = (ROOT / "API_CONTRACT.md").read_text(encoding="utf-8")

        required = [
            "GET /api/djconnect/v1/vibecast",
            '`client_type:"macos"` and `client_type:"ios"`',
            "same endpoint, response contract, item kinds, structured text segment types",
            "`track_fact`",
            "`artist_fact`",
            "`listening_tip`",
            "`text`, `strong`, `emphasis`, `magnify`, `accent` and",
            "`emoji`, and `line_break`",
            "1-3 decorative music/vibe symbols",
            "`context.artist_image_url`",
            "`image_url`/`thumbnail_url`",
            "/api/djconnect/v1/image_proxy/...",
            "`feature_disabled`",
            "`premium_unavailable`",
            "`no_active_playback`",
            "`provider_unavailable`",
            '"ttl_seconds": 45',
            '"poll_after_seconds": 20',
            '"enabled": false',
            "`context.genre_badge`",
            "`genre_badge.label`",
            '"placement": "top_trailing"',
        ]
        for snippet in required:
            self.assertIn(snippet, text)

    def test_user_index_and_sync_prompt_keep_authoritative_vibecast_guidance(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        sync_prompts = (ROOT / "SYNC_PROMPTS.md").read_text(encoding="utf-8")

        self.assertIn("docs/README.md", readme)
        self.assertIn("API_CONTRACT.md", (ROOT / "docs/README.md").read_text())
        self.assertIn("Clients poll:", sync_prompts)
        self.assertIn("GET /api/djconnect/v1/vibecast", sync_prompts)
        self.assertIn("Platform differences are presentation-only", sync_prompts)
        self.assertIn("emoji_safe", sync_prompts)
        self.assertIn("`emoji`", sync_prompts)
        self.assertIn("context.artist_image_url", sync_prompts)
        self.assertIn("artist_fact", sync_prompts)
        self.assertIn("image_url", sync_prompts)
        self.assertIn("DJConnect image proxy", sync_prompts)
        self.assertIn("never show raw", sync_prompts)

    def test_music_discovery_docs_cover_recommendation_contract_and_server_refresh(self) -> None:
        api_contract = (ROOT / "API_CONTRACT.md").read_text(encoding="utf-8")
        sync_prompts = (ROOT / "SYNC_PROMPTS.md").read_text(encoding="utf-8")

        for text in (api_contract, sync_prompts):
            self.assertIn("music_discovery_ready", text)
            self.assertIn("Je nieuwe aanbevelingen staan klaar!", text)
            self.assertIn("new_for_you", text)
            self.assertIn("accepted_recommendations", text)
        self.assertIn("server-side about once per hour", api_contract)
        self.assertIn("must not be surfaced as raw Discovery cards", api_contract)
        self.assertIn("08:00 local HA time", api_contract)
        self.assertIn('"refresh_target": "music_discovery"', api_contract)
        self.assertIn("POST /api/djconnect/v1/music_discovery/refresh", api_contract)
        self.assertIn(
            "not a listening-history list",
            (ROOT / "docs/technical/ENTITIES_AND_SUPPORT.md").read_text(),
        )
        self.assertIn(
            'open_target:"music_discovery"',
            (ROOT / "docs/technical/PUSH_NOTIFICATIONS.md").read_text(),
        )
        self.assertIn("Client: Music Discovery", sync_prompts)
        self.assertIn("must not hardcode section ids", sync_prompts)
        self.assertIn('deeplink:"djconnect://music-discovery"', sync_prompts)


if __name__ == "__main__":
    unittest.main()
