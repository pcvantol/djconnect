from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VibeCastDocsTest(unittest.TestCase):
    def test_api_contract_documents_vibecast_parity_and_response_contract(self) -> None:
        text = (ROOT / "API_CONTRACT.md").read_text(encoding="utf-8")

        required = [
            "GET /api/djconnect/v1/vibecast",
            "`client_type:\"macos\"` and `client_type:\"ios\"`",
            "same endpoint, response contract, item kinds, structured text segment types",
            "`track_fact`",
            "`artist_fact`",
            "`listening_tip`",
            "`text`, `strong`, `emphasis`, `magnify`, `accent` and",
            "`emoji`, and `line_break`",
            "1-3 decorative music/vibe symbols",
            "`feature_disabled`",
            "`premium_unavailable`",
            "`no_active_playback`",
            "`provider_unavailable`",
            "\"ttl_seconds\": 45",
            "\"poll_after_seconds\": 20",
            "\"enabled\": false",
        ]
        for snippet in required:
            self.assertIn(snippet, text)

    def test_readme_and_sync_prompt_keep_vibecast_client_guidance(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        sync_prompts = (ROOT / "SYNC_PROMPTS.md").read_text(encoding="utf-8")

        self.assertIn("macOS and iOS use the same endpoint", readme)
        self.assertIn("Clients poll:", sync_prompts)
        self.assertIn("GET /api/djconnect/v1/vibecast", sync_prompts)
        self.assertIn("Platform differences are presentation-only", sync_prompts)
        self.assertIn("emoji_safe", sync_prompts)
        self.assertIn("`emoji`", sync_prompts)
        self.assertIn("never show raw", sync_prompts)

    def test_music_discovery_docs_cover_deduped_based_on_counts(self) -> None:
        api_contract = (ROOT / "API_CONTRACT.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        sync_prompts = (ROOT / "SYNC_PROMPTS.md").read_text(encoding="utf-8")

        for text in (api_contract, readme, sync_prompts):
            self.assertIn("play_count", text)
            self.assertIn("based_on_count", text)
        self.assertIn("Repeated recent plays are aggregated", api_contract)
        self.assertIn("one item per unique `id`/`uri`", readme)
        self.assertIn("Client: Music Discovery", sync_prompts)
        self.assertIn("4x afgespeeld", sync_prompts)


if __name__ == "__main__":
    unittest.main()
