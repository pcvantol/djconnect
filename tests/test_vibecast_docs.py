from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VibeCastDocsTest(unittest.TestCase):
    def test_api_contract_documents_vibecast_parity_and_response_contract(self) -> None:
        text = (ROOT / "API_CONTRACT.md").read_text(encoding="utf-8")

        required = [
            "GET /api/djconnect/vibecast",
            "`client_type:\"macos\"` and `client_type:\"ios\"`",
            "same endpoint, response contract, item kinds, structured text segment types",
            "`track_fact`",
            "`artist_fact`",
            "`listening_tip`",
            "`text`, `strong`, `emphasis`, `magnify`, `accent` and",
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
        self.assertIn("GET /api/djconnect/vibecast", sync_prompts)
        self.assertIn("Platform differences are presentation-only", sync_prompts)
        self.assertIn("never show raw", sync_prompts)


if __name__ == "__main__":
    unittest.main()
