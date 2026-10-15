"""Presentation-only label resolution does not alter protocol choices."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/djconnect/flow_labels.py"
spec = importlib.util.spec_from_file_location("djc_flow_labels_unit", PATH)
labels = importlib.util.module_from_spec(spec)
spec.loader.exec_module(labels)


class FlowLabelsTest(unittest.TestCase):
    def test_catalogue_covers_five_languages_and_normalizes_regions(self):
        self.assertEqual(set(labels.LABELS), {"en", "nl", "de", "fr", "es"})
        expected = set(labels.LABELS["en"])
        for language, catalogue in labels.LABELS.items():
            self.assertEqual(set(catalogue), expected)
            for key, text in catalogue.items():
                self.assertTrue(text.strip())
                for region in (language, language.upper() + "_XX", language + "-XX"):
                    hass = SimpleNamespace(config=SimpleNamespace(language=region))
                    self.assertEqual(labels.flow_label(hass, key), text)

    def test_unknown_locale_uses_english_without_exposing_a_key(self):
        for language in ("it", "", None):
            hass = SimpleNamespace(config=SimpleNamespace(language=language))
            for key, text in labels.LABELS["en"].items():
                self.assertEqual(labels.flow_label(hass, key), text)
        self.assertEqual(labels.flow_label(None, "default"), "Default")


if __name__ == "__main__":
    unittest.main()
