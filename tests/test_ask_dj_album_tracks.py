"""Reported album follow-up: real owner/routes/storage, external Spotify I/O fixtures."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from urllib.parse import urlsplit
from unittest.mock import patch
import json
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class AlbumTracksTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = shared.SharedDialogueTest()
        await self.f.asyncSetUp()
        from custom_components.djconnect.domain.backend import BackendProvider
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        self.storage = self.f.hass.data["djconnect"]["djconnect_profile_platform"]
        await self.storage.async_upsert_music_backend(
            "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Catalog fixture"
        )
        await self.storage.async_upsert_music_account(
            "album-account",
            "spotify_direct",
            kind=MusicAccountKind.PERSONAL,
            display_name="Catalog fixture",
            linked_profile_ids=frozenset({"profile-a"}),
        )
        await self.storage.async_update_profile(
            "profile-a",
            preferences=replace(
                self.storage.household.profiles["profile-a"].preferences,
                default_backend_id="spotify_direct",
                default_music_account_id="album-account",
            ),
        )
        self.f.runtime.config.update(
            music_backend="spotify_direct", music_account_id="album-account"
        )
        entry = SimpleNamespace(
            entry_id="owner-entry",
            data={**self.f.runtime.config, "device_token": self.f.runtime.device_token},
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.f.runtime.entry = entry
        entries = [
            e
            for e in self.f.hass.config_entries.async_entries("djconnect")
            if e.entry_id != "owner-entry"
        ] + [entry]
        self.f.hass.config_entries.async_entries = lambda domain: entries
        self.f.hass.config_entries.async_get_entry = lambda eid: next(
            (e for e in entries if e.entry_id == eid), None
        )
        self.f.runtime.update = lambda **fields: [
            setattr(self.f.runtime, k, v) for k, v in fields.items()
        ]
        self.calls = []
        self.album = {
            "id": "B" * 22,
            "uri": "spotify:album:" + "B" * 22,
            "name": "Beyond Hell/Above Heaven",
            "artists": [{"id": "A" * 22, "name": "Volbeat"}],
            "images": [{"url": "https://i.scdn.co/image/synthetic-exact-edition"}],
            "release_date": "2015",
            "release_date_precision": "year",
        }
        self.current_album = deepcopy(self.album)
        self.tracks = [
            {
                "id": char * 22,
                "uri": "spotify:track:" + char * 22,
                "name": title,
                "artists": deepcopy(self.album["artists"]),
                "album": deepcopy(self.album),
                "type": "track",
                "disc_number": 1,
                "track_number": i + 1,
                "duration_ms": 200000,
            }
            for i, (char, title) in enumerate(
                (("N", "Current recording"), ("Q", "Second recording"), ("R", "Third recording"))
            )
        ]
        self.provider_error = False
        self.changed = False
        self.total = 3
        self.after_catalog = None
        self.writes = []
        self.readback_album = False
        self.unconfirmed = False
        owner = self

        class Response:
            status = 200
            headers = {}

            def __init__(self, method, url, kwargs):
                self.method, self.path, self.query, self.kwargs = (
                    method,
                    urlsplit(url).path,
                    urlsplit(url).query,
                    kwargs,
                )
                self.status = 204 if method == "PUT" else 200

            async def read(self):
                return b""

            async def __aenter__(self):
                if self.method == "PUT":
                    owner.writes.append((self.path, deepcopy(self.kwargs.get("json"))))
                    owner.readback_album = True
                return self

            async def __aexit__(self, *args):
                return False

            async def json(self, **kwargs):
                owner.calls.append((self.method, self.path))
                if self.method == "PUT":
                    return {}
                assert self.method == "GET", "Unexpected provider mutation"
                if self.path == "/v1/me/player":
                    item = deepcopy(owner.tracks[0])
                    if not owner.readback_album:
                        item["album"] = deepcopy(owner.current_album)
                    if owner.changed:
                        item["album"]["uri"] = "spotify:album:" + "C" * 22
                        item["album"]["id"] = "C" * 22
                    return {
                        "item": item,
                        "context": {
                            "type": "album",
                            "uri": "spotify:album:"
                            + ("Z" if owner.unconfirmed or not owner.readback_album else "B") * 22,
                        },
                        "is_playing": True,
                        "progress_ms": 1000,
                        "device": {"id": "speaker", "name": "Speaker"},
                    }
                if self.path == "/v1/search":
                    from urllib.parse import parse_qs

                    typ = parse_qs(self.query)["type"][0]
                    if typ == "artist":
                        return {
                            "artists": {
                                "items": [
                                    {
                                        "id": "A" * 22,
                                        "uri": "spotify:artist:" + "A" * 22,
                                        "name": "Volbeat",
                                    }
                                ]
                            }
                        }
                    if typ == "album":
                        return {"albums": {"items": [deepcopy(owner.album)]}}
                    if typ == "track":
                        return {"tracks": {"items": [deepcopy(owner.tracks[0])]}}
                    raise AssertionError(typ)
                if self.path == "/v1/artists/" + "A" * 22 + "/albums":
                    return {"items": [dict(deepcopy(owner.album), total_tracks=3)]}
                if self.path == "/v1/me/player/devices":
                    return {
                        "devices": [
                            {
                                "id": "speaker",
                                "name": "Speaker",
                                "is_active": True,
                                "is_restricted": False,
                            }
                        ]
                    }
                if self.path == "/v1/me/player/queue":
                    return {
                        "currently_playing": deepcopy(owner.tracks[0]),
                        "queue": deepcopy(owner.tracks[1:]),
                    }
                if self.path == "/v1/artists/" + "A" * 22:
                    return {"id": "A" * 22, "genres": []}
                if self.path == "/v1/me/tracks/contains":
                    return [False]
                if self.path == "/v1/artists":
                    return {"artists": [{"id": "A" * 22, "genres": []}]}
                if self.path == "/v1/albums/" + "B" * 22:
                    return deepcopy(owner.album)
                if self.path == "/v1/albums/" + "B" * 22 + "/tracks":
                    if owner.provider_error:
                        raise ConnectionError("external catalog unavailable fixture")
                    if owner.after_catalog:
                        await owner.after_catalog()
                    return {
                        "items": deepcopy(owner.tracks),
                        "total": owner.total,
                        "next": "bounded-next" if owner.total > len(owner.tracks) else None,
                    }
                raise AssertionError("Unexpected provider path " + self.path)

            async def text(self):
                return json.dumps(await self.json())

        class Session:
            def request(self, method, url, **kwargs):
                return Response(method, url, kwargs)

        from custom_components.djconnect import spotify_backend

        async def token(*args, **kwargs):
            return "UNUSED_EXTERNAL_FIXTURE_TOKEN"

        self.session_patch = patch.object(
            spotify_backend, "async_get_clientsession", return_value=Session()
        )
        self.token_patch = patch.object(spotify_backend.SpotifyBackend, "_access_token", token)
        self.session_patch.start()
        self.token_patch.start()

    async def asyncTearDown(self):
        self.token_patch.stop()
        self.session_patch.stop()
        await self.f.asyncTearDown()

    async def test_current_album_other_tracks_in_five_languages_are_informational_and_not_promoted_to_model_or_archive(
        self,
    ):
        questions = {
            "nl": "Welke nummers staan er nog meer op dit album?",
            "en": "What other songs are on this album?",
            "de": "Welche anderen Lieder sind auf diesem Album?",
            "fr": "Quels autres morceaux sont sur cet album ?",
            "es": "¿Qué otras canciones hay en este álbum?",
        }
        for locale, question in questions.items():
            with self.subTest(locale=locale):
                answer, status = await self.f.request(
                    question, identifier="album-" + locale, language=locale
                )
                self.assertEqual(status, 200, answer)
                self.assertEqual(
                    [i["title"] for i in answer.get("items", [])[1:]],
                    ["Second recording", "Third recording"],
                )
                self.assertIn(self.album["name"], answer["text"])
                self.assertNotIn("Second recording", answer["text"])
                self.assertNotIn("Current recording", answer["text"])
                actions = answer['playback_actions']
                self.assertEqual(actions, answer['items'])
                self.assertEqual(actions, answer['result_set']['items'])
                self.assertEqual(actions[0]['kind'], 'album')
                self.assertEqual(actions[0]['context_uri'], self.album['uri'])
                self.assertEqual(actions[0]['button_label'], {
                    'en':'Play album','nl':'Speel album','de':'Album abspielen',
                    'fr':'Lire l’album','es':'Reproducir álbum'}[locale])
                self.assertTrue(all(a['action_id'] and a['button_label'] for a in actions))
                self.assertTrue(all(a['image_url'].startswith('/api/djconnect/v1/image_proxy/') for a in actions))
                self.assertEqual({a['image_url'] for a in actions}, {actions[0]['image_url']})
                self.assertNotIn('i.scdn.co', json.dumps(answer))
                layout = answer['result_set']['presentation']
                self.assertEqual(layout['primary_action_id'], actions[0]['action_id'])
                self.assertEqual(layout['track_action_ids'], [a['action_id'] for a in actions[1:]])
                self.assertEqual(answer['images'], [])
                self.assertEqual(answer["album_track_observation"]["state"], "complete")
                self.assertNotIn("assistant_message", answer)
                self.assertNotIn("user_message", answer)
        self.assertEqual(self.f.prompts, [])
        self.assertTrue(all(method == "GET" for method, _ in self.calls))
        self.assertEqual(len([p for _, p in self.calls if p.endswith("/tracks")]), 5)

    async def test_provider_failure_is_unknown_not_empty_and_does_not_start_playback(self):
        self.provider_error = True
        answer, status = await self.f.request("Welke nummers staan op dit album?", language="nl")
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["album_track_observation"]["state"], "unavailable")
        self.assertEqual(answer.get("items", []), [])
        self.assertEqual(answer.get("playback_actions", []), [])
        self.assertEqual(self.f.prompts, [])

    async def test_album_change_during_catalog_lookup_never_delivers_the_other_edition(self):
        async def change():
            self.changed = True

        self.after_catalog = change
        answer, status = await self.f.request("What songs are on this album?")
        self.assertEqual(status, 409, answer)
        self.assertEqual(answer["error"], "playback_context_changed")
        self.assertNotIn("Second recording", answer.get("text", ""))

    async def test_large_album_is_explicitly_partial_and_has_no_per_track_fetch(self):
        self.total = 200
        answer, status = await self.f.request("What other songs are on this album?")
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["album_track_observation"]["state"], "partial")
        self.assertEqual(len([p for _, p in self.calls if p.endswith("/tracks")]), 1)
        self.assertFalse(any("/search" in p or "/v1/tracks/" in p for _, p in self.calls))
        self.assertEqual(self.f.prompts, [])

    async def test_other_album_offer_followup_starts_full_album_context_without_new_search(self):
        self.current_album.update(uri="spotify:album:" + "Z" * 22, id="Z" * 22)
        answer, status = await self.f.request(
            "Heb je een ander album van Volbeat?", identifier="other-album", language="nl"
        )
        self.assertEqual(status, 200, answer)
        actions = answer.get("playback_actions", [])
        self.assertEqual(len(actions), 1, answer)
        action = actions[0]
        self.assertEqual(action["kind"], "album")
        self.assertEqual(action["uri"], self.album["uri"])
        self.assertEqual(action["context_uri"], self.album["uri"])
        self.assertTrue(action["action_id"])
        self.assertEqual(self.writes, [])
        self.assertEqual(self.f.prompts, [])
        before = len([p for _, p in self.calls if p == "/v1/search"])
        reply, status = await self.f.request(
            "Ja, die wil ik afspelen.", identifier="play-other-album", language="nl"
        )
        self.assertEqual(status, 200, reply)
        self.assertTrue(reply.get("success"), reply)
        self.assertEqual(
            self.writes, [("/v1/me/player/play", {"context_uri": self.album["uri"]})], reply
        )
        self.assertEqual(len([p for _, p in self.calls if p == "/v1/search"]), before)
        self.assertIn(self.album["name"], reply["text"])
        retry, status = await self.f.request(
            "Ja, die wil ik afspelen.", identifier="play-other-album", language="nl"
        )
        self.assertEqual(status, 200, retry)
        self.assertEqual(len(self.writes), 1)

    async def test_explicit_album_request_dispatches_context_not_one_recording(self):
        answer, status = await self.f.request(
            "Speel het album Beyond Hell/Above Heaven van Volbeat af.",
            identifier="explicit-album",
            language="nl",
        )
        self.assertEqual(status, 200, answer)
        self.assertEqual(
            self.writes, [("/v1/me/player/play", {"context_uri": self.album["uri"]})], answer
        )
        self.assertIn(self.album["name"], answer["text"])

    async def test_named_album_followup_keeps_album_kind_even_without_word_album(self):
        self.current_album.update(uri="spotify:album:" + "Z" * 22, id="Z" * 22)
        offer, status = await self.f.request(
            "Heb je een ander album van Volbeat?", identifier="named-offer", language="nl"
        )
        self.assertEqual(status, 200, offer)
        before = len([p for _, p in self.calls if p == "/v1/search"])
        answer, status = await self.f.request(
            "Speel Beyond Hell Above Heaven van Volbeat af", identifier="named-play", language="nl"
        )
        self.assertEqual(status, 200, answer)
        self.assertEqual(
            self.writes, [("/v1/me/player/play", {"context_uri": self.album["uri"]})], answer
        )
        self.assertEqual(len([p for _, p in self.calls if p == "/v1/search"]), before)

    async def test_five_language_other_album_and_explicit_confirmation_grammar(self):
        from custom_components.djconnect.ask_dj.album_choices import other_album_request
        from custom_components.djconnect.ask_dj import classify_ask_dj
        from custom_components.djconnect.ask_dj.dialogue import explicit_play, play_selected

        for question, reply in (
            ("Heb je een ander album van Volbeat?", "Ja, die wil ik afspelen."),
            ("Do you have another album by Volbeat?", "Yes, I want to play that."),
            ("Hast du ein anderes Album von Volbeat?", "Das möchte ich abspielen."),
            ("As-tu un autre album de Volbeat ?", "Oui, je veux écouter cet album."),
            ("¿Tienes otro álbum de Volbeat?", "Sí, quiero escuchar ese álbum."),
        ):
            self.assertEqual(other_album_request(question)["artist"], "Volbeat")
            self.assertTrue(explicit_play(reply), reply)
            self.assertTrue(play_selected(reply), reply)
            self.assertEqual(classify_ask_dj(reply).action, "play_music")
        for value in (
            "Ja",
            "Ja, maar niet afspelen",
            "Die wil ik niet afspelen",
            "Als ik die wil afspelen",
            '"Ja, die wil ik afspelen"',
            "Yes, I do not want to play that",
        ):
            self.assertFalse(explicit_play(value), value)

    async def test_confirmation_without_catalog_offer_cannot_start_any_music(self):
        answer, status = await self.f.request(
            "Ja, die wil ik afspelen.", identifier="no-offer", language="nl"
        )
        self.assertEqual(status, 200, answer)
        self.assertEqual(self.writes, [])
        self.assertEqual(answer["intent"]["intent"], "clarification_needed")
        self.assertEqual(self.f.prompts, [])

    async def test_catalogue_read_preserves_original_expiry_across_await(self):
        from datetime import UTC, datetime, timedelta
        from custom_components.djconnect.ask_dj import album_tracks

        started = datetime.now(UTC)

        class Clock(datetime):
            @classmethod
            def now(cls, zone):
                return started

        async def source(hass, runtime, command, value=None, **kwargs):
            if command == "status":
                return {
                    "success": True,
                    "playback": {
                        "uri": self.tracks[0]["uri"],
                        "album_uri": self.album["uri"],
                        "title": "Current recording",
                        "artist": "Volbeat",
                        "expires_at": (started + timedelta(seconds=1)).isoformat(),
                    },
                }
            self.f.history.dialogue.clock = lambda: 1002.0
            return {
                "success": True,
                "state": "complete",
                "items": [],
                "album_uri": self.album["uri"],
                "album_name": self.album["name"],
            }

        self.f.history.dialogue.clock = lambda: 1000.0
        with (
            patch.object(self.f.core, "run_music_command", source),
            patch.object(album_tracks, "datetime", Clock),
        ):
            answer, status = await self.f.request(
                "What other songs are on this album?", identifier="expiry-during-fetch"
            )
        self.assertEqual(status, 409, answer)
        self.assertEqual(answer["error"], "playback_observation_expired")

    async def test_catalogue_unknown_stale_and_empty_are_distinct(self):
        async def stale(hass, runtime, command, value=None, **kwargs):
            self.assertEqual(command, "status")
            return {
                "success": True,
                "playback": {
                    "uri": self.tracks[0]["uri"],
                    "album_uri": self.album["uri"],
                    "title": "Current recording",
                    "artist": "Volbeat",
                    "stale": True,
                },
            }

        with patch.object(self.f.core, "run_music_command", stale):
            answer, status = await self.f.request(
                "What songs are on this album?", identifier="stale-album"
            )
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["album_track_observation"]["state"], "unknown")
        self.tracks = self.tracks[:1]
        self.total = 1
        answer, status = await self.f.request(
            "What other songs are on this album?", identifier="single-track-album"
        )
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["album_track_observation"]["state"], "known_empty")
        self.assertEqual([a['kind'] for a in answer['items']], ['album'])
        self.assertEqual(answer['album_track_observation']['returned_count'], 0)

    async def test_album_header_play_starts_whole_context_and_duplicate_does_not_dispatch_again(self):
        offer, code = await self.f.request('What songs are on this album?', identifier='album-header')
        self.assertEqual(code, 200, offer)
        action = offer['items'][0]
        choice = {k:action[k] for k in ('result_set_id','action_id')}
        choice['operation'] = 'play'
        result, code = await self.f.request('Play', identifier='album-header-play', choice_action=choice)
        self.assertEqual(code, 200, result)
        self.assertEqual(self.writes, [('/v1/me/player/play', {'context_uri':self.album['uri']})])
        await self.f.request('Play', identifier='album-header-play', choice_action=choice)
        self.assertEqual(len(self.writes), 1)
        self.assertFalse(any('/search' in path for _, path in self.calls))

    async def test_nirvana_fourteen_track_album_has_one_header_and_no_repeated_bullets(self):
        # Reproduce the owner's displayed titles as external catalog fixtures,
        # without claiming live Spotify identity or native rendering proof.
        names = ('About A Girl', 'Come As You Are', "Jesus Doesn't Want Me For A Sunbeam",
            'The Man Who Sold The World', 'Pennyroyal Tea', 'Dumb', 'Polly', 'On A Plain',
            'Something In The Way', 'Plateau', 'Oh Me', 'Lake Of Fire', 'All Apologies',
            'Where Did You Sleep Last Night')
        self.album.update(name='MTV Unplugged In New York',
            artists=[{'id':'A'*22,'name':'Nirvana'}])
        self.current_album = deepcopy(self.album)
        prototype = deepcopy(self.tracks[0])
        self.tracks = [{**deepcopy(prototype), 'id':f'{i:022d}',
            'uri':'spotify:track:'+f'{i:022d}', 'name':name+' - Live',
            'artists':deepcopy(self.album['artists']), 'album':deepcopy(self.album),
            'track_number':i+1} for i,name in enumerate(names)]
        self.total = 14
        answer, code = await self.f.request('Welke nummers staan er op dit album?',
            identifier='reported-nirvana-album', language='nl')
        self.assertEqual(code, 200, answer)
        self.assertEqual(answer['items'][0]['title'], self.album['name'])
        self.assertEqual(answer['items'][0]['artist'], 'Nirvana')
        self.assertEqual(answer['items'][0]['button_label'], 'Speel album')
        self.assertEqual([a['title'] for a in answer['items'][1:]], [name+' - Live' for name in names])
        self.assertEqual(answer['items'], answer['playback_actions'])
        self.assertEqual(len(answer['result_set']['presentation']['track_action_ids']), 14)
        self.assertTrue(all(a['image_url'] and a['action_id'] and a['button_label'] for a in answer['items']))
        self.assertNotIn('•', answer['text'])
        self.assertNotIn('About A Girl', answer['text'])
        self.assertNotIn('_album_track_choices', answer)
        self.assertEqual(self.writes, [])
        self.assertEqual(self.f.prompts, [])

    async def test_fifty_track_actions_survive_frozen_choices_and_last_button_plays_exact_track(self):
        prototype = deepcopy(self.tracks[0])
        self.tracks = [{**deepcopy(prototype), 'id':f'{i:022d}',
            'uri':'spotify:track:'+f'{i:022d}', 'name':f'Album recording {i+1}',
            'track_number':i+1} for i in range(50)]
        self.total = 50
        offer, code = await self.f.request('What songs are on this album?', identifier='fifty-tracks')
        self.assertEqual(code, 200, offer)
        self.assertEqual(len(offer['items']), 51)
        self.assertEqual(offer['items'], offer['result_set']['items'])
        self.assertEqual(len({a['action_id'] for a in offer['items']}), 51)
        self.assertEqual(offer['album_track_observation']['returned_count'], 50)
        self.assertEqual(self.writes, [])
        before = len(self.calls)
        duplicate, code = await self.f.request('What songs are on this album?', identifier='fifty-tracks')
        self.assertEqual(code, 200, duplicate)
        self.assertEqual(duplicate['result_set'], offer['result_set'])
        self.assertEqual(len(self.calls), before)
        shown, code = await self.f.request('Show the results', identifier='show-fifty')
        self.assertEqual(code, 200, shown)
        self.assertEqual(shown['result_set']['presentation'], offer['result_set']['presentation'])
        self.assertNotIn('Album recording 50', shown['text'])
        last = offer['items'][-1]
        result, code = await self.f.request('Play', identifier='last-track-play', choice_action={
            'result_set_id':last['result_set_id'], 'action_id':last['action_id'], 'operation':'play'})
        self.assertEqual(code, 200, result)
        self.assertEqual(self.writes, [('/v1/me/player/play', {'uris':[self.tracks[-1]['uri']]})])

    async def test_album_buttons_expire_without_play_or_catalog_retry(self):
        offer, code = await self.f.request('What songs are on this album?', identifier='expiring-album')
        self.assertEqual(code, 200, offer)
        self.assertGreater(offer['result_set']['expires_in'], 590)
        clock = self.f.history.dialogue.clock
        started = clock()
        self.f.history.dialogue.clock = lambda: started + 601
        action = offer['items'][0]
        before = len(self.calls)
        result, code = await self.f.request('Play', identifier='expired-album-play', choice_action={
            'result_set_id':action['result_set_id'], 'action_id':action['action_id'], 'operation':'play'})
        self.assertEqual(code, 409, result)
        self.assertEqual(self.writes, [])
        self.assertEqual(len(self.calls), before)

    def test_explicit_media_kind_wins_over_equal_named_frozen_offer(self):
        from custom_components.djconnect.ask_dj.dialogue import offered_media_index, DialogueError

        album = {"kind": "album", "title": "Hello", "artist": "Adele"}
        track = {**album, "kind": "track"}
        self.assertIsNone(offered_media_index("Speel het nummer Hello van Adele af", [album]))
        self.assertIsNone(offered_media_index("Speel het album Hello van Adele af", [track]))
        self.assertEqual(offered_media_index("Speel Hello van Adele af", [album]), 0)
        self.assertEqual(
            offered_media_index("Speel het album Hello van Adele af", [album, track]), 0
        )
        self.assertEqual(
            offered_media_index("Speel het nummer Hello van Adele af", [album, track]), 1
        )
        with self.assertRaises(DialogueError):
            offered_media_index("Speel Hello van Adele af", [album, dict(album)])

    async def test_selected_historical_recording_is_not_replaced_by_current_album(self):
        session = await self.f.fixture.observed_session()
        from custom_components.djconnect.session_conversation import query_service

        page = await query_service(self.f.hass, self.f.history).async_timeline_page(
            "profile-a", session.session_id
        )
        observed = next(e for e in page["entries"] if e["kind"] == "playback_observed")
        context = {
            "session_id": session.session_id,
            "selected_entry": {"session_id": session.session_id, "entry_id": observed["entry_id"]},
        }
        asked = []

        async def source(hass, runtime, command, value=None, **kwargs):
            asked.append((command, value))
            self.assertEqual(command, "album_tracks")
            self.assertEqual(value["track_uri"], "spotify:track:0123456789abcdefghijkL")
            return {
                "success": True,
                "state": "complete",
                "items": [
                    {
                        "title": "Historical track",
                        "uri": "spotify:track:" + "H" * 22,
                        "artist": "Metallica",
                    }
                ],
                "album_uri": "spotify:album:" + "H" * 22,
                "album_name": "Historical exact edition",
            }

        with patch.object(self.f.core, "run_music_command", source):
            answer, status = await self.f.request(
                "Welke nummers staan er nog meer op dit album?",
                identifier="historical-album",
                context=context,
                language="nl",
            )
        self.assertEqual(status, 200, answer)
        self.assertIn("Historical exact edition", answer["text"])
        self.assertNotIn(self.album["name"], answer["text"])
        self.assertEqual(len(asked), 1)
        self.assertEqual([a['kind'] for a in answer['items']], ['album','track'])
        self.assertTrue(all(a['action_id'] for a in answer['items']))

    async def test_unconfirmed_album_reply_names_request_without_borrowing_current_recording(self):
        self.current_album.update(
            uri="spotify:album:" + "Z" * 22, id="Z" * 22, name="Unrelated old album"
        )
        self.unconfirmed = True
        offer, code = await self.f.request(
            "Heb je een ander album van Volbeat?", identifier="unconfirmed-offer", language="nl"
        )
        self.assertEqual(code, 200, offer)
        result, code = await self.f.request(
            "Ja, die wil ik afspelen.", identifier="unconfirmed-album", language="nl"
        )
        self.assertEqual(code, 200, result)
        self.assertEqual(self.writes, [("/v1/me/player/play", {"context_uri": self.album["uri"]})])
        self.assertIn(self.album["name"], result["text"])
        self.assertNotIn("Unrelated old album", result["text"])
        self.assertNotIn("Current recording", result["text"])
        self.assertIn("nog niet bevestigd", result["text"])
        self.assertFalse(result["action_outcome"]["readback_confirmed"])

    async def test_other_album_action_copy_matches_real_five_language_responses(self):
        self.current_album.update(uri="spotify:album:" + "Z" * 22, id="Z" * 22)
        for i, (locale, question, label, reason) in enumerate(
            (
                ("nl", "Heb je een ander album van Volbeat?", "Afspelen", "Album van Volbeat."),
                ("en", "Do you have another album by Volbeat?", "Play", "Album by Volbeat."),
                ("de", "Hast du ein anderes Album von Volbeat?", "Abspielen", "Album von Volbeat."),
                ("fr", "As-tu un autre album de Volbeat ?", "Lire", "Album de Volbeat."),
                ("es", "¿Tienes otro álbum de Volbeat?", "Reproducir", "Álbum de Volbeat."),
            )
        ):
            answer, code = await self.f.request(
                question, identifier="localized-album-offer-" + str(i), language=locale
            )
            self.assertEqual(code, 200, answer)
            action = answer["playback_actions"][0]
            self.assertEqual(
                (action["label"], action["button_label"], action["reason"]), (label, label, reason)
            )
            self.assertEqual(action["context_uri"], self.album["uri"])
            self.assertEqual(action["kind"], "album")
        self.assertEqual(self.writes, [])
        self.assertEqual(self.f.prompts, [])

    async def test_album_containment_does_not_capture_similar_or_inspiration_questions(self):
        for i, question in enumerate(
            (
                "What songs are similar to this album?",
                "Welke nummers lijken op dit album?",
                "What songs inspired this album?",
                "Quels morceaux ressemblent à cet album ?",
                "Welche Lieder sind ähnlich wie dieses Album?",
                "¿Qué canciones inspiraron este álbum?",
            )
        ):
            answer, code = await self.f.request(
                question, identifier="not-album-containment-" + str(i)
            )
            self.assertEqual(code, 200, answer)
            self.assertNotEqual(
                (answer.get("intent") or {}).get("intent"), "album_tracks_information", question
            )
        self.assertFalse(
            any(path.endswith("/tracks") and "/albums/" in path for _, path in self.calls)
        )
        self.assertEqual(self.writes, [])
