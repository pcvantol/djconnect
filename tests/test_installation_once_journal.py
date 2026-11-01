"""Real disposable SQLite metadata journal; authority is explicitly synthetic."""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tests.test_installation_principal_data import fixture, bootstrap_inputs, canonical
from custom_components.djconnect import installation_principal_data as codec
from custom_components.djconnect.installation_once_journal import (
    InstallationOnceError, InstallationOnceJournal, InstallationOnceOwner,
)
from custom_components.djconnect.persistence import PersistenceService
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider


class OriginalActualOnceProofTests(unittest.TestCase):
    def test_current_HA_originals_and_parent_missing_journal_remain_exact(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/installation_once_metadata_v1/actual-ha-once-metadata.json").read_text())
        raw = proof["original_receipt"]
        self.assertEqual(raw["state"], "PASS")
        self.assertEqual(len(raw["cases"]), 8)
        self.assertEqual(len(raw["preceding_installation_codec_cases"]), 6)
        self.assertEqual(len(raw["preceding_source_origin_cases"]), 19)
        self.assertEqual(len(raw["source_sha256"]), 301)
        for name, digest in raw["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        digest = hashlib.sha256((root / proof["harness"]).read_bytes()).hexdigest()
        self.assertEqual(digest, proof["harness_sha256"])
        # The old parent counterproof retains its exact schema19 harness. The
        # current schema21 assertion has its own new actual HA receipt; do not
        # relabel the old RED as an execution of changed source.
        historical = root / "tests/fixtures/installation_principal/once-ha-schema19-original.py.txt"
        self.assertEqual(hashlib.sha256(historical.read_bytes()).hexdigest(),
            proof["parent_causal_RED"]["same_final_harness_sha256"])
        self.assertEqual(proof["parent_causal_RED"]["actual_products"], 278)
        self.assertEqual(proof["installed"], "NOT_RUN")
        self.assertEqual(raw["actual_key_or_sign_effect"], "NOT_RUN")


class SyntheticOwner(InstallationOnceOwner):
    positive = True
    storage = True
    metadata = True
    intent_ack = True

    def validate_policy(self, capacity):
        if not 1 <= capacity <= 128:
            raise PermissionError("synthetic_policy_closed")

    def validate_storage(self, persistence):
        if not self.storage:
            raise PermissionError("synthetic_storage_closed")

    def validate_positive(self, original):
        if not self.positive or (original.kind == "bootstrap_signing" and not self.intent_ack):
            raise PermissionError("synthetic_positive_closed")

    def validate_metadata(self, original, result_hash):
        if not self.metadata:
            raise PermissionError("synthetic_metadata_closed")


def same_operation_bootstrap_inputs(f):
    """Recompute the complete expired public DATA chain, not a malformed hash."""
    values = bootstrap_inputs(f) | {"intent": f["records"]["original_admission_intent"]["canonical"]}
    v = {k: json.loads(s) for k, s in values.items()}
    operation = v["context"]["registration_operation_id"]
    def digest(name):
        return hashlib.sha256(codec.RECORD_DOMAIN + canonical(v[name]).encode()).hexdigest()
    for name in ("generation", "receipt", "subject", "context", "proof"):
        v[name]["custody_operation_id"] = operation
    v["receipt"]["generation_preparation_sha256"] = digest("generation")
    v["subject"]["custody_public_receipt_sha256"] = digest("receipt")
    v["context"].update(generation_preparation_sha256=digest("generation"),
        custody_public_receipt_sha256=digest("receipt"), subject_sha256=digest("subject"))
    v["original_expected_transcript"]["operator_admission_binding_sha256"] = digest("context")
    v["proof"].update(custody_public_receipt_sha256=digest("receipt"),
        subject_sha256=digest("subject"), admission_context_sha256=digest("context"),
        expected_transcript=canonical(v["original_expected_transcript"]))
    v["intent"].update(subject_sha256=digest("subject"),
        admission_context_sha256=digest("context"), bootstrap_preparation_sha256=digest("proof"))
    return {k: canonical(value) for k, value in v.items()}


class InstallationOnceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Host TMPDIR routes scratch to Shared Data; CI keeps its own runner temp.
        self.directory = tempfile.TemporaryDirectory(prefix="installation-once-")
        self.provider = SQLitePersistenceProvider()
        self.service = PersistenceService(Path(self.directory.name) / "journal.db", self.provider)
        await self.service.async_initialize()
        self.owner = SyntheticOwner()
        self.journal = InstallationOnceJournal(self.service, self.owner, capacity=3)
        self.f = fixture()
        self.text = self.f["records"]["custody_generation_preparation"]["canonical"]

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    def generation(self, number=9, revision=1):
        value = json.loads(self.text)
        value.update(custody_operation_id=f"00000000-0000-4000-8000-{number:012d}",
            expected_local_revision=revision)
        return canonical(value)

    async def reserve(self):
        return await self.journal.async_reserve_generation(self.text)

    async def rows(self):
        return await self.service.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT operation_id,phase,revision,result_hash,terminal_reserved,ledger_revision "
            "FROM djconnect_installation_once ORDER BY operation_id"))

    async def test_new_ack_reserved_terminal_and_metadata_then_retired_truth(self):
        first = await self.reserve()
        self.assertEqual(first.state, "ACKNOWLEDGED_METADATA_RESERVATION")
        self.assertIsNotNone(first.original)
        self.assertEqual((await self.rows())[0][1:], (0, 0, "0" * 64, 1, 1))
        result = await self.journal.async_settle_metadata(first.original, "a" * 64)
        self.assertEqual(result.state, "ACKNOWLEDGED_RESULT_METADATA")
        retired = await self.journal.async_retire(first.original)
        self.assertEqual(retired.state, "ACKNOWLEDGED_TERMINAL_METADATA")
        self.assertEqual((await self.rows())[0][1:], (2, 2, "a" * 64, 1, 3))
        self.assertEqual(retired.classification, "LOCAL_ONCE_METADATA_ONLY")

    async def test_requires_abstract_owner_and_explicit_bounded_policy(self):
        with self.assertRaises(TypeError):
            InstallationOnceOwner()
        for owner, capacity in [(None, 1), (self.owner, True), (self.owner, 0), (self.owner, 129)]:
            with self.assertRaises(InstallationOnceError):
                InstallationOnceJournal(self.service, owner, capacity=capacity)
        with patch.object(self.owner, "validate_policy", return_value=True):
            with self.assertRaises(InstallationOnceError):
                InstallationOnceJournal(self.service, self.owner, capacity=1)

    async def test_boolean_positive_is_not_None_or_raise_attestation(self):
        with patch.object(self.owner, "validate_positive", return_value=True):
            with self.assertRaises(InstallationOnceError):
                await self.reserve()
        self.assertEqual(await self.rows(), [])

    async def test_duplicate_and_new_journal_equal_rows_never_mint_original(self):
        first = await self.reserve()
        for journal in [self.journal, InstallationOnceJournal(self.service, self.owner, capacity=3)]:
            duplicate = await journal.async_reserve_generation(self.text)
            self.assertEqual(duplicate.state, "EXISTING_DATA_ONLY")
            self.assertIsNone(duplicate.original)
            with self.assertRaises(InstallationOnceError):
                journal.retire(duplicate.data)
        self.assertIsNotNone(first.original)

    async def test_concurrent_journals_only_one_original_ack(self):
        other = InstallationOnceJournal(self.service, self.owner, capacity=3)
        outcomes = await asyncio.gather(self.reserve(), other.async_reserve_generation(self.text))
        self.assertEqual(sum(x.original is not None for x in outcomes), 1)
        self.assertEqual(len(await self.rows()), 1)

    async def test_original_uuid_conflict_and_cross_kind_reuse_closed(self):
        await self.reserve()
        original = self.journal._generation(self.text)
        for altered in [replace(original, policy_hash="f" * 64),
                        replace(original, kind="bootstrap_signing")]:
            with self.assertRaises(InstallationOnceError):
                await self.journal._reserve(altered)
        self.assertEqual(len(await self.rows()), 1)

    async def test_stale_local_revision_does_not_insert_and_cannot_retry(self):
        await self.reserve()
        with self.assertRaises(InstallationOnceError):
            await self.journal.async_reserve_generation(self.generation(revision=0))
        duplicate = await self.journal.async_reserve_generation(self.generation(revision=0))
        self.assertEqual(duplicate.state, "EXISTING_DATA_ONLY")
        self.assertIsNone(duplicate.data)

    async def test_retirement_does_not_free_capacity_and_reserved_terminal_still_fits(self):
        j = InstallationOnceJournal(self.service, self.owner, capacity=1)
        first = await j.async_reserve_generation(self.text)
        with self.assertRaises(InstallationOnceError):
            await j.async_reserve_generation(self.generation())
        self.owner.positive = False
        self.assertEqual((await j.async_retire(first.original)).state, "ACKNOWLEDGED_TERMINAL_METADATA")
        self.owner.positive = True
        with self.assertRaises(InstallationOnceError):
            await j.async_reserve_generation(self.generation(revision=2))
        self.assertEqual(len(await self.rows()), 1)

    async def test_positive_withdrawal_keeps_original_negative_terminal(self):
        first = await self.reserve()
        self.owner.positive = False
        with self.assertRaises(PermissionError):
            await self.journal.async_settle_metadata(first.original, "b" * 64)
        self.assertTrue(first.original.closed)
        self.assertEqual((await self.journal.async_retire(first.original)).state,
            "ACKNOWLEDGED_TERMINAL_METADATA")

    async def test_local_fence_precedes_wait_for_terminal_storage_lock(self):
        first = await self.reserve()
        await self.provider._write_lock.acquire()
        task = asyncio.create_task(self.journal.async_retire(first.original))
        try:
            await asyncio.sleep(0)
            self.assertTrue(first.original.closed)
            with self.assertRaises(InstallationOnceError):
                await self.journal.async_settle_metadata(first.original, "a" * 64)
        finally:
            self.provider._write_lock.release()
        self.assertEqual((await task).state, "ACKNOWLEDGED_TERMINAL_METADATA")

    async def test_missing_original_storage_is_unknown_not_new_owner_borrowing(self):
        first = await self.reserve()
        self.owner.storage = False
        self.assertEqual((await self.journal.async_retire(first.original)).state, "UNKNOWN")
        self.owner.storage = True
        self.assertEqual((await self.rows())[0][1], 0)
        self.assertIsNone((await self.journal.async_retire(first.original)).original)
        self.assertEqual((await self.rows())[0][1], 0)

    async def test_close_reopen_equal_rows_cannot_recover_old_capability(self):
        first = await self.reserve()
        await self.service.async_close()
        await self.service.async_initialize()
        self.assertEqual((await self.journal.async_retire(first.original)).state, "UNKNOWN")
        other = InstallationOnceJournal(self.service, self.owner, capacity=3)
        self.assertIsNone((await other.async_reserve_generation(self.text)).original)

    async def test_commit_lost_ack_consumed_row_has_no_original_and_no_reissue(self):
        actual = self.service.async_in_transaction
        async def lost(operation, **options):
            await actual(operation, **options)
            raise OSError("synthetic_lost_ack")
        with patch.object(self.service, "async_in_transaction", side_effect=lost):
            self.assertEqual((await self.reserve()).state, "UNKNOWN")
        self.assertEqual((await self.rows())[0][1], 0)
        duplicate = await self.reserve()
        self.assertEqual(duplicate.state, "EXISTING_DATA_ONLY")
        self.assertIsNone(duplicate.original)

    async def test_commit_then_cancel_delivers_cancel_without_undo_or_handle(self):
        actual = self.service.async_in_transaction
        async def cancelled(operation, **options):
            value = await actual(operation, **options)
            asyncio.current_task().cancel()
            return value
        async def run():
            with patch.object(self.service, "async_in_transaction", side_effect=cancelled):
                return await self.reserve()
        task = asyncio.create_task(run())
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual((await self.rows())[0][1], 0)
        self.assertIsNone((await self.reserve()).original)

    async def test_bootstrap_requires_independent_API_intent_ack_not_matching_json(self):
        values = bootstrap_inputs(self.f) | {"intent": self.f["records"]["original_admission_intent"]["canonical"]}
        self.owner.intent_ack = False
        with self.assertRaises(PermissionError):
            await self.journal.async_reserve_signing(**values)
        self.assertEqual(await self.rows(), [])
        self.owner.intent_ack = True
        result = await self.journal.async_reserve_signing(**values)
        self.assertEqual(result.state, "ACKNOWLEDGED_METADATA_RESERVATION")
        self.assertEqual(result.data.row[1], "bootstrap_signing")

    async def test_metadata_denial_and_duplicate_do_not_produce_effect_receipt(self):
        first = await self.reserve()
        self.owner.metadata = False
        with self.assertRaises(PermissionError):
            await self.journal.async_settle_metadata(first.original, "c" * 64)
        self.assertEqual((await self.rows())[0][1], 0)
        self.assertEqual((await self.journal.async_retire(first.original)).state,
            "ACKNOWLEDGED_TERMINAL_METADATA")

    async def test_terminal_storage_failure_unknown_does_not_free_or_retry(self):
        first = await self.reserve()
        with patch.object(self.service, "async_in_transaction", side_effect=OSError("synthetic_disk")):
            self.assertEqual((await self.journal.async_retire(first.original)).state, "UNKNOWN")
        self.assertEqual((await self.rows())[0][1], 0)
        self.assertEqual((await self.journal.async_retire(first.original)).state, "EXISTING_DATA_ONLY")
        self.assertEqual((await self.rows())[0][1], 0)

    async def test_actual_write_uses_WAL_FULL_then_restores_normal(self):
        observed = []
        actual = self.provider._async_guarded_transaction
        async def inspect(operation, finalize):
            def wrapped(tx):
                observed.append((tx.fetchone("PRAGMA journal_mode")[0],
                    tx.fetchone("PRAGMA synchronous")[0]))
                return operation(tx)
            return await actual(wrapped, finalize)
        with patch.object(self.provider, "_async_guarded_transaction", side_effect=inspect):
            await self.reserve()
        self.assertEqual(observed, [("wal", 2)])
        self.assertEqual(await self.service.async_in_transaction(lambda tx:
            tx.fetchone("PRAGMA synchronous")[0]), 1)
        self.assertEqual(self.service.readiness.schema_version, 21)

    async def test_withdrawal_after_SQL_stage_before_final_fence_rolls_back(self):
        staged, release = asyncio.Event(), threading.Event()
        loop = asyncio.get_running_loop()
        actual = self.provider._async_guarded_transaction
        async def held(operation, finalize):
            def wait(tx):
                result = operation(tx)
                loop.call_soon_threadsafe(staged.set)
                if not release.wait(5):
                    raise AssertionError("synthetic_hold_timeout")
                return result
            return await actual(wait, finalize)
        with patch.object(self.provider, "_async_guarded_transaction", side_effect=held):
            task = asyncio.create_task(self.reserve())
            try:
                await asyncio.wait_for(staged.wait(), 3)
                self.owner.positive = False
            finally:
                release.set()
            self.assertEqual((await task).state, "UNKNOWN")
        self.assertEqual(await self.rows(), [])
        self.owner.positive = True
        duplicate = await self.reserve()
        self.assertIsNone(duplicate.original)
        self.assertIsNone(duplicate.data)

    async def test_actual_commit_before_owner_loss_keeps_closed_original_terminal(self):
        actual = self.provider._async_guarded_transaction
        async def closed_after_commit(operation, finalize):
            result = await actual(operation, finalize)
            self.owner.positive = False
            return result
        with patch.object(self.provider, "_async_guarded_transaction", side_effect=closed_after_commit):
            result = await self.reserve()
        self.assertEqual(result.state, "ACKNOWLEDGED_CLOSED")
        self.assertTrue(result.original.closed)
        self.assertEqual((await self.journal.async_retire(result.original)).state,
            "ACKNOWLEDGED_TERMINAL_METADATA")

    async def test_metadata_commit_with_late_retirement_cannot_become_usable(self):
        first = await self.reserve()
        actual = self.provider._async_guarded_transaction
        async def closed_after_commit(operation, finalize):
            result = await actual(operation, finalize)
            self.journal.retire(first.original)
            return result
        with patch.object(self.provider, "_async_guarded_transaction", side_effect=closed_after_commit):
            result = await self.journal.async_settle_metadata(first.original, "d" * 64)
        self.assertEqual(result.state, "ACKNOWLEDGED_CLOSED")
        self.assertEqual((await self.rows())[0][1:4], (1, 1, "d" * 64))
        self.assertEqual((await self.journal.async_retire(first.original)).state,
            "ACKNOWLEDGED_TERMINAL_METADATA")

    async def test_metadata_commit_lost_ack_keeps_truth_then_original_can_retire(self):
        first = await self.reserve()
        actual = self.service.async_in_transaction
        async def lost(operation, **options):
            await actual(operation, **options)
            raise OSError("synthetic_lost_metadata_ack")
        with patch.object(self.service, "async_in_transaction", side_effect=lost):
            result = await self.journal.async_settle_metadata(first.original, "e" * 64)
        self.assertEqual(result.state, "UNKNOWN")
        self.assertTrue(first.original.closed)
        self.assertEqual((await self.rows())[0][1:4], (1, 1, "e" * 64))
        self.assertEqual((await self.journal.async_retire(first.original)).state,
            "ACKNOWLEDGED_TERMINAL_METADATA")

    async def test_restart_status_is_observational_no_reserve_or_revision(self):
        first = await self.reserve()
        before = await self.rows()
        await self.service.async_close()
        await self.service.async_initialize()
        other = InstallationOnceJournal(self.service, self.owner, capacity=3)
        for _ in range(3):
            data = await other.async_status(first.original.operation.operation_id)
            self.assertFalse(hasattr(data, "original"))
            self.assertIsNone(await other.async_status("00000000-0000-4000-8000-000000000099"))
        self.assertEqual(before, await self.rows())
        self.assertEqual(other._attempted, {})

    async def test_commit_then_actual_storage_close_reopen_is_unknown_not_input_rejection(self):
        actual = self.service.async_in_transaction
        async def reopened(operation, **options):
            result = await actual(operation, **options)
            await self.service.async_close()
            await self.service.async_initialize()
            return result
        with patch.object(self.service, "async_in_transaction", side_effect=reopened):
            result = await self.reserve()
        self.assertEqual(result.state, "UNKNOWN")
        self.assertIsNone(result.original)
        self.assertEqual((await self.rows())[0][1], 0)
        new_journal = InstallationOnceJournal(self.service, self.owner, capacity=3)
        self.assertIsNone((await new_journal.async_reserve_generation(self.text)).original)

    async def test_selfconsistent_DATA_cannot_reuse_generation_ID_for_signing_on_empty_SQL(self):
        values = same_operation_bootstrap_inputs(self.f)
        # The unchanged DATA codec is deliberately not an admission authority.
        chain = codec.check_bootstrap_chain(**{k: v for k, v in values.items() if k != "intent"})
        self.assertEqual(chain[0].values["custody_operation_id"],
            chain[-2].values["registration_operation_id"])
        with self.assertRaises(InstallationOnceError):
            await self.journal.async_reserve_signing(**values)
        self.assertEqual(await self.rows(), [])
        self.assertEqual(self.journal._attempted, {})
