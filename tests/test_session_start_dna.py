"""Profile-bound loaded Music DNA seeds; no provider/model or UI effects."""
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
