from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest

from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]
VARIANTS_PATH = ROOT / "examples" / "ask_dj_intent_variants.json"


class AskDjIntentVariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        cls.ask_dj = importlib.import_module("custom_components.djconnect.ask_dj")
        with VARIANTS_PATH.open(encoding="utf-8") as file:
            cls.variants = json.load(file)

    def test_variant_file_is_large_enough_to_catch_router_regressions(self) -> None:
        self.assertGreaterEqual(len(self.variants), 283)

    def test_variant_ids_and_phrases_are_unique(self) -> None:
        ids = [variant["id"] for variant in self.variants]
        texts = [variant["text"].casefold() for variant in self.variants]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(texts), len(set(texts)))

    def test_ask_dj_intent_variants_classify_as_expected(self) -> None:
        failures: list[str] = []
        for variant in self.variants:
            expected = variant["expect"]
            with self.subTest(variant=variant["id"]):
                intent = self.ask_dj.classify_ask_dj(variant["text"])
                if intent.intent != expected["intent"]:
                    failures.append(
                        f"{variant['id']}: intent expected {expected['intent']!r}, "
                        f"got {intent.intent!r} for {variant['text']!r}"
                    )
                if intent.category != expected["intent_category"]:
                    failures.append(
                        f"{variant['id']}: category expected {expected['intent_category']!r}, "
                        f"got {intent.category!r} for {variant['text']!r}"
                    )
        if failures:
            self.fail("\n".join(failures))
