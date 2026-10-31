"""Real disposable SQLite, synthetic authority and INERT effects only."""
import asyncio
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_installation_once_journal import SyntheticOwner
from tests.test_installation_principal_data import fixture, bootstrap_inputs
from custom_components.djconnect.installation_custody_once import (
    CustodyEffectPort, CustodyOperationOwner, CustodyUnavailable, InstallationCustodyOnce,
)
from custom_components.djconnect.installation_once_journal import InstallationOnceJournal
from custom_components.djconnect.persistence import PersistenceService
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider


DIGEST = hashlib.sha256(b"inert-public-metadata-not-a-key-or-signature").hexdigest()


class CustodyOriginalHaProofTests(unittest.TestCase):
    def test_actual_HA_original_source_and_harness_remain_exact_metadata_only(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/installation_custody_once_v1/actual-ha-custody-metadata.json").read_text())
        raw = proof["original_receipt"]
        self.assertEqual(raw["state"], "PASS")
        self.assertEqual(len(raw["cases"]), 4)
        self.assertEqual(len(raw["preceding_installation_once_cases"]), 8)
        self.assertEqual(len(raw["source_sha256"]), 289)
        for name, digest in raw["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((root / proof["harness"]).read_bytes()).hexdigest(),
                         proof["harness_sha256"])
        self.assertEqual(proof["installed"], "NOT_RUN")
        self.assertEqual(raw["actual_key_generation_signing_registry_provider_or_native_effect"], "NOT_RUN")


class InertPort(CustodyEffectPort):
    def __init__(self):
        self.calls = []
        self.hook = lambda original: DIGEST

    def generate_once(self, original):
        self.calls.append(original.kind)
        return self.hook(original)

    def bootstrap_possession_once(self, original):
        self.calls.append(original.kind)
        return self.hook(original)


class SyntheticCustodyOwner(CustodyOperationOwner):
    def __init__(self):
        self.composition = lambda journal, port: None
        self.attempt = lambda original, port: None
        self.result = lambda original, digest: None

    def validate_composition(self, journal, port):
        return self.composition(journal, port)

    def validate_attempt(self, original, port):
        return self.attempt(original, port)

    def validate_result(self, original, result_hash):
        return self.result(original, result_hash)


class CustodyOnceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="custody-once-")
        self.service = PersistenceService(Path(self.directory.name) / "journal.db", SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.journal_owner = SyntheticOwner()
        self.journal = InstallationOnceJournal(self.service, self.journal_owner, capacity=3)
        self.owner, self.port = SyntheticCustodyOwner(), InertPort()
        self.subject = InstallationCustodyOnce(self.journal, self.owner, self.port)
        self.fixture = fixture()
        self.text = self.fixture["records"]["custody_generation_preparation"]["canonical"]
        self.original = self.journal._generation(self.text)
        self.op = self.original.operation_id

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    async def row(self):
        value = await self.journal.async_status(self.op)
        return None if value is None else value.row

    async def test_generation_ack_precedes_single_inert_call_and_digest_settlement(self):
        def inert(original):
            handle = self.subject._attempts[self.op].reservation
            self.assertIs(self.journal._handles[self.op], handle)
            self.assertTrue(self.subject._attempts[self.op].attempted)
            return DIGEST
        self.port.hook = inert
        result = await self.subject.async_generate(self.text)
        self.assertEqual(result.state, "ACKNOWLEDGED_RESULT_METADATA")
        self.assertEqual(result.classification, "CLOSED_CUSTODY_METADATA_ONLY")
        self.assertEqual(self.port.calls, ["custody_generation"])
        self.assertEqual((await self.row())[6:10], (1, 1, DIGEST, 1))
        with self.assertRaises(CustodyUnavailable):
            await self.subject.async_generate(self.text)
        self.assertEqual(len(self.port.calls), 1)

    async def test_bootstrap_is_separate_kind_with_original_intent(self):
        values = bootstrap_inputs(self.fixture)
        result = await self.subject.async_bootstrap_possession(
            intent=self.fixture["records"]["original_admission_intent"]["canonical"], **values)
        self.assertEqual(result.state, "ACKNOWLEDGED_RESULT_METADATA")
        self.assertEqual(self.port.calls, ["bootstrap_signing"])

    async def test_missing_original_intent_ack_never_calls_port(self):
        self.journal_owner.intent_ack = False
        result = await self.subject.async_bootstrap_possession(
            intent=self.fixture["records"]["original_admission_intent"]["canonical"],
            **bootstrap_inputs(self.fixture))
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(self.port.calls, [])

    async def test_existing_sql_in_new_coordinator_cannot_mint_invocation(self):
        await self.subject.async_generate(self.text)
        journal = InstallationOnceJournal(self.service, self.journal_owner, capacity=3)
        other = InstallationCustodyOnce(journal, self.owner, self.port)
        result = await other.async_generate(self.text)
        self.assertEqual(result.state, "EXISTING_DATA_ONLY")
        self.assertEqual(len(self.port.calls), 1)

    async def test_restart_reopens_real_SQL_but_not_effect_authority(self):
        await self.subject.async_generate(self.text)
        await self.service.async_close()
        await self.service.async_initialize()
        journal = InstallationOnceJournal(self.service, self.journal_owner, capacity=3)
        other = InstallationCustodyOnce(journal, self.owner, self.port)
        self.assertEqual((await other.async_generate(self.text)).state, "EXISTING_DATA_ONLY")
        self.assertEqual(len(self.port.calls), 1)

    async def test_pending_withdrawal_and_concurrent_duplicate_before_ACK(self):
        started, release = asyncio.Event(), asyncio.Event()
        reserve = self.journal._reserve
        async def held(original):
            result = await reserve(original)
            started.set()
            await release.wait()
            return result
        with patch.object(self.journal, "_reserve", held):
            task = asyncio.create_task(self.subject.async_generate(self.text))
            await started.wait()
            with self.assertRaises(CustodyUnavailable):
                await self.subject.async_generate(self.text)
            self.subject.retire(self.op)
            release.set()
            self.assertEqual((await task).state, "ACKNOWLEDGED_CLOSED")
        self.assertEqual(self.port.calls, [])
        self.assertTrue(self.journal._handles[self.op].closed)
        self.assertEqual((await self.subject.async_retire_metadata(self.op)).state,
                         "ACKNOWLEDGED_TERMINAL_METADATA")
        self.assertEqual((await self.row())[6], 2)

    async def test_lost_ACK_leaves_committed_spent_row_without_call(self):
        reserve = self.journal._reserve
        async def lost(original):
            await reserve(original)
            raise OSError("synthetic-private-value-must-not-escape")
        with patch.object(self.journal, "_reserve", lost):
            self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(self.port.calls, [])
        self.assertEqual((await self.row())[6:8], (0, 0))
        with self.assertRaises(CustodyUnavailable):
            await self.subject.async_generate(self.text)

    async def test_cancel_after_real_commit_ACK_has_no_call_and_no_retry(self):
        reserve = self.journal._reserve
        async def cancelled(original):
            result = await reserve(original)
            asyncio.current_task().cancel()
            return result
        with patch.object(self.journal, "_reserve", cancelled):
            task = asyncio.create_task(self.subject.async_generate(self.text))
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.port.calls, [])
        self.assertTrue(self.journal._handles[self.op].closed)
        self.assertEqual((await self.row())[6], 0)

    async def test_reentrant_retirement_in_final_owner_validation_blocks_call(self):
        def check(original, port):
            if self.subject._attempts[self.op].attempted:
                self.subject.retire(self.op)
        self.owner.attempt = check
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(self.port.calls, [])
        self.assertTrue(self.journal._handles[self.op].closed)

    async def test_reentrant_port_replacement_is_not_invoked(self):
        replacement = InertPort()
        def check(original, port):
            if self.subject._attempts[self.op].attempted:
                self.subject._port = replacement
        self.owner.attempt = check
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(self.port.calls + replacement.calls, [])

    async def test_direct_original_journal_retirement_in_validation_blocks_call(self):
        def check(original, port):
            slot = self.subject._attempts[self.op]
            if slot.attempted:
                self.journal.retire(slot.reservation)
        self.owner.attempt = check
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(self.port.calls, [])

    async def test_owner_true_is_not_None_or_authority(self):
        self.owner.attempt = lambda original, port: True
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(self.port.calls, [])

    async def test_original_clock_revocation_or_storage_denial_is_closed(self):
        for field in ("positive", "storage"):
            with self.subTest(field=field):
                setattr(self.journal_owner, field, False)
                other = InstallationCustodyOnce(self.journal, self.owner, self.port)
                self.assertEqual((await other.async_generate(self.text)).state, "UNKNOWN")
                setattr(self.journal_owner, field, True)
        self.assertEqual(self.port.calls, [])

    async def test_inert_port_failure_preserves_UNKNOWN_without_leaking_values(self):
        def fail(original):
            raise OSError("synthetic-private-provider-value")
        self.port.hook = fail
        result = await self.subject.async_generate(self.text)
        self.assertEqual(result.state, "UNKNOWN")
        self.assertNotIn("synthetic", repr(result))
        self.assertEqual((await self.row())[6:8], (0, 0))
        self.assertEqual(len(self.port.calls), 1)

    async def test_coroutine_result_is_closed_without_executing_body(self):
        executed = []
        async def invalid():
            executed.append(True)
            return DIGEST
        coroutine = invalid()
        self.port.hook = lambda original: coroutine
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertIsNone(coroutine.cr_frame)
        self.assertEqual(executed, [])
        self.assertEqual((await self.row())[6], 0)

    async def test_withdrawal_during_result_attestation_keeps_result_closed(self):
        self.owner.result = lambda original, digest: self.subject.retire(self.op)
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(len(self.port.calls), 1)
        self.assertEqual((await self.row())[6], 0)

    async def test_rejected_suspended_coroutine_does_not_execute_finally(self):
        finalized = []
        async def invalid():
            try:
                await asyncio.sleep(0)
            finally:
                finalized.append(True)
        coroutine = invalid()
        coroutine.send(None)  # Owner-side inert preparation, NOT coordinator work.
        self.port.hook = lambda original: coroutine
        try:
            self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
            self.assertEqual(finalized, [])
        finally:
            coroutine.close()  # Test owner disposes its own rejected object.

    async def test_late_settlement_after_withdrawal_cannot_return_positive(self):
        settle = self.journal.async_settle_metadata
        async def late(handle, digest):
            result = await settle(handle, digest)
            self.subject.retire(self.op)
            return result
        with patch.object(self.journal, "async_settle_metadata", late):
            self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(len(self.port.calls), 1)
        self.assertEqual((await self.row())[6], 1)  # Committed truth is retained.

    async def test_no_effect_factory_or_operational_signing_entrypoint(self):
        for name in ("sign", "operational_sign", "resume", "reset", "retry", "enroll"):
            self.assertFalse(hasattr(self.subject, name))
        self.assertEqual((await self.subject.async_retire_metadata(self.op)).state, "UNKNOWN")

    async def test_constructor_sanitizes_owner_exception(self):
        def fail(journal, port):
            raise ValueError("synthetic-private-owner-value")
        self.owner.composition = fail
        with self.assertRaisesRegex(CustodyUnavailable, "^installation_custody_unavailable$"):
            InstallationCustodyOnce(self.journal, self.owner, self.port)

    async def test_direct_journal_retirement_inside_journal_owner_blocks_call(self):
        validate = self.journal_owner.validate_positive
        def reentrant(original):
            validate(original)
            slot = self.subject._attempts[self.op]
            if slot.attempted:
                self.journal.retire(slot.reservation)
        self.journal_owner.validate_positive = reentrant
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(self.port.calls, [])

    async def test_awaitable_rejection_never_calls_its_iterator(self):
        called = []
        class Invalid:
            def __await__(self):
                called.append(True)
                yield
        self.port.hook = lambda original: Invalid()
        self.assertEqual((await self.subject.async_generate(self.text)).state, "UNKNOWN")
        self.assertEqual(called, [])

    async def test_invalid_public_result_types_retain_spent_capacity(self):
        for index, value in enumerate((True, "A" * 64, "a" * 65)):
            with self.subTest(value_type=type(value).__name__, index=index):
                document = json.loads(self.text)
                document["custody_operation_id"] = f"00000000-0000-4000-8000-{index + 20:012d}"
                document["expected_local_revision"] = index
                self.port.hook = lambda original, value=value: value
                text = json.dumps(document, sort_keys=True, separators=(",", ":"))
                self.assertEqual((await self.subject.async_generate(text)).state, "UNKNOWN")
        self.assertEqual(len(self.port.calls), 3)
        with self.assertRaises(CustodyUnavailable):
            await self.subject.async_generate(self.text)
        self.assertEqual(len(self.subject._attempts), 3)

    async def test_cancel_after_settlement_preserves_committed_truth_not_success(self):
        settle = self.journal.async_settle_metadata
        async def cancelled(handle, digest):
            result = await settle(handle, digest)
            asyncio.current_task().cancel()
            return result
        with patch.object(self.journal, "async_settle_metadata", cancelled):
            task = asyncio.create_task(self.subject.async_generate(self.text))
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(len(self.port.calls), 1)
        self.assertEqual((await self.row())[6:9], (1, 1, DIGEST))
        with self.assertRaises(CustodyUnavailable):
            await self.subject.async_generate(self.text)
