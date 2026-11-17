from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/release/PLATFORM_4_0_RC1_HOME_ASSISTANT_OPERATIONAL_MANIFEST.json"
WORKFLOWS = ROOT / ".github/workflows"
OLD = "pcvantol/djconnect"
NEW = "djconnect-music-dj/djconnect"


class HomeAssistantManifestIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST.read_text())
        self.sha = self.manifest["repositories"][0]["source_sha"]
        self.binding = self.manifest["artifact_bindings"][0]

    def run_binding(self, workflow: str, manifest: dict, current: str, repository_id: str = "1258575431", artifact: str | None = None) -> bool:
        data = (WORKFLOWS / workflow).read_text()
        part = data.split("name: Require approved central operational manifest source", 1)[1]
        body = part.split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
        script = textwrap.dedent(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "manifest.json"
            fixture.write_text(json.dumps(manifest))
            curl = root / "curl"
            curl.write_text('#!/bin/bash\nseen=0\nwhile (($#)); do if [[ "$1" == "$EXPECTED_URL" ]]; then seen=1; fi; if [[ "$1" == "--output" ]]; then out="$2"; shift; fi; shift; done\ntest "$seen" = 1 || exit 1\ncp "$FIXTURE" "$out"\n')
            curl.chmod(0o700)
            manifest_path = ("docs/release/PLATFORM_4_0_RC1_HOME_ASSISTANT_OPERATIONAL_MANIFEST.json"
                             if manifest["manifest_id"] == "release-4.0.0-home-assistant-prod-20261110"
                             else f"docs/release/home-assistant-manifests/{manifest['manifest_id']}.json")
            env = os.environ | {
                "PATH": f"{root}:{os.environ['PATH']}", "FIXTURE": str(fixture),
                "EXPECTED_URL": f"https://raw.githubusercontent.com/{current}/main/{manifest_path}",
                "GITHUB_REPOSITORY_ID": repository_id, "GITHUB_REPOSITORY": current,
                "CANDIDATE_SHA": self.sha, "MANIFEST_ID": manifest["manifest_id"],
                "ARTIFACT_ID": artifact or self.binding["artifact_id"],
                "ARTIFACT_SHA256": self.binding["artifact_sha256"], "TARGET": "home_assistant_pi5",
                "RELEASE_PROFILE": "INTERNAL_RELEASE", "GITHUB_OUTPUT": str(root / "out"),
            }
            return subprocess.run(["bash", "-c", script], env=env, capture_output=True, check=False).returncode == 0

    def both(self, manifest: dict, current: str, expected: bool, **kwargs: str) -> None:
        for workflow in ("deploy-home-assistant-private-network.yml", "smoke-home-assistant-private-network.yml"):
            with self.subTest(workflow=workflow, current=current, kwargs=kwargs):
                self.assertEqual(self.run_binding(workflow, manifest, current, **kwargs), expected)

    def test_historical_manifest_remains_valid_for_both_current_names(self) -> None:
        self.both(self.manifest, OLD, True)
        self.both(self.manifest, NEW, True)

    def test_new_name_requires_consistent_manifest_binding(self) -> None:
        doc = copy.deepcopy(self.manifest)
        doc["repositories"][0]["repository"] = NEW
        doc["manifest_id"] = "release-synthetic-future"
        for key in ("owner", "artifact_id", "artifact_url"):
            doc["artifact_bindings"][0][key] = doc["artifact_bindings"][0][key].replace(OLD, NEW)
        self.both(doc, NEW, True, artifact=doc["artifact_bindings"][0]["artifact_id"])
        self.both(doc, OLD, False, artifact=doc["artifact_bindings"][0]["artifact_id"])
        doc["artifact_bindings"][0]["owner"] = OLD
        self.both(doc, NEW, False, artifact=doc["artifact_bindings"][0]["artifact_id"])

    def test_wrong_repository_and_id_fail_closed(self) -> None:
        self.both(self.manifest, "other/djconnect", False)
        self.both(self.manifest, NEW, False, repository_id="1")
        self.both(self.manifest, NEW, False, artifact=self.binding["artifact_id"].replace(OLD, "other/djconnect"))

    def test_wrong_sha_hash_url_and_ambiguous_binding_fail_closed(self) -> None:
        self.both(self.manifest, NEW, False, artifact=self.binding["artifact_id"].replace(self.sha, "a" * 40))
        for field, value in (("artifact_sha256", "0" * 64), ("artifact_url", "https://example.invalid/file")):
            doc = copy.deepcopy(self.manifest)
            doc["artifact_bindings"][0][field] = value
            self.both(doc, NEW, False)
        doc = copy.deepcopy(self.manifest)
        doc["artifact_bindings"].append(copy.deepcopy(doc["artifact_bindings"][0]))
        self.both(doc, NEW, False)
        doc = copy.deepcopy(self.manifest)
        doc["repositories"].append(copy.deepcopy(doc["repositories"][0]))
        self.both(doc, NEW, False)

    def test_provenance_requires_successful_completed_exact_run(self) -> None:
        data = (WORKFLOWS / "deploy-home-assistant-private-network.yml").read_text()
        part = data.split("name: Verify immutable artifact provenance", 1)[1]
        body = part.split("        run: |\n", 1)[1].split("\n      - ", 1)[0]
        script = textwrap.dedent(body)
        valid = {"headSha": self.sha, "workflowName": "Home Assistant release artifact", "status": "completed", "conclusion": "success"}
        cases = [(valid, True)]
        for field, value in (("headSha", "0" * 40), ("workflowName", "other"), ("status", "in_progress"), ("conclusion", "failure")):
            cases.append((valid | {field: value}, False))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gh = root / "gh"
            gh.write_text('#!/bin/bash\nprintf "%s" "$MOCK_RUN"\n')
            gh.chmod(0o700)
            for result, expected in cases:
                with self.subTest(result=result):
                    env = os.environ | {"PATH": f"{root}:{os.environ['PATH']}", "MOCK_RUN": json.dumps(result), "ARTIFACT_RUN": "123", "CANDIDATE_SHA": self.sha, "GITHUB_REPOSITORY": OLD, "GITHUB_OUTPUT": str(root / "out")}
                    actual = subprocess.run(["bash", "-c", script], env=env, capture_output=True, check=False)
                    self.assertEqual(actual.returncode == 0, expected)
            env["ARTIFACT_RUN"] = "missing"
            self.assertNotEqual(subprocess.run(["bash", "-c", script], env=env, capture_output=True, check=False).returncode, 0)

    def test_approval_is_still_required(self) -> None:
        doc = copy.deepcopy(self.manifest)
        doc["approval"]["state"] = "PENDING"
        self.both(doc, NEW, False)


if __name__ == "__main__":
    unittest.main()
