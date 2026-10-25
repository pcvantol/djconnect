"""Development probes cannot widen code, spending, or catalogue qualification."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.verification import help_content_probe as policy
from tools.verification import run_help_content_probe as runner


class ContentProbeTests(unittest.TestCase):
    def test_only_literal_value_can_change_not_code_or_other_bytes(self):
        original = (
            b'"""Fixed module."""\nSTYLE = "A sufficiently long telling instruction."\nlimit = 22\n'
        )
        candidate = original.replace(
            b"A sufficiently long telling instruction.",
            b"Tell one concrete musical episode, briefly.",
        )
        value, fixed = policy.instruction_only(original, candidate, "STYLE")
        self.assertEqual(value, "Tell one concrete musical episode, briefly.")
        equivalent = candidate.replace(b"Tell", b"\\u0054ell")
        self.assertEqual(policy.instruction_only(original, equivalent, "STYLE"), (value, fixed))
        for bad in (
            candidate + b"# comment\n",
            b"# coding:utf-8\n" + candidate,
            candidate.replace(b"22", b"392"),
            candidate + b"import os\n",
            candidate.replace(b'STYLE = "', b'STYLE = f"'),
            candidate + b'STYLE = "Another instruction that is sufficiently long."\n',
            candidate.replace(b"STYLE = ", b"STYLE: str = "),
            candidate.replace(b"Tell one", b"\\nData:\\nTell one"),
            candidate.replace(b"Tell one", b"\\u202eTell one"),
        ):
            with self.subTest(bad=bad), self.assertRaises((ValueError, SyntaxError)):
                policy.instruction_only(original, bad, "STYLE")

    def test_actual_case_chain_and_two_distinct_budgets(self):
        from scripts.verification.askdj_example_catalogue_golden import (
            cases,
            chain_cases,
            manifest_digest,
        )

        all_cases = cases() + chain_cases()
        self.assertEqual(manifest_digest(), policy.MANIFEST)
        self.assertEqual(
            [c["id"] for c in all_cases if c["id"] in policy.TARGET], list(policy.TARGET)
        )
        self.assertEqual(policy.mode_policy("target6"), (policy.TARGET, 22, 600))
        self.assertEqual(policy.mode_policy("full100"), ((), 392, 1800))
        for mode in ("target5", "retry", None, True):
            with self.assertRaises(ValueError):
                policy.mode_policy(mode)

    def test_new_activity18_original_cases_complete_chains_and_tight_budget(self):
        from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases
        original = cases() + chain_cases()
        selected, attempts, seconds = policy.mode_policy('target18_activity_v2')
        self.assertEqual(len(selected), 18)
        self.assertEqual((attempts, seconds), (62, 900))
        self.assertEqual(tuple(c['id'] for c in original if c['id'] in selected), selected)
        duplicates = [c for c in original if c['id'] in selected and c.get('operation') == 'duplicate']
        self.assertEqual(len(duplicates), 3)
        self.assertEqual(attempts, 4 * (18 - len(duplicates)) + 2)
        for case in original:
            if case['id'] in selected and case.get('chain'):
                self.assertTrue({c['id'] for c in original if c.get('chain') == case['chain']}.issubset(selected))
        # The historical mode is retained rather than silently reinterpreted.
        self.assertEqual(policy.mode_policy('target6'), (policy.TARGET, 22, 600))
        self.assertEqual(policy.mode_policy('full100'), ((), 392, 1800))
        self.assertEqual(len(policy.TARGET), 6)

    def test_activity18_progress_is_explicit_separate_and_reserves_before_io(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'activity18.json'
            progress = policy.DiagnosticProgress(path, content_digest='c' * 64,
                mode='target18_activity_v2')
            value = json.loads(path.read_text())
            self.assertEqual(value['schema_version'], 2)
            self.assertEqual(value['mode'], 'target18_activity_v2')
            self.assertEqual(value['selected_case_ids'], list(policy.TARGET18_ACTIVITY_V2))
            self.assertFalse(policy.validate_progress(value, content_digest='c' * 64))
            self.assertTrue(policy.validate_progress(value, content_digest='c' * 64,
                mode='target18_activity_v2'))
            for i in range(62):
                progress.before_model(policy.TARGET18_ACTIVITY_V2[0])
                saved = json.loads(path.read_text())
                self.assertEqual(saved['sdk_attempts_reserved'], i + 1)
                self.assertEqual(saved['sdk_completed_responses'], i)
                progress.completed_response()
            with self.assertRaises(RuntimeError):
                progress.before_model(policy.TARGET18_ACTIVITY_V2[0])
            self.assertFalse(progress.healthy)
            with self.assertRaises(FileExistsError):
                policy.DiagnosticProgress(path, content_digest='c' * 64,
                    mode='target18_activity_v2')

    def test_activity18_does_not_relabel_old_progress_or_hide_chain_members(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = policy.DiagnosticProgress(Path(directory) / 'case.json',
                content_digest='d' * 64, mode='target18_activity_v2')
            for case in policy.TARGET18_ACTIVITY_V2:
                progress.completed_case(case, passed=True)
            progress.terminal('COMPLETE_NOT_QUALIFIED')
            good = deepcopy(progress.value)
            self.assertTrue(policy.validate_progress(good, content_digest='d' * 64,
                mode='target18_activity_v2'))
            for field, replacement in (
                ('mode', 'target6'), ('schema_version', 1), ('schema_version', True),
                ('selected_case_ids', list(policy.TARGET)),
                ('completed_cases', list(policy.TARGET18_ACTIVITY_V2[:-1])),
                ('sdk_attempts_reserved', 63), ('qualification', 'QUALIFIED'),
            ):
                wrong = {**good, field: replacement}
                with self.subTest(field=field, replacement=replacement):
                    self.assertFalse(policy.validate_progress(wrong, content_digest='d' * 64,
                        mode='target18_activity_v2'))
            self.assertFalse(policy.selected_inputs_complete({}, mode='unknown'))
            self.assertFalse(policy.validate_selected_report({}, good, pin={},
                mode='target18_activity_v2'))
        with self.assertRaises(ValueError):
            policy.DiagnosticProgress(Path('/unused'), content_digest='a' * 64, mode='full100')

    def test_progress_reserves_before_io_never_resumes_or_exceeds22(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            progress = policy.DiagnosticProgress(path, content_digest="a" * 64)
            with self.assertRaises(FileExistsError):
                policy.DiagnosticProgress(path, content_digest="a" * 64)
            for i in range(22):
                progress.before_model(policy.TARGET[0])
                stored = json.loads(path.read_text())
                self.assertEqual(stored["sdk_attempts_reserved"], i + 1)
                self.assertEqual(stored["sdk_completed_responses"], i)
                progress.completed_response()
            with self.assertRaises(RuntimeError):
                progress.before_model(policy.TARGET[0])
            self.assertFalse(progress.healthy)
            self.assertEqual(json.loads(path.read_text())["sdk_attempts_reserved"], 22)

    def test_progress_persistence_error_and_bad_case_close_before_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = policy.DiagnosticProgress(
                Path(directory) / "progress.json", content_digest="a" * 64
            )
            with patch.object(policy.os, "fsync", side_effect=OSError("synthetic failure")):
                with self.assertRaises(OSError):
                    progress.before_model(policy.TARGET[0])
            self.assertFalse(progress.healthy)
            with self.assertRaises(RuntimeError):
                progress.before_model(policy.TARGET[0])
        with tempfile.TemporaryDirectory() as directory:
            progress = policy.DiagnosticProgress(
                Path(directory) / "progress.json", content_digest="b" * 64
            )
            with self.assertRaises(ValueError):
                progress.before_model("unknown-case")
            self.assertFalse(progress.healthy)

    def test_progress_only_ordered_original_six_and_closed_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = policy.DiagnosticProgress(
                Path(directory) / "progress.json", content_digest="a" * 64
            )
            initial = deepcopy(progress.value)
            changes = [
                {"content_digest": None},
                {"sdk_attempts_reserved": True},
                {"sdk_completed_responses": 1},
                {"sdk_attempts_reserved": 23},
                {"completed_cases": [policy.TARGET[1]]},
                {"failed_cases": [policy.TARGET[0]]},
                {"current_case": "unknown"},
                {"outcome": "COMPLETE_NOT_QUALIFIED"},
                {"phase": "terminal"},
                {"phase": []},
                {"completed_cases": [None]},
                {"qualification": "QUALIFIED"},
                {"extra": 1},
            ]
            for change in changes:
                self.assertFalse(
                    policy.validate_progress(initial | change, content_digest="a" * 64), change
                )
            for case in policy.TARGET:
                progress.completed_case(case, passed=True)
            progress.terminal("COMPLETE_NOT_QUALIFIED")
            self.assertTrue(policy.validate_progress(progress.value, content_digest="a" * 64))
            with self.assertRaises(RuntimeError):
                progress.before_model(policy.TARGET[0])

    def test_wire_witness_case_language_and_exact_closed_schema(self):
        cases = [
            {"id": case, "language": case.rsplit("-", 1)[1], "entry_id": "listen.artist"}
            for case in policy.TARGET[:3]
        ]
        rows = [
            {
                "case_id": case["id"],
                "artist_generation_wire": {
                    "research_schema": 3,
                    "language": case["language"],
                    "drafts_requested": True,
                    "wire_contract_first": True,
                    "trusted_instructions_sha256": "a" * 64,
                },
            }
            for case in cases
        ]
        self.assertTrue(policy.generation_wire_complete({"model_calls": rows}, cases=cases))
        for bad in (rows[:-1], rows + rows[:1], rows[:2] + rows[:1]):
            self.assertFalse(policy.generation_wire_complete({"model_calls": bad}, cases=cases))
        for field, value in [
            ("research_schema", True),
            ("language", "en"),
            ("drafts_requested", 1),
            ("trusted_instructions_sha256", "x" * 64),
            ("extra", True),
        ]:
            bad = deepcopy(rows)
            bad[0]["artist_generation_wire"][field] = value
            self.assertFalse(policy.generation_wire_complete({"model_calls": bad}, cases=cases))

    def test_original_context_before_secret_denies_wrong_actor_attempt_ref_digest(self):
        env = {
            "GITHUB_REPOSITORY": "pcvantol/djconnect",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_WORKFLOW_REF": runner.WORKFLOW,
            "GITHUB_ACTOR": "pcvantol",
            "GITHUB_TRIGGERING_ACTOR": "pcvantol",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "123",
            "GITHUB_SHA": "a" * 40,
            "DJC_CONTROLLER_SHA": "a" * 40,
            "DJC_CANDIDATE_SHA": "b" * 40,
            "DJC_CONTENT_DIGEST": "c" * 64,
            "DJC_PLAN_DIGEST": "d" * 64,
            "DJC_CONTENT_MODE": "target6",
        }
        self.assertEqual(runner.context(env)["qualification"], "NOT_QUALIFIED")
        for field, value in [
            ("GITHUB_ACTOR", "other"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_REF", "refs/heads/candidate"),
            ("DJC_CONTROLLER_SHA", "b" * 40),
            ("DJC_CONTENT_DIGEST", "bad"),
            ("DJC_CONTENT_MODE", "retry"),
        ]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                runner.context(env | {field: value})


if __name__ == "__main__":
    unittest.main()
