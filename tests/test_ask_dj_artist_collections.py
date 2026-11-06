"""Reported HAEVN collection question: real owner/route, synthetic provider I/O."""

from copy import deepcopy
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
import json
import unittest

from tests import test_ask_dj_album_tracks as base


class ArtistCollectionsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        base.AlbumTracksTests.setUpClass()
        import aiohttp

        aiohttp.ClientError = getattr(aiohttp, "ClientError", type("ClientError", (Exception,), {}))

    @classmethod
    def tearDownClass(cls):
        base.AlbumTracksTests.tearDownClass()

    async def asyncSetUp(self):
        self.base = base.AlbumTracksTests()
        await self.base.asyncSetUp()
        self.f = self.base.f
        self.artist = {"id": "H" * 22, "uri": "spotify:artist:" + "H" * 22, "name": "HAEVN"}
        self.plan = {
            "read": "artist_collections",
            "reference": "named",
            "exclude_current": False,
            "artist": "HAEVN",
        }
        self.calls = []
        self.deny_playlists = False
        self.deny_albums = False
        self.fail_artist = False
        self.foreign_albums = False
        self.playlists_uncredited = False
        self.album_count = 6
        self.after_read = None

        async def provider(backend, method, path, **kwargs):
            self.calls.append((method, path))
            self.assertEqual(method, "GET", "A catalogue question must never write")
            parsed = urlsplit(path)
            query = parse_qs(parsed.query)
            if parsed.path == "/search":
                if query.get("type") == ["artist"]:
                    if self.fail_artist:
                        from custom_components.djconnect.spotify_backend import SpotifyBackendError

                        raise SpotifyBackendError(
                            "Synthetic named identity outage", http_status=404
                        )
                    return {"artists": {"items": [deepcopy(self.artist)]}}
                if query.get("type") == ["playlist"]:
                    if self.deny_playlists:
                        from custom_components.djconnect.spotify_backend import SpotifyBackendError

                        raise SpotifyBackendError("Synthetic inaccessible section", http_status=403)
                    return {
                        "playlists": {
                            "items": [
                                {
                                    "id": chr(65 + i) * 22,
                                    "uri": "spotify:playlist:" + chr(65 + i) * 22,
                                    "name": "HAEVN fixture playlist " + str(i),
                                    "owner": {
                                        "id": "fixture-owner",
                                        "display_name": "Fixture owner",
                                    },
                                    "images": [],
                                }
                                for i in range(6)
                            ]
                        }
                    }
            if parsed.path == "/artists/" + "H" * 22 + "/albums":
                if self.after_read:
                    await self.after_read()
                if self.deny_albums:
                    from custom_components.djconnect.spotify_backend import SpotifyBackendError

                    raise SpotifyBackendError("Synthetic album section outage", http_status=403)
                credited = (
                    {"id": "X" * 22, "name": "Different performer"}
                    if self.foreign_albums
                    else self.artist
                )
                return {
                    "items": [
                        {
                            "id": str(i) * 22,
                            "uri": "spotify:album:" + str(i) * 22,
                            "name": "HAEVN fixture album " + str(i),
                            "artists": [deepcopy(credited)],
                            "images": [],
                            "album_type": "album",
                        }
                        for i in range(self.album_count)
                    ]
                }
            if parsed.path.startswith("/playlists/") and parsed.path.endswith("/items"):
                return {
                    "items": [
                        {
                            "item": {
                                "type": "track",
                                "is_local": False,
                                "artists": [{"id": "X" * 22}]
                                if self.playlists_uncredited
                                else [deepcopy(self.artist)],
                            }
                        }
                    ]
                }
            raise AssertionError("Unexpected catalogue provider read " + path)

        async def agent(hass, data, **kwargs):
            self.f.prompts.append(json.loads(data["text"].split("\nData:\n", 1)[1]))
            return {"response": {"speech": {"plain": {"speech": json.dumps(self.plan)}}}}

        from custom_components.djconnect import spotify_backend

        self.provider = patch.object(spotify_backend.SpotifyBackend, "_request", provider)
        self.agent = patch.object(self.f.pipeline, "_call_conversation_process_transport", agent)
        self.provider.start()
        self.agent.start()

    async def asyncTearDown(self):
        self.agent.stop()
        self.provider.stop()
        await self.base.asyncTearDown()

    async def test_reported_haevn_question_offers_five_albums_and_five_playlists_without_playing(
        self,
    ):
        answer, code = await self.f.request("Heb je iets van de artiest haevn", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertEqual([i["kind"] for i in answer.get("items", [])].count("album"), 5)
        self.assertEqual([i["kind"] for i in answer.get("items", [])].count("playlist"), 5)
        self.assertTrue(all(i.get("action_id") for i in answer["items"]))
        self.assertEqual(len(self.f.prompts), 1)
        self.assertFalse(self.f.effects)
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    async def test_partial_catalogue_is_honest_and_keeps_available_albums(self):
        self.deny_playlists = True
        self.album_count = 2
        answer, code = await self.f.request("Have you got something by HAEVN?", language="en")
        self.assertEqual(code, 200, answer)
        self.assertEqual(len(answer.get("items", [])), 2)
        self.assertEqual({i["kind"] for i in answer["items"]}, {"album"})
        self.assertIn("2 albums", answer["text"])
        self.assertIn("0 playlists", answer["text"])
        self.assertFalse(self.f.effects)

    async def test_named_collection_plan_rejects_extra_uri_and_private_subject(self):
        from custom_components.djconnect.ask_dj.semantic_reads import parse_plan

        self.assertIsNotNone(parse_plan(json.dumps(self.plan)))
        for value in (
            {**self.plan, "uri": "spotify:album:" + "A" * 22},
            {**self.plan, "artist": "my wife Anja"},
            {**self.plan, "exclude_current": True},
        ):
            self.assertIsNone(parse_plan(json.dumps(value)))

    async def test_inaccessible_albums_keep_verified_playlist_rows(self):
        self.deny_albums = True
        answer, code = await self.f.request("Do you have anything by HAEVN?", language="en")
        self.assertEqual(code, 200, answer)
        self.assertEqual([i["kind"] for i in answer["items"]], ["playlist"] * 5)
        self.assertIn("0 albums", answer["text"])
        self.assertFalse(self.f.effects)

    async def test_named_lookup_outage_never_uses_current_volbeat_artist(self):
        self.fail_artist = True
        answer, code = await self.f.request("Heb je iets van de artiest haevn", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertTrue(answer["success"])
        self.assertFalse(answer.get("items"))
        self.assertNotIn("Volbeat", answer["text"])
        self.assertFalse(self.f.effects)
        self.assertTrue(all("/search?" in path for _, path in self.calls))

    async def test_foreign_credits_are_not_filled_with_invented_rows(self):
        self.foreign_albums = self.playlists_uncredited = True
        answer, code = await self.f.request("Have you got something by HAEVN?", language="en")
        self.assertEqual(code, 200, answer)
        self.assertFalse(answer.get("items"))
        self.assertFalse(answer.get("playback_actions"))
        self.assertLessEqual(len(self.calls), 13)
        self.assertFalse(self.f.effects)

    async def test_full_supported_copy_and_exact_reported_nl_en_wording(self):
        questions = {
            "nl": "Heb je iets van de artiest haevn",
            "en": "Have you got something by HAEVN?",
            "de": "Hast du etwas von HAEVN?",
            "fr": "Tu as quelque chose de HAEVN ?",
            "es": "¿Tienes algo de HAEVN?",
        }
        for language, question in questions.items():
            with self.subTest(language=language):
                answer, code = await self.f.request(
                    question, language=language, identifier="collections-" + language
                )
                self.assertEqual(code, 200, answer)
                self.assertEqual(len(answer["items"]), 10)
                self.assertFalse(self.f.effects)

    async def test_profile_changes_during_catalogue_read_withdraw_offer(self):
        from dataclasses import replace

        async def withdraw():
            storage = self.base.storage
            profile = storage.household.profiles["profile-a"]
            await storage.async_update_profile(
                "profile-a",
                preferences=replace(
                    profile.preferences, default_backend_id="later_manual", default_music_account_id=None
                ),
            )

        self.after_read = withdraw
        answer, code = await self.f.request("Heb je iets van de artiest haevn", language="nl")
        self.assertEqual(code, 409, answer)
        self.assertFalse(answer.get("items"))
        self.assertFalse(self.f.effects)

    async def test_private_catalogue_root_projection_does_not_impersonate_stored_history(self):
        answer, code = await self.f.request(
            "Heb je iets van de artiest HAEVN?", language="nl", identifier="private-catalogue-wire"
        )
        self.assertEqual(code, 200, answer)
        self.assertTrue(answer["success"])
        self.assertFalse(answer["history_persisted"])
        self.assertEqual(answer["conversation"]["history_scope"], "private_ephemeral")
        self.assertEqual(answer["conversation"]["entry_ids"], [])
        self.assertTrue(answer["conversation"]["turn_id"])
        self.assertTrue(answer["owner_profile_id"])
        self.assertEqual(answer["client_message_id"], "private-catalogue-wire")
        for key in ("assistant_message", "user_message", "messages", "history_revision", "clear_revision"):
            self.assertNotIn(key, answer, "Nonstored replies cannot impersonate canonical history rows")
        self.assertTrue(answer["text"])
        self.assertEqual(len(answer["items"]), 10)
        self.assertEqual(len(answer["playback_actions"]), 10)
        self.assertTrue(answer["result_set"]["result_set_id"])
        self.assertTrue(all(row.get("action_id") for row in answer["playback_actions"]))
        self.assertFalse(self.f.effects)
