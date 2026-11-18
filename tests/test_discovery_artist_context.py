"""Synthetic Spotify wires: exact artist-to-playlist resolution, no live playback."""

import asyncio
from copy import deepcopy
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from tests.test_http_voice_helpers import install_http_stubs


class DiscoveryArtistResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.module = importlib.import_module("custom_components.djconnect.spotify_backend")

    def setUp(self):
        self.artist = "A" * 22
        self.playlist = "B" * 22
        self.item = {
            "id": self.playlist,
            "uri": "spotify:playlist:" + self.playlist,
            "type": "playlist",
            "name": "This Is Fixture Artist",
            "owner": {"id": "spotify"},
        }
        self.artist_data = {
            "id": self.artist,
            "uri": "spotify:artist:" + self.artist,
            "type": "artist",
            "name": "Fixture Artist",
        }
        self.details = {
            **deepcopy(self.item),
            "tracks": {
                "items": [
                    {
                        "track": {
                            "id": "C" * 22,
                            "uri": "spotify:track:" + "C" * 22,
                            "type": "track",
                            "artists": [
                                {"id": self.artist, "uri": "spotify:artist:" + self.artist}
                            ],
                        }
                    }
                ]
            },
        }
        self.results = [self.item]
        self.calls = []
        self.backend = object.__new__(self.module.SpotifyBackend)
        self.backend.runtime = SimpleNamespace(config={})

        async def request(method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            route = urlsplit(path).path
            if route == "/artists/" + self.artist:
                return deepcopy(self.artist_data)
            if route == "/search":
                q = parse_qs(urlsplit(path).query)
                self.assertEqual(q["type"], ["playlist"])
                self.assertLessEqual(int(q["limit"][0]), 10)
                return {"playlists": {"items": deepcopy(self.results)}}
            if route == "/playlists/" + self.playlist:
                return deepcopy(self.details)
            raise self.module.SpotifyBackendError("synthetic denied", http_status=403)

        self.backend._request = request

    def resolve(self):
        return asyncio.run(self.backend.resolve_discovery_artist("spotify:artist:" + self.artist))

    def test_real_exact_artist_and_official_this_is_identity_without_mutation(self):
        selected = self.resolve()
        self.assertEqual(selected["uri"], "spotify:playlist:" + self.playlist)
        self.assertEqual(selected["artist_uri"], "spotify:artist:" + self.artist)
        self.assertEqual([m for m, _, _ in self.calls], ["GET"] * len(self.calls))

    def test_new_item_envelope_qualifies_exact_credited_artist(self):
        self.details["items"] = {
            "items": [{"item": self.details.pop("tracks")["items"][0]["track"]}]
        }
        self.assertEqual(self.resolve()["uri"], "spotify:playlist:" + self.playlist)

    def test_fan_playlist_and_guessed_title_are_not_an_official_resolution(self):
        for changed in [
            {"owner": {"id": "fan"}},
            {"name": "Best of Fixture Artist"},
            {"uri": "spotify:playlist:" + "D" * 22},
        ]:
            with self.subTest(changed=changed):
                self.results = [{**self.item, **changed}]
                with self.assertRaises(self.module.SpotifyBackendError):
                    self.resolve()

    def test_wrong_artist_id_even_same_display_name_is_rejected(self):
        self.details["tracks"]["items"][0]["track"]["artists"] = [
            {"id": "E" * 22, "name": "Fixture Artist"}
        ]
        with self.assertRaises(self.module.SpotifyBackendError):
            self.resolve()

    def test_missing_or_restricted_item_evidence_never_becomes_a_guess(self):
        self.details.pop("tracks")
        with self.assertRaises(self.module.SpotifyBackendError):
            self.resolve()
        self.assertTrue(all(method == "GET" for method, _, _ in self.calls))

    def test_wrong_artist_endpoint_identity_and_empty_playlist_fail_closed(self):
        self.artist_data["id"] = "F" * 22
        with self.assertRaises(self.module.SpotifyBackendError):
            self.resolve()
        self.artist_data["id"] = self.artist
        self.details["tracks"]["items"] = []
        with self.assertRaises(self.module.SpotifyBackendError):
            self.resolve()

    def test_null_search_candidates_are_not_executed(self):
        self.results = [None, self.item]
        self.assertEqual(self.resolve()["uri"], "spotify:playlist:" + self.playlist)

    def test_context_only_payload_cannot_use_the_old_offset_command(self):
        with self.assertRaises(ValueError):
            asyncio.run(
                self.backend.play_context_at({"context_uri": "spotify:playlist:" + self.playlist})
            )
        self.assertEqual(self.calls, [])

    def test_direct_read_qualifies_real_candidate_even_if_search_omits_it(self):
        self.results = []
        self.details["name"] = "This is Fixture Artist"
        with self.assertRaisesRegex(self.module.SpotifyDiscoveryError, "this_is_not_found"):
            self.resolve()
        item = asyncio.run(
            self.backend.discovery_playlist_identity(
                "spotify:artist:" + self.artist, "spotify:playlist:" + self.playlist
            )
        )
        self.assertEqual(item["uri"], "spotify:playlist:" + self.playlist)
        self.assertTrue(all(method == "GET" for method, _, _ in self.calls))

    def test_direct_denial_is_evidence_of_403_instead_of_search_miss(self):
        original = self.backend._request

        async def denied(method, path, **kwargs):
            if urlsplit(path).path.startswith("/playlists/"):
                raise self.module.SpotifyBackendError("fixture denial", http_status=403)
            return await original(method, path, **kwargs)

        self.backend._request = denied
        with self.assertRaises(self.module.SpotifyDiscoveryError) as caught:
            asyncio.run(
                self.backend.discovery_playlist_identity(
                    "spotify:artist:" + self.artist, "spotify:playlist:" + self.playlist
                )
            )
        self.assertEqual(caught.exception.code, "music_discovery_playlist_access_denied")
        self.assertEqual(caught.exception.http_status, 403)

    def test_identity_withdrawal_is_not_relabelled_as_provider_denial(self):
        original = self.backend._request

        async def withdrawn(method, path, **kwargs):
            if urlsplit(path).path.startswith("/playlists/"):
                raise self.module.SpotifyDiscoveryError("music_discovery_context_changed")
            return await original(method, path, **kwargs)

        self.backend._request = withdrawn
        with self.assertRaisesRegex(self.module.SpotifyDiscoveryError, "context_changed"):
            self.resolve()


class DirectDiscoveryArtistCommandTests(unittest.TestCase):
    """Current artist dispatch resolves identity, never editorial playlists."""

    setUpClass = classmethod(DiscoveryArtistResolverTests.setUpClass.__func__)
    setUp = DiscoveryArtistResolverTests.setUp

    def test_current_command_uses_original_artist_without_playlist_reads(self):
        for name, ident in [
            ("London Grammar", "3Bd1cgCjtCI32PYvDC3ynO"),
            ("Snow Patrol", "3rIZMv9rysU7JkLzEaC5Jp"),
            ("Son Mieux", "1BCBAzjX8J0qpvNTPRDCLc"),
        ]:
            with self.subTest(artist=name):
                self.setUp()
                self.artist = ident
                self.artist_data.update(id=ident, uri="spotify:artist:" + ident, name=name)
                self.results = []

                async def exercise():
                    with patch.object(self.module, "SpotifyBackend", return_value=self.backend):
                        with self.module.discovery_dispatch(lambda: True, lambda: None):
                            return await self.module.handle_spotify_command(
                                None,
                                self.backend.runtime,
                                "resolve_discovery_artist",
                                self.artist_data["uri"],
                                play=False,
                            )

                result = asyncio.run(exercise())
                self.assertTrue(result["success"])
                self.assertEqual(result["item"]["uri"], self.artist_data["uri"])
                self.assertEqual(result["item"]["identity_basis"], "spotify_artist_identity")
                self.assertEqual([(m, p) for m, p, _ in self.calls], [("GET", "/artists/" + ident)])

    def test_current_command_rejects_inconsistent_provider_artist(self):
        for changed in [
            {"id": "Z" * 22},
            {"uri": "spotify:artist:" + "Z" * 22},
            {"type": "playlist"},
            {"name": ""},
        ]:
            with self.subTest(changed=changed):
                self.setUp()
                self.artist_data.update(changed)

                async def exercise():
                    with patch.object(self.module, "SpotifyBackend", return_value=self.backend):
                        with self.module.discovery_dispatch(lambda: True, lambda: None):
                            return await self.module.handle_spotify_command(
                                None,
                                self.backend.runtime,
                                "resolve_discovery_artist",
                                "spotify:artist:" + self.artist,
                                play=False,
                            )

                with self.assertRaisesRegex(self.module.SpotifyDiscoveryError, "artist_invalid"):
                    asyncio.run(exercise())
                self.assertTrue(all(m == "GET" for m, _, _ in self.calls))

    def test_current_command_rejects_withdrawal_during_artist_read(self):
        active = [True]
        original = self.backend._request

        async def withdraw(*args, **kwargs):
            result = await original(*args, **kwargs)
            active[0] = False
            return result

        self.backend._request = withdraw

        async def exercise():
            with patch.object(self.module, "SpotifyBackend", return_value=self.backend):
                with self.module.discovery_dispatch(lambda: active[0], lambda: None):
                    return await self.module.handle_spotify_command(
                        None,
                        self.backend.runtime,
                        "resolve_discovery_artist",
                        self.artist_data["uri"],
                        play=False,
                    )

        with self.assertRaisesRegex(self.module.SpotifyDiscoveryError, "context_changed"):
            asyncio.run(exercise())
        self.assertTrue(all(m == "GET" for m, _, _ in self.calls))

    def test_current_command_cannot_mint_effect_scope(self):
        async def exercise():
            with patch.object(self.module, "SpotifyBackend", return_value=self.backend):
                return await self.module.handle_spotify_command(
                    None,
                    self.backend.runtime,
                    "resolve_discovery_artist",
                    self.artist_data["uri"],
                    play=False,
                )

        with self.assertRaisesRegex(self.module.SpotifyDiscoveryError, "effect_not_authorized"):
            asyncio.run(exercise())
        self.assertEqual(self.calls, [])
