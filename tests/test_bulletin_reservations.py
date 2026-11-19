"""Actual SQLite commit/rollback/reopen and forward-only v12→v13 migration."""
import asyncio
import threading
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from tests import test_bulletin_builder as fixture_module
from custom_components.djconnect.bulletin_builder import BulletinBuilder, BuilderError
from custom_components.djconnect.bulletin_reservations import BulletinReservationStore
from custom_components.djconnect.persistence.schema import apply_migration


class BulletinSQLiteReservationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "reservations.sqlite"
        self.persistence = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.fixture = fixture_module.BulletinBuilderTests()
        await self.fixture.asyncSetUp()
        self.store = BulletinReservationStore(self.persistence)
        self.calls = []
        async def model(prompt, session, guard):
            self.assertEqual(len((await self.store.async_load())["reservations"]), 4)
            self.calls.append(prompt)
            if "Assess every" in prompt:
                return json.dumps({"supported": True, "independent_stories": True,
                    "language_ok": True, "style_ok": True})
            return json.dumps({"text": self.fixture.text,
                "story_ids": [i.fingerprint for i in self.fixture.items]})
        self.model = model
        self.builder = self.new_builder(self.store)
        await self.builder.initialize()

    def new_builder(self, store):
        return BulletinBuilder(store, self.model, wall=lambda: self.fixture.clock[0],
            monotonic=lambda: self.fixture.clock[1])

    async def prepare(self, builder=None):
        return await (builder or self.builder).prepare(self.fixture.items,
            session=self.fixture.session, guard=self.fixture.guard)

    async def asyncTearDown(self):
        await self.persistence.async_close()
        self.directory.cleanup()

    async def test_confirmed_sql_commit_precedes_each_model_call_and_restart_never_rebuilds(self):
        self.assertIsNotNone(await self.prepare())
        self.assertEqual(len(self.calls), 2)
        persisted = await self.store.async_load()
        self.assertNotIn(self.fixture.text, json.dumps(persisted))
        self.assertNotIn(self.fixture.session.session_id, json.dumps(persisted))
        await self.persistence.async_close()
        self.persistence = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.store = BulletinReservationStore(self.persistence)
        restart = self.new_builder(self.store)
        await restart.initialize()
        self.assertIsNone(await self.prepare(restart))
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(await self.store.async_load(), persisted)

    async def test_actual_sqlite_trigger_failure_rolls_back_and_no_model_runs(self):
        before = await self.store.async_load()
        await self.persistence.async_in_transaction(lambda tx: tx.execute(
            "CREATE TRIGGER synthetic_reservation_failure BEFORE INSERT ON djconnect_bulletin_attempts "
            "BEGIN SELECT RAISE(ABORT, 'synthetic reservation failure'); END"))
        with self.assertRaises(BuilderError):
            await self.prepare()
        self.assertTrue(self.builder._failed)
        self.assertEqual(self.calls, [])
        self.assertEqual(await self.store.async_load(), before)

    async def test_closed_provider_cannot_silently_accept_a_reservation(self):
        await self.persistence.async_close()
        with self.assertRaises(BuilderError):
            await self.prepare()
        self.assertEqual(self.calls, [])

    async def test_highwater_does_not_rewind_and_source_text_cannot_enter_hash_store(self):
        original = {"schema": 1, "clock": 1000, "reservations": {"a" * 64: 2000}}
        await self.store.async_save(original)
        await self.store.async_save({**original, "clock": 900})
        self.assertEqual((await self.store.async_load())["clock"], 1000)
        for malformed in ({**original, "text": self.fixture.text},
                {**original, "reservations": {"article-title": 2000}},
                {**original, "clock": True}):
            with self.assertRaises(BuilderError):
                await self.store.async_save(malformed)

    async def test_real_v12_upgrade_preserves_profile_session_and_original_migrations(self):
        path = Path(self.directory.name) / "v12.sqlite"
        provider = SQLitePersistenceProvider()
        await provider.async_open(str(path))
        for version in range(1, 13):
            await provider.async_run_transaction(lambda tx, v=version: apply_migration(tx, v))
        def seed(tx):
            tx.execute("INSERT INTO djconnect_profile_dj_settings VALUES (?,?,?,?,?)",
                ("synthetic-owner", '{"presence":"balanced"}', 7, "original", 3))
            tx.execute("INSERT INTO djconnect_persistent_sessions "
                "(session_id,owner_profile_id,lifecycle_status,created_at,updated_at) VALUES (?,?,?,?,?)",
                ("synthetic-session", "synthetic-owner", "ENDED", "original", "original"))
        await provider.async_run_transaction(seed)
        tables = ("djconnect_profile_dj_settings", "djconnect_persistent_sessions", "djconnect_schema_migrations")
        before = await provider.async_run_transaction(lambda tx: {
            table: tx.fetchall("SELECT * FROM " + table) for table in tables})
        await provider.async_close()
        upgraded = PersistenceService(path, SQLitePersistenceProvider())
        try:
            readiness = await upgraded.async_initialize()
            from custom_components.djconnect.persistence.schema import CURRENT_SCHEMA_VERSION
            self.assertEqual(readiness.schema_version, CURRENT_SCHEMA_VERSION)
            after = await upgraded.async_in_transaction(lambda tx: {
                table: tx.fetchall("SELECT * FROM " + table) for table in tables})
            for table in tables[:2]:
                self.assertEqual(before[table], after[table])
            self.assertEqual(before[tables[2]], after[tables[2]][:12])
            empty = await BulletinReservationStore(upgraded).async_load()
            self.assertEqual(empty, {"schema": 1, "clock": 0, "reservations": {}})
        finally:
            await upgraded.async_close()

    async def test_cancel_during_definitive_SQL_reservation_commit_never_starts_model(self):
        entered,release = threading.Event(),threading.Event()
        provider = self.persistence._provider
        original = provider._run_transaction
        def held(operation):
            def run(tx):
                value = operation(tx)
                count = tx.fetchone("SELECT COUNT(*) FROM djconnect_bulletin_attempts")[0]
                if count==4 and not entered.is_set():
                    entered.set()
                    if not release.wait(3):
                        raise RuntimeError("synthetic-reservation-hold-timeout")
                return value
            return original(run)
        provider._run_transaction = held
        task = asyncio.create_task(self.prepare())
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait,2))
            task.cancel()
            release.set()
            cancelled = False
            try:
                await task
            except asyncio.CancelledError:
                cancelled = True
            self.assertEqual(len(self.calls),0)
            self.assertTrue(cancelled)
            self.assertEqual(len((await self.store.async_load())["reservations"]),4)
            self.assertIsNone(self.builder._candidate)
            self.assertIsNone(await self.prepare())  # Same original stories stay reserved.
            self.assertFalse(self.calls)
        finally:
            release.set()
            provider._run_transaction = original
            if not task.done():
                task.cancel()
                await asyncio.gather(task,return_exceptions=True)
