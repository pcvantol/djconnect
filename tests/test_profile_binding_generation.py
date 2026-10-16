"""Durable owner generations survive restart but never reassignment/import ABA."""

import asyncio
from copy import deepcopy
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

from tests.test_profile_storage import MemoryStore
from custom_components.djconnect.domain.storage import (
    ProfilePlatformStorage, ProfileStorageValidationError,
)
from custom_components.djconnect.domain.profile.models import ProfilePrivacyMode
from custom_components.djconnect.profile_export import async_export_household, async_import_household


class FaultStore(MemoryStore):
    def __init__(self, data=None):
        super().__init__(data)
        self.fail = False
        self.block = False
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.writes = 0

    async def async_save(self, data):
        self.writes += 1
        if self.fail:
            raise OSError('controlled store failure')
        if self.block:
            self.entered.set()
            await self.release.wait()
        await super().async_save(data)


class ProfileBindingGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = FaultStore()
        from custom_components.djconnect.persistence.service import PersistenceService
        from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider
        self.directory = tempfile.TemporaryDirectory()
        self.service = PersistenceService(Path(self.directory.name)/'binding.sqlite', SQLitePersistenceProvider())
        await self.service.async_initialize()
        hass = SimpleNamespace(data={'djconnect': {'persistence_service': self.service}})
        self.manager = ProfilePlatformStorage(hass=hass, store=self.store)
        await self.manager.async_create_profile('A', profile_id='a')
        await self.manager.async_create_profile('B', profile_id='b')
        await self.manager.async_upsert_device('owner-device','ios',linked_profile_id='a')

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    def generation(self):
        return self.manager.household.devices['owner-device'].binding_generation

    async def test_restart_keeps_generation_and_ordinary_metadata_does_not_rotate(self):
        original=self.generation()
        self.assertRegex(original,r'^[a-f0-9]{32}$')
        await self.manager.async_upsert_device('owner-device','ios',linked_profile_id='a',display_name='Renamed')
        self.assertEqual(self.generation(),original)
        reloaded=ProfilePlatformStorage(store=MemoryStore(self.store.data))
        restored=await reloaded.async_load()
        self.assertEqual(restored.devices['owner-device'].binding_generation,original)

    async def test_device_and_privacy_ABA_never_revive_original_generation(self):
        generations=[self.generation()]
        for profile in ('b','a'):
            await self.manager.async_upsert_device('owner-device','ios',linked_profile_id=profile)
            generations.append(self.generation())
        for mode in (ProfilePrivacyMode.PRIVATE,ProfilePrivacyMode.NORMAL):
            await self.manager.async_update_profile('a',privacy_mode=mode)
            generations.append(self.generation())
        self.assertEqual(len(set(generations)),5)
        await self.manager.async_update_profile('a',display_name='A renamed')
        self.assertEqual(self.generation(),generations[-1])

    async def test_failed_store_write_exposes_neither_new_binding_nor_new_epoch(self):
        original=self.manager.household
        authority=self.manager.authority_revision
        self.store.fail=True
        with self.assertRaises(OSError):
            await self.manager.async_upsert_device('owner-device','ios',linked_profile_id='b')
        self.assertEqual(self.manager.household,original)
        self.assertEqual(self.manager.authority_revision,authority)
        reloaded=await ProfilePlatformStorage(store=MemoryStore(self.store.data)).async_load()
        self.assertEqual(reloaded.devices['owner-device'].linked_profile_id,'a')

    async def test_pending_write_is_hidden_and_second_stale_write_cannot_overwrite(self):
        original=self.manager.household
        self.store.block=True
        first=asyncio.create_task(self.manager.async_upsert_device('owner-device','ios',linked_profile_id='b'))
        await self.store.entered.wait()
        self.assertEqual(self.manager.household,original)
        second=asyncio.create_task(self.manager.async_update_profile('a',display_name='stale name'))
        await asyncio.sleep(0)
        self.assertEqual(self.manager.household,original)
        self.store.release.set()
        await first
        with self.assertRaises(ProfileStorageValidationError):
            await second
        self.assertEqual(self.manager.household.devices['owner-device'].linked_profile_id,'b')
        self.assertEqual(self.manager.household.profiles['a'].display_name,'A')

    async def test_legacy_missing_epoch_is_durably_migrated_once_before_readiness(self):
        legacy=deepcopy(self.store.data)
        for device in legacy['household']['devices']:
            device.pop('binding_generation')
        store=FaultStore(legacy)
        manager=ProfilePlatformStorage(store=store)
        result=await manager.async_load()
        generation=result.devices['owner-device'].binding_generation
        self.assertEqual(store.writes,1)
        for _ in range(3):
            self.assertEqual((await manager.async_load()).devices['owner-device'].binding_generation,generation)
        self.assertEqual(store.writes,1)
        restarted=await ProfilePlatformStorage(store=MemoryStore(store.data)).async_load()
        self.assertEqual(restarted.devices['owner-device'].binding_generation,generation)

    async def test_export_omits_server_epoch_and_import_rotates_existing_binding(self):
        original=self.generation()
        envelope=await async_export_household(self.manager)
        self.assertNotIn('binding_generation',str(envelope))
        await async_import_household(self.manager,envelope,overwrite=True)
        self.assertNotEqual(self.generation(),original)
        self.assertEqual(self.manager.household.devices['owner-device'].linked_profile_id,'a')
