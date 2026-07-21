from __future__ import annotations

import asyncio
import importlib
import sys
import types
import unittest
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install_backend_stubs() -> list[dict]:
    issues: list[dict] = []
    deleted: list[dict] = []
    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    aiohttp_client = sys.modules.setdefault("homeassistant.helpers.aiohttp_client", types.ModuleType("homeassistant.helpers.aiohttp_client"))
    issue_registry = types.ModuleType("homeassistant.helpers.issue_registry")

    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class IssueSeverity:
        WARNING = "warning"

    def async_create_issue(hass, domain, issue_id, **kwargs):
        issues.append({"domain": domain, "issue_id": issue_id, **kwargs})

    def async_delete_issue(hass, domain, issue_id):
        deleted.append({"domain": domain, "issue_id": issue_id})

    aiohttp.ClientTimeout = ClientTimeout
    core.HomeAssistant = object
    aiohttp_client.async_get_clientsession = lambda hass: types.SimpleNamespace()
    issue_registry.IssueSeverity = IssueSeverity
    issue_registry.async_create_issue = async_create_issue
    issue_registry.async_delete_issue = async_delete_issue
    helpers.issue_registry = issue_registry
    sys.modules["homeassistant.helpers.issue_registry"] = issue_registry

    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)
    install_backend_stubs.deleted = deleted
    return issues


class SpotifyBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.issues = install_backend_stubs()
        cls.backend = importlib.import_module("custom_components.djconnect.spotify_backend")
        cls.oauth = importlib.import_module("custom_components.djconnect.spotify_oauth")
        cls.const = importlib.import_module("custom_components.djconnect.const")

    def setUp(self) -> None:
        self.issues.clear()
        install_backend_stubs.deleted.clear()

    def test_spotify_search_type_supports_track_album_and_playlist(self) -> None:
        self.assertEqual(self.backend._spotify_search_type("track"), "track")
        self.assertEqual(self.backend._spotify_search_type("album"), "album")
        self.assertEqual(self.backend._spotify_search_type("playlist"), "playlist")
        self.assertEqual(self.backend._spotify_search_type("artist"), "artist")

    def test_playback_observation_returns_normalized_renderer_metadata(self) -> None:
        runtime = types.SimpleNamespace(config={})
        backend = self.backend.SpotifyBackend(object(), runtime)
        calls: list[tuple[str, str]] = []

        async def request(method, path):
            calls.append((method, path))
            return {
                "is_playing": True,
                "item": {
                    "uri": "spotify:track:observed",
                    "name": "Never enters Runtime",
                    "artists": [{"name": "Hidden metadata"}],
                    "duration_ms": 180000,
                },
                "progress_ms": 12000,
            }

        backend._request = request
        observed = asyncio.run(backend.async_observe_current_playback())

        self.assertEqual(calls, [("GET", "/me/player")])
        self.assertTrue(observed.is_playing)
        self.assertEqual(observed.media_identity, "spotify:track:observed")
        self.assertEqual(observed.title, "Never enters Runtime")
        self.assertEqual(observed.artist, "Hidden metadata")
        self.assertEqual(observed.state, "playing")
        self.assertEqual(observed.artwork_url, "")
        self.assertEqual(observed.duration_ms, 180000)
        self.assertEqual(observed.position_ms, 12000)
        self.assertFalse(hasattr(runtime, "last_playback"))

    def test_playback_observation_rejects_non_track_or_inactive_media(self) -> None:
        runtime = types.SimpleNamespace(config={})
        backend = self.backend.SpotifyBackend(object(), runtime)

        async def request(method, path):
            return {"is_playing": True, "item": {"uri": "spotify:episode:podcast"}}

        backend._request = request
        observed = asyncio.run(backend.async_observe_current_playback())

        self.assertFalse(observed.is_playing)
        self.assertEqual(observed.media_identity, "")

    def test_search_albums_returns_normalized_album_list(self) -> None:
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                if "/search?" in url:
                    return Response(
                        {
                            "albums": {
                                "items": [
                                    {
                                        "id": "hardcore-1",
                                        "name": "Hardcore Album 1",
                                        "uri": "spotify:album:hardcore-1",
                                        "release_date": "1994-01-01",
                                        "images": [{"url": "https://img.example/hardcore.jpg", "width": 640}],
                                        "artists": [{"name": "Artist One"}],
                                    }
                                ]
                            }
                        }
                    )
                raise AssertionError(f"unexpected URL: {url}")

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        result = asyncio.run(backend.search_albums("hardcore", limit=10))

        self.assertIn("q=hardcore", session.urls[0])
        self.assertIn("type=album", session.urls[0])
        self.assertEqual(result[0]["uri"], "spotify:album:hardcore-1")
        self.assertEqual(result[0]["title"], "Hardcore Album 1")
        self.assertEqual(result[0]["artist"], "Artist One")

    def test_normalize_playback_exposes_best_album_art_for_media_player(self) -> None:
        playback = self.backend._normalize_playback(
            {
                "is_playing": True,
                "context": {"uri": "spotify:playlist:abc"},
                "item": {
                    "name": "Song",
                    "uri": "spotify:track:123",
                    "artists": [{"name": "Artist"}],
                    "album": {
                        "name": "Album",
                        "images": [
                            {"url": "https://example.test/small.jpg", "width": 64, "height": 64},
                            {"url": "https://example.test/large.jpg", "width": 640, "height": 640},
                        ],
                    },
                },
                "device": {"name": "iPhone", "volume_percent": 30},
            }
        )

        self.assertEqual(playback["album_image_url"], "https://example.test/large.jpg")
        self.assertEqual(playback["media_image_url"], "https://example.test/large.jpg")
        self.assertEqual(playback["uri"], "spotify:track:123")
        self.assertEqual(playback["current_uri"], "spotify:track:123")
        self.assertEqual(playback["context_uri"], "spotify:playlist:abc")
        self.assertEqual(playback["queue_context"], "spotify:playlist:abc")
        self.assertEqual(
            playback["context"],
            {"type": "", "uri": "spotify:playlist:abc", "href": ""},
        )

    def test_listening_profile_fetches_recently_played_and_top_items(self) -> None:
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                if "recently-played" in url:
                    return Response(
                        {
                            "items": [
                                {
                                    "played_at": "2026-06-19T10:00:00Z",
                                    "track": {
                                        "id": "track-1",
                                        "name": "Intro",
                                        "uri": "spotify:track:1",
                                        "artists": [{"name": "The xx"}],
                                        "album": {"name": "xx", "images": []},
                                    },
                                }
                            ]
                        }
                    )
                if "/me/top/artists" in url:
                    return Response(
                        {
                            "items": [
                                {
                                    "id": "artist-1",
                                    "name": "The xx",
                                    "uri": "spotify:artist:1",
                                    "genres": ["indie", "ambient pop"],
                                }
                            ]
                        }
                    )
                if "/me/top/tracks" in url:
                    return Response(
                        {
                            "items": [
                                {
                                    "id": "track-2",
                                    "name": "Holocene",
                                    "uri": "spotify:track:2",
                                    "artists": [{"name": "Bon Iver"}],
                                    "album": {"name": "Bon Iver", "images": []},
                                }
                            ]
                        }
                    )
                return Response({})

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        profile = asyncio.run(backend.listening_profile())

        self.assertTrue(any("/me/player/recently-played?limit=50" in url for url in session.urls))
        self.assertEqual(sum("/me/top/artists" in url for url in session.urls), 3)
        self.assertEqual(sum("/me/top/tracks" in url for url in session.urls), 3)
        self.assertEqual(profile["recent_tracks"][0]["artist"], "The xx")
        self.assertIn("indie", profile["inferred_genres"])
        self.assertIn("spotify_recently_played", profile["sources"])

    def test_recently_played_command_fetches_only_recent_tracks(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "items": [
                        {
                            "played_at": "2026-06-23T10:00:00Z",
                            "track": {
                                "id": "track-1",
                                "name": "Bella",
                                "uri": "spotify:track:1",
                                "artists": [{"name": "Finnebassen"}],
                                "album": {
                                    "name": "Album",
                                    "uri": "spotify:album:1",
                                    "images": [],
                                },
                            },
                            "context": {
                                "type": "playlist",
                                "uri": "spotify:playlist:recent",
                            },
                        }
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        session = Session()

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: session
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "recently_played",
                    {"limit": 10},
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(
            session.urls,
            ["https://api.spotify.com/v1/me/player/recently-played?limit=10"],
        )
        self.assertEqual(result["tracks"][0]["track_name"], "Bella")
        self.assertEqual(result["tracks"][0]["artist"], "Finnebassen")
        self.assertEqual(result["tracks"][0]["played_at"], "2026-06-23T10:00:00Z")
        self.assertEqual(result["tracks"][0]["album_uri"], "spotify:album:1")
        self.assertEqual(result["tracks"][0]["context_uri"], "spotify:playlist:recent")
        self.assertEqual(result["tracks"][0]["context_type"], "playlist")
        self.assertEqual(result["source"], "spotify_recently_played")

    def test_empty_playback_does_not_clear_cached_sensor_fields(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {}

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={
                "volume": 35,
                "last_track": "Alive",
                "sound_output": "Living room",
                "ha_pairing_status": "paired",
            },
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()

        playback = asyncio.run(backend.playback_state())

        self.assertFalse(playback["has_playback"])
        self.assertEqual(runtime.device_status["spotify_status"], "idle")
        self.assertEqual(runtime.device_status["volume"], 35)
        self.assertEqual(runtime.device_status["last_track"], "Alive")
        self.assertEqual(runtime.device_status["sound_output"], "Living room")
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")

    def test_playback_state_appends_ambient_fact_once_per_artist_album(self) -> None:
        class Response:
            status = 200

            def __init__(self, track_name):
                self.track_name = track_name

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "is_playing": True,
                    "item": {
                        "name": self.track_name,
                        "uri": f"spotify:track:{self.track_name}",
                        "artists": [{"name": "Radiohead"}],
                        "album": {"name": "OK Computer"},
                    },
                    "device": {"name": "Living room"},
                }

            async def text(self):
                return "{}"

        class Session:
            def __init__(self):
                self.calls = 0

            def request(self, method, url, **kwargs):
                self.calls += 1
                return Response("Paranoid Android" if self.calls == 1 else "No Surprises")

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, response):
                self.messages.append((user_id, request_payload, response))

        class Services:
            def __init__(self):
                self.calls = 0

            async def async_call(self, domain, service, data, **kwargs):
                self.calls += 1
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": "OK Computer is een klassieker."
                            }
                        }
                    }
                }

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=History(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()
        hass = types.SimpleNamespace(services=Services())
        backend.hass = hass

        asyncio.run(backend.playback_state())
        asyncio.run(backend.playback_state())

        self.assertEqual(len(runtime.ask_dj_history.messages), 1)
        self.assertEqual(runtime.last_ambient_fact_key, "radiohead|ok computer")
        self.assertEqual(hass.services.calls, 1)
        self.assertEqual(runtime.ask_dj_history.messages[0][2]["message_kind"], "system")
        self.assertEqual(runtime.ask_dj_history.messages[0][2]["origin"], "spotify_playback_context")

    def test_playback_state_records_artist_genres_in_music_dna_when_enabled(self) -> None:
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return "{}"

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                if "/artists?ids=artist-1" in url:
                    return Response(
                        {
                            "artists": [
                                {
                                    "id": "artist-1",
                                    "name": "RUFUS DU SOL",
                                    "genres": ["australian dance", "indietronica"],
                                }
                            ]
                        }
                    )
                if "/me/tracks/contains" in url:
                    return Response([False])
                return Response(
                    {
                        "is_playing": True,
                        "item": {
                            "id": "track-1",
                            "name": "Innerbloom",
                            "uri": "spotify:track:track-1",
                            "duration_ms": 585000,
                            "artists": [{"id": "artist-1", "name": "RUFUS DU SOL"}],
                            "album": {"name": "Bloom"},
                        },
                        "device": {"name": "Living room"},
                    }
                )

        class Memory:
            def __init__(self):
                self.tracks = []
                self.saved = 0

            def update_recent_tracks(self, key, track):
                self.tracks.append((key, dict(track)))

            async def async_save(self):
                self.saved += 1

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={"device_id": "djconnect-ios-123456789ABC"},
            ask_dj_history=None,
            memory=Memory(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()
        backend.hass = types.SimpleNamespace(services=types.SimpleNamespace())

        playback = asyncio.run(backend.playback_state())

        self.assertEqual(playback["genres"], ["australian dance", "indietronica"])
        self.assertEqual(runtime.memory.tracks[0][0], "djconnect-ios-123456789ABC")
        self.assertEqual(runtime.memory.tracks[0][1]["genres"], ["australian dance", "indietronica"])
        self.assertEqual(runtime.memory.saved, 1)
        self.assertTrue(any("/artists?ids=artist-1" in url for url in backend.session.urls))

    def test_playback_state_backs_off_artist_genre_lookup_after_429(self) -> None:
        class Response:
            def __init__(self, status, payload):
                self.status = status
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.artist_calls = 0

            def request(self, method, url, **kwargs):
                if "/artists?ids=artist-1" in url:
                    self.artist_calls += 1
                    return Response(429, {"error": {"message": "Too many requests"}})
                if "/me/tracks/contains" in url:
                    return Response(200, [False])
                return Response(
                    200,
                    {
                        "is_playing": True,
                        "item": {
                            "id": "track-1",
                            "name": "Innerbloom",
                            "uri": "spotify:track:track-1",
                            "duration_ms": 585000,
                            "artists": [{"id": "artist-1", "name": "RUFUS DU SOL"}],
                            "album": {"name": "Bloom"},
                        },
                        "device": {"name": "Living room"},
                    },
                )

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=None,
            memory=None,
            backend_cache={},
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session
        backend.hass = types.SimpleNamespace(services=types.SimpleNamespace())

        first = asyncio.run(backend.playback_state())
        second = asyncio.run(backend.playback_state())

        self.assertTrue(first["has_playback"])
        self.assertTrue(second["has_playback"])
        self.assertEqual(session.artist_calls, 1)

    def test_playback_state_skips_ambient_fact_prompt_leak(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "is_playing": True,
                    "item": {
                        "name": "Hollywood",
                        "uri": "spotify:track:hollywood",
                        "artists": [{"name": "LA Vision"}, {"name": "GIGI D'AGOSTINO"}],
                        "album": {"name": "Hollywood"},
                    },
                    "device": {"name": "Living room"},
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, response):
                self.messages.append((user_id, request_payload, response))

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": (
                                    "Sorry, ik kan Nederlands Gebruik alleen breed bekende kennis "
                                    "over deze artiest of dit album Als je geen betrouwbaar feitje "
                                    "weet antwoord exact met SKIP Noem geen Spotify URI's en voer "
                                    "geen playbackactie uit Maximaal twee korte zinnen Artiest "
                                    "LA Vision GIGI D'AGOSTINO Album Hollywood Huidig nummer "
                                    "Hollywood niet vinden"
                                )
                            }
                        }
                    }
                }

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=History(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()
        backend.hass = types.SimpleNamespace(services=Services())

        asyncio.run(backend.playback_state())

        self.assertEqual(runtime.ask_dj_history.messages, [])
        self.assertEqual(runtime.last_ambient_fact_key, "la vision, gigi d'agostino|hollywood")

    def test_playback_state_appends_ambient_fact_after_album_change(self) -> None:
        class Response:
            status = 200

            def __init__(self, album_name):
                self.album_name = album_name

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "is_playing": True,
                    "item": {
                        "name": "Track",
                        "uri": f"spotify:track:{self.album_name}",
                        "artists": [{"name": "Radiohead"}],
                        "album": {"name": self.album_name},
                    },
                    "device": {"name": "Living room"},
                }

            async def text(self):
                return "{}"

        class Session:
            def __init__(self):
                self.albums = ["OK Computer", "Kid A"]

            def request(self, method, url, **kwargs):
                return Response(self.albums.pop(0))

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": "Een kort feitje."
                            }
                        }
                    }
                }

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, response):
                self.messages.append((request_payload, response))

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=History(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(types.SimpleNamespace(services=Services()), runtime)
        backend.session = Session()

        asyncio.run(backend.playback_state())
        asyncio.run(backend.playback_state())

        self.assertEqual(len(runtime.ask_dj_history.messages), 2)
        self.assertEqual(runtime.last_ambient_fact_key, "radiohead|kid a")

    def test_playback_state_dedupes_ambient_fact_from_history_after_runtime_reset(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "is_playing": True,
                    "item": {
                        "name": "Give Me Everything",
                        "uri": "spotify:track:give-me-everything",
                        "artists": [{"name": "Pitbull"}],
                        "album": {"name": "Planet Pit"},
                    },
                    "device": {"name": "Living room"},
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        class Services:
            def __init__(self):
                self.calls = 0

            async def async_call(self, domain, service, data, **kwargs):
                self.calls += 1
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": "Give Me Everything was een wereldhit."
                            }
                        }
                    }
                }

        class History:
            def __init__(self):
                self.messages = []

            async def async_has_client_message_id(self, user_id, client_message_id):
                return any(
                    message[1].get("client_message_id") == client_message_id
                    for message in self.messages
                )

            async def async_append_assistant_message(self, user_id, request_payload, response):
                self.messages.append((user_id, request_payload, response))

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=History(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()
        hass = types.SimpleNamespace(services=Services())
        backend.hass = hass

        asyncio.run(backend.playback_state())
        runtime.last_ambient_fact_key = ""
        asyncio.run(backend.playback_state())

        self.assertEqual(len(runtime.ask_dj_history.messages), 1)
        self.assertEqual(hass.services.calls, 1)
        self.assertEqual(runtime.last_ambient_fact_key, "pitbull|planet pit")

    def test_ambient_fact_prefers_home_assistant_language_over_assist_language(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "is_playing": True,
                    "item": {
                        "name": "Friendships",
                        "uri": "spotify:track:friendships",
                        "artists": [{"name": "Pascal Letoublon"}],
                        "album": {"name": "Friendships"},
                    },
                    "device": {"name": "Living room"},
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, response):
                self.messages.append((user_id, request_payload, response))

        class Services:
            def __init__(self):
                self.calls = []

            async def async_call(self, domain, service, data, **kwargs):
                self.calls.append(data)
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": "Friendships werd een grote hit door zijn melodische house-sound."
                            }
                        }
                    }
                }

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "tts_language": "en-US",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=History(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="nl"),
            services=Services(),
        )
        backend.hass = hass

        asyncio.run(backend.playback_state())

        self.assertEqual(hass.services.calls[0]["language"], "nl-NL")
        self.assertIn("Antwoord uitsluitend in het Nederlands", hass.services.calls[0]["text"])
        self.assertIn("Pascal Letoublon", hass.services.calls[0]["text"])
        self.assertEqual(
            runtime.ask_dj_history.messages[0][2]["text"],
            "Friendships werd een grote hit door zijn melodische house-sound.",
        )

    def test_ambient_fact_adds_proxied_artist_image_from_wikipedia(self) -> None:
        ambient = importlib.import_module("custom_components.djconnect.ambient_ask_dj")

        class SpotifyResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "is_playing": True,
                    "item": {
                        "name": "In And Out Of Love",
                        "uri": "spotify:track:in-out-love",
                        "artists": [{"name": "Armin van Buuren"}],
                        "album": {"name": "Imagine"},
                    },
                    "device": {"name": "Living room"},
                }

            async def text(self):
                return "{}"

        class SpotifySession:
            def request(self, method, url, **kwargs):
                return SpotifyResponse()

        class WikiResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "title": "Armin van Buuren",
                    "description": "Nederlands dj",
                    "thumbnail": {"source": "https://upload.wikimedia.org/armin.jpg"},
                    "content_urls": {
                        "desktop": {"page": "https://nl.wikipedia.org/wiki/Armin_van_Buuren"}
                    },
                }

        class WikiSession:
            def __init__(self):
                self.urls = []

            def get(self, url, **kwargs):
                self.urls.append(url)
                return WikiResponse()

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, response):
                self.messages.append((user_id, request_payload, response))

        class Services:
            async def async_call(self, domain, service, data, **kwargs):
                return {
                    "response": {
                        "speech": {
                            "plain": {
                                "speech": "Armin van Buuren is een bekende Nederlandse trance-dj."
                            }
                        }
                    }
                }

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            ask_dj_history=History(),
            update=lambda **kwargs: [setattr(runtime, key, value) for key, value in kwargs.items()],
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = SpotifySession()
        wiki_session = WikiSession()
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="nl"),
            data={},
            services=Services(),
        )
        backend.hass = hass

        original_clientsession = ambient.async_get_clientsession
        ambient.async_get_clientsession = lambda hass_arg: wiki_session
        try:
            asyncio.run(backend.playback_state())
        finally:
            ambient.async_get_clientsession = original_clientsession

        response = runtime.ask_dj_history.messages[0][2]
        self.assertEqual(response["images"][0]["source"], "wikipedia")
        self.assertTrue(response["images"][0]["url"].startswith(self.const.API_IMAGE_PROXY_BASE))
        self.assertEqual(response["links"][0]["source"], "wikipedia")
        self.assertIn("Armin_van_Buuren", wiki_session.urls[0])
        proxy_token = response["images"][0]["url"].rsplit("/", 1)[-1]
        self.assertEqual(
            hass.data[self.const.DOMAIN]["image_proxy"][proxy_token],
            "https://upload.wikimedia.org/armin.jpg",
        )

    def test_play_search_query_resolves_to_spotify_uri_before_playback(self) -> None:
        class Response:
            def __init__(self, status, payload=None):
                self.status = status
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if method == "GET" and "/search?" in url:
                    return Response(
                        200,
                        {
                            "artists": {
                                "total": 1,
                                "items": [
                                    {
                                        "name": "Pearl Jam",
                                        "uri": "spotify:artist:pearl-jam",
                                    }
                                ],
                            }
                        },
                    )
                return Response(204)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        asyncio.run(backend.play({"query": "ik wil pearl jam starten", "type": "music"}))

        self.assertIn("/search?", session.calls[0]["url"])
        self.assertIn("q=ik+wil+pearl+jam+starten", session.calls[0]["url"])
        self.assertIn("type=artist", session.calls[0]["url"])
        self.assertEqual(session.calls[0]["method"], "GET")
        self.assertEqual(session.calls[1]["method"], "PUT")
        self.assertEqual(
            session.calls[1]["json"],
            {"context_uri": "spotify:artist:pearl-jam"},
        )
        self.assertEqual(runtime.last_resolved_media["title"], "")
        self.assertEqual(runtime.last_resolved_media["artist"], "Pearl Jam")
        self.assertEqual(runtime.last_resolved_media["uri"], "spotify:artist:pearl-jam")
        self.assertEqual(runtime.last_spotify_search["query"], "ik wil pearl jam starten")
        self.assertEqual(runtime.last_spotify_search["type"], "artist")
        self.assertEqual(runtime.last_spotify_search["returned"], 1)
        self.assertEqual(
            runtime.last_spotify_search["selected"]["uri"],
            "spotify:artist:pearl-jam",
        )

    def test_play_artist_top_tracks_searches_artist_and_starts_popular_tracks(self) -> None:
        class Response:
            def __init__(self, status, payload=None):
                self.status = status
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if method == "GET" and "/search?" in url:
                    return Response(
                        200,
                        {
                            "artists": {
                                "total": 1,
                                "items": [
                                    {
                                        "id": "artist-id",
                                        "name": "Above & Beyond",
                                        "uri": "spotify:artist:artist-id",
                                        "images": [
                                            {
                                                "url": "https://example.test/artist.jpg",
                                                "width": 640,
                                                "height": 640,
                                            }
                                        ],
                                    }
                                ],
                            }
                        },
                    )
                if method == "GET" and "/artists/artist-id/top-tracks?" in url:
                    return Response(
                        200,
                        {
                            "tracks": [
                                {"uri": "spotify:track:sun-and-moon"},
                                {"uri": "spotify:track:thing-called-love"},
                            ]
                        },
                    )
                return Response(204)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        asyncio.run(backend.play_artist_top_tracks("Above & Beyond"))

        self.assertIn("/search?", session.calls[0]["url"])
        self.assertIn("type=artist", session.calls[0]["url"])
        self.assertIn("/artists/artist-id/top-tracks?", session.calls[1]["url"])
        self.assertEqual(session.calls[2]["method"], "PUT")
        self.assertEqual(
            session.calls[2]["json"],
            {"uris": ["spotify:track:sun-and-moon", "spotify:track:thing-called-love"]},
        )
        self.assertEqual(runtime.last_resolved_media["name"], "Above & Beyond")
        self.assertEqual(
            runtime.last_spotify_search["selected"]["uri"],
            "spotify:artist:artist-id",
        )

    def test_play_artist_top_tracks_corrects_known_artist_typo(self) -> None:
        class Response:
            def __init__(self, status, payload=None):
                self.status = status
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if method == "GET" and "/search?" in url:
                    return Response(
                        200,
                        {
                            "artists": {
                                "items": [
                                    {
                                        "id": "paul-van-dyk",
                                        "name": "Paul van Dyk",
                                        "uri": "spotify:artist:paul-van-dyk",
                                    }
                                ]
                            }
                        },
                    )
                if method == "GET" and "/artists/paul-van-dyk/top-tracks?" in url:
                    return Response(200, {"tracks": [{"uri": "spotify:track:for-an-angel"}]})
                return Response(204)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        asyncio.run(backend.play_artist_top_tracks("paul van dijk"))

        self.assertIn("q=Paul+van+Dyk", session.calls[0]["url"])
        self.assertIn("/artists/paul-van-dyk/top-tracks?", session.calls[1]["url"])
        self.assertEqual(session.calls[2]["json"], {"uris": ["spotify:track:for-an-angel"]})
        self.assertEqual(runtime.last_resolved_media["name"], "Paul van Dyk")

    def test_artist_albums_searches_artist_and_returns_chronological_albums(self) -> None:
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                if "/search?" in url:
                    return Response(
                        {
                            "artists": {
                                "items": [
                                    {
                                        "id": "radiohead",
                                        "name": "Radiohead",
                                        "uri": "spotify:artist:radiohead",
                                    }
                                ]
                            }
                        }
                    )
                if "/artists/radiohead/albums?" in url:
                    return Response(
                        {
                            "items": [
                                {
                                    "id": "okc",
                                    "name": "OK Computer",
                                    "uri": "spotify:album:okc",
                                    "release_date": "1997-05-21",
                                    "album_type": "album",
                                    "total_tracks": 12,
                                    "images": [{"url": "https://img.example/okc.jpg", "width": 640}],
                                    "artists": [{"name": "Radiohead"}],
                                },
                                {
                                    "id": "bends",
                                    "name": "The Bends",
                                    "uri": "spotify:album:bends",
                                    "release_date": "1995-03-13",
                                    "album_type": "album",
                                    "total_tracks": 12,
                                    "images": [{"url": "https://img.example/bends.jpg", "width": 640}],
                                    "artists": [{"name": "Radiohead"}],
                                },
                            ]
                        }
                    )
                raise AssertionError(f"unexpected URL: {url}")

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        result = asyncio.run(backend.artist_albums("Radiohead"))

        self.assertIn("/search?", session.urls[0])
        self.assertIn("q=Radiohead", session.urls[0])
        self.assertIn("/artists/radiohead/albums?", session.urls[1])
        self.assertEqual(result["artist"], "Radiohead")
        self.assertEqual([album["name"] for album in result["albums"]], ["The Bends", "OK Computer"])
        self.assertEqual(result["albums"][0]["image_url"], "https://img.example/bends.jpg")

    def test_related_artists_searches_artist_and_normalizes_results(self) -> None:
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                if "/search?" in url:
                    return Response(
                        {
                            "artists": {
                                "items": [
                                    {
                                        "id": "radiohead",
                                        "name": "Radiohead",
                                        "uri": "spotify:artist:radiohead",
                                    }
                                ]
                            }
                        }
                    )
                if "/artists/radiohead/related-artists" in url:
                    return Response(
                        {
                            "artists": [
                                {
                                    "id": "the-smile",
                                    "name": "The Smile",
                                    "uri": "spotify:artist:the-smile",
                                    "genres": ["art rock"],
                                    "images": [{"url": "https://img.example/smile.jpg", "width": 640}],
                                }
                            ]
                        }
                    )
                raise AssertionError(f"unexpected URL: {url}")

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        result = asyncio.run(backend.related_artists("Radiohead"))

        self.assertIn("/search?", session.urls[0])
        self.assertIn("/artists/radiohead/related-artists", session.urls[1])
        self.assertEqual(result["artist"], "Radiohead")
        self.assertEqual(result["artists"][0]["name"], "The Smile")
        self.assertEqual(result["artists"][0]["image_url"], "https://img.example/smile.jpg")

    def test_artist_profile_searches_artist_and_returns_genres(self) -> None:
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.urls = []

            def request(self, method, url, **kwargs):
                self.urls.append(url)
                if "/search?" in url:
                    return Response(
                        {
                            "artists": {
                                "items": [
                                    {
                                        "id": "beastie-boys",
                                        "name": "Beastie Boys",
                                        "uri": "spotify:artist:beasties",
                                        "genres": ["old school hip hop", "rap rock"],
                                        "images": [{"url": "https://img.example/beasties.jpg", "width": 640}],
                                    }
                                ]
                            }
                        }
                    )
                raise AssertionError(f"unexpected URL: {url}")

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        result = asyncio.run(backend.artist_profile("Beastie Boys"))

        self.assertIn("/search?", session.urls[0])
        self.assertEqual(result["name"], "Beastie Boys")
        self.assertEqual(result["genres"], ["old school hip hop", "rap rock"])
        self.assertEqual(result["image_url"], "https://img.example/beasties.jpg")

    def test_play_recovers_no_active_device_by_transferring_to_configured_source(self) -> None:
        class Response:
            def __init__(self, status, payload=None):
                self.status = status
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []
                self.play_attempts = 0

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if method == "PUT" and url.endswith("/me/player/play"):
                    self.play_attempts += 1
                    if self.play_attempts == 1:
                        return Response(
                            404,
                            {"error": {"message": "No active device found"}},
                        )
                    return Response(204)
                if method == "GET" and url.endswith("/me/player/devices"):
                    return Response(
                        200,
                        {
                            "devices": [
                                {"id": "dev-1", "name": "Kitchen", "is_active": False},
                                {"id": "dev-2", "name": "Living room", "is_active": False},
                            ]
                        },
                    )
                return Response(204)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_source": "Living room",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        asyncio.run(backend.play("spotify:track:alive"))

        self.assertEqual(session.play_attempts, 2)
        transfer = next(call for call in session.calls if call["url"].endswith("/me/player"))
        self.assertEqual(transfer["json"], {"device_ids": ["dev-2"], "play": False})

    def test_devices_merges_recent_server_side_cache(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "devices": [
                        {"id": "dev-1", "name": "Kitchen", "type": "speaker"},
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        entry_updates = []
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        now = time.time()
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=now + 1800,
            backend_cache={},
            device_status={
                "spotify_device_cache": {
                    "devices": [
                        {
                            "id": "dev-2",
                            "name": "Living room",
                            "type": "speaker",
                            "last_seen_at": now - 60,
                        }
                    ]
                }
            },
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        hass = types.SimpleNamespace(
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda entry_arg, **kwargs: entry_updates.append(kwargs)
            )
        )
        backend = self.backend.SpotifyBackend(hass, runtime)
        backend.session = Session()

        devices = asyncio.run(backend.devices())

        self.assertEqual([device["name"] for device in devices], ["Kitchen", "Living room"])
        self.assertFalse(devices[0]["cached"])
        self.assertTrue(devices[1]["cached"])
        self.assertEqual(runtime.device_status["available_outputs"], devices)
        self.assertIn("spotify_device_cache", entry_updates[-1]["data"]["last_device_status"])

    def test_devices_drops_month_old_server_side_cache(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {"devices": []}

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        now = time.time()
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=now + 1800,
            backend_cache={},
            device_status={
                "spotify_device_cache": {
                    "devices": [
                        {
                            "id": "old-dev",
                            "name": "Old speaker",
                            "type": "speaker",
                            "last_seen_at": now - self.backend.SPOTIFY_DEVICE_CACHE_TTL_SECONDS - 1,
                        }
                    ]
                }
            },
            update=lambda **kwargs: setattr(runtime, "last_update", kwargs),
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        backend.session = Session()

        devices = asyncio.run(backend.devices())

        self.assertEqual(devices, [])
        self.assertEqual(runtime.device_status["available_outputs"], [])

    def test_invalid_grant_creates_reauth_issue_and_friendly_error(self) -> None:
        async def revoked(*args, **kwargs):
            raise self.oauth.SpotifyTokenRefreshError(
                400,
                {"error": "invalid_grant", "error_description": "Refresh token revoked"},
            )

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "secret-refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(entry=entry, latest_spotify_refresh_token=None)
        runtime.config = dict(entry.data)
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(object(), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = revoked
        try:
            with self.assertRaises(self.backend.SpotifyReauthRequiredError) as captured:
                asyncio.run(backend._access_token())
        finally:
            self.backend.refresh_access_token = original

        self.assertIn("Reauthorize DJConnect", str(captured.exception))
        self.assertEqual(runtime.last_update["last_error"], str(captured.exception))
        self.assertEqual(self.issues[0]["issue_id"], "spotify_refresh_token_revoked")
        self.assertEqual(self.issues[0]["translation_key"], "spotify_refresh_token_revoked")
        self.assertNotIn("secret-refresh", str(captured.exception))

    def test_repeated_invalid_grant_throttles_duplicate_reauth_issue(self) -> None:
        async def revoked(*args, **kwargs):
            raise self.oauth.SpotifyTokenRefreshError(
                400,
                {"error": "invalid_grant", "error_description": "Refresh token revoked"},
            )

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "secret-refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(entry=entry, latest_spotify_refresh_token=None)
        runtime.config = dict(entry.data)
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(types.SimpleNamespace(data={}), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = revoked
        try:
            with self.assertRaises(self.backend.SpotifyReauthRequiredError):
                asyncio.run(backend._access_token(force_refresh=True))
            with self.assertLogs(self.backend._LOGGER, level="DEBUG") as captured:
                with self.assertRaises(self.backend.SpotifyReauthRequiredError):
                    asyncio.run(backend._access_token(force_refresh=True))
        finally:
            self.backend.refresh_access_token = original

        self.assertEqual(
            [issue["issue_id"] for issue in self.issues],
            ["spotify_refresh_token_revoked"],
        )
        self.assertIn("suppressing duplicate", "\n".join(captured.output))

    def test_concurrent_access_token_refresh_uses_single_refresh_call(self) -> None:
        calls = []

        async def refresh(*args, **kwargs):
            calls.append(kwargs["refresh_token"])
            await asyncio.sleep(0)
            return {"access_token": "new-access", "expires_in": 3600}

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token=None,
            spotify_access_token_expires_at=0,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            async def run_concurrent():
                return await asyncio.gather(
                    backend._access_token(),
                    backend._access_token(),
                )

            tokens = asyncio.run(run_concurrent())
        finally:
            self.backend.refresh_access_token = original

        self.assertEqual(tokens, ["new-access", "new-access"])
        self.assertEqual(calls, ["refresh"])

    def test_invalid_grant_retries_when_refresh_token_rotated_during_refresh(self) -> None:
        calls = []

        async def refresh(*args, **kwargs):
            refresh_token = kwargs["refresh_token"]
            calls.append(refresh_token)
            if refresh_token == "old-refresh":
                runtime.latest_spotify_refresh_token = "new-refresh"
                raise self.oauth.SpotifyTokenRefreshError(
                    400,
                    {"error": "invalid_grant", "error_description": "Refresh token revoked"},
                )
            return {"access_token": "new-access", "expires_in": 3600}

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "old-refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token=None,
            spotify_access_token_expires_at=0,
        )
        runtime.config = dict(entry.data)
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(object(), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            token = asyncio.run(backend._access_token())
        finally:
            self.backend.refresh_access_token = original

        self.assertEqual(token, "new-access")
        self.assertEqual(calls, ["old-refresh", "new-refresh"])
        self.assertEqual(self.issues, [])
        self.assertFalse(hasattr(runtime, "last_update"))

    def test_invalid_grant_retries_entry_token_when_runtime_token_is_stale(self) -> None:
        calls = []

        async def refresh(*args, **kwargs):
            refresh_token = kwargs["refresh_token"]
            calls.append(refresh_token)
            if refresh_token == "old-runtime-refresh":
                raise self.oauth.SpotifyTokenRefreshError(
                    400,
                    {"error": "invalid_grant", "error_description": "Refresh token revoked"},
                )
            return {"access_token": "new-access", "expires_in": 3600}

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "new-entry-refresh",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token="old-runtime-refresh",
            spotify_access_token=None,
            spotify_access_token_expires_at=0,
        )
        runtime.config = dict(entry.data)
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(object(), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            with self.assertLogs(self.backend._LOGGER, level="DEBUG") as captured:
                token = asyncio.run(backend._access_token())
        finally:
            self.backend.refresh_access_token = original

        logs = "\n".join(captured.output)
        self.assertEqual(token, "new-access")
        self.assertEqual(calls, ["old-runtime-refresh", "new-entry-refresh"])
        self.assertEqual(self.issues, [])
        self.assertIn("source=entry", logs)
        self.assertNotIn("old-runtime-refresh", logs)
        self.assertNotIn("new-entry-refresh", logs)

    def test_invalid_grant_retries_entry_options_token_when_data_token_is_stale(self) -> None:
        calls = []

        async def refresh(*args, **kwargs):
            refresh_token = kwargs["refresh_token"]
            calls.append(refresh_token)
            if refresh_token in {"old-runtime-refresh", "old-data-refresh"}:
                raise self.oauth.SpotifyTokenRefreshError(
                    400,
                    {"error": "invalid_grant", "error_description": "Refresh token revoked"},
                )
            return {"access_token": "new-access", "expires_in": 3600}

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "old-data-refresh",
            },
            options={"spotify_refresh_token": "new-options-refresh"},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token="old-runtime-refresh",
            spotify_access_token=None,
            spotify_access_token_expires_at=0,
        )
        runtime.config = {**entry.data, **entry.options}
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(object(), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            with self.assertLogs(self.backend._LOGGER, level="DEBUG") as captured:
                token = asyncio.run(backend._access_token())
        finally:
            self.backend.refresh_access_token = original

        logs = "\n".join(captured.output)
        self.assertEqual(token, "new-access")
        self.assertEqual(calls, ["old-runtime-refresh", "old-data-refresh", "new-options-refresh"])
        self.assertEqual(self.issues, [])
        self.assertIn("source=entry_options", logs)
        self.assertNotIn("old-runtime-refresh", logs)
        self.assertNotIn("old-data-refresh", logs)
        self.assertNotIn("new-options-refresh", logs)

    def test_rotated_refresh_token_persists_even_when_runtime_already_updated(self) -> None:
        updates = []

        class ConfigEntries:
            def async_update_entry(self, entry, *, data):
                updates.append(data)
                entry.data = data

        async def refresh(*args, **kwargs):
            return {
                "access_token": "new-access",
                "expires_in": 3600,
                "refresh_token": "rotated-refresh",
            }

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "old-refresh"},
            options={},
        )

        class Runtime(types.SimpleNamespace):
            def update_spotify_refresh_token(self, token):
                self.latest_spotify_refresh_token = token
                return False

        runtime = Runtime(
            entry=entry,
            latest_spotify_refresh_token="rotated-refresh",
            spotify_access_token=None,
            spotify_access_token_expires_at=0,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(
            types.SimpleNamespace(config_entries=ConfigEntries()),
            runtime,
        )

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            with self.assertLogs(self.backend._LOGGER, level="DEBUG") as captured:
                token = asyncio.run(backend._access_token())
        finally:
            self.backend.refresh_access_token = original

        logs = "\n".join(captured.output)
        self.assertEqual(token, "new-access")
        self.assertEqual(updates[0]["spotify_refresh_token"], "rotated-refresh")
        self.assertEqual(entry.data["spotify_refresh_token"], "rotated-refresh")
        self.assertIn(
            {"domain": "djconnect", "issue_id": "spotify_refresh_token_revoked"},
            install_backend_stubs.deleted,
        )
        self.assertIn(
            {"domain": "djconnect", "issue_id": "entry-1_spotify_refresh_token_revoked"},
            install_backend_stubs.deleted,
        )
        self.assertIn("runtime_changed=False", logs)
        self.assertNotIn("rotated-refresh", logs)

    def test_access_token_cache_avoids_unnecessary_refresh(self) -> None:
        calls = []

        async def refresh(*args, **kwargs):
            calls.append(kwargs)
            return {"access_token": "new-access", "expires_in": 3600}

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="cached-access",
            spotify_access_token_expires_at=time.time() + 1800,
        )
        runtime.config = dict(entry.data)
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(object(), runtime)

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            token = asyncio.run(backend._access_token())
        finally:
            self.backend.refresh_access_token = original

        self.assertEqual(token, "cached-access")
        self.assertEqual(calls, [])

    def test_spotify_api_401_refreshes_access_token_once_without_repair(self) -> None:
        refreshes = []

        async def refresh(*args, **kwargs):
            refreshes.append(kwargs)
            return {"access_token": f"access-{len(refreshes)}", "expires_in": 3600}

        class Response:
            def __init__(self, status, payload):
                self.status = status
                self.payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if len(self.calls) == 1:
                    return Response(401, {"error": {"message": "The access token expired"}})
                return Response(
                    200,
                    {
                        "is_playing": True,
                        "item": {"name": "Song", "artists": [], "album": {}},
                        "device": {"name": "iPhone", "volume_percent": 30},
                    },
                )

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="expired-access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
        )
        runtime.config = dict(entry.data)
        runtime.update = lambda **kwargs: setattr(runtime, "last_update", kwargs)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        original = self.backend.refresh_access_token
        self.backend.refresh_access_token = refresh
        try:
            playback = asyncio.run(backend.playback_state())
        finally:
            self.backend.refresh_access_token = original

        self.assertTrue(playback["has_playback"])
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(len(refreshes), 1)
        self.assertEqual(session.calls[0]["headers"]["Authorization"], "Bearer expired-access")
        self.assertEqual(session.calls[1]["headers"]["Authorization"], "Bearer access-1")
        self.assertEqual(self.issues, [])

    def test_shuffle_and_repeat_commands_map_to_spotify_endpoints(self) -> None:
        class Response:
            def __init__(self, status, payload=None):
                self.status = status
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if method == "GET" and "/me/tracks/contains" in url:
                    return Response(200, [True])
                if method == "GET":
                    return Response(
                        200,
                        {
                            "is_playing": True,
                            "shuffle_state": True,
                            "repeat_state": "context",
                            "item": {"name": "Song", "uri": "spotify:track:saved-track", "artists": [], "album": {}},
                            "device": {"name": "iPhone", "volume_percent": 30},
                        },
                    )
                return Response(204)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        updates = []
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: updates.append(kwargs),
        )
        runtime.config = dict(entry.data)
        session = Session()

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: session
        try:
            shuffle = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "set_shuffle",
                    True,
                )
            )
            repeat = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "set_repeat",
                    "context",
                )
            )
            saved = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "save_current_track",
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        urls = [call["url"] for call in session.calls]
        self.assertIn(
            "https://api.spotify.com/v1/me/player/shuffle?state=true",
            urls,
        )
        self.assertIn(
            "https://api.spotify.com/v1/me/player/repeat?state=context",
            urls,
        )
        self.assertIn(
            "https://api.spotify.com/v1/me/tracks?ids=saved-track",
            urls,
        )
        self.assertIn(
            "https://api.spotify.com/v1/me/tracks/contains?ids=saved-track",
            urls,
        )
        self.assertTrue(shuffle["playback"]["shuffle"])
        self.assertEqual(repeat["playback"]["repeat_state"], "context")
        self.assertEqual(saved["playback"]["uri"], "spotify:track:saved-track")
        self.assertTrue(saved["playback"]["is_liked"])
        self.assertEqual(runtime.device_status["shuffle"], True)
        self.assertEqual(runtime.device_status["repeat_state"], "context")

    def test_queue_command_returns_context_and_album_art(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "queue": [
                        {
                            "name": "Next Song",
                            "uri": "spotify:track:next",
                            "duration_ms": 213000,
                            "artists": [{"name": "Artist"}, {"name": "Guest"}],
                            "album": {
                                "name": "Next Album",
                                "images": [
                                    {
                                        "url": "https://example.test/queue.jpg",
                                        "width": 300,
                                        "height": 300,
                                    }
                                ]
                            },
                        },
                        {
                            "name": "Episode One",
                            "uri": "spotify:episode:one",
                            "duration_ms": 1800000,
                            "show": {
                                "name": "Show Name",
                                "publisher": "Publisher Name",
                                "images": [
                                    {
                                        "url": "https://example.test/show.jpg",
                                        "width": 300,
                                        "height": 300,
                                    }
                                ],
                            },
                        },
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            last_playback={"context_uri": "spotify:playlist:abc"},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(object(), runtime, "queue")
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertTrue(result["success"])
        self.assertEqual(result["context_uri"], "spotify:playlist:abc")
        self.assertEqual(result["contextUri"], "spotify:playlist:abc")
        self.assertEqual(result["queue"][0]["album_image_url"], "https://example.test/queue.jpg")
        self.assertEqual(result["queue"][0]["imageUrl"], "https://example.test/queue.jpg")
        self.assertEqual(result["queue"][0]["context_uri"], "spotify:playlist:abc")
        self.assertEqual(result["queue"][0]["contextUri"], "spotify:playlist:abc")
        self.assertEqual(result["queue"][0]["id"], "spotify:track:next")
        self.assertEqual(result["queue"][0]["artist"], "Artist, Guest")
        self.assertEqual(result["queue"][0]["artist_name"], "Artist, Guest")
        self.assertEqual(result["queue"][0]["subtitle"], "Artist, Guest")
        self.assertEqual(result["queue"][0]["album"], "Next Album")
        self.assertEqual(result["queue"][0]["album_name"], "Next Album")
        self.assertEqual(result["queue"][0]["duration_ms"], 213000)
        self.assertEqual(result["queue"][1]["artist"], "Publisher Name")
        self.assertEqual(result["queue"][1]["artist_name"], "Publisher Name")
        self.assertEqual(result["queue"][1]["album"], "Show Name")
        self.assertEqual(result["queue"][1]["album_image_url"], "https://example.test/show.jpg")
        self.assertEqual(runtime.device_status["queue"]["items"], result["queue"])

    def test_queue_command_caps_client_items_at_100(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "queue": [
                        {
                            "name": f"Song {index}",
                            "uri": f"spotify:track:{index}",
                            "artists": [{"name": "Artist"}],
                            "album": {},
                        }
                        for index in range(105)
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            last_playback={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(object(), runtime, "queue")
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(len(result["queue"]), 100)
        self.assertEqual(result["queue"][-1]["title"], "Song 99")
        self.assertEqual(len(runtime.device_status["queue"]["items"]), 100)

    def test_queue_command_caps_at_100_real_backend_items(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                invalid_items = [
                    {},
                    {"name": "", "uri": ""},
                    {"album": {"images": []}},
                    None,
                    "not-a-track",
                ]
                valid_items = [
                    {
                        "name": f"Song {index}",
                        "uri": f"spotify:track:{index}",
                        "artists": [{"name": "Artist"}],
                        "album": {},
                    }
                    for index in range(105)
                ]
                return {"queue": [*invalid_items, *valid_items]}

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            last_playback={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(object(), runtime, "queue")
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(len(result["queue"]), 100)
        self.assertEqual(result["queue"][0]["title"], "Song 0")
        self.assertEqual(result["queue"][-1]["title"], "Song 99")
        self.assertEqual(len(runtime.device_status["queue"]["items"]), 100)

    def test_playlists_command_returns_playlist_art_aliases(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            def __init__(self, url):
                self.url = url

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                offset = 50 if "offset=50" in self.url else 0
                return {
                    "items": [
                        {
                            "id": "playlist-id",
                            "name": f"Default playlist {offset + index}",
                            "uri": f"spotify:playlist:{offset + index}",
                            "owner": {"display_name": "Peter"},
                            "images": [
                                {
                                    "url": "https://example.test/playlist-small.jpg",
                                    "width": 64,
                                    "height": 64,
                                },
                                {
                                    "url": "https://example.test/playlist-large.jpg",
                                    "width": 640,
                                    "height": 640,
                                },
                            ],
                        }
                        for index in range(50)
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response(url)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(object(), runtime, "playlists")
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        playlist = result["playlists"][0]
        self.assertTrue(result["backend_available"])
        self.assertEqual(result["items"], result["playlists"])
        self.assertEqual(result["data"]["playlists"], result["playlists"])
        self.assertEqual(result["data"]["items"], result["playlists"])
        self.assertEqual(result["result"]["playlists"], result["playlists"])
        self.assertEqual(result["result"]["items"], result["playlists"])
        self.assertEqual(result["count"], 100)
        self.assertEqual(len(result["playlists"]), 100)
        self.assertEqual(playlist["id"], "spotify:playlist:0")
        self.assertEqual(playlist["name"], "Default playlist 0")
        self.assertEqual(playlist["title"], "Default playlist 0")
        self.assertEqual(playlist["display_title"], "Default playlist 0")
        self.assertEqual(playlist["uri"], "spotify:playlist:0")
        self.assertEqual(playlist["value"], "spotify:playlist:0")
        self.assertEqual(playlist["playlist_uri"], "spotify:playlist:0")
        self.assertEqual(playlist["owner"], "Peter")
        self.assertEqual(playlist["subtitle"], "Peter")
        self.assertEqual(playlist["image_url"], "https://example.test/playlist-large.jpg")
        self.assertEqual(playlist["imageUrl"], "https://example.test/playlist-large.jpg")
        self.assertEqual(playlist["album_image_url"], "https://example.test/playlist-large.jpg")
        self.assertEqual(playlist["album_art_url"], "https://example.test/playlist-large.jpg")
        self.assertEqual(playlist["media_image_url"], "https://example.test/playlist-large.jpg")
        self.assertEqual(playlist["entity_picture"], "https://example.test/playlist-large.jpg")
        self.assertEqual(runtime.device_status["playlists"], result["playlists"])
        self.assertTrue(any("/me/playlists?limit=50&offset=0" in url for url in requested_urls))
        self.assertTrue(any("/me/playlists?limit=50&offset=50" in url for url in requested_urls))

    def test_search_playlists_command_returns_top_playlist_matches(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "playlists": {
                        "total": 2,
                        "items": [
                            {
                                "id": "above-1",
                                "name": "Above & Beyond Essentials",
                                "uri": "spotify:playlist:above-1",
                                "owner": {"display_name": "Spotify"},
                                "images": [{"url": "https://example.test/above.jpg", "width": 300, "height": 300}],
                            },
                            {
                                "id": "above-2",
                                "name": "Group Therapy",
                                "uri": "spotify:playlist:above-2",
                                "owner": {"display_name": "Anjunabeats"},
                                "images": [{"url": "https://example.test/group.jpg", "width": 300, "height": 300}],
                            },
                        ],
                    }
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "search_playlists",
                    {"query": "above & beyond", "limit": 5},
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertTrue(result["backend_available"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["playlists"][0]["uri"], "spotify:playlist:above-1")
        self.assertEqual(result["playlists"][0]["image_url"], "https://example.test/above.jpg")
        self.assertEqual(result["items"], result["playlists"])
        self.assertEqual(runtime.last_spotify_search["type"], "playlist")
        self.assertTrue(any("/search?" in url and "type=playlist" in url for url in requested_urls))
        self.assertTrue(any("limit=5" in url and "market=NL" in url for url in requested_urls))

    def test_search_tracks_command_returns_top_track_matches(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "tracks": {
                        "total": 2,
                        "items": [
                            {
                                "id": "grunge-1",
                                "name": "Grunge Track 1",
                                "uri": "spotify:track:grunge-1",
                                "artists": [{"name": "Artist 1"}],
                                "album": {
                                    "name": "Album 1",
                                    "uri": "spotify:album:grunge-1",
                                    "images": [{"url": "https://example.test/grunge-1.jpg", "width": 300, "height": 300}],
                                },
                            },
                            {
                                "id": "grunge-2",
                                "name": "Grunge Track 2",
                                "uri": "spotify:track:grunge-2",
                                "artists": [{"name": "Artist 2"}],
                                "album": {
                                    "name": "Album 2",
                                    "uri": "spotify:album:grunge-2",
                                    "images": [{"url": "https://example.test/grunge-2.jpg", "width": 300, "height": 300}],
                                },
                            },
                        ],
                    }
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "search_tracks",
                    {"query": "grunge", "limit": 10},
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertTrue(result["backend_available"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["tracks"][0]["uri"], "spotify:track:grunge-1")
        self.assertEqual(result["tracks"][0]["album_image_url"], "https://example.test/grunge-1.jpg")
        self.assertEqual(result["items"], result["tracks"])
        self.assertEqual(runtime.last_spotify_search["type"], "track")
        self.assertTrue(any("/search?" in url and "type=track" in url for url in requested_urls))
        self.assertTrue(any("limit=10" in url and "market=NL" in url for url in requested_urls))

    def test_artist_recommendations_support_artist_track_and_genre_seeds(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            def __init__(self, url):
                self.url = url

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                if "/search?" in self.url and "type=artist" in self.url:
                    return {
                        "artists": {
                            "items": [
                                {
                                    "id": "artist-id",
                                    "name": "Radiohead",
                                    "uri": "spotify:artist:artist-id",
                                }
                            ]
                        }
                    }
                if "/search?" in self.url and "type=track" in self.url:
                    return {
                        "tracks": {
                            "items": [
                                {
                                    "id": "track-id",
                                    "name": "Teardrop",
                                    "uri": "spotify:track:track-id",
                                    "artists": [{"name": "Massive Attack"}],
                                }
                            ]
                        }
                    }
                if "/recommendations?" in self.url:
                    return {
                        "tracks": [
                            {
                                "id": "rec-id",
                                "name": "Recommended",
                                "uri": "spotify:track:rec-id",
                                "artists": [{"name": "Artist"}],
                                "album": {
                                    "name": "Album",
                                    "images": [{"url": "https://example.test/rec.jpg", "width": 300, "height": 300}],
                                },
                            }
                        ]
                    }
                return {}

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response(url)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "artist_recommendations",
                    {
                        "artists": ["Radiohead"],
                        "tracks": ["Teardrop"],
                        "genres": ["ambient"],
                        "limit": 25,
                    },
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(result["tracks"][0]["uri"], "spotify:track:rec-id")
        recommendation_url = next(url for url in requested_urls if "/recommendations?" in url)
        self.assertIn("seed_artists=artist-id", recommendation_url)
        self.assertIn("seed_tracks=track-id", recommendation_url)
        self.assertIn("seed_genres=ambient", recommendation_url)

    def test_artist_recommendations_use_track_uri_seed_without_search(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            def __init__(self, url):
                self.url = url

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                if "/search?" in self.url:
                    raise AssertionError("track URI seed should not trigger Spotify search")
                if "/recommendations?" in self.url:
                    return {
                        "tracks": [
                            {
                                "id": "rec-id",
                                "name": "Recommended",
                                "uri": "spotify:track:rec-id",
                                "artists": [{"name": "Artist"}],
                                "album": {"name": "Album", "images": []},
                            }
                        ]
                    }
                return {}

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response(url)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                "spotify_client_id": "client-id",
                "spotify_refresh_token": "refresh",
                "spotify_market": "NL",
            },
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "artist_recommendations",
                    {"tracks": ["spotify:track:freed"], "limit": 25},
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(result["seed_tracks"][0]["uri"], "spotify:track:freed")
        recommendation_url = next(url for url in requested_urls if "/recommendations?" in url)
        self.assertIn("seed_tracks=freed", recommendation_url)

    def test_create_playlist_command_creates_private_playlist_and_adds_tracks(self) -> None:
        calls = []

        class Response:
            status = 200

            def __init__(self, payload=None):
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                calls.append({"method": method, "url": url, **kwargs})
                if method == "GET" and url.endswith("/me"):
                    return Response({"id": "user-id"})
                if method == "POST" and "/users/user-id/playlists" in url:
                    return Response(
                        {
                            "id": "playlist-id",
                            "name": "DJConnect mix",
                            "uri": "spotify:playlist:playlist-id",
                            "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist-id"},
                            "owner": {"display_name": "Peter"},
                        }
                    )
                return Response({})

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "create_playlist",
                    {
                        "name": "DJConnect mix",
                        "uris": ["spotify:track:one", "spotify:track:two"],
                    },
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(result["playlist"]["uri"], "spotify:playlist:playlist-id")
        self.assertEqual(calls[1]["json"]["public"], False)
        self.assertEqual(calls[2]["json"]["uris"], ["spotify:track:one", "spotify:track:two"])

    def test_playlists_command_respects_esp_limit(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "items": [
                        {
                            "name": f"Playlist {index}",
                            "uri": f"spotify:playlist:{index}",
                            "owner": {"display_name": "Peter"},
                            "images": [],
                        }
                        for index in range(30)
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "playlists",
                    {"client_type": "esp32", "limit": 20},
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(len(result["playlists"]), 20)
        self.assertEqual(result["items"], result["playlists"])
        self.assertEqual(result["data"]["playlists"], result["playlists"])
        self.assertEqual(result["data"]["items"], result["playlists"])
        self.assertEqual(result["result"]["playlists"], result["playlists"])
        self.assertEqual(result["result"]["items"], result["playlists"])
        self.assertEqual(result["count"], 20)
        self.assertTrue(any("/me/playlists?limit=20&offset=0" in url for url in requested_urls))

    def test_playlists_command_caps_esp_limit_at_20(self) -> None:
        requested_urls = []

        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {
                    "items": [
                        {
                            "name": f"Playlist {index}",
                            "uri": f"spotify:playlist:{index}",
                            "owner": {"display_name": "Peter"},
                            "images": [],
                        }
                        for index in range(100)
                    ]
                }

            async def text(self):
                return "{}"

        class Session:
            def request(self, method, url, **kwargs):
                requested_urls.append(url)
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            backend_cache={},
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: Session()
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "playlists",
                    {"client_type": "esp32", "limit": 100},
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertEqual(len(result["playlists"]), 20)
        self.assertTrue(any("/me/playlists?limit=20&offset=0" in url for url in requested_urls))

    def test_play_context_at_artist_context_plays_track_without_offset(self) -> None:
        class Response:
            status = 204

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {}

            async def text(self):
                return ""

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            last_playback={"context_uri": "spotify:artist:abc"},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        asyncio.run(
            backend.play_context_at(
                {
                    "context_uri": "spotify:artist:abc",
                    "offset_uri": "spotify:track:def",
                }
            )
        )

        self.assertEqual(
            session.calls[0]["json"],
            {"uris": ["spotify:track:def"]},
        )

    def test_play_context_at_without_context_plays_direct_uri(self) -> None:
        class Response:
            status = 204

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return {}

            async def text(self):
                return ""

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                return Response()

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            last_playback={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        backend = self.backend.SpotifyBackend(object(), runtime)
        session = Session()
        backend.session = session

        asyncio.run(backend.play_context_at({"uri": "spotify:episode:episode-1"}))

        self.assertEqual(
            session.calls[0]["json"],
            {"uris": ["spotify:episode:episode-1"]},
        )

    def test_seek_relative_uses_current_progress_and_clamps_to_duration(self) -> None:
        class Response:
            def __init__(self, status, payload=None):
                self.status = status
                self.payload = payload or {}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def json(self, content_type=None):
                return self.payload

            async def text(self):
                return str(self.payload)

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append({"method": method, "url": url, **kwargs})
                if method == "GET" and url.endswith("/me/player"):
                    return Response(
                        200,
                        {
                            "is_playing": True,
                            "progress_ms": 175000,
                            "item": {
                                "name": "Song",
                                "duration_ms": 180000,
                                "artists": [],
                                "album": {},
                            },
                            "device": {"name": "iPhone", "volume_percent": 30},
                        },
                    )
                return Response(204)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"spotify_client_id": "client-id", "spotify_refresh_token": "refresh"},
            options={},
        )
        runtime = types.SimpleNamespace(
            entry=entry,
            latest_spotify_refresh_token=None,
            spotify_access_token="access",
            spotify_access_token_expires_at=time.time() + 1800,
            device_status={},
            update=lambda **kwargs: None,
        )
        runtime.config = dict(entry.data)
        session = Session()

        original_clientsession = self.backend.async_get_clientsession
        self.backend.async_get_clientsession = lambda hass: session
        try:
            result = asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "seek_relative",
                    15000,
                )
            )
        finally:
            self.backend.async_get_clientsession = original_clientsession

        self.assertTrue(result["success"])
        self.assertEqual(
            session.calls[1]["url"],
            "https://api.spotify.com/v1/me/player/seek?position_ms=180000",
        )

    def test_set_play_mode_is_no_longer_supported(self) -> None:
        runtime = types.SimpleNamespace(config={})
        with self.assertRaises(ValueError):
            asyncio.run(
                self.backend.handle_spotify_command(
                    object(),
                    runtime,
                    "set_play_mode",
                    "shuffle",
                )
            )


if __name__ == "__main__":
    unittest.main()
