"""Focused checks for the read-only execution lifecycle projection."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.engineering.agent_state import StateStore, TransactionState
from tools.engineering.execution_lifecycle import intended_path, projection


class ExecutionLifecycleProjectionTests(unittest.TestCase):
    def _state(self, root: Path, phase: str, **values: object) -> None:
        StateStore(root / ".engineering" / "engineering-runs").save(TransactionState(
            run_id="inbox-flow", repository="pcvantol/djconnect", prompt_path="prompt.md",
            phase=phase, terminal=phase in {"COMPLETE", "BLOCKED", "FAILED"}, **values,
        ))

    def test_managed_projects_start_completed_active_and_pending_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._state(root, "INITIALIZE")
            self._state(root, "EXECUTE_AGENT")
            value = projection(root, "inbox-flow")
        self.assertEqual(value["run_id"], "inbox-flow")
        self.assertTrue(value["available"])
        self.assertEqual(value["steps"][0]["state"], "START")
        self.assertEqual(value["steps"][1]["state"], "COMPLETED")
        self.assertEqual(value["steps"][2]["state"], "ACTIVE")
        self.assertEqual(value["steps"][-1]["state"], "PENDING")

    def test_terminal_outcome_keeps_later_steps_pending_and_repairs_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._state(root, "INITIALIZE")
            self._state(root, "REPAIR_AGENT", repair_iterations=2)
            self._state(root, "BLOCKED", repair_iterations=2)
            value = projection(root, "inbox-flow")
        by_id = {step["id"]: step for step in value["steps"]}
        self.assertEqual(by_id["REPAIR_AGENT"]["iteration_count"], 2)
        self.assertEqual(by_id["WAIT_FOR_OPERATOR_MERGE"]["state"], "PENDING")
        self.assertEqual(by_id["TERMINAL"]["state"], "BLOCKED")

    def test_genesis_has_its_own_canonical_path(self) -> None:
        self.assertNotIn("WAIT_FOR_OPERATOR_MERGE", intended_path("GENESIS"))
        self.assertIn("WAIT_FOR_OPERATOR_MERGE", intended_path("MANAGED"))

    def test_missing_run_never_infers_historical_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(projection(Path(temporary), "inbox-missing"), {
                "run_id": "inbox-missing", "available": False, "steps": []
            })
