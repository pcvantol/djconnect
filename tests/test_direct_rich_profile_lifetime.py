"""Actual committed Profile lifetime; no fabricated positive owner/clock port."""
import asyncio
from dataclasses import replace
import unittest

from tests.test_profile_storage import MemoryStore, ProfilePlatformStorage
from tests.test_ask_dj_profile_committed_observation import Hass
from custom_components.djconnect import profile_observation as observation


class RichProfileLifetimeTests(unittest.IsolatedAsyncioTestCase):
    async def fresh(self, store=None):
        hass = Hass()
        observation.bootstrap_from_integration_setup(hass)
        manager = ProfilePlatformStorage(hass, store=store or MemoryStore())
        observation.publish_manager(hass, hass.data['djconnect'], manager)
        await manager.async_load()
        lifetime = observation.capture_committed_lifetime(hass)
        self.assertIsNotNone(lifetime)
        return hass, manager, lifetime

    async def test_cold_and_untracked_capture_never_creates_or_loads(self):
        hass = Hass()
        self.assertIsNone(observation.capture_committed_lifetime(hass))
        self.assertEqual(hass.data, {})
        observation.bootstrap_from_integration_setup(hass)
        manager = ProfilePlatformStorage(hass, store=MemoryStore())
        observation.publish_manager(hass, hass.data['djconnect'], manager)
        self.assertIsNone(observation.capture_committed_lifetime(hass))
        self.assertFalse(manager._loaded)

    async def test_cosmetic_commit_uses_new_exact_snapshot_without_pinning_household(self):
        _hass, manager, lifetime = await self.fresh()
        old = lifetime.attempt()
        await manager.async_save(replace(manager.household, display_name='Synthetic renamed'))
        current = lifetime.attempt()
        self.assertFalse(old.current())
        self.assertTrue(current.current())
        self.assertIsNot(current.household, old.household)
        self.assertEqual(current.household.display_name, 'Synthetic renamed')
        self.assertEqual(set(lifetime.__dict__), {'hass', 'owner', 'manager', 'store', 'retired'})

    async def test_queued_known_write_suspends_before_and_after_lock_release(self):
        _hass, manager, lifetime = await self.fresh()
        await manager._write_lock.acquire()
        operation = asyncio.create_task(manager.async_save())
        await asyncio.sleep(0)  # Reach actual queued writer, before lock admission.
        self.assertIsNone(lifetime.attempt())
        manager._write_lock.release()
        self.assertFalse(manager._write_lock.locked())
        self.assertIsNone(lifetime.attempt())  # Actual owner.pending still holds.
        await operation
        self.assertTrue(lifetime.attempt().current())
        self.assertFalse(lifetime.retired)

    async def test_cancelled_queued_write_irreversibly_retires_and_scrubs(self):
        hass, manager, lifetime = await self.fresh()
        owner = lifetime.owner
        await manager._write_lock.acquire()
        operation = asyncio.create_task(manager.async_save())
        await asyncio.sleep(0)
        operation.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await operation
        manager._write_lock.release()
        self.assertTrue(lifetime.retired)  # Actual transition hook, before another read.
        self.assertNotIn(lifetime, owner.lifetimes)
        self.assertTrue(all(getattr(lifetime, k) is None for k in ('hass', 'owner', 'manager', 'store')))
        await manager.async_load()
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()
        self.assertIsNone(observation.capture_committed_lifetime(hass))

    async def test_actual_store_replacement_and_manager_replacement_retire_synchronously(self):
        _hass, manager, lifetime = await self.fresh()
        manager._store = MemoryStore()
        self.assertTrue(lifetime.retired)
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()
        hass, _manager, lifetime = await self.fresh()
        replacement = ProfilePlatformStorage(hass, store=MemoryStore())
        self.assertTrue(lifetime.retired)
        observation.publish_manager(hass, hass.data['djconnect'], replacement)
        await replacement.async_load()
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()
        self.assertIsNone(observation.capture_committed_lifetime(hass))

    async def test_actual_entry_invalidation_and_split_anchor_are_terminal(self):
        hass, _manager, lifetime = await self.fresh()
        observation.invalidate(hass)
        self.assertTrue(lifetime.retired)
        hass, _manager, lifetime = await self.fresh()
        domain = hass.data['djconnect']
        hass.data['djconnect'] = dict(domain)
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()
        hass.data['djconnect'] = domain
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()

    async def test_uncommitted_staging_without_known_writer_does_not_become_transient(self):
        _hass, manager, lifetime = await self.fresh()
        original = manager._committed_household
        manager._household = replace(original, display_name='Uncommitted synthetic')
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()
        manager._household = original
        with self.assertRaises(observation.ProfileObservationUnavailable):
            lifetime.attempt()
