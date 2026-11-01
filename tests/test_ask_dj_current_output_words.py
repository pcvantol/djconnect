"""Current output questions read the music backend, never public research."""

import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class CurrentOutputWordsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def test_reported_question_reads_fresh_output_without_model_or_mutation(self):
        fixture = shared.SharedDialogueTest()
        await fixture.asyncSetUp()
        calls = []

        async def status(hass, runtime, command, *args, **kwargs):
            calls.append(command)
            self.assertEqual(command, "status")
            return {"success": True, "playback": {"device": {"name": "Observed speaker"}}}

        try:
            with patch.object(fixture.core, "run_music_command", status):
                for index, question in enumerate((
                    "welke speaker is nu actief",
                    "Welke speaker is nu actief?",
                    "welke speaker is momenteel actief",
                    "welke luidspreker is nu actief?",
                    "welk apparaat is nu actief?",
                    "welke speaker is actief",
                )):
                    answer, code = await fixture.request(
                        question, identifier=f"current-output-{index}", language="nl"
                    )
                    self.assertEqual(code, 200, answer)
                    self.assertTrue(answer["success"], answer)
                    self.assertEqual(answer["intent"]["intent"], "current_output")
                    self.assertIn("Observed speaker", answer["text"])
                    self.assertEqual(answer["playback_actions"], [])
            self.assertEqual(calls, ["status"] * 6)
            self.assertEqual(fixture.prompts, [])
            self.assertEqual(fixture.web_calls, [])
            self.assertEqual(fixture.effects, [])
        finally:
            await fixture.asyncTearDown()

    async def test_missing_current_output_never_borrows_previous_observation(self):
        fixture = shared.SharedDialogueTest()
        await fixture.asyncSetUp()
        observations = iter((
            {"success": True, "playback": {"device_name": "Previous speaker"}},
            {"success": True, "playback": {}},
        ))

        async def status(hass, runtime, command, *args, **kwargs):
            self.assertEqual(command, "status")
            return next(observations)

        try:
            with patch.object(fixture.core, "run_music_command", status):
                first, _ = await fixture.request(
                    "welke speaker is nu actief", identifier="output-before", language="nl"
                )
                second, code = await fixture.request(
                    "welke speaker is nu actief", identifier="output-after", language="nl"
                )
            self.assertIn("Previous speaker", first["text"])
            self.assertEqual(code, 200, second)
            self.assertNotIn("Previous speaker", second["text"])
            self.assertEqual(second["text"], "Ik kan nu niet zien waarop muziek speelt.")
            self.assertEqual(second["playback_actions"], [])
            self.assertEqual(fixture.prompts, [])
            self.assertEqual(fixture.effects, [])
        finally:
            await fixture.asyncTearDown()

    async def test_failed_status_never_relabels_cached_output_as_current(self):
        for failure in (OSError("provider unavailable"), {"success": False,
                "playback": {"device_name": "Stale response speaker"}}):
            with self.subTest(failure=type(failure).__name__):
                fixture = shared.SharedDialogueTest()
                await fixture.asyncSetUp()
                calls = []

                async def status(hass, runtime, command, *args, **kwargs):
                    calls.append(command)
                    self.assertEqual(command, "status")
                    if len(calls) == 1:
                        return {"success": True, "playback": {"device_name": "Previous speaker"}}
                    if isinstance(failure, Exception):
                        raise failure
                    return failure

                try:
                    with patch.object(fixture.core, "run_music_command", status):
                        first, _ = await fixture.request(
                            "welke speaker is nu actief", identifier="fresh-output", language="nl"
                        )
                        second, code = await fixture.request(
                            "welke speaker is nu actief", identifier="failed-output", language="nl"
                        )
                    self.assertIn("Previous speaker", first["text"])
                    self.assertEqual(code, 200, second)
                    self.assertEqual(second["text"], "Ik kan nu niet zien waarop muziek speelt.")
                    self.assertEqual(second["playback_actions"], [])
                    self.assertEqual(calls, ["status", "status"])
                    self.assertEqual(fixture.prompts, [])
                    self.assertEqual(fixture.effects, [])
                finally:
                    await fixture.asyncTearDown()
