"""Shared-service current-subject regressions; provider/agent boundaries are fixtures."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from copy import deepcopy
from tests import test_ask_dj_contextual_dialogue as dialogue_fixtures


class CurrentArtistIdentificationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        dialogue_fixtures.SharedDialogueTest.setUpClass()
        cls.core, cls.pipeline, cls.dialogue = dialogue_fixtures.SharedDialogueTest.core, dialogue_fixtures.SharedDialogueTest.pipeline, dialogue_fixtures.SharedDialogueTest.dialogue

    @classmethod
    def tearDownClass(cls):
        dialogue_fixtures.SharedDialogueTest.tearDownClass()

    asyncSetUp = dialogue_fixtures.SharedDialogueTest.asyncSetUp
    asyncTearDown = dialogue_fixtures.SharedDialogueTest.asyncTearDown
    request = dialogue_fixtures.SharedDialogueTest.request

    async def test_exact_text_and_stt_completion_are_same_direct_read(self):
        playback = {"uri": "spotify:track:" + "A" * 22, "title": "Major Drop", "artist": "Above & Beyond"}
        reads = []

        async def provider(hass, runtime, command, *args, **kwargs):
            reads.append(command)
            self.assertEqual(command, "status", "An information question must never dispatch an effect")
            return {"success": True, "playback": deepcopy(playback)}

        with patch.object(self.core, "run_music_command", provider), patch.object(self.core, "_playback_context", return_value=playback):
            for index, (text, voice) in enumerate([("welke artiest is dit", False), ("Welke artiest is dit?", True), ("wie hoor ik nu", False), ("wie is dit", True)]):
                data = {**self.identity, "client_message_id": "artist-" + str(index), "text": text, "language": "nl", "audio_response": "never"}
                result, status = await self.handlers.async_handle_ask_dj_message_payload(self.hass, data, headers=self.headers, voice_input=voice)
                self.assertEqual(status, 200)
                self.assertIn("Above & Beyond", result["text"])
                self.assertIn("Major Drop", result["text"])
                self.assertEqual(result["playback_actions"], [])
        self.assertEqual(self.prompts, [], "Spotify playback must not be sent to the agent")
        self.assertEqual(self.effects, [])
        self.assertTrue(reads)

    async def test_selected_catalog_result_precedes_implicit_current_artist(self):
        async def offer(*args, **kwargs):
            return {"success": True, "text": "Catalog result", "playback_actions": [{"kind": "track",
                "uri": "spotify:track:" + "A" * 22, "title": "Selected work", "subtitle": "Selected Artist"}]}
        with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", offer):
            await self.request("Find tracks", identifier="catalog-offer")
        await self.request("the first", identifier="catalog-select")
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        original_deadline = frame.result_set["deadline"]
        async def provider(*args, **kwargs):
            return {"success": True, "playback": {"uri": "spotify:track:" + "B" * 22,
                "title": "Other work", "artist": "Other Artist"}}
        with patch.object(self.core, "run_music_command", provider):
            result, status = await self.request("Who is this artist?", identifier="catalog-question")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["intent"]["intent"], "selected_result_identification")
        self.assertIn("Selected Artist", result["text"])
        self.assertNotIn("Other Artist", result["text"])
        archived = await self.history.async_history("profile:profile-a")
        self.assertNotIn(result["text"], [m.get("text") for m in archived["messages"]])
        self.assertFalse(result["history_persisted"])
        self.assertEqual(frame.result_set["deadline"], original_deadline)
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.effects, [])

        from custom_components.djconnect import http
        async def play(h, r, action, payload):
            async def dispatch():
                await self.dialogue.guard_effect_dispatch(method="PUT", path="/me/player/play", body={"uris": [action["uri"]]})
                self.effects.append(action["uri"])
            return await dialogue_fixtures.SharedDialogueTest.external_effect_probe(self, "play", action["uri"], dispatch)
        with patch.object(http, "_handle_ask_dj_play_recommendation", play):
            played, status = await self.request("Play that", identifier="catalog-explicit-play")
        self.assertEqual(status, 200, played)
        self.assertEqual(self.effects, ["spotify:track:" + "A" * 22])

    async def test_missing_expired_or_cached_context_never_borrows_runtime_cache(self):
        self.runtime.last_playback = {"uri": "spotify:track:" + "A" * 22, "artist": "Old artist", "title": "Old track"}
        cases = [{}, None, {"uri":"spotify:track:"+"A"*22,"artist":"A"*513,"title":"Oversized"}, {"state":"unavailable", **self.runtime.last_playback}, {"valid_until":"bad-date", **self.runtime.last_playback}, {"valid_until":"2000-01-01T00:00:00", **self.runtime.last_playback}, {"cached": True, **self.runtime.last_playback}, {"valid_until": "2000-01-01T00:00:00+00:00", **self.runtime.last_playback}, {"artist": "No identity", "title": "No identity"}]
        for index, playback in enumerate(cases):
            async def provider(*args, **kwargs):
                return {"success": True, "playback": playback}
            with patch.object(self.core, "run_music_command", provider):
                result, status = await self.request("welke artiest is dit", identifier="missing-"+str(index), language="nl")
            self.assertEqual(status, 200)
            self.assertIn("niet betrouwbaar", result["text"])
            self.assertNotIn("Old artist", result["text"])
        self.assertEqual(self.prompts, [])

    async def test_track_change_during_read_rejects_old_answer(self):
        count = 0
        async def provider(*args, **kwargs):
            nonlocal count
            count += 1
            return {"success": True, "playback": {"uri": "spotify:track:" + str(count)*22, "title": "Track "+str(count), "artist": "Artist "+str(count)}}
        with patch.object(self.core, "run_music_command", provider):
            result, status = await self.request("Welke artiest is dit?", language="nl")
        self.assertEqual(status, 409)
        self.assertEqual(result["error"], "playback_context_changed")
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.effects, [])

    async def test_pending_proposal_and_retry_cannot_authorize_information_question(self):
        await self.request("A standalone information question", identifier="seed")
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        import time
        frame.pending = {"deadline": time.monotonic()+600, "action": "play", "payload": {"uri": "spotify:track:"+"B"*22}}
        frame.retry = {"text": "play an old song", "uncertain": False}
        calls = []
        async def provider(hass, runtime, command, *args, **kwargs):
            calls.append(command)
            self.assertEqual(command, "status")
            return {"success": True, "playback": {"uri":"spotify:track:"+"A"*22,"artist":"Above & Beyond","title":"Major Drop"}}
        before = len(self.prompts)
        with patch.object(self.core, "run_music_command", provider):
            result, status = await self.request("welke artiest is dit", identifier="not-confirmation", language="nl")
        self.assertEqual(status, 200)
        self.assertIn("Above & Beyond", result["text"])
        self.assertEqual(calls, ["status", "status"])
        self.assertEqual(len(self.prompts), before)
        self.assertEqual(self.effects, [])

    async def test_selected_contribution_never_borrows_current_track(self):
        session, moment, target = await dialogue_fixtures.SharedDialogueTest.selected_credit(self)
        async def prohibited(*args, **kwargs):
            raise AssertionError("A selected contribution must not borrow now-playing")
        with patch.object(self.core, "run_music_command", prohibited):
            result, status = await self.request("welke artiest is dit", context={"selected_entry":target}, language="nl")
        self.assertEqual(status, 200, result)
        self.assertIn("niet betrouwbaar", result["text"])
        self.assertNotIn("Brian Eno", result["text"], "A composer is not automatically the performing artist")
        self.assertEqual(self.prompts, [])

    async def test_information_intent_and_local_presentation_in_five_languages(self):
        cases = [("en","Which artist is this?","This is"),("nl","welke artiest is dit","Dit is"),("de","Welcher Künstler ist das?","Das ist"),("fr","Qui est cet artiste ?","C’est"),("es","¿Quién es este artista?","Es")]
        async def provider(*args, **kwargs):
            return {"success":True,"playback":{"uri":"spotify:track:"+"A"*22,"artist":"Above & Beyond","title":"Major Drop"}}
        with patch.object(self.core,"run_music_command",provider):
            for language,text,prefix in cases:
                intent = self.core.classify_ask_dj(text)
                self.assertEqual(intent.category,"informational")
                result,status=await self.request(text,identifier="language-"+language,language=language)
                self.assertEqual(status,200)
                self.assertTrue(result["text"].startswith(prefix),result["text"])
                self.assertEqual(result["playback_actions"],[])
        self.assertEqual(self.prompts,[])

    async def test_selected_earlier_playback_uses_qualified_stored_identity(self):
        session, _, _ = await dialogue_fixtures.SharedDialogueTest.selected_credit(self)
        entries = (await self.fixture.queries.async_timeline_page("profile-a", session.session_id))["entries"]
        selected = next(e for e in entries if e["kind"] == "playback_observed")
        async def prohibited(*args, **kwargs):
            raise AssertionError("Do not replace selected historical music with now-playing")
        target = {"session_id":session.session_id,"entry_id":selected["entry_id"]}
        with patch.object(self.core,"run_music_command",prohibited):
            result,status=await self.request("welke artiest is dit",context={"selected_entry":target},language="nl")
        self.assertEqual(status,200,result)
        self.assertEqual(result["text"],"Dit is Synthetic performer, met Synthetic work.")
        self.assertEqual(self.prompts,[])
        self.assertFalse(result["history_persisted"])

    async def test_active_track_change_fences_standalone_request_without_session_hint(self):
        session, _, _ = await dialogue_fixtures.SharedDialogueTest.selected_credit(self)
        async def provider(*args, **kwargs):
            await self.fixture.manager.async_update_playback_projection(owner_profile_id="profile-a",session_id=session.session_id,state="playing",media_identity="spotify:track:"+"B"*22,title="New track",artist="New artist")
            return {"success":True,"playback":{"uri":"spotify:track:"+"A"*22,"artist":"Old artist","title":"Old track"}}
        with patch.object(self.core,"run_music_command",provider):
            result,status=await self.request("Welke artiest is dit?",language="nl")
        self.assertEqual(status,409,result)
        self.assertEqual(result["error"],"session_context_changed")
        self.assertNotIn("Old artist",result.get("text",""))
        self.assertEqual(self.prompts,[])

    async def test_different_profile_is_rejected_before_read_or_generation(self):
        async def prohibited(*args, **kwargs):
            raise AssertionError("Cross-Profile request must be rejected before provider access")
        with patch.object(self.core,"run_music_command",prohibited):
            result,status=await self.request("Welke artiest is dit?",profile_id="not-the-owner")
        self.assertEqual(status,403,result)
        self.assertEqual(self.prompts,[])

    async def test_stale_session_target_and_failed_read_do_not_retain_old_music_retry(self):
        await self.request("A standalone information question", identifier="seed-retry")
        await dialogue_fixtures.SharedDialogueTest.selected_credit(self)
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        frame.retry = {"text":"play an old song","uncertain":False}
        async def provider(hass,runtime,command,*args,**kwargs):
            self.assertEqual(command,"status")
            return {"success":True,"playback":{"uri":"spotify:track:"+"B"*22,"artist":"Different artist","title":"Different track"}}
        with patch.object(self.core,"run_music_command",provider):
            result,status=await self.request("Welke artiest is dit?",identifier="read-new-track",language="nl")
        self.assertEqual(status,409,result)
        self.assertEqual(result["error"],"session_context_changed")
        self.assertIsNone(frame.retry)
        self.assertEqual(self.effects,[])

    async def test_missing_selected_source_clears_obsolete_music_retry(self):
        session, _, _ = await dialogue_fixtures.SharedDialogueTest.selected_credit(self)
        await self.request("A standalone information question", identifier="source-retry-seed")
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        frame.retry = {"text": "play an old song", "uncertain": False}
        result, status = await self.request("welke artiest is dit", identifier="missing-selected",
            context={"selected_moment": {"session_id": session.session_id, "moment_id": "missing"}})
        self.assertGreaterEqual(status, 400, result)
        self.assertIsNone(frame.retry)
        await self.request("retry", identifier="after-missing-selected")
        self.assertEqual(self.effects, [])

    async def test_selected_published_artist_moment_keeps_its_subject_and_attribution(self):
        from custom_components.djconnect import session_facts
        uri="spotify:track:"+"A"*22
        session=await self.fixture.manager.async_start(owner_profile_id="profile-a",locale="nl",selected_mood="groove",music_backend="spotify_direct")
        await self.fixture.manager.async_update_playback_projection(owner_profile_id="profile-a",session_id=session.session_id,state="playing",media_identity=uri,title="A recording",artist="Synthetic group",duration_ms=300000,position_ms=1000)
        fact=session_facts._fact("artist_begin",{"uri":uri},"artist_story",["Synthetic group"]*5,["Synthetic group formed in 2000.","Synthetic group is opgericht in 2000.","Synthetic group wurde 2000 gegründet.","Synthetic group a été formé en 2000.","Synthetic group se formó en 2000."],"MusicBrainz","https://musicbrainz.org/artist/11111111-1111-1111-1111-111111111111",session_facts.DisplayFactCore("artist_begin","Synthetic group",date="2000",precision="year",entity_type="Group"))
        async def provider():
            return {"_qualified_facts":(fact,)}
        moment=await self.fixture.manager.async_process_track_started(owner_profile_id="profile-a",session_id=session.session_id,media_identity=uri,insight_provider=provider,require_current_playback=True,allow_initial_facts=True)
        self.assertIsNotNone(moment)
        self.assertEqual(moment.moment_type.value,"artist")
        async def prohibited(*args,**kwargs):
            raise AssertionError("Selected artist cannot be replaced with current playback")
        with patch.object(self.core,"run_music_command",prohibited):
            result,status=await self.request("welke artiest is dit",context={"selected_moment":{"session_id":session.session_id,"moment_id":moment.moment_id}},language="nl")
        self.assertEqual(status,200,result)
        self.assertEqual(result["text"],"Dit is Synthetic group.")
        self.assertEqual(result["sources"][0]["url"],fact.source_url)
        self.assertEqual(result["sources"][0]["license"],"CC0-1.0")
        self.assertEqual(self.prompts,[])

    async def test_selected_playback_link_requires_exact_spotify_host(self):
        from custom_components.djconnect.ask_dj.observations import current_artist_read
        valid = "https://open.spotify.com/track/" + "A" * 22
        for i, url in enumerate((valid, valid.replace("open.spotify", "openXspotify"),
                valid.replace("spotify.com", "spotifyXcom"), valid + "?redirect=other")):
            async def read(*args, **kwargs):
                return await current_artist_read(self.hass, self.runtime, {"playback": {
                    "item_id": "qualified-stored-identity", "artist": "Selected Artist",
                    "title": "Selected work", "provider": "Spotify", "source_url": url}})
            with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", read):
                result, status = await self.request("Who is this artist?", identifier="source-host-" + str(i))
            self.assertEqual(status, 200, result)
            self.assertEqual([x["url"] for x in result["links"]], [valid] if i == 0 else [])
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.effects, [])

    async def test_transport_failure_never_reuses_old_playback(self):
        self.runtime.last_playback={"uri":"spotify:track:"+"A"*22,"title":"Old track","artist":"Old artist"}
        async def unavailable(*args,**kwargs):
            raise ConnectionError("External provider fixture unavailable")
        with patch.object(self.core,"run_music_command",unavailable):
            result,status=await self.request("welke artiest is dit",language="nl")
        self.assertEqual(status,200,result)
        self.assertIn("niet betrouwbaar",result["text"])
        self.assertNotIn("Old artist",result["text"])
        self.assertEqual(self.prompts,[])

    def test_information_question_is_not_a_bare_track_answer_to_old_clarification(self):
        context={"server_history":[{"role":"user","text":"Ik zoek muziek"},{"role":"assistant","text":"Welk nummer of welke artiest wil je horen?"}]}
        for text in ["welke artiest is dit","Welke artiest is dit?","wie hoor ik nu?","wie is dit?"]:
            with self.subTest(text=text):
                turn=self.core.classify_conversation_turn(text,context)
                self.assertEqual(turn.text,text)
                self.assertEqual(self.core.classify_ask_dj(turn.text).category,"informational")
