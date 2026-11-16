"""Current release components must resolve to the verified ownership register."""

from pathlib import Path
import unittest

from tools.release.component_scope import COMPONENT_PROFILES, validate_component_selection
from tools.release.discovery import discover_repositories
from tools.release.versioning import PlatformVersion


class ReleaseRepositoryIdentityTests(unittest.TestCase):
    def test_selectable_component_participants_exist_in_ownership(self):
        names = {node.name for node in discover_repositories(Path("REPOSITORY_OWNERSHIP.md"))}
        for component_id, profile in COMPONENT_PROFILES.items():
            if profile.selectable:
                with self.subTest(component=component_id):
                    self.assertIn(profile.source_repository, names)
                    self.assertTrue(set(profile.participants) <= names)

    def test_firmware_selection_binds_current_namespace(self):
        profile = COMPONENT_PROFILES["esp32-firmware"]
        sha = "a" * 40
        selection = {
            "component_id": profile.component_id,
            "component_owner": profile.component_owner,
            "source_repository": profile.source_repository,
            "source_sha": sha,
            "version": "4.0.0",
            "platform_train": "4.0",
            "artifact_identity": "test-artifact",
            "artifact_sha256": "b" * 64,
            "manifest_id": "test-manifest",
            "manifest_sha256": "c" * 64,
            "release_channel": profile.release_channel,
            "target_distribution": profile.target_distribution,
            "artifact_kind": profile.artifact_kind,
            "participants": list(profile.participants),
        }
        bindings = {key: selection[key] for key in ("component_id", "source_sha", "artifact_identity", "artifact_sha256", "manifest_id", "manifest_sha256", "version")}
        selection["evidence"] = {name: {"status": "PASS", **bindings} for name in (
            "source_qualification", "build_test", "software_assurance", "trusted_delivery", "artifact_provenance", "manifest_validation", "channel_validation", "durable_post_merge", "owner_authorization")}
        current = "djconnect-music-dj/djconnect-esp32"
        result = validate_component_selection(selection, PlatformVersion.parse("4.0"), {current: "4.0.0"}, {current: sha})
        self.assertEqual(result["readiness"], "READY")
        selection["source_repository"] = "pcvantol/djconnect-esp32"
        result = validate_component_selection(selection, PlatformVersion.parse("4.0"), {current: "4.0.0"}, {current: sha})
        self.assertEqual(result["readiness"], "BLOCKED")
        self.assertIn("source_repository_mismatch", {item["code"] for item in result["conditions"]})
