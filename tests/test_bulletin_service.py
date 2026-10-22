"""Single cancellable HA-owner service, real Runtime plus synthetic HTTP/model."""
import asyncio
import unittest

from tests import test_bulletin_runtime as runtime_fixture
from tests.test_bulletin_builder import Store
from tests.test_bulletin_intake import HTTP, Response, rss
from custom_components.djconnect.bulletin_intake import SOURCES
from custom_components.djconnect.bulletin_service import BulletinService


class BulletinServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        runtime_fixture.BulletinRuntimeTests.setUpClass()
        self.fixture = runtime_fixture.BulletinRuntimeTests()
        await self.fixture.asyncSetUp()
        self.fixture.calls.clear()
        self.http = HTTP()
        self.http.closed = 0
        async def close():
            self.http.closed += 1
        self.http.close = close
        from datetime import datetime, timezone
        from email.utils import format_datetime
        self.http.reply = lambda source: Response(200, rss(source,
            date=format_datetime(datetime.fromtimestamp(self.fixture.items[0].published_at, timezone.utc)),
            title=self.fixture.items[0 if source == SOURCES[0] else 1].title,
            suffix="one" if source == SOURCES[0] else "two")) if source in SOURCES[:2] else Response(503)
        self.unsubscribed = 0
        self.callbacks = []
        self.tasks = []
        def subscribe(callback):
            self.callbacks.append(callback)
            def unsubscribe():
                self.unsubscribed += 1
            return unsubscribe
        def create(coro):
            task = asyncio.create_task(coro)
            self.tasks.append(task)
            return task
        self.store = Store()
        self.service = BulletinService(self.fixture.manager, self.store, self.http,
            create_task=create, subscribe=subscribe)

    async def asyncTearDown(self):
        await self.service.close()
        await self.fixture.asyncTearDown()
        runtime_fixture.BulletinRuntimeTests.tearDownClass()

    async def start_ready(self):
        await self.service.start()
        await self.service._task
        self.assertIsNotNone(self.service.ready(self.fixture.work.owner, self.fixture.sid))

    async def test_single_poll_owner_prepares_without_publishing_or_duplicate_background_work(self):
        await self.service.start()
        self.service.tick()
        self.service.tick()
        await self.service._task
        self.assertEqual(len(self.tasks), 1)
        self.assertEqual(len(self.http.calls), 5)
        self.assertEqual(len(self.fixture.calls), 2)
        self.assertEqual(self.fixture.active.presence_ledger.total_published, 0)
        self.assertFalse(self.fixture.active.broadcast.state.dj_moments)
        self.assertIsNotNone(self.service.ready(self.fixture.work.owner, self.fixture.sid))
        self.assertIsNone(self.service.ready("other-owner", self.fixture.sid))
        self.assertIsNone(self.service.ready(self.fixture.work.owner, "other-session"))
        await self.service.poll()
        self.assertEqual(len(self.http.calls), 5)
        self.assertEqual(len(self.fixture.calls), 2)

    async def test_existing_planner_consumes_ready_service_once_and_stop_withdraws_further_access(self):
        await self.start_ready()
        self.assertIsNotNone(await self.fixture.publish())
        self.assertEqual(self.fixture.active.presence_ledger.total_published, 1)
        self.assertIsNone(await self.fixture.publish())
        await self.service.close()
        self.assertEqual(self.unsubscribed, 1)
        self.assertIsNone(self.fixture.manager._bulletin_service)
        self.assertIsNone(self.service.ready(self.fixture.work.owner, self.fixture.sid))
        self.service.tick()
        self.assertEqual(len(self.tasks), 1)

    async def test_close_cancels_inflight_generation_without_late_candidate_or_released_reservations(self):
        entered = asyncio.Event()
        async def wait():
            entered.set()
            await asyncio.Event().wait()
        self.fixture.hook = wait
        await self.service.start()
        await entered.wait()
        self.assertEqual(len(self.store.data["reservations"]), 4)
        await self.service.close()
        self.assertTrue(self.tasks[0].cancelled())
        self.assertIsNone(self.service.builder._candidate)
        self.assertFalse(self.fixture.active.broadcast.state.dj_moments)
        self.assertEqual(self.http.closed, 1)

    async def test_original_owner_loss_during_generation_is_silent_without_model_retry(self):
        async def withdraw():
            self.fixture.authorized = False
        self.fixture.hook = withdraw
        await self.service.start()
        await self.service._task
        self.assertIsNone(self.service.ready(self.fixture.work.owner, self.fixture.sid))
        self.assertEqual(len(self.fixture.calls), 1)
        self.fixture.authorized, self.fixture.hook = True, None
        await self.service.poll()
        self.assertEqual(len(self.fixture.calls), 1)
        self.assertFalse(self.fixture.active.broadcast.state.dj_moments)

    async def test_technical_collection_failure_drops_original_candidate_not_rebinds_it_to_fresh_authority(self):
        await self.start_ready()
        original = self.service.collector.collect
        async def unavailable(**kwargs):
            raise ValueError("synthetic-clock-failure")
        self.service.collector.collect = unavailable
        await self.service.poll()
        self.assertIsNone(self.service.builder._candidate)
        self.assertIsNone(self.service._work)
        self.fixture.revision[0] += 1
        self.service.collector.collect = original
        await self.service.poll()
        self.assertIsNone(self.service.ready(self.fixture.work.owner, self.fixture.sid))
        self.assertEqual(len(self.fixture.calls), 2)
