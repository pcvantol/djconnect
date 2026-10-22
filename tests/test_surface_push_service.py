"""Real service task ownership and Runtime teardown, synthetic purpose/relay."""
import asyncio
import hashlib
from types import SimpleNamespace
import unittest

from tests import test_bulletin_runtime as runtime_fixture
from tests import test_surface_push_registry as registry_fixture
from custom_components.djconnect.surface_push_service import SurfacePushService
from custom_components.djconnect.surface_push_contract import SurfacePushError


class SurfaceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        runtime_fixture.BulletinRuntimeTests.setUpClass()
        self.runtime = runtime_fixture.BulletinRuntimeTests()
        await self.runtime.asyncSetUp()
        self.fixture = registry_fixture.SurfaceRegistryTests()
        await self.fixture.asyncSetUp()
        self.tasks = []
        def create(coro, name):
            task = asyncio.create_task(coro,name=name)
            self.tasks.append(task)
            return task
        self.hass = SimpleNamespace(async_create_background_task=create)
        self.service = SurfacePushService(self.hass,self.runtime.manager,self.runtime.persistence)
        self.service.registry = self.fixture.registry

    async def asyncTearDown(self):
        await self.service.close()
        await self.runtime.asyncTearDown()
        runtime_fixture.BulletinRuntimeTests.tearDownClass()

    async def test_no_config_or_client_purpose_adoption_and_no_eager_external_work(self):
        self.assertFalse(self.service._purposes)
        self.assertFalse(self.tasks)
        self.assertFalse(self.fixture.calls)

    async def test_close_cancels_owned_operation_without_late_read_grant(self):
        entered = asyncio.Event()
        async def hook(action, request):
            entered.set()
            await asyncio.Event().wait()
        self.fixture.hook = hook
        outer = asyncio.create_task(self.service.run(self.fixture.registry.register(
            self.fixture.intent(),self.fixture.admission)))
        await entered.wait()
        row = next(iter(self.fixture.registry._entries.values()))
        await self.service.close()
        with self.assertRaisesRegex(SurfacePushError,"surface_unavailable"):
            await outer
        self.assertFalse(self.service._tasks)
        self.assertIsNone(self.runtime.manager._surface_push_service)
        self.assertEqual(row.read_secret,"")
        self.assertNotEqual(row.phase,"registered")
        self.assertEqual(len(self.fixture.calls),1)

    async def test_caller_cancellation_does_not_leave_unowned_operation_running(self):
        entered = asyncio.Event()
        async def work():
            entered.set()
            await asyncio.Event().wait()
        outer = asyncio.create_task(self.service.run(work()))
        await entered.wait()
        outer.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await outer
        self.assertFalse(self.service._tasks)
        self.assertTrue(self.tasks[0].cancelled())

    async def test_session_end_withdraws_before_real_persistence_failure_and_never_rearms(self):
        owner = self.runtime.active.owner_profile_id
        key = (hashlib.sha256(owner.encode()).hexdigest(),"2"*64,"3"*64,self.runtime.sid)
        self.service._purposes[key] = self.fixture.purpose
        entered = asyncio.Event()
        async def failure(*args,**kwargs):
            entered.set()
            self.assertFalse(self.fixture.purpose.is_current())
            raise OSError("synthetic-end-storage-failure")
        self.runtime.manager._persistent_sessions.async_transition = failure
        with self.assertRaisesRegex(OSError,"synthetic-end-storage-failure"):
            await self.runtime.manager.async_end(owner_profile_id=owner,session_id=self.runtime.sid)
        self.assertTrue(entered.is_set())
        self.assertIsNotNone(self.runtime.manager.current_active(owner))
        self.assertFalse(self.service._purposes)
        self.assertFalse(self.fixture.purpose.is_current())

    async def test_entry_unload_latches_even_if_other_runtime_settings_remain_current(self):
        result = await self.fixture.registry.register(self.fixture.intent(),self.fixture.admission)
        self.service._purposes[("1"*64,"2"*64,"3"*64,"session-synthetic")] = self.fixture.purpose
        self.service.invalidate_entry("synthetic-entry")
        self.assertFalse(self.service._purposes)
        self.assertFalse(self.fixture.purpose.is_current())
        self.assertEqual(next(iter(self.fixture.registry._entries.values())).read_secret,"")
        with self.assertRaises(SurfacePushError):
            self.fixture.registry.read(result["registration"]["registration_id"],result["background_read"]["credential"])
