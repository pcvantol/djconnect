"""Named-artist questions use Core owners and explicit external I/O fixtures."""

import json
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
import unittest

from tests import test_ask_dj_album_tracks as albums


class ArtistHitsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        albums.AlbumTracksTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        albums.AlbumTracksTests.tearDownClass()

    async def asyncSetUp(self):
        self.base = albums.AlbumTracksTests()
        await self.base.asyncSetUp()
        self.f = self.base.f
        self.calls = []
        self.fail_catalog = False
        self.after_catalog = None
        self.playback_index = 0
        self.fail_status = False
        self.artist = {"id": "A" * 22, "uri": "spotify:artist:" + "A" * 22,
                       "name": "Armin van Buuren"}
        self.tracks = [dict(deepcopy(t), name=title, artists=[self.artist])
                       for t, title in zip(self.base.tracks,
                           ("Current recording", "This Is What It Feels Like", "Blah Blah Blah"), strict=True)]
        self.foreign = dict(deepcopy(self.tracks[1]), id="X" * 22,
                            uri="spotify:track:" + "X" * 22, name="Patience",
                            artists=[{"id": "Z" * 22, "name": "Guns N' Roses"}])
        self.plan = {"read": "artist_tracks", "reference": "named",
                     "artist": "Armin van Buuren", "exclude_current": True}
        from custom_components.djconnect import spotify_backend
        async def provider(backend, method, path, **kwargs):
            self.calls.append((method, path))
            if method != "GET":
                raise AssertionError("An informational question must never mutate playback")
            parsed = urlsplit(path)
            if parsed.path == "/search":
                typ = parse_qs(parsed.query)["type"][0]
                if typ == "artist":
                    return {"artists": {"items": [deepcopy(self.artist)]}}
                if typ == "track":
                    if self.fail_catalog:
                        raise ConnectionError("Explicit external catalog outage fixture")
                    if self.after_catalog:
                        await self.after_catalog()
                    return {"tracks": {"items": deepcopy([*self.tracks, self.foreign])}}
            if parsed.path == "/me/player":
                if self.fail_status:
                    raise ConnectionError("Explicit independent status outage fixture")
                return {"item": deepcopy(self.tracks[self.playback_index]), "is_playing": True,
                        "device": {"id": "speaker", "name": "Existing speaker"}}
            if parsed.path == "/me/tracks/contains":
                return [False]
            if parsed.path == "/artists":
                return {"artists": [dict(deepcopy(self.artist), genres=[])]}
            raise AssertionError("Unexpected provider read " + path)
        async def agent(hass, data, **kwargs):
            self.f.prompts.append(json.loads(data["text"].split("\nData:\n", 1)[1]))
            return {"response": {"speech": {"plain": {"speech": json.dumps(self.plan)}}}}
        self.provider = patch.object(spotify_backend.SpotifyBackend, "_request", provider)
        self.agent = patch.object(self.f.pipeline, "_call_conversation_process_transport", agent)
        self.provider.start()
        self.agent.start()

    async def asyncTearDown(self):
        self.agent.stop()
        self.provider.stop()
        await self.base.asyncTearDown()

    async def test_armin_hits_question_returns_actual_other_titles_and_no_playback(self):
        answer, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertEqual([a["title"] for a in answer.get("items", [])],
                         ["This Is What It Feels Like", "Blah Blah Blah"])
        self.assertNotIn("Patience", answer["text"])
        self.assertNotIn("Current recording", answer["text"])
        self.assertEqual(len(self.f.prompts), 1)
        self.assertTrue(all(method == "GET" for method, _ in self.calls))
        self.assertTrue(all(a.get("action_id") for a in answer["playback_actions"]))

    async def test_free_artist_wording_and_typos_in_five_languages_use_one_agent_then_real_rows(self):
        questions = {"nl": "wat voor andere hists heeft armin van buren eigelijk",
                     "en": "what else has armin van buren got in the hits department",
                     "de": "welche anderen hits hat armin van buren eigendlich",
                     "fr": "il a quoi comme autres tubes armin van buren",
                     "es": "qué otros exitoss tiene armin van buren"}
        for language, question in questions.items():
            with self.subTest(language=language):
                before = len(self.f.prompts)
                answer, code = await self.f.request(question, language=language, identifier="hits-" + language)
                self.assertEqual(code, 200, answer)
                self.assertEqual(len(self.f.prompts) - before, 1)
                self.assertEqual([a["title"] for a in answer.get("items", [])],
                                 ["This Is What It Feels Like", "Blah Blah Blah"])
                self.assertNotIn("Patience", answer["text"])
                self.assertNotIn("This Is What", json.dumps(self.f.prompts))
                self.assertFalse(answer["history_persisted"])

    async def test_named_artist_plan_is_closed_and_cannot_supply_a_uri_or_private_query(self):
        from custom_components.djconnect.ask_dj.semantic_reads import parse_plan
        for value in ({**self.plan, "uri": self.tracks[1]["uri"]},
                      {**self.plan, "artist": "https://example.org/"},
                      {**self.plan, "artist": "my wife Anja"},
                      {**self.plan, "read": "play"},
                      {**self.plan, "artist": 1}):
            with self.subTest(value=value):
                self.assertIsNone(parse_plan(json.dumps(value)))

    async def test_catalog_outage_is_music_unavailable_without_history_error_or_current_fallback(self):
        self.fail_catalog = True
        answer, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertTrue(answer["success"])
        self.assertFalse(answer.get("items"))
        self.assertFalse(answer.get("sources"))
        self.assertNotIn("history", str(answer.get("error")))
        self.assertNotIn("Current recording", answer["text"])
        self.assertTrue(all(m == "GET" for m, _ in self.calls))

    async def test_clear_during_catalog_read_denies_late_result_without_playback(self):
        async def clear():
            await self.f.history.async_clear("profile:profile-a")
        self.after_catalog = clear
        answer, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertEqual(code, 409, answer)
        self.assertFalse(answer.get("items"))
        self.assertTrue(all(m == "GET" for m, _ in self.calls))

    async def test_current_without_session_rejects_track_change_during_catalog_read(self):
        self.plan = {"read": "artist_tracks", "reference": "current", "exclude_current": True}
        async def change():
            self.playback_index = 1
        self.after_catalog = change
        answer, code = await self.f.request("wat heeft deze artiest nog aan andere nummmers?", language="nl")
        self.assertEqual(code, 409, answer)
        self.assertEqual(answer["error"], "playback_context_changed")
        self.assertFalse(answer.get("playback_actions"))
        self.assertTrue(all(m == "GET" for m, _ in self.calls))

    async def test_original_expiry_cannot_be_renewed_during_catalog_read(self):
        from datetime import UTC, datetime, timedelta
        started = datetime.now(UTC)
        self.plan = {"read": "artist_tracks", "reference": "current", "exclude_current": True}
        clock = [1000.0]
        self.f.history.dialogue.clock = lambda: clock[0]
        original = self.f.core.run_music_command
        async def source(hass, runtime, command, value=None, **kwargs):
            result = await original(hass, runtime, command, value, **kwargs)
            if command == "status":
                result["playback"]["expires_at"] = (started + timedelta(seconds=1)).isoformat()
            return result
        async def expire():
            clock[0] += 2
        self.after_catalog = expire
        with patch.object(self.f.core, "run_music_command", source):
            answer, code = await self.f.request("wat heeft deze artiest nog aan andere nummmers?", language="nl")
        self.assertEqual(code, 409, answer)
        self.assertEqual(answer["error"], "playback_observation_expired")
        self.assertFalse(answer.get("playback_actions"))

    async def test_selected_recording_is_omitted_instead_of_different_current_track(self):
        from custom_components.djconnect.session_conversation import query_service
        session = await self.f.fixture.observed_session()
        page = await query_service(self.f.hass, self.f.history).async_timeline_page("profile-a", session.session_id)
        observed = next(e for e in page["entries"] if e["kind"] == "playback_observed")
        self.artist["name"] = "Metallica"
        for t in self.tracks:
            t["artists"] = [deepcopy(self.artist)]
        self.tracks[0].update(uri="spotify:track:0123456789abcdefghijkL", id="0123456789abcdefghijkL")
        self.playback_index = 1
        self.plan = {"read": "artist_tracks", "reference": "selected", "exclude_current": True}
        answer, code = await self.f.request("wat heeft de artiest hierbij nog aan nummmers?", language="nl",
            context={"selected_entry": {"session_id": session.session_id, "entry_id": observed["entry_id"]}})
        self.assertEqual(code, 200, answer)
        self.assertEqual([i["uri"] for i in answer.get("items", [])], [t["uri"] for t in self.tracks[1:]])
        self.assertFalse(any(path == "/me/player" for _, path in self.calls))

    async def test_qualified_selected_group_has_artist_identity_but_never_a_recording_title(self):
        from custom_components.djconnect import session_facts
        self.artist["name"] = "Qualified group"
        for t in self.tracks:
            t["artists"] = [deepcopy(self.artist)]
        manager = self.f.fixture.manager
        session = await manager.async_start(owner_profile_id="profile-a", locale="nl",
            selected_mood="groove", music_backend="spotify_direct")
        uri = self.tracks[0]["uri"]
        await manager.async_update_playback_projection(owner_profile_id="profile-a", session_id=session.session_id,
            state="playing", media_identity=uri, title="Recording", artist="Qualified group", duration_ms=300000, position_ms=1000)
        fact = session_facts._fact("artist_begin", {"uri": uri}, "artist_story", ["Qualified group"] * 5,
            ["Qualified group formed in 2000.", "Qualified group is opgericht in 2000.",
             "Qualified group wurde 2000 gegründet.", "Qualified group a été formé en 2000.",
             "Qualified group se formó en 2000."], "MusicBrainz",
            "https://musicbrainz.org/artist/11111111-1111-1111-1111-111111111111",
            session_facts.DisplayFactCore("artist_begin", "Qualified group", date="2000", precision="year", entity_type="Group"))
        async def facts():
            return {"_qualified_facts": (fact,)}
        moment = await manager.async_process_track_started(owner_profile_id="profile-a", session_id=session.session_id,
            media_identity=uri, insight_provider=facts, require_current_playback=True, allow_initial_facts=True)
        context = {"selected_moment": {"session_id": session.session_id, "moment_id": moment.moment_id}}
        self.plan = {"read": "artist_tracks", "reference": "selected", "exclude_current": True}
        answer, code = await self.f.request("wat heeft deze groep voor nummmers?", context=context, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertEqual(len(answer.get("items", [])), 3)
        self.plan = {"read": "recording", "reference": "selected", "exclude_current": False}
        answer, code = await self.f.request("hoe heet het liedjuh hierbij nou?", context=context, language="nl", identifier="group-no-recording")
        self.assertEqual(code, 200, answer)
        self.assertIn("opname", answer["text"])
        self.assertFalse(answer.get("playback_actions"))

    async def test_named_catalog_survives_independent_current_status_outage(self):
        self.fail_status = True
        answer, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertEqual(len(answer.get("items", [])), 3)
        self.assertNotIn("Patience", answer["text"])

    async def test_wrong_canonical_artist_never_uses_current_as_fallback(self):
        self.artist["name"] = "Guns N' Roses"
        answer, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertFalse(answer.get("items"))
        self.assertNotIn("Patience", answer["text"])

    async def test_duplicate_question_reuses_frozen_result_without_provider_or_agent_retry(self):
        question = "welke hits heeft armin van buuren nog meer"
        first, code = await self.f.request(question, identifier="one-hits-turn", language="nl")
        self.assertEqual(code, 200, first)
        before = (len(self.calls), len(self.f.prompts))
        repeated, code = await self.f.request(question, identifier="one-hits-turn", language="nl")
        self.assertEqual(code, 200, repeated)
        self.assertEqual(repeated["playback_actions"], first["playback_actions"])
        self.assertEqual((len(self.calls), len(self.f.prompts)), before)

    async def test_account_withdrawal_during_catalog_read_denies_late_result(self):
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        async def withdraw():
            await self.base.storage.async_upsert_music_account("album-account", "spotify_direct",
                kind=MusicAccountKind.PERSONAL, display_name="Catalog fixture", linked_profile_ids=frozenset())
        self.after_catalog = withdraw
        answer, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertIn(code, (403, 409), answer)
        self.assertFalse(answer.get("playback_actions"))
        self.assertTrue(all(m == "GET" for m, _ in self.calls))

    async def test_retry_of_expired_or_displaced_offer_never_renews_or_refetches(self):
        question = "welke hits heeft armin van buuren nog meer"
        for mode in ("expired", "displaced"):
            first, code = await self.f.request(question, identifier="original-" + mode, language="nl")
            self.assertEqual(code, 200, first)
            frame = self.f.history.dialogue.owners["profile:profile-a"][first["conversation"]["thread_id"]]
            if mode == "expired":
                self.f.history.dialogue.clock = lambda: frame.result_set["deadline"] + 1
                # Capture the original time before frame() expires the result.
                tick = self.f.history.dialogue.clock()
                self.f.history.dialogue.clock = lambda: tick
            else:
                newer, code = await self.f.request(question, identifier="replacement", language="nl")
                self.assertEqual(code, 200, newer)
                self.assertNotEqual(newer["result_set"]["result_set_id"], first["result_set"]["result_set_id"])
            before = (len(self.calls), len(self.f.prompts))
            denied, code = await self.f.request(question, identifier="original-" + mode, language="nl")
            self.assertEqual(code, 409, denied)
            self.assertIn(denied["error"], ("choice_expired", "choice_changed"))
            self.assertEqual((len(self.calls), len(self.f.prompts)), before)

    async def test_frozen_first_offer_starts_only_after_explicit_play_and_duplicate_never_repeats_effect(self):
        offered, code = await self.f.request("welke hits heeft armin van buuren nog meer", language="nl")
        self.assertEqual(code, 200, offered)
        self.assertEqual(self.base.writes, [])
        # Keep the real Spotify dispatch guard; only its HTTP session remains
        # the external fixture inherited from AlbumTracksTests.
        self.provider.stop()
        answer, code = await self.f.request("speel de eerste", identifier="explicit-frozen-hit", language="nl")
        self.assertEqual(code, 200, answer)
        self.assertEqual(self.base.writes, [("/v1/me/player/play", {"context_uri": self.base.album["uri"],
            "offset": {"uri": self.tracks[1]["uri"]}})])
        repeated, code = await self.f.request("speel de eerste", identifier="explicit-frozen-hit", language="nl")
        self.assertIn(code, (200, 409), repeated)
        self.assertEqual(len(self.base.writes), 1)

    async def test_operational_replays_are_bounded_and_history_clear_discards_private_bodies(self):
        question = "welke hits heeft armin van buuren nog meer"
        for index in range(6):
            answer, code = await self.f.request(question, identifier="bounded-" + str(index), language="nl")
            self.assertEqual(code, 200, answer)
            self.assertFalse(answer["history_persisted"])
        frame = self.f.history.dialogue.owners["profile:profile-a"][answer["conversation"]["thread_id"]]
        self.assertLessEqual(sum(row[1] is not None for row in frame.catalogue_replays.values()), 4)
        self.assertLessEqual(sum(row[3] for row in frame.catalogue_replays.values()), 64 * 1024)
        await self.f.history.async_clear("profile:profile-a")
        self.assertEqual(frame.catalogue_replays, {})

    async def test_evicted_private_body_leaves_opaque_receipt_without_agent_or_provider_retry(self):
        question = "welke hits heeft armin van buuren nog meer"
        for index in range(6):
            answer, code = await self.f.request(question, identifier="eviction-" + str(index), language="nl")
            self.assertEqual(code, 200, answer)
        before = (len(self.calls), len(self.f.prompts))
        denied, code = await self.f.request(question, identifier="eviction-0", language="nl")
        self.assertEqual(code, 409, denied)
        self.assertEqual(denied["error"], "choice_expired")
        self.assertEqual((len(self.calls), len(self.f.prompts)), before)
