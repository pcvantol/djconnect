"""Synthetic coordinated release behavior; no registry or Docker writes."""
import unittest
from unittest.mock import patch
from tools.verification import ghcr_release_guard as guard
from tools.verification import docker_release


class GHCRReleaseGuardTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.digest = "sha256:" + "b" * 64
        self.old = "sha256:" + "c" * 64
        self.state = {"1.1.0": guard.HISTORICAL_DIGEST, "latest": self.old, "1.2": self.old}
        self.writes = []
        self.events = []
        journal = type("Journal", (), {"append": lambda _, event, **fields: self.events.append((event, fields))})()
        self.args = dict(image=guard.TARGET, version="1.2.0", release_sha=self.sha,
                         checkout_sha=self.sha, repository=guard.CORE_REPOSITORY,
                         repository_id=guard.CORE_ID, probe=self.probe, push=self.push,
                         expected_digest=self.digest, journal=journal)

    def probe(self, tag):
        return (200, self.state[tag]) if tag in self.state else (404, None)

    def push(self, reference):
        self.writes.append(reference.rsplit(":", 1)[-1])
        self.state[self.writes[-1]] = self.digest

    def test_default_only_pushes_immutable_tags_and_reads_back(self):
        self.assertEqual(guard.publish(**self.args), self.digest)
        self.assertEqual(self.writes, ["1.2.0", "1.2.0-aaaaaaaaaaaa", "sha-aaaaaaaaaaaa"])
        self.assertEqual(self.state["latest"], self.old)
        self.assertEqual(self.state["1.2"], self.old)
        self.assertEqual(self.state["1.1.0"], guard.HISTORICAL_DIGEST)
        self.assertEqual(self.events[-1][0], "completed")

    def test_mutable_aliases_require_explicit_expected_digests(self):
        self.assertEqual(guard.publish(**self.args, mutable_expected={"1.2": self.old, "latest": self.old}), self.digest)
        self.assertEqual(self.writes[-2:], ["1.2", "latest"])
        self.assertEqual(self.state["latest"], self.digest)

    def test_existing_immutable_or_wrong_alias_fails_before_push(self):
        self.state["1.2.0"] = self.old
        with self.assertRaises(ValueError):
            guard.publish(**self.args)
        self.assertEqual(self.writes, [])
        del self.state["1.2.0"]
        with self.assertRaises(ValueError):
            guard.publish(**self.args, mutable_expected={"1.2": "ABSENT", "latest": self.old})
        self.assertEqual(self.writes, [])

    def test_historical_version_wrong_target_and_wrong_sha_are_rejected(self):
        for changes in ({"version": "1.1.0"}, {"image": "other"}, {"release_sha": "b" * 40}, {"repository_id": "1"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                guard.publish(**{**self.args, **changes})
        self.assertEqual(self.writes, [])

    def test_historical_minor_alias_cannot_be_promoted(self):
        with self.assertRaises(ValueError):
            guard.publish(**{**self.args, "version": "1.1.1"},
                          mutable_expected={"1.1": guard.HISTORICAL_DIGEST, "latest": self.old})
        self.assertEqual(self.writes, [])

    def test_mutable_tag_change_during_release_stops_promotion(self):
        original_push = self.push
        def concurrent_push(reference):
            original_push(reference)
            if reference.endswith(":sha-aaaaaaaaaaaa"):
                self.state["1.2"] = "sha256:" + "d" * 64
        with self.assertRaises(ValueError):
            guard.publish(**{**self.args, "push": concurrent_push},
                          mutable_expected={"1.2": self.old, "latest": self.old})
        self.assertEqual(self.writes, ["1.2.0", "1.2.0-aaaaaaaaaaaa", "sha-aaaaaaaaaaaa"])
        self.assertEqual(self.state["latest"], self.old)

    def test_cli_push_cannot_bypass_coordinated_workflow(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(docker_release, "_git_sha", return_value=self.sha), \
             patch.object(docker_release.subprocess, "check_call") as command:
            with self.assertRaises(ValueError):
                docker_release.main(["--push", "--release-sha", self.sha])
        self.assertEqual(command.call_count, 0)  # no build or push outside the coordinated workflow

    def test_failed_registry_access_or_wrong_readback_stops(self):
        def denied(tag):
            return (200, guard.HISTORICAL_DIGEST) if tag == "1.1.0" else (403, None)
        with self.assertRaises(ValueError):
            guard.publish(**{**self.args, "probe": denied})
        self.assertEqual(self.writes, [])

        def bad_push(reference):
            self.writes.append(reference.rsplit(":", 1)[-1])
            self.state[self.writes[-1]] = "not-a-digest"
        with self.assertRaises(ValueError):
            guard.publish(**{**self.args, "push": bad_push})
        self.assertEqual(self.writes, ["1.2.0"])

    def test_absent_alias_can_only_be_explicitly_promoted(self):
        del self.state["1.2"]
        guard.publish(**self.args, mutable_expected={"1.2": "ABSENT", "latest": self.old})
        self.assertEqual(self.state["1.2"], self.digest)
        self.assertEqual(self.state["latest"], self.digest)

    def test_first_registry_readback_cannot_define_expected_digest(self):
        with self.assertRaises(ValueError):
            guard.publish(**{**self.args, "expected_digest": "sha256:" + "e" * 64})
        self.assertEqual(self.writes, ["1.2.0"])
        self.assertEqual(self.events[-1][0], "failure")

    def test_partial_push_failure_is_journaled_without_retry(self):
        def failing_push(reference):
            if reference.endswith(":1.2.0-aaaaaaaaaaaa"):
                raise OSError("synthetic failure")
            self.push(reference)
        with self.assertRaises(OSError):
            guard.publish(**{**self.args, "push": failing_push})
        self.assertEqual(self.writes, ["1.2.0"])
        self.assertEqual(self.events[-1][0], "failure")
        self.assertFalse(any(tag == "sha-aaaaaaaaaaaa" for tag in self.writes))

class GHCRRunProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.run = {"id": 21, "run_attempt": 1,
                    "path": ".github/workflows/verification-platform-docker-release.yml",
                    "status": "in_progress", "head_sha": self.sha, "event": "workflow_dispatch",
                    "head_branch": "main", "repository": {"id": int(guard.CORE_ID)},
                    "head_repository": {"id": int(guard.CORE_ID)}}

    def test_exact_api_provenance(self):
        guard.validate_run_metadata(self.run, run_id="21", attempt="1", release_sha=self.sha, version="1.2.0")

    def test_wrong_run_attempt_workflow_source_or_event_fails(self):
        for field, value in (("id", 22), ("run_attempt", 2), ("path", "other.yml"),
                             ("status", "completed"), ("head_sha", "b" * 40),
                             ("event", "pull_request"), ("head_branch", "other"),
                             ("repository", {"id": 1}), ("head_repository", {"id": 1})):
            with self.subTest(field=field), self.assertRaises(ValueError):
                guard.validate_run_metadata({**self.run, field: value}, run_id="21", attempt="1", release_sha=self.sha, version="1.2.0")

    def test_push_event_requires_exact_runtime_version_tag(self):
        run = {**self.run, "event": "push", "head_branch": "verification-platform-v1.2.0"}
        guard.validate_run_metadata(run, run_id="21", attempt="1", release_sha=self.sha, version="1.2.0")
        for tag in ("verification-platform-v1.1.0", "verification-platform-v1.2.0-extra", "main"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                guard.validate_run_metadata({**run, "head_branch": tag}, run_id="21", attempt="1", release_sha=self.sha, version="1.2.0")
