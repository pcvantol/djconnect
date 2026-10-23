"""Real SQLite commit/rollback/CAS/restart/cancel before synthetic relay effects."""
import asyncio
import json
from pathlib import Path
import tempfile
import threading
import unittest

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from tests import test_surface_push_registry as fixture_module
from custom_components.djconnect.surface_push_journal import SurfaceOperationStore
from custom_components.djconnect.transport_operations import OperationError, OperationJournal


class SurfaceSQLiteJournalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.persistence = PersistenceService(Path(self.directory.name)/"surface.sqlite", SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.fixture = fixture_module.SurfaceRegistryTests()
        await self.fixture.asyncSetUp()
        self.store = SurfaceOperationStore(self.persistence)
        self.journal = self.make_journal(self.store)
        self.fixture.journal = self.journal
        self.fixture.registry.journal = self.journal
        original = self.fixture.registry.relay
        async def relay(action, request, admission):
            row = await self.row()
            records = json.loads(row[2])["records"]
            self.assertTrue(any(r["phase"]=="sent_unknown" for r in records.values()))
            return await original(action,request,admission)
        self.fixture.registry.relay = relay

    def make_journal(self, store):
        return OperationJournal(store,wall_ms=lambda:self.fixture.clock[0],
            monotonic=lambda:self.fixture.clock[1])

    async def row(self):
        return await self.persistence.async_in_transaction(lambda tx:tx.fetchone(
            "SELECT revision,high_water_ms,body FROM djconnect_surface_journal WHERE singleton=1"))

    async def asyncTearDown(self):
        await self.fixture.registry.close()
        await self.persistence.async_close()
        self.directory.cleanup()

    async def test_confirmed_SQL_precedes_relay_and_contains_no_token_or_private_body(self):
        result = await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        self.assertTrue(result["success"])
        self.assertEqual(len(self.fixture.calls),1)
        row = await self.row()
        encoded = row[2]
        for forbidden in (self.fixture.payload["apns_token"], "djcs_", "djcsurface_", "session-synthetic"):
            self.assertNotIn(forbidden,encoded)
        self.assertEqual(next(iter(json.loads(encoded)["records"].values()))["phase"],"confirmed")

    async def test_widget_event_commit_precedes_single_effect_and_survives_unknown_replay(self):
        registered = await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        coordinate = {k:registered["registration"][k] for k in ("registration_id","generation","revision")}
        from tests.test_transport_operation_journal import identifier
        async def event(action,request):
            records = json.loads((await self.row())[2])["records"]
            original = next(r for r in records.values() if r["operation"]=="push/surface/event")
            self.assertEqual(original["phase"],"sent_unknown")
            return {"success":False}
        self.fixture.hook = event
        operation_id = identifier(self.fixture.clock[0],5)
        result = await self.fixture.registry.signal_widget(self.fixture.admission,coordinate,operation_id=operation_id)
        replay = await self.fixture.registry.signal_widget(self.fixture.admission,coordinate,operation_id=operation_id)
        self.assertFalse(result["success"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(self.fixture.calls),2)
        records = json.loads((await self.row())[2])["records"]
        self.assertEqual(next(r for r in records.values() if r["operation"]=="push/surface/event")["phase"],"unknown")

    async def test_real_SQL_abort_quarantines_before_any_remote_attempt(self):
        await self.persistence.async_in_transaction(lambda tx:tx.execute(
            "CREATE TRIGGER reject_surface BEFORE UPDATE ON djconnect_surface_journal "
            "BEGIN SELECT RAISE(ABORT,'synthetic'); END"))
        with self.assertRaises(Exception):
            await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        self.assertTrue(self.journal._failed)
        self.assertFalse(self.fixture.calls)
        self.assertEqual(json.loads((await self.row())[2])["records"],{})

    async def test_restart_never_restores_RAM_credential_or_replays_a_remote_mutation(self):
        result = await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        before = await self.row()
        fresh = self.make_journal(SurfaceOperationStore(self.persistence))
        await fresh._load()
        original = next(iter(fresh._state["records"].values()))
        self.assertEqual(original["expires_ms"],result["operation"]["expires_at_ms"])
        with self.assertRaisesRegex(OperationError,"operation_conflict"):
            await fresh.reserve(owner=original["owner"],device=original["device"],binding=original["binding"],
                identifier=original["operation_id"],epoch=fresh.epoch,operation=original["operation"],digest=original["digest"])
        self.assertEqual(await self.row(),before)
        self.assertEqual(len(self.fixture.calls),1)

    async def test_second_stale_journal_owner_CAS_cannot_overwrite_committed_receipts(self):
        stale = self.make_journal(SurfaceOperationStore(self.persistence))
        await stale._load()
        await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        before = await self.row()
        with self.assertRaisesRegex(OperationError,"operation_unavailable"):
            await stale.reserve(owner="1"*64,device="2"*64,binding="3"*64,
                identifier=self.fixture.intent(2).metadata()["operation_id"],epoch=stale.epoch,
                operation="push/surface/register",digest="d"*64)
        self.assertEqual(await self.row(),before)
        self.assertTrue(stale._failed)
        self.assertEqual(len(self.fixture.calls),1)

    async def test_cancel_during_definitive_real_SQL_commit_never_starts_relay(self):
        entered,release = threading.Event(),threading.Event()
        provider = self.persistence._provider
        original = provider._run_transaction
        def held(operation):
            def run(tx):
                value = operation(tx)
                row = tx.fetchone("SELECT revision FROM djconnect_surface_journal WHERE singleton=1")
                if row[0] == 1 and not entered.is_set():
                    entered.set()
                    if not release.wait(3):
                        raise RuntimeError("synthetic hold timed out")
                return value
            return original(run)
        provider._run_transaction = held
        task = asyncio.create_task(self.fixture.registry.register(self.fixture.intent(),self.fixture.admission))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait,2))
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertFalse(self.fixture.calls)
            self.assertFalse(self.journal._active)
        finally:
            release.set()
            provider._run_transaction = original
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)

    async def test_closed_provider_never_creates_storage_or_starts_relay(self):
        await self.persistence.async_close()
        with self.assertRaises(Exception):
            await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        self.assertFalse(self.fixture.calls)
