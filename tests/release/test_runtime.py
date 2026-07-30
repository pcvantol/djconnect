from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from tools.release.cli import main
from tools.release.component_scope import COMPONENT_PROFILES
from tools.release.discovery import discover_repositories
from tools.release.execution import ExecutionAction, ExecutionError, ExecutionRequest, ReleaseExecutor, write_execution_evidence
from tools.release.manifest import validate_manifest
from tools.release.simulation import ReleaseSimulation
from tools.release.versioning import PlatformVersion, RepositoryVersion, VersionError, read_repository_version
from tools.trusted_delivery.post_merge_reconciliation import reconcile


OWNERSHIP = """# Ownership

## `example/source`
Owns: source implementation.

## `example/distribution`
Owns: public release distribution artifacts only.

## `example/optional`
Owns: optional client implementation.
Release role: optional
"""


class RecordingClient:
    """Test double with the sole capability allowed to the runtime: dispatch."""

    def __init__(self, fail_on: str | None = None, evidence: bool = True) -> None:
        self.fail_on, self.evidence, self.calls = fail_on, evidence, []

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]:
        self.calls.append(f"dispatch:{action.repository}")
        if self.fail_on == action.repository:
            raise ExecutionError("workflow failed")
        receipt: dict[str, object] = {"kind": "workflow_dispatch", "workflow": action.workflow, "channel": "internal"}
        if self.evidence:
            receipt["evidence"] = {
                "workflow": action.workflow, "workflow_run_id": "123", "repository": action.repository,
                "candidate_sha": action.inputs["candidate_sha"], "platform_version": action.inputs["platform_version"],
                "action": action.category, "artifact_hashes": {}, "deployment_result": "NOT_APPLICABLE",
                "rollback": "PREPARED", "timestamp": "2026-01-01T00:00:00Z", "status": "PASS",
            }
        return receipt


class ReleaseRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.ownership = self.root / "REPOSITORY_OWNERSHIP.md"
        self.ownership.write_text(OWNERSHIP, encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manifest(self) -> dict[str, object]:
        shas = {"example/source": "a" * 40, "example/distribution": "b" * 40}
        def reconciliation(repository: str, main_sha: str, pr_sha: str) -> dict[str, object]:
            return reconcile({"repository": repository, "main_sha": main_sha, "main_parents": ["c" * 40], "timestamp": "2026-01-01T00:00:00Z", "originating_pr": {"number": 1, "state": "MERGED", "base_ref": "main", "head_sha": pr_sha, "merge_commit_sha": main_sha, "merge_strategy": "SQUASH", "merge_actor": "maintainer", "merged_at": "2026-01-01T00:00:00Z", "changed_files": ["x"], "main_changed_files": ["x"]}, "pre_merge": {"candidate_sha": pr_sha, "risk_classification": "NORMAL_RISK", "owner_authorization": "PASS", "verification": "PASS", "software_assurance": "PASS", "trusted_delivery": "PASS", "workflow_integrity": "PASS", "required_checks": "PASS"}, "post_merge": {"sha": main_sha, "ci": "PASS", "tests": "PASS", "lint": "PASS", "static_analysis": "PASS", "build_validation": "PASS", "governance": "PASS", "coverage": "PASS", "coverage_report_sha": main_sha, "coverage_artifact_sha": "d" * 64, "workflow_run_ids": ["1"]}})
        return ReleaseSimulation(self.ownership).run("3.3", mode="production", versions={"example/source": "3.3.1", "example/distribution": "3.3.2"}, shas=shas, evidence={"verification": "PASS", "software_assurance": "PASS", "trusted_delivery": "PASS", "coverage": "PASS", "platform_qualification": "PASS"}, reconciliations={"example/source": reconciliation("example/source", shas["example/source"], "d" * 40), "example/distribution": reconciliation("example/distribution", shas["example/distribution"], "e" * 40)})

    def _component_manifest(self, mutate: callable | None = None) -> dict[str, object]:
        ownership = self.root / "component_ownership.md"
        ownership.write_text("""# Ownership

## `pcvantol/djconnect-app`
Owns: Apple client source.

## `pcvantol/djconnect-app-releases`
Owns: internal release distribution artifacts only.
""", encoding="utf-8")
        source, distribution = "pcvantol/djconnect-app", "pcvantol/djconnect-app-releases"
        shas = {source: "a" * 40, distribution: "b" * 40}
        def reconciliation(repository: str, main_sha: str) -> dict[str, object]:
            return reconcile({"repository": repository, "main_sha": main_sha, "main_parents": ["c" * 40], "timestamp": "2026-01-01T00:00:00Z", "originating_pr": {"number": 1, "state": "MERGED", "base_ref": "main", "head_sha": "d" * 40, "merge_commit_sha": main_sha, "merge_strategy": "SQUASH", "merge_actor": "maintainer", "merged_at": "2026-01-01T00:00:00Z", "changed_files": ["x"], "main_changed_files": ["x"]}, "pre_merge": {"candidate_sha": "d" * 40, "risk_classification": "NORMAL_RISK", "owner_authorization": "PASS", "verification": "PASS", "software_assurance": "PASS", "trusted_delivery": "PASS", "workflow_integrity": "PASS", "required_checks": "PASS"}, "post_merge": {"sha": main_sha, "ci": "PASS", "tests": "PASS", "lint": "PASS", "static_analysis": "PASS", "build_validation": "PASS", "governance": "PASS", "coverage": "PASS", "coverage_report_sha": main_sha, "coverage_artifact_sha": "d" * 64, "workflow_run_ids": ["1"]}})
        identity = {"component_id": "apple-macos", "source_sha": shas[source], "artifact_identity": "djconnect-macos-3.3.1.zip", "artifact_sha256": "e" * 64, "manifest_id": "apple-macos-3.3.1", "manifest_sha256": "f" * 64, "version": "3.3.1"}
        selection: dict[str, object] = {**identity, "component_owner": "DJConnect Apple Client", "source_repository": source, "platform_train": "3.3", "release_channel": "apple-macos-internal", "target_distribution": "Apple macOS internal distribution", "artifact_kind": "macos_artifact", "participants": [source, distribution], "evidence": {name: {"status": "PASS", **identity} for name in ("source_qualification", "build_test", "software_assurance", "trusted_delivery", "artifact_provenance", "manifest_validation", "channel_validation", "durable_post_merge", "owner_authorization")}}
        if mutate:
            mutate(selection)
        return ReleaseSimulation(ownership).run("3.3", mode="production", versions={source: "3.3.1", distribution: "3.3.1"}, shas=shas, evidence={"verification": "PASS", "software_assurance": "PASS", "trusted_delivery": "PASS", "coverage": "PASS", "platform_qualification": "PASS"}, reconciliations={source: reconciliation(source, shas[source]), distribution: reconciliation(distribution, shas[distribution])}, component_selection=selection)

    def _action(self, manifest: dict[str, object], repository: str, category: str = "build", mode: str = "execute") -> dict[str, object]:
        sha = "a" * 40 if repository == "example/source" else "b" * 40
        return {"operation": "workflow_dispatch", "repository": repository, "category": category, "workflow": "platform-release-execution.yml", "ref": sha, "inputs": {"action": category, "candidate_sha": sha, "execution_mode": mode, "manifest_id": manifest["manifest_id"], "platform_version": "3.3", "release_profile": "INTERNAL_RELEASE"}}

    def _request(self, manifest: dict[str, object], actions: list[dict[str, object]], non_production: bool = False) -> ExecutionRequest:
        return ExecutionRequest.from_dict({"release_profile": "INTERNAL_RELEASE", "requested_by": "maintainer", "non_production": non_production, "actions": actions})

    def test_versions_validate_and_align_on_major_minor_only(self) -> None:
        self.assertTrue(RepositoryVersion.parse("3.3.8").compatible_with(PlatformVersion.parse("3.3")))
        self.assertFalse(RepositoryVersion.parse("3.4.0").compatible_with(PlatformVersion.parse("3.3")))
        with self.assertRaises(VersionError):
            RepositoryVersion.parse("3.3")

    def test_reads_local_version_without_repository_mapping(self) -> None:
        (self.root / "manifest.json").write_text('{"version":"3.3.9"}', encoding="utf-8")
        self.assertEqual(str(read_repository_version(self.root)), "3.3.9")

    def test_discovery_uses_ownership_content_not_repository_names(self) -> None:
        self.assertEqual([node.role for node in discover_repositories(self.ownership)], ["active_source", "distribution", "optional"])

    def test_simulation_produces_ready_canonical_manifest(self) -> None:
        manifest = self._manifest()
        self.assertTrue(manifest["simulation_only"])
        self.assertEqual(manifest["readiness"]["state"], "READY")
        self.assertEqual(manifest["rollback_plan"]["execution"], "NOT_PERMITTED")
        self.assertEqual(validate_manifest(manifest), [])

    def test_cli_simulate_is_non_mutating_and_returns_zero(self) -> None:
        for name, data in {"evidence.json": {"verification": "PASS"}, "versions.json": {"example/source": "3.3.1", "example/distribution": "3.3.2"}, "shas.json": {"example/source": "a", "example/distribution": "b"}}.items():
            (self.root / name).write_text(json.dumps(data), encoding="utf-8")
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["--ownership", str(self.ownership), "--platform-version", "3.3", "--mode", "dry_run", "--versions-file", str(self.root / "versions.json"), "--shas-file", str(self.root / "shas.json"), "--evidence-file", str(self.root / "evidence.json"), "simulate"]), 0)

    def test_runtime_rejects_pr_only_or_missing_post_merge_evidence(self) -> None:
        manifest = ReleaseSimulation(self.ownership).run("3.3", mode="production", versions={"example/source": "3.3.1", "example/distribution": "3.3.2"}, shas={"example/source": "a" * 40, "example/distribution": "b" * 40}, evidence={"verification": "PASS", "software_assurance": "PASS", "trusted_delivery": "PASS", "coverage": "PASS", "platform_qualification": "PASS"})
        self.assertEqual(manifest["readiness"]["state"], "NOT_READY")
        self.assertTrue(any(item["code"] == "post_merge_evidence_missing" for item in manifest["readiness"]["conditions"]))

    def test_runtime_has_no_direct_mutation_operations(self) -> None:
        self.assertFalse(hasattr(RecordingClient(), "create_tag"))
        self.assertFalse(hasattr(RecordingClient(), "create_draft_release"))
        with self.assertRaisesRegex(ExecutionError, "workflow_dispatch"):
            ExecutionRequest.from_dict({"release_profile": "INTERNAL_RELEASE", "requested_by": "maintainer", "actions": [{"operation": "create_tag"}]})
        with self.assertRaisesRegex(ExecutionError, "workflow_dispatch"):
            ExecutionRequest.from_dict({"release_profile": "INTERNAL_RELEASE", "requested_by": "maintainer", "actions": [{"operation": "draft_release"}]})

    def test_dispatch_requires_bounded_inputs_and_qualified_scope(self) -> None:
        manifest = self._manifest()
        action = self._action(manifest, "example/source")
        action["inputs"]["candidate_sha"] = "b" * 40
        outcome = ReleaseExecutor(RecordingClient()).execute(manifest, self._request(manifest, [action]))
        self.assertEqual(outcome["status"], "FAILED")
        self.assertIn("immutable release scope", outcome["failure"]["reason"])

    def test_missing_workflow_evidence_blocks_release(self) -> None:
        manifest = self._manifest()
        outcome = ReleaseExecutor(RecordingClient(evidence=False)).execute(manifest, self._request(manifest, [self._action(manifest, "example/source")]))
        self.assertEqual(outcome["status"], "FAILED")
        self.assertIn("canonical execution evidence", outcome["failure"]["reason"])

    def test_dispatch_stops_and_preserves_rollback_evidence_on_failure(self) -> None:
        manifest = self._manifest()
        outcome = ReleaseExecutor(RecordingClient(fail_on="example/distribution")).execute(manifest, self._request(manifest, [self._action(manifest, "example/source"), self._action(manifest, "example/distribution", "deployment")]))
        self.assertEqual(outcome["status"], "FAILED")
        self.assertEqual(outcome["rollback_evidence"]["state"], "PRESERVE_AND_STOP")

    def test_evidence_writing_and_safe_rehearsal(self) -> None:
        manifest = self._manifest()
        action = self._action(manifest, "example/source", mode="dry_run")
        outcome = ReleaseExecutor(RecordingClient()).execute(manifest, self._request(manifest, [action], non_production=True))
        self.assertEqual({path.name for path in write_execution_evidence(outcome, self.root / "evidence")}, {"release-execution-report.json", "release-deployment-evidence.json", "release-publication-evidence.json"})

    def test_component_selection_is_deterministic_and_excludes_other_components(self) -> None:
        manifest = self._component_manifest()
        self.assertEqual(manifest["readiness"]["state"], "READY")
        self.assertEqual(manifest["component_selection"]["component_id"], "apple-macos")
        self.assertEqual({item["name"] for item in manifest["repositories"] if item["included"]}, {"pcvantol/djconnect-app", "pcvantol/djconnect-app-releases"})
        self.assertFalse(manifest["component_execution_authorized"])
        with self.assertRaisesRegex(ExecutionError, "component selection is qualification-only"):
            ReleaseExecutor(RecordingClient()).execute(manifest, self._request(manifest, [self._action(manifest, "pcvantol/djconnect-app")]))

    def test_component_selection_rejects_checksum_or_evidence_identity_drift(self) -> None:
        manifest = self._component_manifest(lambda selection: selection.__setitem__("artifact_sha256", "invalid"))
        codes = {item["code"] for item in manifest["readiness"]["conditions"]}
        self.assertEqual(manifest["readiness"]["state"], "BLOCKED")
        self.assertIn("artifact_sha256_invalid", codes)
        self.assertIn("component_evidence_binding_mismatch", codes)

    def test_component_selection_rejects_non_selectable_pi_product_profile(self) -> None:
        manifest = self._component_manifest(lambda selection: selection.__setitem__("component_id", "pi-4-inch"))
        self.assertEqual(manifest["readiness"]["state"], "BLOCKED")
        self.assertIn("component_profile_not_selectable", {item["code"] for item in manifest["readiness"]["conditions"]})

    def test_component_profile_inventory_preserves_all_registered_boundaries(self) -> None:
        self.assertEqual(set(COMPONENT_PROFILES), {"hacs-integration", "api-worker", "website", "esp32-firmware", "apple-ios-watchos", "apple-macos", "windows-client", "pi-renderer-family", "pi-4-inch", "pi-10-inch"})
        self.assertFalse(COMPONENT_PROFILES["pi-4-inch"].selectable)
        self.assertFalse(COMPONENT_PROFILES["pi-10-inch"].selectable)
