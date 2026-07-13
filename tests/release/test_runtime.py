from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from tools.release.cli import main
from tools.release.discovery import discover_repositories
from tools.release.manifest import validate_manifest
from tools.release.simulation import ReleaseSimulation
from tools.release.versioning import PlatformVersion, RepositoryVersion, VersionError, read_repository_version


OWNERSHIP = """# Ownership

## `example/source`

Owns: source implementation.

## `example/distribution`

Owns: public release distribution artifacts only.

## `example/optional`

Owns: optional client implementation.
Release role: optional

## `example/future`

Owns: future capability.
Release role: future
"""


class ReleaseRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.ownership = self.root / "REPOSITORY_OWNERSHIP.md"
        self.ownership.write_text(OWNERSHIP, encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_versions_validate_and_align_on_major_minor_only(self) -> None:
        platform = PlatformVersion.parse("3.3")
        self.assertTrue(RepositoryVersion.parse("3.3.8").compatible_with(platform))
        self.assertFalse(RepositoryVersion.parse("3.4.0").compatible_with(platform))
        with self.assertRaises(VersionError):
            RepositoryVersion.parse("3.3")

    def test_reads_local_version_without_repository_mapping(self) -> None:
        (self.root / "manifest.json").write_text('{"version":"3.3.9"}', encoding="utf-8")
        self.assertEqual(str(read_repository_version(self.root)), "3.3.9")

    def test_discovery_uses_ownership_content_not_repository_names(self) -> None:
        nodes = discover_repositories(self.ownership)
        self.assertEqual([node.role for node in nodes], ["active_source", "distribution", "optional", "future"])
        self.assertTrue(nodes[0].mandatory)
        self.assertFalse(nodes[2].mandatory)
        self.assertFalse(nodes[3].mandatory)

    def test_simulation_produces_ready_canonical_manifest(self) -> None:
        manifest = ReleaseSimulation(self.ownership).run(
            "3.3",
            versions={"example/source": "3.3.1", "example/distribution": "3.3.2"},
            shas={"example/source": "a" * 40, "example/distribution": "b" * 40},
            evidence={
                "verification": "PASS",
                "software_assurance": "PASS",
                "trusted_delivery": "PASS",
                "coverage": "PASS",
                "platform_qualification": "PASS",
            },
        )
        self.assertTrue(manifest["simulation_only"])
        self.assertEqual(manifest["readiness"]["state"], "READY")
        self.assertEqual(manifest["rollback_plan"]["execution"], "NOT_PERMITTED")
        self.assertEqual(manifest["rollback_plan"]["checkpoints"][0]["tag_checkpoint"], "NOT_APPLICABLE_SIMULATION")
        self.assertEqual(manifest["certification_state"], "PLANNED")
        self.assertEqual(manifest["execution_plan"][0]["name"], "release_control")
        self.assertEqual(manifest["execution_plan"][-1]["name"], "distribution_candidates")
        optional = next(record for record in manifest["repositories"] if record["name"] == "example/optional")
        self.assertFalse(optional["included"])
        self.assertEqual(validate_manifest(manifest), [])

    def test_readiness_explains_alignment_and_evidence_blocks(self) -> None:
        manifest = ReleaseSimulation(self.ownership).run(
            "3.3",
            versions={"example/source": "3.4.1", "example/distribution": "3.3.2"},
            shas={"example/source": "a", "example/distribution": "b"},
            evidence={"verification": "FAIL"},
        )
        self.assertEqual(manifest["readiness"]["state"], "BLOCKED")
        codes = {condition["code"] for condition in manifest["readiness"]["conditions"]}
        self.assertIn("platform_misalignment", codes)
        self.assertIn("evidence_not_qualified", codes)

    def test_cli_simulate_is_non_mutating_and_returns_zero(self) -> None:
        evidence = self.root / "evidence.json"
        versions = self.root / "versions.json"
        shas = self.root / "shas.json"
        evidence.write_text(json.dumps({"verification": "PASS"}), encoding="utf-8")
        versions.write_text(json.dumps({"example/source": "3.3.1", "example/distribution": "3.3.2"}), encoding="utf-8")
        shas.write_text(json.dumps({"example/source": "a", "example/distribution": "b"}), encoding="utf-8")
        with redirect_stdout(StringIO()):
            result = main([
                "--ownership", str(self.ownership), "--platform-version", "3.3", "--mode", "dry_run",
                "--versions-file", str(versions), "--shas-file", str(shas), "--evidence-file", str(evidence), "simulate",
            ])
        self.assertEqual(result, 0)
