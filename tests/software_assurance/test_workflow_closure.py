from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.software_assurance.workflow_closure import scan_workflow_closure  # noqa: E402


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


class WorkflowClosureTest(unittest.TestCase):
    def test_resolves_recursive_closure_and_keeps_duplicate_edges(self) -> None:
        sources = {
            ".github/workflows/root.yml": (
                "jobs:\n  first:\n    uses: acme/platform/.github/workflows/first.yml@%s\n"
                "  second:\n    uses: acme/platform/.github/workflows/first.yml@%s\n" % (SHA_A, SHA_A)
            )
        }
        remote = {
            ("acme/platform", ".github/workflows/first.yml", SHA_A): (
                "jobs:\n  nested:\n    uses: acme/platform/.github/workflows/second.yml@%s\n" % SHA_B
            ),
            ("acme/platform", ".github/workflows/second.yml", SHA_B): (
                "jobs:\n  cycle:\n    uses: acme/platform/.github/workflows/first.yml@%s\n"
                "  action:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@%s\n" % (SHA_A, SHA_C)
            ),
        }
        edges, findings = scan_workflow_closure(
            "acme/root", sources, {("actions/checkout", SHA_C)}, lambda *key: remote[key]
        )

        self.assertEqual(findings, [])
        self.assertEqual(sum(edge.kind == "reusable_workflow" for edge in edges), 4)
        self.assertEqual(sum(edge.kind == "terminal_action" for edge in edges), 1)

    def test_reports_mutable_reference_and_unregistered_action(self) -> None:
        edges, findings = scan_workflow_closure(
            "acme/root",
            {
                ".github/workflows/root.yml": (
                    "jobs:\n  a:\n    uses: acme/platform/.github/workflows/check.yml@main\n"
                    "  b:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/setup-python@%s\n" % SHA_A
                )
            },
            set(),
        )

        self.assertEqual(len(edges), 2)
        self.assertTrue(any("mutable reusable workflow" in finding for finding in findings))
        self.assertTrue(any("not in approved registry" in finding for finding in findings))

