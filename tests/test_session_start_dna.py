"""Profile-bound loaded Music DNA seeds; no provider/model or UI effects."""
import asyncio
from copy import deepcopy
from unittest import IsolatedAsyncioTestCase

from tests.test_music_dna import FakeStore, MusicDNAManager


class LoadedGenreSeedTests(IsolatedAsyncioTestCase):
    def manager(self, **row):
        store = FakeStore({"version": 1, "memories": {"profile:owner-a": {
            "enabled": True, "generation": 3,
            "favorite_genres": ["Neo Soul", "R&B", "indie rock"], **row}}})
        return MusicDNAManager(store=store), store

    def snapshot(self, manager, owner="owner-a"):
        reader = getattr(manager, "loaded_genre_seed_snapshot", None)
        self.assertTrue(callable(reader), "The Core Music DNA seed reader is missing")
        return reader(owner)

    async def test_unloaded_missing_disabled_or_other_profile_never_warms_or_falls_back(self):
        manager, store = self.manager()
        self.assertIsNone(self.snapshot(manager))
        self.assertFalse(manager._loaded)
        await manager.async_load()
        self.assertIsNone(self.snapshot(manager, "owner-b"))
        self.assertIsNone(store.saved)
        manager.data["memories"]["profile:owner-a"]["enabled"] = False
        self.assertIsNone(self.snapshot(manager))

    async def test_three_genres_are_read_from_owned_dna_without_writes(self):
        manager, store = self.manager()
        await manager.async_load()
        before = deepcopy(manager.data)
        snapshot = self.snapshot(manager)
        self.assertEqual(snapshot.genres, ("neo soul", "r&b", "indie rock"))
        self.assertTrue(snapshot.valid())
        self.assertEqual(manager.data, before)
        self.assertIsNone(store.saved)

    async def test_generation_preserving_genre_replacement_aba_retires_original(self):
        manager, _ = self.manager()
        await manager.async_load()
        snapshot = self.snapshot(manager)
        row = manager.data["memories"]["profile:owner-a"]
        original = list(row["favorite_genres"])
        row["favorite_genres"] = ["house", "jazz", "funk"]
        row["favorite_genres"] = original
        self.assertEqual(row["generation"], 3)
        self.assertFalse(snapshot.valid(), "Restored values must not renew an old DNA offer")

    async def test_fewer_three_or_query_injection_does_not_invent_a_third_genre(self):
        manager, _ = self.manager(favorite_genres=["jazz", "JAZZ", 'rock\" OR artist:other', "https://other"])
        await manager.async_load()
        self.assertIsNone(self.snapshot(manager))

    async def test_inferred_genres_are_owned_data_and_duplicates_are_not_extra_choices(self):
        manager, _ = self.manager(favorite_genres=["Jazz", "JAZZ"],
            listening_profile={"inferred_genres": ["jazz", "ambient", "neo soul"]})
        await manager.async_load()
        self.assertEqual(self.snapshot(manager).genres, ("jazz", "ambient", "neo soul"))

    async def test_failed_write_then_recovery_cannot_revive_old_seed_snapshot(self):
        manager, store = self.manager()
        await manager.async_load()
        original = self.snapshot(manager)
        saved = store.async_save
        async def fail(data):
            raise OSError("synthetic store failure")
        store.async_save = fail
        with self.assertRaises(OSError):
            await manager.async_save()
        self.assertIsNone(self.snapshot(manager))
        store.async_save = saved
        await manager.async_save()
        self.assertTrue(self.snapshot(manager).valid())
        self.assertFalse(original.valid())

    async def test_unrelated_metadata_save_does_not_refresh_or_invalidate_original_genres(self):
        manager, _ = self.manager()
        await manager.async_load()
        original = self.snapshot(manager)
        manager.data["memories"]["profile:owner-a"]["last_seen"] = "synthetic-change"
        await manager.async_save()
        self.assertTrue(original.valid())

    async def test_pending_unrelated_save_preserves_only_original_committed_seed_basis(self):
        manager, store = self.manager()
        await manager.async_load()
        original = self.snapshot(manager)
        before = original.genres
        entered, release = asyncio.Event(), asyncio.Event()
        save = store.async_save
        async def pending(data):
            entered.set()
            await release.wait()
            await save(data)
        store.async_save = pending
        manager.data['memories']['profile:owner-a']['last_seen'] = 'unrelated-metadata'
        task = asyncio.create_task(manager.async_save())
        await entered.wait()
        try:
            new_snapshot = self.snapshot(manager)
            during = original.valid()
        finally:
            release.set()
            await task
        self.assertIsNone(new_snapshot, 'Pending cache must never mint a new committed basis')
        self.assertTrue(during, 'Same already-committed original genres survive unrelated save')
        self.assertTrue(original.valid())
        self.assertEqual(original.genres, before)

    async def test_pending_relevant_change_or_failed_write_still_retires_original(self):
        for mode in ('genres', 'disabled', 'generation', 'failure'):
            with self.subTest(mode=mode):
                manager, store = self.manager()
                await manager.async_load()
                original = self.snapshot(manager)
                entered, release = asyncio.Event(), asyncio.Event()
                save = store.async_save
                async def pending(data):
                    entered.set()
                    await release.wait()
                    if mode == 'failure':
                        raise OSError('declared fixture failure')
                    await save(data)
                store.async_save = pending
                row = manager.data['memories']['profile:owner-a']
                if mode == 'genres':
                    row['favorite_genres'] = ['jazz', 'funk', 'house']
                elif mode == 'disabled':
                    row['enabled'] = False
                elif mode == 'generation':
                    row['generation'] += 1
                task = asyncio.create_task(manager.async_save())
                await entered.wait()
                try:
                    during = original.valid()
                    self.assertIsNone(self.snapshot(manager))
                finally:
                    release.set()
                    if mode == 'failure':
                        with self.assertRaises(OSError):
                            await task
                    else:
                        await task
                if mode != 'failure':
                    self.assertFalse(during)
                self.assertFalse(original.valid())


class OriginalDnaHTTPContractTests(IsolatedAsyncioTestCase):
    async def test_actual_cached_offer_keeps_original_committed_basis_and_lease(self):
        import hashlib
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        wire = json.loads((root / 'examples/client_contracts/for_you_original_dna_v1/actual-ha-wire.json').read_text())
        self.assertTrue(wire['source_before_after_equal'])
        self.assertEqual(len(wire['source_pins']), 308)
        for name, expected in {**wire['source_pins'], **wire['harness_pins']}.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected, name)
        receipt = wire['receipt']
        self.assertTrue(receipt['source_unchanged'])
        extension = receipt['extension']
        self.assertEqual(set(extension['cases'].values()), {'PASS'})
        examples = extension['dna_snapshot_examples']
        self.assertEqual({x['language'] for x in examples}, {'en', 'nl'})
        for example in examples:
            before, during = example['original_offer'], example['during_save']
            self.assertEqual(during['state'], 'available')
            self.assertTrue(during['actions_available'])
            self.assertEqual(before['offer_id'], during['offer_id'])
            self.assertEqual(before['result_set']['items'], during['result_set']['items'])
            self.assertLessEqual(during['expires_in'], before['expires_in'])
            self.assertTrue(example['original_deadlines_unchanged'])
            self.assertEqual(example['new_snapshots_on_poll'], 0)
            self.assertEqual(len(example['synthetic_effects']), 1)
            self.assertTrue(example['original_choice_response']['action_outcome']['readback_confirmed'])
        self.assertEqual(extension['real_provider_calls'], 0)
        self.assertEqual(extension['model_provider_calls'], 0)
        self.assertEqual(extension['native_installed_acceptance'], 'NOT_RUN')
