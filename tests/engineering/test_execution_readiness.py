from __future__ import annotations

from pathlib import Path
import unittest
from types import SimpleNamespace

from tools.engineering.execution_readiness import ReadinessFacts, Requirement, decide, evaluate, selected_profile


class ExecutionReadinessTest(unittest.TestCase):
    def test_genesis_selects_only_target_profile(self) -> None:
        result = evaluate(
            selected_profile("GENESIS"), host_root=Path("/host"), target_root=Path("/target"),
            managed_clean=lambda _: False, genesis_preflight=lambda _: None,
        )
        self.assertEqual(result.profile.profile_id, "genesis_target")
        self.assertEqual(result.profile.remote, Requirement.NOT_APPLICABLE)
        self.assertTrue(result.ready)

    def test_managed_failure_does_not_call_genesis_preflight(self) -> None:
        result = evaluate(
            selected_profile("MANAGED"), host_root=Path("/host"), target_root=None,
            managed_clean=lambda _: False,
            genesis_preflight=lambda _: self.fail("Genesis readiness must not run for Managed work"),
        )
        self.assertFalse(result.ready)
        self.assertEqual(result.profile.profile_id, "managed_repository")
        self.assertEqual(result.profile.remote, Requirement.REQUIRED)

    def test_decision_lists_failed_typed_requirements(self) -> None:
        decision = decide(selected_profile("MANAGED"), ReadinessFacts(True, True, False, True))
        self.assertFalse(decision.passed)
        self.assertEqual(decision.failed_requirements, ("clean_worktree",))

    def test_preflight_adapter_uses_existing_observed_outcomes(self) -> None:
        workspace = SimpleNamespace(checks=(SimpleNamespace(identifier="target_repository", outcome="PASS"), SimpleNamespace(identifier="clean_worktree", outcome="PASS")))
        facts = ReadinessFacts.from_preflight(host=SimpleNamespace(outcome="PASS"), workspace=workspace, capability=SimpleNamespace(outcome="PASS"), lease_available=True)
        self.assertEqual(facts, ReadinessFacts(True, True, True, True))
