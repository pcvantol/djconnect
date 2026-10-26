"""Committed Profile reader races use the actual storage implementation."""
import asyncio
from dataclasses import replace
import gc
import importlib
import unittest
import weakref

from tests.test_profile_storage import MemoryStore, ProfilePlatformStorage
from custom_components.djconnect import profile_observation as observation


class Hass:
    def __init__(self):
        self.data = {}


class CommittedObservationTests(unittest.IsolatedAsyncioTestCase):
    def fresh(self, store=None):
        hass = Hass()
        observation.bootstrap_from_integration_setup(hass)
        manager = ProfilePlatformStorage(hass, store=store or MemoryStore())
        observation.publish_manager(hass, hass.data['djconnect'], manager)
        return hass, manager

    async def test_cold_reader_does_not_create_or_load(self):
        hass = Hass()
        self.assertIsNone(observation.capture_committed(hass))
        self.assertEqual(hass.data, {})
        hass, manager = self.fresh()
        before = dict(hass.data)
        self.assertIsNone(observation.capture_committed(hass))
        self.assertFalse(manager._loaded)
        self.assertEqual(hass.data, before)
        await manager.async_load()
        self.assertTrue(observation.capture_committed(hass).current())

    async def test_existing_untracked_manager_is_not_bootstrap_evidence(self):
        hass = Hass()
        manager = ProfilePlatformStorage(hass, store=MemoryStore())
        hass.data['djconnect'] = {observation.STORE_KEY: manager}
        await manager.async_load()
        observation.bootstrap_from_integration_setup(hass)
        self.assertIsNone(observation.capture_committed(hass))

    async def test_queued_load_closes_even_when_committed_state_is_unchanged(self):
        entered, release = asyncio.Event(), asyncio.Event()
        class SlowStore(MemoryStore):
            async def async_load(self):
                entered.set()
                await release.wait()
                return None
        hass, manager = self.fresh(SlowStore())
        operation = asyncio.create_task(manager.async_load())
        await entered.wait()
        self.assertIsNone(observation.capture_committed(hass))
        release.set()
        await operation
        self.assertTrue(observation.capture_committed(hass).current())

    async def test_queued_writer_before_lock_is_visible(self):
        hass, manager = self.fresh()
        await manager.async_load()
        snapshot = observation.capture_committed(hass)
        await manager._write_lock.acquire()
        operation = asyncio.create_task(manager.async_save())
        await asyncio.sleep(0)
        owner = snapshot.owner
        self.assertEqual(owner.pending, 1)
        manager._write_lock.release()
        # The queued task has not run; the lock alone now incorrectly says idle.
        self.assertFalse(manager._write_lock.locked())
        self.assertIsNone(observation.capture_committed(hass))
        self.assertFalse(snapshot.current())
        await operation
        self.assertTrue(observation.capture_committed(hass).current())

    async def test_household_staging_and_A_A_and_A_B_A_retire_original(self):
        hass, manager = self.fresh()
        await manager.async_load()
        original = observation.capture_committed(hass)
        manager._household = manager._household
        self.assertFalse(original.current())
        original = observation.capture_committed(hass)
        before = manager._household
        manager._household = replace(before, display_name='staged')
        self.assertIsNone(observation.capture_committed(hass))
        manager._household = before
        self.assertFalse(original.current())
        self.assertTrue(observation.capture_committed(hass).current())

    async def test_cancelled_queued_writer_latches_uncertainty(self):
        hass, manager = self.fresh()
        await manager.async_load()
        await manager._write_lock.acquire()
        operation = asyncio.create_task(manager.async_save())
        await asyncio.sleep(0)
        operation.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await operation
        manager._write_lock.release()
        await manager.async_load()
        self.assertIsNone(observation.capture_committed(hass))
        self.assertEqual(observation._owner(hass).pending, 0)

    async def test_failed_store_and_successful_later_load_do_not_clear_uncertainty(self):
        class FailedStore(MemoryStore):
            async def async_load(self):
                raise OSError('synthetic storage failure')
        hass, manager = self.fresh(FailedStore())
        with self.assertRaises(OSError):
            await manager.async_load()
        manager._store = MemoryStore()
        await manager.async_load()
        self.assertIsNone(observation.capture_committed(hass))

    async def test_double_cancel_cannot_advertise_idle_while_compensation_is_still_writing(self):
        first_started, first_release = asyncio.Event(), asyncio.Event()
        compensation_started, compensation_release, compensation_done = (
            asyncio.Event(), asyncio.Event(), asyncio.Event())
        class ControlledStore(MemoryStore):
            calls = 0
            async def async_save(self, data):
                self.calls += 1
                if self.calls == 1:
                    first_started.set()
                    await first_release.wait()
                else:
                    compensation_started.set()
                    await compensation_release.wait()
                self.data = data
                if self.calls == 2:
                    compensation_done.set()
        store = ControlledStore()
        hass, manager = self.fresh(store)
        await manager.async_load()
        before = manager._committed_household
        task = asyncio.create_task(manager.async_commit_onboarding(
            before, replace(before, display_name='Synthetic draft')))
        await first_started.wait()
        task.cancel()
        await asyncio.sleep(0)
        first_release.set()
        await compensation_started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        owner = observation._owner(hass)
        self.assertEqual(owner.pending, 0)
        self.assertTrue(owner.uncertain)
        self.assertFalse(manager._write_lock.locked())
        self.assertIs(manager._household, before)
        self.assertFalse(compensation_done.is_set())
        self.assertIsNone(observation.capture_committed(hass))
        compensation_release.set()
        await compensation_done.wait()
        await asyncio.sleep(0)
        self.assertIsNone(observation.capture_committed(hass))

    async def test_original_save_swallowed_cancel_behavior_is_preserved_but_read_remains_uncertain(self):
        entered, release = asyncio.Event(), asyncio.Event()
        class ControlledStore(MemoryStore):
            async def async_save(self, data):
                entered.set()
                await release.wait()
                await super().async_save(data)
        hass, manager = self.fresh(ControlledStore())
        await manager.async_load()
        task = asyncio.create_task(manager.async_save())
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        self.assertIs(await task, manager._committed_household)
        self.assertIsNone(observation.capture_committed(hass))

    async def test_manager_replacement_carries_old_pending_and_uncertainty(self):
        hass, manager = self.fresh()
        await manager.async_load()
        original = observation.capture_committed(hass)
        other = ProfilePlatformStorage(hass, store=MemoryStore())
        observation.publish_manager(hass, hass.data['djconnect'], other)
        await other.async_load()
        self.assertFalse(original.current())
        observation.publish_manager(hass, hass.data['djconnect'], manager)
        self.assertIsNone(observation.capture_committed(hass))

    async def test_store_A_B_A_is_not_new_safe_lifetime(self):
        hass, manager = self.fresh()
        await manager.async_load()
        original = observation.capture_committed(hass)
        before = manager._store
        manager._store = MemoryStore()
        manager._store = before
        self.assertFalse(original.current())
        self.assertIsNone(observation.capture_committed(hass))

    async def test_split_anchor_and_hot_reload_cannot_be_repaired_by_reader_or_setup(self):
        for lost in ('registry', 'witness', 'domain'):
            hass, manager = self.fresh()
            await manager.async_load()
            if lost == 'registry':
                del observation._owners[hass]
            elif lost == 'witness':
                del hass.data[observation._WITNESS]
            else:
                hass.data['djconnect'] = {observation.STORE_KEY: manager}
            self.assertIsNone(observation.capture_committed(hass))
            observation.bootstrap_from_integration_setup(hass)
            self.assertIsNone(observation.capture_committed(hass))
        hass, manager = self.fresh()
        await manager.async_load()
        importlib.reload(observation)
        self.assertIsNone(observation.capture_committed(hass))
        observation.bootstrap_from_integration_setup(hass)
        self.assertIsNone(observation.capture_committed(hass))

    async def test_staged_hassless_onboarding_is_never_observable(self):
        manager = ProfilePlatformStorage(store=MemoryStore())
        await manager.async_load()
        self.assertIsNone(manager._observation_owner)
        manager._household = manager._household

    async def test_registry_has_no_strong_path_back_to_hass(self):
        hass, manager = self.fresh()
        await manager.async_load()
        reference = weakref.ref(hass)
        del hass, manager
        gc.collect()
        self.assertIsNone(reference())
