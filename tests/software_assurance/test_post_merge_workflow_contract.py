from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PostMergeWorkflowContractTest(unittest.TestCase):
    def test_reconciliation_requires_a_successful_main_workflow_run(self) -> None:
        workflow = (ROOT / ".github/workflows/post-merge-release-evidence.yml").read_text()

        self.assertIn("github.event_name == 'workflow_run'", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertNotIn("github.event_name == 'push' && github.ref", workflow)
        self.assertIn("MAIN_SHA: ${{ github.event.workflow_run.head_sha }}", workflow)

    def test_reconciliation_status_is_bound_to_the_workflow_run_main_sha(self) -> None:
        workflow = (ROOT / ".github/workflows/post-merge-release-evidence.yml").read_text()

        self.assertIn("sha: evidence.main_sha", workflow)
        self.assertNotIn("sha: context.sha, context: \"Post-Merge Release Evidence", workflow)

    def test_qualified_main_evidence_is_published_append_only_and_read_back(self) -> None:
        workflow = (ROOT / ".github/workflows/post-merge-release-evidence.yml").read_text()
        dispatch = (ROOT / ".github/workflows/post-merge-release-evidence-dispatch.yml").read_text()

        self.assertIn("contents: write", workflow)
        self.assertIn("contents: write", dispatch)
        self.assertIn("Produce redacted durable qualification evidence", workflow)
        self.assertIn("Publish append-only durable qualification evidence", workflow)
        self.assertIn("durable evidence collision: existing record will not be overwritten", workflow)
        self.assertIn("gh release download", workflow)
        self.assertLess(
            workflow.index("Publish append-only durable qualification evidence"),
            workflow.index("Publish exact-main-SHA reconciliation status"),
        )
