"""Owning artwork identity, lifecycle and serialized Store failure controls."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import time
import types
import unittest
from unittest.mock import patch

from tests.test_music_dna import FakeStore, MusicDNAManager, runtime_for
from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()
from custom_components.djconnect import discovery_artwork as art  # noqa: E402
from custom_components.djconnect.music_dna import _compact_track  # noqa: E402
from custom_components.djconnect.spotify_backend import (  # noqa: E402
    _normalize_profile_track,
    _normalize_profile_artist,
    _normalize_album_item,
)

TRACK_URI = "spotify:track:" + "A" * 22
ALBUM_URI = "spotify:album:" + "B" * 22
ARTIST_URI = "spotify:artist:" + "C" * 22
URL = "https://i.scdn.co/image/" + "a" * 40


def provider_track():
    return {
        "id": "A" * 22,
        "uri": TRACK_URI,
        "name": "Track",
        "album": {"id": "B" * 22, "uri": ALBUM_URI, "name": "Album", "images": [{"url": URL}]},
        "artists": [{"name": "Artist"}],
    }


def profile():
    return {
        "top_tracks_by_range": {"short_term": [_normalize_profile_track(provider_track())]},
        "top_artists_by_range": {
            "short_term": [
                _normalize_profile_artist(
                    {"id": "C" * 22, "uri": ARTIST_URI, "name": "Artist", "images": [{"url": URL}]}
                )
            ]
        },
    }


class ArtworkReferenceTest(unittest.TestCase):
    def test_exact_provider_route_and_identity(self):
        for url in [
            URL.replace("https:", "http:"),
            URL + "?token=secret",
            URL + "#fragment",
            URL.replace("i.scdn.co", "i.scdn.co.evil"),
            URL.replace("i.scdn.co", "user@i.scdn.co"),
            URL.replace("i.scdn.co", "i.scdn.co:443"),
            URL.replace("/image/", "/image/%2f"),
            "https://127.0.0.1/image/" + "a" * 40,
            URL + " ",
            123,
        ]:
            with self.subTest(url=url):
                self.assertFalse(art.provider_asset_id(url))
        self.assertEqual(art.provider_asset_id(URL), "a" * 40)
        track = _normalize_profile_track(provider_track())
        self.assertTrue(art.compact_artwork(track))
        self.assertNotIn("artwork", _compact_track(track))
        self.assertEqual(_compact_track(track, retain_artwork=True)["artwork"], track["artwork"])
        for mutate in ("album_id", "album_uri", "track_id"):
            raw = provider_track()
            if mutate == "album_id":
                raw["album"]["id"] = "D" * 22
            if mutate == "album_uri":
                raw["album"]["uri"] = "spotify:album:" + "D" * 22
            if mutate == "track_id":
                raw["id"] = "D" * 22
            self.assertFalse(_normalize_profile_track(raw).get("artwork"))
        self.assertTrue(_normalize_album_item(provider_track()["album"])["artwork"])
        self.assertFalse(art.capture_artwork(URL, ARTIST_URI, ALBUM_URI))
        self.assertFalse(art.capture_artwork(URL, ALBUM_URI, "spotify:album:" + "D" * 22))

    def test_invalid_reference_and_expiry_never_renew(self):
        now = time.time()
        item = {
            "uri": TRACK_URI,
            "album_uri": ALBUM_URI,
            "artwork": art.capture_artwork(URL, TRACK_URI, ALBUM_URI, now=now - 100),
        }
        valid = art.compact_artwork(item, now=now)
        self.assertEqual(valid["captured_at"], now - 100)
        self.assertEqual(valid, art.compact_artwork({**item, "artwork": valid}, now=now + 100))
        for field, value in [
            ("version", True),
            ("version", 2),
            ("provider", "other"),
            ("asset_id", "../evil"),
            ("subject_uri", ARTIST_URI),
            ("media_uri", ARTIST_URI),
            ("captured_at", True),
            ("captured_at", float("nan")),
            ("captured_at", now + 10),
            ("expires_at", now - 1),
            ("expires_at", now + 40000),
        ]:
            broken = deepcopy(item)
            broken["artwork"][field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(art.compact_artwork(broken, now=now))
        self.assertFalse(art.compact_artwork({**item, "id": "D" * 22}, now=now))
        self.assertFalse(art.compact_artwork({**item, "album_uri": ARTIST_URI}, now=now))
        self.assertFalse(art.compact_artwork(item, now=now + art.ARTWORK_TTL_SECONDS))
        self.assertFalse(art.capture_artwork(URL, "spotify:track:unknown", ALBUM_URI))

    def test_import_export_strip_recursive_art_and_credentials_urls(self):
        source = {
            "image_url": URL,
            "nested": [{"artwork": {"asset_id": "a" * 40}, "title": "Safe"}],
        }
        self.assertEqual(art.strip_artwork(source), {"nested": [{"title": "Safe"}]})
        self.assertIn("image_url", source)
        aliases = {"imageURL": URL, "albumArtURL": URL, "imageAttribution": {}, "Images": []}
        self.assertEqual(art.strip_artwork(aliases), {})


class ArtworkLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = FakeStore()
        self.manager = MusicDNAManager(store=self.store)
        self.runtime = runtime_for()
        self.runtime.memory = self.manager
        self.runtime.profile_context_profile_id = "one"
        self.runtime.profile_context_backend_id = "spotify_direct"
        self.runtime.profile_context_music_account_id = "account-one"
        self.runtime.device_token = "ordinary-device-token"
        self.payload = {"music_dna_key": "profile:one"}
        await self.manager.async_set_enabled(self.runtime, True, self.payload)
        self.hass = types.SimpleNamespace(data={"djconnect": {}})

    async def test_store_reload_partial_recent_and_historical_snapshots(self):
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        await self.manager.async_update_listening_profile(
            self.runtime, profile(), self.payload, refresh_guard=guard
        )
        stored = deepcopy(self.store.data)
        self.assertNotIn(
            "artwork", repr(stored["memories"]["profile:one"]["listening_profile_snapshots"])
        )
        self.assertNotIn(URL, repr(stored))
        manager = MusicDNAManager(store=FakeStore(stored))
        await manager.async_load()
        self.runtime.memory = manager
        before = (await manager.async_listening_profile(self.runtime, self.payload))[
            "top_tracks_by_range"
        ]
        await manager.async_update_listening_profile(
            self.runtime,
            {"recent_tracks": [_normalize_profile_track(provider_track())]},
            self.payload,
        )
        after = await manager.async_listening_profile(self.runtime, self.payload)
        self.assertEqual(before, after["top_tracks_by_range"])
        self.assertEqual(
            after["top_tracks_by_range"]["short_term"][0]["artwork"]["owner"],
            art.artwork_owner(self.runtime),
        )

    async def test_clear_off_on_allclear_and_owner_switch_reject_late_profile(self):
        for change in ("clear", "off_on", "allclear", "account", "profile", "pairing", "manager"):
            with self.subTest(change=change):
                await self.asyncSetUp()
                guard = await art.capture_refresh_guard(self.runtime, self.payload)
                if change == "clear":
                    await self.manager.async_clear("profile:one")
                elif change == "off_on":
                    await self.manager.async_set_enabled(self.runtime, False, self.payload)
                    await self.manager.async_set_enabled(self.runtime, True, self.payload)
                elif change == "allclear":
                    await self.manager.async_clear()
                    await self.manager.async_set_enabled(self.runtime, True, self.payload)
                elif change == "account":
                    self.runtime.profile_context_music_account_id = "account-two"
                elif change == "profile":
                    self.runtime.profile_context_profile_id = "two"
                elif change == "pairing":
                    self.runtime.device_token = "rotated-device-token"
                else:
                    self.runtime.memory = MusicDNAManager(store=FakeStore())
                self.assertFalse(guard.valid())
                await self.manager.async_update_listening_profile(
                    self.runtime, profile(), self.payload, refresh_guard=guard
                )
                self.assertNotIn("listening_profile", self.manager.data["memories"]["profile:one"])

    async def test_scoped_headerless_grant_expiry_revocation_and_bound(self):
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        ref = _normalize_profile_track(provider_track())["artwork"]
        ref["owner"] = art.artwork_owner(self.runtime)
        url, expiry = art.register_discovery_image(self.hass, guard, ref)
        self.assertTrue(url.startswith("/api/djconnect/v1/image_proxy/disc-"))
        self.assertLessEqual(expiry, ref["expires_at"])
        wrong = {**ref, "owner": {**ref["owner"], "account_id": "other"}}
        self.assertEqual(art.register_discovery_image(self.hass, guard, wrong), ("", 0))
        with patch.object(art, "ARTWORK_MAX_GRANTS", 2):
            for _ in range(5):
                art.register_discovery_image(self.hass, guard, ref)
            self.assertEqual(len(self.hass.data["djconnect"]["discovery_image_grants"]), 2)
        await self.manager.async_clear("profile:one")
        self.assertEqual(art.register_discovery_image(self.hass, guard, ref), ("", 0))

    async def test_save_failure_does_not_publish_ref_and_load_failure_fails_closed(self):
        async def fail(_):
            raise OSError("bounded fixture write failure")

        self.store.async_save = fail
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        with self.assertRaises(OSError):
            await self.manager.async_update_listening_profile(
                self.runtime, profile(), self.payload, refresh_guard=guard
            )
        self.assertNotIn("listening_profile", self.manager.data["memories"]["profile:one"])
        bad = MusicDNAManager(store=self.store)

        async def fail_load():
            raise OSError("bounded fixture read failure")

        self.store.async_load = fail_load
        with self.assertRaises(OSError):
            await bad.async_load()
        self.assertFalse(bad._loaded)

    async def test_save_is_serial_and_cancel_cannot_outlive_new_clear(self):
        started = asyncio.Event()
        release = asyncio.Event()
        writes = []

        async def delayed(data):
            if not writes:
                started.set()
                await release.wait()
            writes.append(deepcopy(data))
            self.store.data = data

        self.store.async_save = delayed
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        save = asyncio.create_task(
            self.manager.async_update_listening_profile(
                self.runtime, profile(), self.payload, refresh_guard=guard
            )
        )
        await started.wait()
        clear = asyncio.create_task(self.manager.async_clear("profile:one"))
        await asyncio.sleep(0)
        save.cancel()
        await asyncio.sleep(0)
        save.cancel()
        await asyncio.sleep(0)
        self.assertFalse(clear.done())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await save
        await clear
        self.assertNotIn("listening_profile", self.store.data["memories"]["profile:one"])
        self.assertEqual(len(writes), 2)

    async def test_source_owner_change_does_not_rebind_partial_profile_ref(self):
        await self.manager.async_update_listening_profile(self.runtime, profile(), self.payload)
        self.runtime.profile_context_music_account_id = "account-two"
        await self.manager.async_update_listening_profile(
            self.runtime, {"recent_tracks": []}, self.payload
        )
        saved = await self.manager.async_listening_profile(self.runtime, self.payload)
        self.assertNotIn("artwork", saved["top_tracks_by_range"]["short_term"][0])

    async def test_failed_profile_save_preserves_concurrent_trusted_choice(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def fail_late(_):
            entered.set()
            await release.wait()
            raise OSError("fixture late save failure")

        self.store.async_save = fail_late
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        write = asyncio.create_task(
            self.manager.async_update_listening_profile(
                self.runtime, profile(), self.payload, refresh_guard=guard
            )
        )
        await entered.wait()
        memory = self.manager.data["memories"]["profile:one"]
        memory["favorite_artists"] = ["Concurrent trusted selection"]
        release.set()
        with self.assertRaises(OSError):
            await write
        self.assertEqual(memory["favorite_artists"], ["Concurrent trusted selection"])
        self.assertNotIn("listening_profile", memory)

    async def test_private_read_cannot_persist_or_reuse_normal_source_cache(self):
        from custom_components.djconnect.profile_privacy import ProfilePrivacyPolicy
        from custom_components.djconnect.domain.profile import ProfilePrivacyMode
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        self.runtime.profile_context_privacy_policy = ProfilePrivacyPolicy(
            ProfilePrivacyMode.PRIVATE, private_session=True, allow_music_dna_persistence=False
        )
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        self.assertTrue(guard.valid())
        self.assertFalse(guard.persistence_allowed)
        await self.manager.async_update_listening_profile(
            self.runtime, profile(), self.payload, refresh_guard=guard
        )
        self.assertNotIn("listening_profile", self.manager.data["memories"]["profile:one"])
        backend = SpotifyBackend(self.hass, self.runtime)
        calls = []

        async def external_fixture():
            calls.append(1)
            return len(calls)

        first = await backend._cached("listening_profile:v1", external_fixture)
        self.runtime.profile_context_privacy_policy = ProfilePrivacyPolicy(
            ProfilePrivacyMode.NORMAL
        )
        self.assertFalse(guard.valid())
        second = await backend._cached("listening_profile:v1", external_fixture)
        self.assertEqual((first, second), (1, 2))
        for index in range(100):
            self.runtime.profile_context_music_account_id = str(index)
            await backend._cached("listening_profile:v1", external_fixture)
        self.assertEqual(len(self.runtime.backend_cache), 1)

    async def test_actual_stored_recent_art_asset_and_expiry_invalidate_feed(self):
        from custom_components.djconnect.music_discovery import _context_signature

        item = _normalize_profile_track(provider_track())
        context = {"memory": {"listening_profile": {"recent_tracks": [item]}}}
        original = _context_signature(context)
        item["artwork"]["asset_id"] = "d" * 40
        changed = _context_signature(context)
        self.assertNotEqual(original, changed)
        item["artwork"]["expires_at"] = time.time() - 1
        self.assertNotEqual(changed, _context_signature(context))

    async def test_disabled_consent_guard_rejects_enable_during_explicit_read(self):
        await self.manager.async_set_enabled(self.runtime, False, self.payload)
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        self.assertTrue(guard.valid())
        self.assertFalse(guard.persistence_allowed)
        await self.manager.async_set_enabled(self.runtime, True, self.payload)
        self.assertFalse(guard.valid())
        await self.manager.async_update_listening_profile(
            self.runtime, profile(), self.payload, refresh_guard=guard
        )
        self.assertNotIn("listening_profile", self.manager.data["memories"]["profile:one"])

    async def test_normal_token_rotation_keeps_guard_but_discards_source_cache(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        self.runtime.config["spotify_client_id"] = "fixture-client"
        self.runtime.config["spotify_refresh_token"] = "fixture-first"
        guard = await art.capture_refresh_guard(self.runtime, self.payload)
        backend = SpotifyBackend(self.hass, self.runtime)
        calls = []

        async def fixture():
            calls.append(1)
            return len(calls)

        self.assertEqual(await backend._cached("listening_profile:v1", fixture), 1)
        self.runtime.config["spotify_refresh_token"] = "fixture-rotated"
        self.assertTrue(guard.valid())
        self.assertEqual(await backend._cached("listening_profile:v1", fixture), 2)
        self.assertEqual(len(self.runtime.backend_cache), 1)
        self.runtime.config["spotify_client_id"] = "different-provider-client"
        self.assertFalse(guard.valid())
