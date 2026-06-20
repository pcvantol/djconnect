from __future__ import annotations

import importlib
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


class SmartHomeContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        cls.context = importlib.import_module("custom_components.djconnect.smart_home_context")

    def test_normalize_entity_allowlist(self) -> None:
        self.assertEqual(
            self.context.normalize_entity_allowlist(
                "sensor.outdoor_rain, climate.living_room\nsensor.outdoor_rain, invalid"
            ),
            ["sensor.outdoor_rain", "climate.living_room"],
        )

    def test_reads_only_allowed_entities(self) -> None:
        class States:
            def __init__(self):
                self.values = {
                    "sensor.outdoor_rain": types.SimpleNamespace(
                        state="regen",
                        name="Regen buiten",
                        attributes={"friendly_name": "Regen buiten"},
                    ),
                    "sensor.secret": types.SimpleNamespace(
                        state="private",
                        name="Secret",
                        attributes={},
                    ),
                }

            def get(self, entity_id):
                return self.values.get(entity_id)

        runtime = types.SimpleNamespace(
            config={"smart_home_context_entities": ["sensor.outdoor_rain"]},
            options={},
        )
        result = self.context.smart_home_context(types.SimpleNamespace(states=States()), runtime)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["entity_id"], "sensor.outdoor_rain")
        self.assertEqual(result[0]["state"], "regen")


if __name__ == "__main__":
    unittest.main()
