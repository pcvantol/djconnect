"""Real SQL source-origin phases; source witnesses here are explicitly synthetic.

Actual original capture/manager/HTTP/lifecycle paths have a separate HA harness.
"""
from __future__ import annotations

import asyncio
import importlib
import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from custom_components.djconnect.persistence import PersistenceService, PersistenceError  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider, _SQLiteTransaction  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE  # noqa: E402
from custom_components.djconnect.surface_source_origin import OriginInput, SourceJournal  # noqa: E402
from tests.test_profile_storage import MemoryStore, ProfilePlatformStorage  # noqa: E402
from tests.test_ask_dj_profile_committed_observation import Hass  # noqa: E402
from custom_components.djconnect import profile_observation as observation  # noqa: E402


class SourceOriginActualProofTests(unittest.TestCase):
    def test_current_source_joins_original_actual_HA_and_same_harness_parent_failure(self):
        root = Path(__file__).resolve().parents[1]
        receipt = json.loads((root / "examples/client_contracts/source_origin_v1/actual-ha-source-origin-data.json").read_text())
        self.assertEqual(receipt["state"], "PASS")
        self.assertEqual(len(receipt["cases"]), 19)
        self.assertEqual(len(receipt["source_sha256"]), 277)
        for relative, digest in receipt["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest, relative)
        harness = hashlib.sha256((root / receipt["harness"]).read_bytes()).hexdigest()
        self.assertEqual(harness, receipt["harness_sha256"])
        self.assertEqual(harness, receipt["parent_causal_RED"]["same_harness_sha256"])
        self.assertEqual(receipt["parent_causal_RED"]["sha"], "99c3ab376047a376415d61c1234645a2c631f3af")
        self.assertTrue(receipt["source_origin_DATA_only"])
        self.assertEqual(receipt["af201_native_mapping"], "NOT_IMPLEMENTED")
        self.assertEqual(receipt["authority"], "NOT_GRANTED")
        for key in ("installed", "native", "provider_activation"):
            self.assertEqual(receipt[key], "NOT_RUN")


class SourceCommittedDataTests(unittest.IsolatedAsyncioTestCase):
    def fresh(self, store=None):
        hass = Hass()
        observation.bootstrap_from_integration_setup(hass)
        manager = ProfilePlatformStorage(hass, store=store or MemoryStore())
        observation.publish_manager(hass, hass.data['djconnect'], manager)
        return hass, manager

    async def test_cold_source_capture_has_no_bootstrap_load_or_mutation(self):
        hass = Hass()
        self.assertIsNone(observation.capture_source_committed(hass))
        self.assertEqual(hass.data, {})
        hass, manager = self.fresh()
        self.assertIsNone(observation.capture_source_committed(hass))
        self.assertFalse(manager._loaded)

    async def test_only_actual_loaded_cached_reads_preserve_source_DATA_continuity(self):
        class CountedStore(MemoryStore):
            calls = 0
            async def async_load(self):
                self.calls += 1
                return await super().async_load()
        store = CountedStore()
        hass, manager = self.fresh(store)
        await manager.async_load()
        old_reader = observation.capture_committed(hass)
        source = observation.capture_source_committed(hass)
        for _ in range(5):
            self.assertIs(await manager.async_load(), source.household)
        self.assertEqual(store.calls, 1)
        self.assertTrue(source.current())
        self.assertFalse(old_reader.current())  # Existing Help snapshot unchanged.

    async def test_original_source_closes_before_queued_write_acquires_lock(self):
        hass, manager = self.fresh()
        await manager.async_load()
        source = observation.capture_source_committed(hass)
        await manager._write_lock.acquire()
        try:
            task = asyncio.create_task(manager.async_create_profile('Synthetic owner'))
            await asyncio.sleep(0)
            self.assertFalse(source.current())
            self.assertIsNone(observation.capture_source_committed(hass))
        finally:
            manager._write_lock.release()
        await task
        self.assertFalse(source.current())

    async def test_failed_store_write_never_reestablishes_original_source_snapshot(self):
        class FailingStore(MemoryStore):
            async def async_save(self, value):
                raise OSError('synthetic_store_failure')
        hass, manager = self.fresh(FailingStore())
        await manager.async_load()
        source = observation.capture_source_committed(hass)
        with self.assertRaises(OSError):
            await manager.async_create_profile('Synthetic owner')
        self.assertFalse(source.current())
        self.assertIsNone(observation.capture_source_committed(hass))

    async def test_actual_commit_ABA_and_module_epoch_cannot_revive_old_source(self):
        hass, manager = self.fresh()
        await manager.async_load()
        source = observation.capture_source_committed(hass)
        original = manager.household
        await manager.async_create_profile('Synthetic owner')
        await manager.async_save(original)
        self.assertFalse(source.current())
        current = observation.capture_source_committed(hass)
        self.assertTrue(current.current())
        importlib.reload(observation)
        self.assertFalse(current.current())
        self.assertIsNone(observation.capture_source_committed(hass))


class SourceOriginSQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "synthetic-origins.sqlite3"
        self.provider = SQLitePersistenceProvider()
        self.service = PersistenceService(self.path, self.provider)
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        self.journal = SourceJournal(self.service)
        self.owner = "explicit-synthetic-owner"
        self.session = (await self.sessions.async_create(self.owner)).session_id
        self.original = self.input(self.session)

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    def input(self, session, owner=None):
        return OriginInput(*(str(uuid.uuid4()) for _ in range(4)), "a" * 64, "b" * 64,
            "c" * 64, session, owner or self.owner, 10000)

    async def rows(self):
        return await self.service.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT origin_id,operation_id,acceptance_id,terminal_id,scope_hash,phase,revision "
            "FROM djconnect_source_origins"))

    async def prepared(self):
        return await self.journal.prepare(self.original, lambda: True)

    async def accepted(self):
        await self.prepared()
        await self.sessions.async_transition(self.owner, self.session, ACTIVE)
        return await self.journal.accept(self.original, lambda: True)

    async def test_original_prepare_accept_and_terminal_have_distinct_recorded_phases(self):
        pending = await self.prepared()
        self.assertEqual((pending.phase, pending.revision), ("prepared", 0))
        await self.sessions.async_transition(self.owner, self.session, ACTIVE)
        result = await self.journal.accept(self.original, lambda: True)
        self.assertEqual((result.phase, result.revision), ("accepted", 1))
        self.assertNotEqual(result.origin, result.operation)
        self.assertEqual(await self.journal.retire(self.original), self.original.terminal)
        row = (await self.rows())[0]
        self.assertEqual(row[-2:], ("retired", 2))
        self.assertEqual(row[:4], (self.original.origin, self.original.operation,
            self.original.acceptance, self.original.terminal))

    async def test_prepare_needs_actual_original_SQL_session_owner_and_opening(self):
        for wrong in [replace(self.original, owner="wrong-owner"), replace(self.original, session="absent")]:
            with self.assertRaises(PersistenceError):
                await self.journal.prepare(wrong, lambda: True)
        await self.sessions.async_transition(self.owner, self.session, ACTIVE)
        with self.assertRaises(PersistenceError):
            await self.prepared()
        self.assertEqual(await self.rows(), [])

    async def test_accept_cannot_replace_actual_ACTIVE_settlement_with_true_callback(self):
        await self.prepared()
        with self.assertRaises(PersistenceError):
            await self.journal.accept(self.original, lambda: True)
        self.assertEqual((await self.rows())[0][-2:], ("prepared", 0))

    async def test_identical_prepare_keeps_original_but_accept_and_retire_cannot_reissue(self):
        first = await self.prepared()
        self.assertEqual(first, await self.prepared())
        await self.sessions.async_transition(self.owner, self.session, ACTIVE)
        await self.journal.accept(self.original, lambda: True)
        with self.assertRaises(PersistenceError):
            await self.journal.accept(self.original, lambda: True)
        with self.assertRaises(PersistenceError):
            await self.prepared()
        await self.journal.retire(self.original)
        before = await self.rows()
        self.assertEqual(await self.journal.retire(self.original), self.original.terminal)
        self.assertEqual(before, await self.rows())
        with self.assertRaises(PersistenceError):
            await self.journal.accept(self.original, lambda: True)

    async def test_terminal_before_accept_preserves_original_and_denies_late_accept(self):
        await self.prepared()
        await self.journal.retire(self.original)
        await self.sessions.async_transition(self.owner, self.session, ACTIVE)
        with self.assertRaises(PersistenceError):
            await self.journal.accept(self.original, lambda: True)
        self.assertEqual((await self.rows())[0][-2:], ("retired", 1))

    async def test_same_session_or_operation_with_different_original_conflicts(self):
        await self.prepared()
        for wrong in [self.input(self.session), replace(self.original, scope="d" * 64),
                      replace(self.original, terminal_nonce="e" * 64)]:
            with self.assertRaises(PersistenceError):
                await self.journal.prepare(wrong, lambda: True)
        self.assertEqual(len(await self.rows()), 1)

    async def test_reserved_terminal_cannot_be_borrowed_by_another_origin_operation(self):
        await self.prepared()
        sid = (await self.sessions.async_create("other-owner")).session_id
        wrong = replace(self.input(sid, "other-owner"), operation=self.original.terminal)
        with self.assertRaises(PersistenceError):
            await self.journal.prepare(wrong, lambda: True)
        with self.assertRaises(PersistenceError):
            await self.journal.retire(replace(self.original, terminal_nonce="f" * 64))
        self.assertEqual((await self.rows())[0][-2:], ("prepared", 0))

    async def test_full_record_and_operation_budgets_leave_existing_terminal_slot_usable(self):
        with patch("custom_components.djconnect.surface_source_origin.MAX_ROWS", 1), \
             patch("custom_components.djconnect.surface_source_origin.MAX_OPERATIONS", 3):
            await self.accepted()
            sid = (await self.sessions.async_create("other-owner")).session_id
            with self.assertRaises(PersistenceError):
                await self.journal.prepare(self.input(sid, "other-owner"), lambda: True)
            await self.journal.retire(self.original)
            with self.assertRaises(PersistenceError):
                await self.journal.prepare(self.input(sid, "other-owner"), lambda: True)
        self.assertEqual(len(await self.rows()), 1)
        self.assertEqual((await self.rows())[0][-2:], ("retired", 2))

    async def test_insufficient_three_slot_budget_refuses_original_without_partial_row(self):
        with patch("custom_components.djconnect.surface_source_origin.MAX_OPERATIONS", 2):
            with self.assertRaises(PersistenceError):
                await self.prepared()
        self.assertEqual(await self.rows(), [])

    async def test_another_nonterminal_session_blocks_new_source_adoption_not_recovery(self):
        second = (await self.sessions.async_create(self.owner)).session_id
        with self.assertRaises(PersistenceError):
            await self.journal.prepare(self.input(second), lambda: True)
        self.assertEqual(await self.rows(), [])

    async def test_real_fault_after_insert_rolls_back_all_original_slots(self):
        execute = _SQLiteTransaction.execute
        def fail_after_insert(tx, statement, parameters=()):
            execute(tx, statement, parameters)
            if statement.startswith("INSERT INTO djconnect_source_origins"):
                raise sqlite3.OperationalError("synthetic_after_actual_insert")
        with patch.object(_SQLiteTransaction, "execute", fail_after_insert):
            with self.assertRaises(PersistenceError):
                await self.prepared()
        self.assertEqual(await self.rows(), [])

    async def test_final_authorization_loss_rolls_back_prepared_record(self):
        count = 0
        def current():
            nonlocal count
            count += 1
            return count == 1
        with self.assertRaises(PermissionError):
            await self.journal.prepare(self.original, current)
        self.assertGreaterEqual(count, 2)
        self.assertEqual(await self.rows(), [])

    async def test_cancel_after_actual_prepare_commit_preserves_truth_and_cancellation(self):
        connection = self.provider._connection
        entered, release = threading.Event(), threading.Event()
        class HeldConnection:
            def execute(self, statement, *args):
                result = connection.execute(statement, *args)
                if statement == "COMMIT":
                    entered.set()
                    assert release.wait(5)
                return result
            def __getattr__(self, name):
                return getattr(connection, name)
        with patch.object(self.provider, "_connection", HeldConnection()):
            task = asyncio.create_task(self.prepared())
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 3))
                task.cancel()
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual((await self.rows())[0][-2:], ("prepared", 0))
        await self.journal.retire(self.original)
        self.assertEqual((await self.rows())[0][-2:], ("retired", 1))

    async def test_lost_ACK_after_actual_accept_commit_does_not_reissue_or_claim_rollback(self):
        await self.prepared()
        await self.sessions.async_transition(self.owner, self.session, ACTIVE)
        execute = self.service.async_in_transaction
        async def lose_reply(*args, **kwargs):
            await execute(*args, **kwargs)
            raise PersistenceError("synthetic_lost_after_real_commit")
        with patch.object(self.service, "async_in_transaction", lose_reply):
            with self.assertRaises(PersistenceError):
                await self.journal.accept(self.original, lambda: True)
        self.assertEqual((await self.rows())[0][-2:], ("accepted", 1))
        with self.assertRaises(PersistenceError):
            await self.journal.accept(self.original, lambda: True)
        await self.journal.retire(self.original)
        self.assertEqual((await self.rows())[0][-2:], ("retired", 2))

    async def test_reopen_retains_phase_and_original_identity_without_any_live_factory(self):
        await self.accepted()
        before = await self.rows()
        await self.service.async_close()
        self.provider = SQLitePersistenceProvider()
        self.service = PersistenceService(self.path, self.provider)
        await self.service.async_initialize()
        self.journal = SourceJournal(self.service)
        self.assertEqual(before, await self.rows())
        self.assertFalse(hasattr(self.journal, "restore_active"))
        await self.journal.retire(self.original)
        self.assertEqual((await self.rows())[0][-2:], ("retired", 2))

    async def test_malformed_original_identity_or_clock_never_creates_row(self):
        for wrong in [replace(self.original, origin="not-uuid"), replace(self.original, created_ms=True),
                      replace(self.original, created_ms=0), replace(self.original, nonce="x"),
                      replace(self.original, acceptance=self.original.operation)]:
            with self.assertRaises(PersistenceError):
                await self.journal.prepare(wrong, lambda: True)
        self.assertEqual(await self.rows(), [])
