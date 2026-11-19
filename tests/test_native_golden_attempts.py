"""Private attempt-journal boundaries; no credential, network or native claims."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch
import uuid

from tools.verification.native_golden_attempts import ACTIVE, AttemptJournal, sha


def admission(cases=1, *, limit=40, per_turn=2, policy="one_or_two"):
    now = datetime.now(UTC)
    return {"schema_version": 1, "scope": "PRIVATE_OBSERVER_NOT_FIXTURE_ADMISSION",
        "run_id": str(uuid.uuid4()), "producer_commit": "a" * 40,
        "catalog_sha256": "b" * 64, "profile_sha256": sha("profile-fixture"),
        "session_sha256": sha("session-fixture"), "app_executable_sha256": "c" * 64,
        "core_install_receipt_sha256": "d" * 64, "max_model_calls": limit,
        "attempts_per_turn": per_turn, "starts_at": (now-timedelta(seconds=1)).isoformat(),
        "expires_at": (now+timedelta(seconds=60)).isoformat(),
        "cases": [{"id": f"case-{i}", "question_sha256": sha(f"question-{i}"), "model_policy": policy}
                  for i in range(cases)]}


def turn(journal, index=0, **changes):
    values = {"client_message_id": f"client-{index}", "question": f"question-{index}",
              "profile_id": "profile-fixture", "session_id": "session-fixture"}
    return journal.turn(f"case-{index}", **(values | changes))


class NativeGoldenAttemptTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / "attempts.json"

    def journal(self, **kwargs):
        return AttemptJournal.create(self.path, admission(**kwargs))

    def test_retries_share_atomic_per_turn_budget_across_threads(self):
        journal = self.journal()
        with turn(journal):
            binding = ACTIVE.get()
            def attempt(_):
                token = ACTIVE.set(binding)
                try:
                    try:
                        return journal.reserve("fixture-model")
                    except ValueError:
                        return None
                finally:
                    ACTIVE.reset(token)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(attempt, range(24)))
        self.assertEqual(sorted(v for v in results if v is not None), [1, 2])
        report = journal.export()
        self.assertEqual(report["observed_total_provider_attempts"], 2)
        self.assertTrue(all(r["reserved_before_io"] and not r["completed"] for r in report["provider_attempts"]))

    def test_total_limit_survives_reopen_and_failed_attempts_count(self):
        journal = self.journal(cases=21)
        for i in range(20):
            with turn(journal, i):
                for _ in range(2):
                    ordinal = journal.reserve("fixture-model")
                    journal.finish(ordinal)
        resumed = AttemptJournal(self.path, journal.admission)
        with turn(resumed, 20), self.assertRaises(ValueError):
            resumed.reserve("fixture-model")
        self.assertEqual(resumed.export()["observed_total_provider_attempts"], 40)
        with self.assertRaises(FileExistsError):
            AttemptJournal.create(self.path, journal.admission)

    def test_wrong_owner_question_order_and_zero_policy_fail_before_dispatch(self):
        journal = self.journal(policy="zero")
        for change in ({"question": "another"}, {"profile_id": "another"}, {"session_id": "another"}):
            with self.assertRaises(ValueError), turn(journal, **change):
                self.fail("wrong context entered")
        with turn(journal), self.assertRaises(ValueError):
            journal.reserve("fixture-model")
        self.assertEqual(journal.export()["observed_total_provider_attempts"], 0)
        with self.assertRaises(ValueError), turn(journal):
            self.fail("replay entered")
        with self.assertRaises(ValueError):
            journal.reserve("fixture-model")

    def test_expiry_or_budget_mutation_cannot_reserve(self):
        journal = self.journal()
        with turn(journal):
            before = self.path.read_bytes()
            with patch("tools.verification.native_golden_attempts.time.time", return_value=10**12), self.assertRaises(ValueError):
                journal.reserve("fixture-model")
            self.assertEqual(self.path.read_bytes(), before)
        altered = deepcopy(journal.admission)
        altered["max_model_calls"] = 39
        with self.assertRaises(ValueError):
            AttemptJournal(self.path, altered).export()
        for change in ({"max_model_calls": 41}, {"attempts_per_turn": 3}, {"max_model_calls": True},
                       {"scope": "QUALIFIED"}):
            with self.assertRaises(ValueError):
                AttemptJournal(self.path, journal.admission | change)

    def test_closed_admission_rejects_unknown_secret_fields_without_writing(self):
        for key in ("api_key", "prompt", "authorization", "history", "native", "unknown"):
            settings = admission() | {key: "PRIVATE_SENTINEL"}
            with self.assertRaises(ValueError):
                AttemptJournal.create(self.path, settings)
            self.assertFalse(self.path.exists())

    def test_monotonic_deadline_is_not_renewed_by_rollback_or_reopen(self):
        journal = self.journal()
        lifetime = json.loads(self.path.read_text())["lifetime"]
        with turn(journal):
            before = self.path.read_bytes()
            utc_inside = datetime.fromisoformat(journal.admission["starts_at"]).timestamp() + .5
            resumed = AttemptJournal(self.path, journal.admission)
            with patch("tools.verification.native_golden_attempts.time.time", return_value=utc_inside), \
                    patch("tools.verification.native_golden_attempts.time.monotonic", return_value=lifetime["deadline_monotonic"] + 1), \
                    self.assertRaises(ValueError):
                resumed.reserve("fixture-model")
            self.assertEqual(before, self.path.read_bytes())
            with patch("tools.verification.native_golden_attempts._PROCESS", "f" * 32), self.assertRaises(ValueError):
                resumed.reserve("fixture-model")
            self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(json.loads(self.path.read_text())["lifetime"], lifetime)
        self.assertEqual(journal.export()["deadline_policy"], "NON_RENEWABLE_MONOTONIC_RESTART_REFUSES_NEW_IO")

    def test_private_journal_and_original_server_binding_not_native_echo(self):
        journal = self.journal()
        with turn(journal):
            ordinal = journal.reserve("fixture-model")
            journal.finish(ordinal, completed=True, model="fixture-model", input_tokens=10,
                           output_tokens=2, response_id="provider-id-private")
        response = {"success": True, "owner_profile_id": "profile-fixture", "client_message_id": "client-0",
                    "assistant_message": {"id": "assistant-message-id", "text": "Private answer fixture"},
                    "conversation": {"history_scope": "profile", "turn_id": "different-conversation-turn-id",
                                     "context": {"session_id": "session-fixture"}}}
        history = {"id": "assistant-message-id", "client_message_id": "client-0", "text": "Private answer fixture"}
        entry = {"entry_id": "entry-fixture", "session_id": "session-fixture", "kind": "conversation_dj",
                 "body": {"message_id": "assistant-message-id", "turn_id": "different-conversation-turn-id"}}
        bad = deepcopy(entry)
        bad["body"]["message_id"] = "some-other-message"
        with self.assertRaises(ValueError):
            journal.record_result("case-0", response, history, bad)
        journal.record_result("case-0", response, history, entry)
        report = journal.export()
        self.assertEqual(report["cases"][0]["server_turn_sha256"], sha("assistant-message-id"))
        self.assertNotEqual(report["cases"][0]["server_turn_sha256"], sha("different-conversation-turn-id"))
        self.assertEqual(report["export_status"], "OBSERVED_NOT_QUALIFIED")
        self.assertIsNone(report["unattributed_provider_attempts"])
        self.assertEqual(report["semantic_verdict"], "NOT_REVIEWED")
        raw = self.path.read_text()
        for private in ("Private answer fixture", "question-0", "profile-fixture", "provider-id-private"):
            self.assertNotIn(private, raw)
        link = self.path.parent / "alias.json"
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            AttemptJournal(link, journal.admission).export()
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            journal.export()

    def test_persisted_unknown_fields_or_changed_usage_are_rejected(self):
        journal = self.journal()
        with turn(journal):
            ordinal = journal.reserve("fixture-model")
            journal.finish(ordinal, completed=True, model="fixture-model", input_tokens=1,
                           output_tokens=1, response_id="fixture-id")
        original = json.loads(self.path.read_text())
        for location, key, value in (("admission", "api_key", "PRIVATE_SENTINEL"),
                                     ("turns", "prompt", "PRIVATE_SENTINEL"),
                                     ("attempts", "authorization", "PRIVATE_SENTINEL"),
                                     ("attempts", "output_tokens", 100)):
            altered = deepcopy(original)
            target = altered[location] if location == "admission" else altered[location][0]
            target[key] = value
            self.path.write_text(json.dumps(altered))
            with self.assertRaises(ValueError):
                journal.export()
        self.path.write_text(json.dumps(original))
        self.assertEqual(journal.export()["observed_total_provider_attempts"], 1)

    def test_missing_usage_or_boolean_tokens_cannot_become_completed(self):
        journal = self.journal()
        with turn(journal):
            for output in (None, True):
                ordinal = journal.reserve("fixture-model")
                journal.finish(ordinal, completed=True, model="fixture-model", input_tokens=10,
                               output_tokens=output, response_id="fixture-id")
        self.assertTrue(all(not a["completed"] for a in journal.export()["provider_attempts"]))
        self.assertTrue(all(a["provider_receipt_sha256"] for a in journal.export()["provider_attempts"]))
        self.assertEqual(len({a["provider_receipt_sha256"] for a in journal.export()["provider_attempts"]}), 2)


if __name__ == "__main__":
    unittest.main()
