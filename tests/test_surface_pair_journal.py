"""Real SQLite local-pair settlement, cancellation and monotonic retirement."""
from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from custom_components.djconnect.persistence import PersistenceError, PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.surface_pair_journal import PairJournal, schedule_pair_registration  # noqa: E402
from custom_components.djconnect.surface_registration import PairingRetirement, retire_runtime  # noqa: E402


class PairJournalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "pairs.sqlite3"
        self.provider = SQLitePersistenceProvider()
        self.service = PersistenceService(self.path, self.provider)
        await self.service.async_initialize()
        self.journal = PairJournal(self.service)
        self.generation = str(uuid.uuid4())

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    async def record(self, binding="a", generation=None, current=lambda: True):
        return await self.journal.record(binding, "entry", generation or self.generation, current)

    async def rows(self):
        return await self.service.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT binding,auth_generation,state FROM djconnect_surface_pairs ORDER BY binding"))

    async def test_real_commit_reopen_duplicate_keeps_original_identity_and_generation(self):
        ack = await self.record()
        duplicate = await self.record(generation=str(uuid.uuid4()))
        self.assertEqual(ack, duplicate)
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.journal = PairJournal(self.service)
        self.assertEqual(await self.record(generation=str(uuid.uuid4())), ack)
        self.assertEqual(len(await self.rows()), 1)
        # This is private storage data only, no lease/authority/SDK capability.
        self.assertEqual(set(ack.__dataclass_fields__), {"instance_id", "auth_generation"})

    async def test_full_sync_applies_during_operation_then_normal_restored(self):
        policy = await self.service.async_in_transaction(
            lambda tx: tx.fetchone("PRAGMA synchronous")[0], require_full_sync=True)
        self.assertEqual(policy, 2)
        self.assertEqual(await self.service.async_in_transaction(
            lambda tx: tx.fetchone("PRAGMA synchronous")[0]), 1)
        with self.assertRaises(ValueError):
            await self.service.async_in_transaction(lambda tx: (_ for _ in ()).throw(ValueError()),
                                                    require_full_sync=True)
        self.assertEqual(await self.service.async_in_transaction(
            lambda tx: tx.fetchone("PRAGMA synchronous")[0]), 1)

    async def test_non_WAL_mode_is_rejected_without_repair_or_record(self):
        await asyncio.to_thread(self.provider._connection.execute, "PRAGMA journal_mode=DELETE")
        with self.assertRaises(PersistenceError):
            await self.record()
        self.assertEqual(await self.rows(), [])
        self.assertEqual(await self.service.async_in_transaction(
            lambda tx: tx.fetchone("PRAGMA journal_mode")[0]), "delete")

    async def test_silently_ignored_policy_restore_poisons_later_writes(self):
        connection = self.provider._connection
        class IgnoreRestore:
            def execute(self, sql, *args):
                if sql == "PRAGMA synchronous=1":
                    return connection.execute("SELECT 1")
                return connection.execute(sql, *args)
            def __getattr__(self, key):
                return getattr(connection, key)
        self.provider._connection = IgnoreRestore()
        with self.assertRaises(PersistenceError):
            await self.record()
        self.assertTrue(self.provider._write_poisoned)
        with self.assertRaises(PersistenceError):
            await self.service.async_in_transaction(lambda tx: tx.execute("SELECT 1"))
        # A commit may have happened, but it was never an acknowledged result.
        self.assertEqual(connection.execute("SELECT state FROM djconnect_surface_pairs").fetchall(),
                         [("recorded",)])

    async def test_late_authorization_failure_rolls_back_full_commit(self):
        checks = []
        def current():
            checks.append(1)
            return len(checks) == 1
        with self.assertRaises(PermissionError):
            await self.record(current=current)
        self.assertEqual(await self.rows(), [])

    async def test_token_rotation_and_ABA_cannot_resurrect_old_binding(self):
        await self.record("a")
        await self.record("b", str(uuid.uuid4()))
        with self.assertRaises(PersistenceError):
            await self.record("a", str(uuid.uuid4()))
        self.assertEqual([row[2] for row in await self.rows()], ["retired", "recorded"])

    async def test_early_retirement_tombstone_blocks_late_record(self):
        await self.journal.retire("a", "entry", self.generation)
        with self.assertRaises(PersistenceError):
            await self.record()
        # A distinct actual auth binding can still be recorded.
        await self.record("b", str(uuid.uuid4()))
        self.assertEqual([row[2] for row in await self.rows()], ["retired", "recorded"])

    async def test_missing_store_identity_is_not_repaired_from_pair_records(self):
        await self.record()
        await self.service.async_in_transaction(lambda tx: tx.execute(
            "DELETE FROM djconnect_surface_pair_store"))
        with self.assertRaises(PersistenceError):
            await self.record("b")
        self.assertEqual(len(await self.rows()), 1)

    def configure_runtime(self):
        self.entry = SimpleNamespace(entry_id="entry", disabled_by=None,
            state=SimpleNamespace(value="loaded"), options={}, data={
                "device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios",
                "device_token": "SYNTHETIC-PAIR-ONLY", "ha_install_id": "synthetic-ha"})
        self.runtime = SimpleNamespace(entry=self.entry,
            device_token=self.entry.data["device_token"],
            pairing_device_id=self.entry.data["device_id"],
            surface_registration_retirement=PairingRetirement())
        self.hass = SimpleNamespace(is_stopping=False,
            data={"djconnect": {"entry": self.runtime}},
            async_create_task=asyncio.create_task,
            config_entries=SimpleNamespace(async_entries=lambda _: [self.entry]))
        # Use platform's actual singleton key, not a competing provider.
        from custom_components.djconnect.persistence import PERSISTENCE_SERVICE_KEY
        self.hass.data["djconnect"][PERSISTENCE_SERVICE_KEY] = self.service

    async def settle(self, record):
        while record.tasks:
            await asyncio.gather(*tuple(record.tasks))

    async def test_real_pair_schedules_once_and_retirement_is_synchronous(self):
        self.configure_runtime()
        schedule_pair_registration(self.hass, self.runtime)
        record = self.runtime.surface_pair_registration
        await self.settle(record)
        self.assertEqual(record.phase, "recorded")
        first = record.acknowledgement
        schedule_pair_registration(self.hass, self.runtime)
        self.assertIs(self.runtime.surface_pair_registration, record)
        self.assertFalse(record.tasks)
        retire_runtime(self.runtime)
        self.assertTrue(record.retired)
        self.assertIsNone(record.acknowledgement)
        await self.settle(record)
        self.assertEqual((await self.rows())[0][2], "retired")
        schedule_pair_registration(self.hass, self.runtime)
        self.assertIs(self.runtime.surface_pair_registration, record)
        self.assertNotEqual(first, record.acknowledgement)

    async def test_cancel_during_thread_stage_has_no_late_ack(self):
        self.configure_runtime()
        entered, release = threading.Event(), threading.Event()
        original = self.provider._async_guarded_transaction
        async def held(operation, authorize):
            def stage(tx):
                result = operation(tx)
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("synthetic release timeout")
                return result
            return await original(stage, authorize)
        self.provider._async_guarded_transaction = held
        schedule_pair_registration(self.hass, self.runtime)
        record = self.runtime.surface_pair_registration
        await asyncio.to_thread(entered.wait, 5)
        self.assertTrue(entered.is_set())
        task = next(iter(record.tasks))
        task.cancel()
        release.set()
        await self.settle(record)
        self.assertIsNone(record.acknowledgement)
        self.assertNotEqual(record.phase, "recorded")
        self.assertEqual(await self.rows(), [])

    async def test_postcommit_retirement_suppresses_late_storage_ack(self):
        self.configure_runtime()
        original = self.provider._async_guarded_transaction
        async def retired_after_commit(operation, authorize):
            result = await original(operation, authorize)
            retire_runtime(self.runtime)
            return result
        self.provider._async_guarded_transaction = retired_after_commit
        schedule_pair_registration(self.hass, self.runtime)
        record = self.runtime.surface_pair_registration
        await self.settle(record)
        self.assertTrue(record.retired)
        self.assertIsNone(record.acknowledgement)
        self.assertEqual((await self.rows())[0][2], "retired")

    async def test_replaced_entry_mapping_before_first_await_never_records(self):
        self.configure_runtime()
        schedule_pair_registration(self.hass, self.runtime)
        record = self.runtime.surface_pair_registration
        self.entry.data = dict(self.entry.data)
        await self.settle(record)
        self.assertIsNone(record.acknowledgement)
        self.assertEqual(await self.rows(), [])

    async def test_old_retired_observer_stays_retired_after_local_data_ack(self):
        self.configure_runtime()
        self.runtime.surface_registration_retirement.retire()
        schedule_pair_registration(self.hass, self.runtime)
        record = self.runtime.surface_pair_registration
        await self.settle(record)
        self.assertEqual(record.phase, "recorded")
        self.assertTrue(self.runtime.surface_registration_retirement.retired)
        self.assertFalse(hasattr(record, "authority"))

    async def test_retire_during_thread_stage_cannot_publish_or_restore(self):
        self.configure_runtime()
        schedule_pair_registration(self.hass, self.runtime)
        record = self.runtime.surface_pair_registration
        retire_runtime(self.runtime)
        await self.settle(record)
        self.assertIsNone(record.acknowledgement)
        self.assertEqual((await self.rows())[0][2], "retired")
