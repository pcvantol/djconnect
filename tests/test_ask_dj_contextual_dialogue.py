"""Owning causal regressions: common routes, actual Store/SQLite owner boundaries.

Agent/provider responses in this suite are explicit routing/failure fixtures.
Real OpenAI-generated conversation quality is independently qualified in the HA lab.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixture_defs


class SharedDialogueTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixture_defs.SessionConversationHistoryTest.setUpClass()
        from custom_components.djconnect import ask_dj, pipeline
        from custom_components.djconnect.ask_dj import dialogue

        cls.core, cls.pipeline, cls.dialogue = ask_dj, pipeline, dialogue

    @classmethod
    def tearDownClass(cls):
        fixture_defs.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixture_defs.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        (
            self.hass,
            self.runtime,
            self.history,
            self.identity,
            self.headers,
        ) = await self.fixture.transport_fixture()
        self.handlers = self.fixture.handlers
        self.prompts, self.effects = [], []
        self.reply = "A synthetic agent answer about the requested subject."
        from types import SimpleNamespace

        async def unavailable(*args, **kwargs):
            raise AssertionError("Routing fixture must supply the explicit agent transport")

        self.hass.services = SimpleNamespace(async_call=unavailable)

        async def agent(hass, data, **kwargs):
            projection = json.loads(data["text"].split("\nData:\n", 1)[1])
            self.prompts.append(projection)
            return {"response": {"speech": {"plain": {"speech": self.reply}}}}

        self.agent_patch = patch.object(
            self.pipeline, "_call_conversation_process_transport", agent
        )
        self.original_transport = self.pipeline._call_conversation_process_transport
        self.agent_patch.start()

    async def asyncTearDown(self):
        self.agent_patch.stop()
        await self.fixture.asyncTearDown()

    async def request(self, text, *, identifier="unit-1", context=None, **fields):
        payload = {
            **self.identity,
            "client_message_id": identifier,
            "text": text,
            "language": "en",
            "audio_response": "never",
            **fields,
        }
        if context is not None:
            payload["conversation_context"] = context
        return await asyncio.wait_for(
            self.handlers.async_handle_ask_dj_message_payload(
                self.hass, payload, headers=self.headers
            ),
            5,
        )

    async def selected_credit(self):
        session = await self.fixture.manager.async_start(
            owner_profile_id="profile-a",
            locale="en",
            selected_mood="groove",
            music_backend="spotify_direct",
            history_source_context={
                "backend_id": "source-spotify",
                "music_account_id": "source-account",
                "provider_entry_id": "source-entry",
            },
        )
        from custom_components.djconnect import session_facts

        fact = session_facts._fact(
            "work_composers",
            {"uri": "spotify:track:0123456789abcdefghijkL"},
            "track_context",
            ["Brian Eno"] * 5,
            [
                "Composers of the work behind this recording: Brian Eno.",
                "Componisten van het werk achter deze opname: Brian Eno.",
                "Komponisten des Werks hinter dieser Aufnahme: Brian Eno.",
                "Compositeurs de l’œuvre de cet enregistrement : Brian Eno.",
                "Compositores de la obra de esta grabación: Brian Eno.",
            ],
            "MusicBrainz",
            "https://musicbrainz.org/work/11111111-1111-1111-1111-111111111111",
            session_facts.DisplayFactCore("work_composers", roles=(("composer", ("Brian Eno",)),)),
        )
        # Real Moment engine and publication/storage chain, only external source evidence is synthetic.
        await self.fixture.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity=fact.media_identity,
            title="Synthetic work",
            artist="Synthetic performer",
            duration_ms=300000,
            position_ms=1000,
        )

        async def provider():
            return {"_qualified_facts": (fact,)}

        moment = await self.fixture.manager.async_process_track_started(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            media_identity=fact.media_identity,
            insight_provider=provider,
            require_current_playback=True,
            allow_initial_facts=True,
        )
        self.assertIsNotNone(moment)
        entries = await self.fixture.queries.async_timeline_page("profile-a", session.session_id)
        entry = next(e for e in entries["entries"] if e.get("moment_id") == moment.moment_id)
        return session, moment, {"session_id": session.session_id, "entry_id": entry["entry_id"]}

    async def test_one_service_screen_and_voice_parity_with_rich_results(self):
        calls = []

        async def core(h, r, p, **kwargs):
            calls.append(kwargs)
            return {
                "success": True,
                "text": "Same capabilities",
                "items": [{"kind": "album", "title": "Real provider-shaped result"}],
            }

        with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", core):
            for i, context in enumerate((None, {})):
                result, status = await self.request(
                    "An open music question",
                    identifier=f"parity-{i}",
                    context=context,
                    input_type="voice",
                )
                self.assertEqual(status, 200, result)
                self.assertEqual(result["conversation"]["history_scope"], "profile")
                self.assertEqual(result["items"][0]["kind"], "album")
        self.assertEqual(len(calls), 2)
        self.assertEqual({c["conversation_history_scope"] for c in calls}, {"profile:profile-a"})
        state = await self.history.async_history("profile:profile-a")
        self.assertEqual(len(state["messages"]), 4)
        self.assertEqual((await self.history.async_history(None))["messages"], [])

    async def test_search_refinement_uses_new_user_subject_and_real_cards_without_playing(self):
        from custom_components.djconnect.domain.profile import ProfilePreferences
        await self.handlers.profile_storage(self.hass).async_update_profile("profile-a", preferences=ProfilePreferences(default_backend_id="source-spotify"))
        self.runtime.config["music_backend"] = "spotify_direct"
        self.reply = json.dumps({"text": "I will search for acoustic jazz.", "intent": "lookup", "query": "acoustic jazz"})
        queries = []
        async def search(hass, runtime, query, **kwargs):
            queries.append(query)
            return {"tracks": [{"uri": "spotify:track:0123456789abcdefghijkL", "title": "Synthetic Live", "artist": "Synthetic performer"}]}
        async def command(*args, **kwargs):
            raise AssertionError("Searching and refining cannot change playback")
        with patch.object(self.core, "_spotify_track_search", search), patch.object(self.core, "run_music_command", command):
            result, status = await self.request("Suggest acoustic jazz songs to search for, keeping playback unchanged.")
            self.assertEqual(status, 200, result)
            self.assertIn("result_set", result, result)
            self.assertEqual(self.prompts[-1]["requested_operation"], "lookup")
            self.reply = json.dumps({"text": "I will refine that search.", "intent": "refine", "query": "acoustic live jazz"})
            refined, status = await self.request("Rather a live version; search for one, do not play yet.", identifier="refine")
            self.assertEqual(status, 200, refined)
            self.assertTrue(refined["result_set"])
            self.assertEqual(self.prompts[-1]["requested_operation"], "refine")
            self.assertNotIn("Synthetic performer", json.dumps(self.prompts))
            self.assertEqual(queries, ["acoustic jazz", "acoustic live jazz"])
            self.reply = json.dumps({"intent": "refine", "query": "quiet live jazz"})
            recovered, status = await self.request("Rather quieter live jazz", identifier="missing-model-caption")
            self.assertEqual(status, 200, recovered)
            self.assertIn("result_set", recovered)
            self.assertEqual(recovered["text"], "Found 1 track for quiet live jazz.")
            self.assertNotIn('"intent":', recovered["text"])

    async def test_analysis_discussion_does_not_open_a_screen_and_explicit_navigation_does(self):
        async def insight(*args, **kwargs):
            return {"language": "en", "track": {"title": "Synthetic", "artist": "Synthetic performer"}, "analysis": {"summary": "No audio measurement is available for this recording."}}
        async def status(*args, **kwargs):
            return {"success": True, "playback": {}}
        with patch.object(self.core, "async_call_ai_tool", insight), patch.object(self.core, "run_music_command", status):
            discussed, status_code = await self.request("Why does this track sound emotional?")
            self.assertEqual(status_code, 200, discussed)
            self.assertEqual(discussed["action"], "none")
            self.assertEqual(discussed["type"], "message")
            self.assertNotIn("open_screen", discussed)
            self.assertNotIn("track_insight", discussed)
            opened, status_code = await self.request("Open Track Insight for this track", identifier="open")
            self.assertEqual(status_code, 200, opened)
            self.assertEqual(opened["open_screen"], "track_insight")
            negated, status_code = await self.request("Do not open Track Insight; explain it here", identifier="negated-open")
            self.assertEqual(status_code, 200, negated)
            self.assertNotIn("open_screen", negated)
            for i, (language, text) in enumerate((("en", "Open the analysis of this track"), ("nl", "Open de analyse van dit nummer"), ("de", "Öffne die Analyse dieses Titels"), ("fr", "Ouvre l’analyse de cette chanson"), ("es", "Abre el análisis de esta canción"))):
                opened, status_code = await self.request(text, identifier=f"analysis-open-{i}", language=language)
                self.assertEqual(status_code, 200, opened)
                self.assertEqual(opened.get("open_screen"), "track_insight")
        self.assertEqual(self.prompts, [])

    async def test_selected_cc0_credit_calls_agent_instead_of_quote_echo(self):
        session, moment, target = await self.selected_credit()
        result, status = await self.request(
            "Who is that?", context={"session_id": session.session_id, "selected_entry": target}
        )
        self.assertEqual(status, 200, result)
        self.assertNotEqual(result["text"], moment.content)
        self.assertEqual(result["conversation"]["metrics"]["agent_calls"], 1)
        data = self.prompts[0]["context"]
        self.assertEqual(data["subjects"], [{"name": "Brian Eno", "role": "composer"}])
        self.assertNotIn("Synthetic performer", json.dumps(self.prompts))
        self.assertEqual(data["attribution"]["license"], "CC0-1.0")

    async def test_five_language_deictic_credit_roles_keep_the_selected_source(self):
        examples = [
            ("en", "Who is that composer?"),
            ("nl", "Wie is die componist?"),
            ("de", "Wer ist der Komponist?"),
            ("fr", "Qui est le compositeur ?"),
            ("es", "¿Quién es el compositor?"),
        ]
        session, moment, reference = await self.selected_credit()
        for i, (language, text) in enumerate(examples):
            result, status = await self.request(
                text,
                identifier="role-" + str(i),
                language=language,
                context={"selected_entry": reference, "thread_id": "credit-role"},
            )
            self.assertEqual(status, 200, result)
            self.assertEqual(
                self.prompts[-1]["context"].get("subjects"),
                [{"name": "Brian Eno", "role": "composer"}],
            )
            self.assertFalse(self.dialogue.explicit_subject(text))
        for text in ["his approach", "zijn aanpak", "seinen Ansatz", "son approche", "su enfoque"]:
            self.assertTrue(self.dialogue.references_topic(text))

    async def test_qualified_agent_failure_never_falls_back_to_an_unqualified_default(self):
        calls = []

        async def unavailable(domain, service, data, **kwargs):
            calls.append(dict(data))
            raise ValueError("Invalid agent ID fixture")

        self.hass.services.async_call = unavailable
        with patch.object(
            self.pipeline, "_call_conversation_process_transport", self.original_transport
        ):
            with self.assertRaises(ValueError):
                await self.pipeline.call_conversation_process_with_agent_retry(
                    self.hass,
                    {
                        "agent_id": "qualified-fixture-agent",
                        "text": "Approved current question only",
                    },
                    model_guard=lambda: None,
                )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["agent_id"], "qualified-fixture-agent")

    async def test_clear_five_language_volume_controls_keep_topic_without_agent(self):
        await self.request("Who is Brian Eno?", identifier="volume-topic")
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        topic = deepcopy(frame.messages)
        calls = []

        async def control(hass, runtime, text, intent, *args, **kwargs):
            calls.append((intent.action, intent.value))
            return {"success": True, "text": "Explicit control routing fixture"}

        examples = [
            ("en", "Turn the volume down"),
            ("nl", "Zet zachter"),
            ("de", "Mach leiser"),
            ("fr", "Baisse le volume"),
            ("es", "Baja el volumen"),
        ]
        with patch.object(self.core, "_handle_action", control):
            for i, (language, text) in enumerate(examples):
                result, status = await self.request(
                    text, identifier="volume-language-" + str(i), language=language
                )
                self.assertEqual(status, 200, result)
                self.assertEqual(result["conversation"]["metrics"]["agent_calls"], 0)
                self.assertEqual(frame.messages, topic)
        self.assertEqual(calls, [("volume_delta", -10)] * 5)
        self.assertEqual(len(self.prompts), 1)

    async def test_explicit_quote_has_zero_model_calls(self):
        session, moment, target = await self.selected_credit()
        result, status = await self.request(
            "Quote this verbatim",
            context={"session_id": session.session_id, "selected_entry": target},
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["text"], moment.content)
        self.assertEqual(result["conversation"]["metrics"]["agent_calls"], 0)
        self.assertEqual(self.prompts, [])

    async def test_new_explicit_subject_ignores_missing_old_chip(self):
        result, status = await self.request(
            "Who is Miles Davis?",
            context={"selected_entry": {"session_id": "expired", "entry_id": "missing"}},
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(len(self.prompts), 1)
        self.assertEqual(self.prompts[0]["context"], {})
        self.assertNotIn("selected_entry", result["conversation"]["context"])

    async def test_general_trivia_survives_track_change_and_no_backend(self):
        session = await self.fixture.observed_session()
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {
                "success": True,
                "text": "A public biography",
                "model_processing_basis": "qualified_dialogue_v1",
            }

        with patch.object(self.core, "_handle_informational", delayed):
            task = asyncio.create_task(
                self.request("Who is Miles Davis?", context={"session_id": session.session_id})
            )
            await asyncio.wait_for(entered.wait(), 2)
            await self.fixture.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=session.session_id,
                state="playing",
                media_identity="spotify:track:1123456789abcdefghijkL",
                title="Other",
                artist="Other",
                duration_ms=300000,
                position_ms=0,
            )
            release.set()
            result, status = await task
        self.assertEqual(status, 200, result)
        self.assertEqual(result["text"], "A public biography")

    async def test_short_window_is_not_legacy_archive_or_dna(self):
        await self.history.async_append_exchange(
            "ha-user",
            {"client_message_id": "legacy", "text": "LEGACY PRIVATE"},
            {"text": "LEGACY BODY"},
        )
        for i in range(20):
            result, status = await self.request(
                "A general music discussion " + str(i), identifier=f"long-{i}"
            )
            self.assertEqual(status, 200, result)
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        self.assertLessEqual(len(frame.messages), 12)
        self.assertLessEqual(self.dialogue.encoded_size(frame.messages), 12 * 1024)
        self.assertNotIn("LEGACY", json.dumps(self.prompts))
        self.assertEqual(
            len((await self.history.async_history("profile:profile-a"))["messages"]), 40
        )

    async def test_controls_do_not_reset_subject_and_make_zero_agent_calls(self):
        await self.request("Who is Brian Eno?")
        before = deepcopy(self.history.dialogue.owners["profile:profile-a"]["default"].messages)

        async def control(*args, **kwargs):
            return {"success": True, "text": "Volume request dispatched"}

        with patch.object(self.core, "_handle_action", control):
            result, status = await self.request("Zet zachter", identifier="control")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["conversation"]["metrics"]["agent_calls"], 0)
        self.assertEqual(
            self.history.dialogue.owners["profile:profile-a"]["default"].messages, before
        )
        _, status = await self.request("What influence did he have?", identifier="followup")
        self.assertEqual(status, 200)
        self.assertIn("Who is Brian Eno?", json.dumps(self.prompts[-1]))

    async def test_new_topic_detaches_prior_source_dependencies(self):
        session, _moment, target = await self.selected_credit()
        await self.request("Who is that?", context={"selected_entry": target})
        _, status = await self.request("Who is Miles Davis?", identifier="new-topic")
        self.assertEqual(status, 200)
        self.assertEqual(self.prompts[-1]["recent_turns"], [])
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        self.assertEqual(frame.dependencies, [])
        self.assertEqual(frame.subjects, [])
        await self.fixture.repo.async_remove_entry_records("profile-a", [target["entry_id"]])
        _, status = await self.request("What influence did he have?", identifier="new-followup")
        self.assertEqual(status, 200)
        self.assertIn("Miles Davis", json.dumps(self.prompts[-1]))
        self.assertNotIn("Brian Eno", json.dumps(self.prompts[-1]))

    async def test_profile_clear_revalidates_owner_after_waiting_for_history_writer(self):
        await self.request("Who is Brian Eno?")
        storage = self.handlers.profile_storage(self.hass)
        await storage.async_create_profile("Other", profile_id="profile-new", default_backend_id="later_manual")
        entered = asyncio.Event()
        clear = self.history.async_clear
        async def observed_clear(*args, **kwargs):
            entered.set()
            return await clear(*args, **kwargs)
        await self.history._write_lock.acquire()
        try:
            with patch.object(self.history, "async_clear", observed_clear):
                task = asyncio.create_task(self.handlers.async_handle_ask_dj_history_clear_payload(self.hass, self.identity, headers=self.headers))
                await asyncio.wait_for(entered.wait(), 2)
                await storage.async_upsert_device(self.identity["device_id"], "ios", linked_profile_id="profile-new")
                self.history._write_lock.release()
                result, status = await task
        finally:
            if self.history._write_lock.locked():
                self.history._write_lock.release()
        self.assertEqual(status, 403, result)
        self.assertEqual(len((await self.history.async_history("profile:profile-a"))["messages"]), 2)
        self.assertTrue(self.history.dialogue.owners["profile:profile-a"]["default"].messages)

    async def test_voice_owner_withdrawal_at_body_stt_and_model_boundaries_leaks_nothing(self):
        from types import SimpleNamespace
        from custom_components.djconnect import http

        storage = self.handlers.profile_storage(self.hass)
        await storage.async_create_profile("Other", profile_id="voice-other", default_backend_id="later_manual")
        self.runtime.update = lambda **values: self.runtime.__dict__.update(values)
        before = await self.history.async_history("profile:profile-a")
        before.pop("server_time", None)
        for boundary in ("body", "stt", "model"):
            with self.subTest(boundary=boundary):
                await storage.async_upsert_device(self.identity["device_id"], "ios", linked_profile_id="profile-a")
                speech_calls = []

                async def withdraw():
                    await storage.async_upsert_device(self.identity["device_id"], "ios", linked_profile_id="voice-other")

                async def read():
                    if boundary == "body":
                        await withdraw()
                    return b"RIFFxxxxWAVEdata"

                async def speech(*args):
                    speech_calls.append(True)
                    if boundary == "stt":
                        await withdraw()
                        raise RuntimeError("Private old-owner STT error")
                    return "Who is Brian Eno?"

                async def model(*args, **kwargs):
                    await withdraw()
                    return {"response": {"speech": {"plain": {"speech": "Private old-owner model answer"}}}}

                request = SimpleNamespace(
                    app={"hass": self.hass}, read=read,
                    headers={**self.headers, "X-DJConnect-Device-ID": self.identity["device_id"],
                        "X-DJConnect-Client-Type": "ios", "Content-Type": "audio/wav", "X-DJConnect-Language": "en"},
                )
                with patch.object(http, "transcribe_wav_with_assist", speech), patch.object(self.pipeline, "_call_conversation_process_transport", model):
                    response = await http.DJConnectVoiceView(self.hass).post(request)
                payload = json.loads(response.text)
                self.assertEqual(response.status, 403, payload)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                for key in ("transcript", "recognized_text", "audio_url", "assistant_message", "conversation"):
                    self.assertNotIn(key, payload)
                self.assertNotIn("Private old-owner", response.text)
                self.assertEqual(len(speech_calls), 0 if boundary == "body" else 1)
                after = await self.history.async_history("profile:profile-a")
                after.pop("server_time", None)
                self.assertEqual(after, before)

    async def test_exact_target_rejects_malformed_unpublished_and_style_changed_proof(self):
        from custom_components.djconnect.track_insight_target import resolve_target
        from custom_components.djconnect.track_insight import TrackInsightError
        from custom_components.djconnect.session_runtime import DJPersona

        session, moment, entry = await self.selected_credit()
        ref = {"schema_version": 1, "session_id": session.session_id, "moment_id": moment.moment_id, "action_id": "insight-" + moment.moment_id}
        for malformed in (True, {}, {**ref, "schema_version": True}, {**ref, "extra": "grant"}, {**ref, "moment_id": ""}):
            response, status = await self.detail(malformed)
            self.assertEqual(status, 400, response)
        with self.assertRaises(TrackInsightError) as denied:
            await resolve_target(self.hass, self.runtime, {}, owner_profile_id="", reference=ref)
        self.assertEqual(denied.exception.status, 403)
        response, status = await self.detail({**ref, "moment_id": "unpublished", "action_id": "insight-unpublished"})
        self.assertEqual(status, 403, response)
        qualified = await resolve_target(self.hass, self.runtime, {"conversation_context": {"selected_entry": entry}}, owner_profile_id="profile-a")
        self.assertEqual(qualified.reference, ref)
        await self.fixture.manager.async_update_persona(owner_profile_id="profile-a", session_id=session.session_id, dj_persona=DJPersona.CLUB_DJ)
        with self.assertRaises(TrackInsightError) as changed:
            qualified.guard()
        self.assertEqual(changed.exception.status, 409)
        self.assertEqual(self.prompts, [])

    async def test_profile_history_state_export_and_clear_share_the_same_namespace(self):
        accepted, status = await self.request("Who is Brian Eno?")
        self.assertEqual(status, 200, accepted)
        state, status = await self.handlers.async_handle_ask_dj_history_state_payload(self.hass, self.identity, headers=self.headers)
        self.assertEqual(status, 200, state)
        export, status = await self.handlers.async_handle_ask_dj_history_export_payload(self.hass, self.identity, headers=self.headers)
        self.assertEqual(status, 200, export)
        self.assertEqual(state["history_revision"], accepted["history_revision"])
        self.assertEqual(export["history_revision"], accepted["history_revision"])
        self.assertEqual(len(export["messages"]), 2)
        self.assertEqual(export["owner_profile_id"], "profile-a")
        for scope, expected in (("legacy", 401), ("typo", 400), ({}, 400)):
            result, status = await self.handlers.async_handle_ask_dj_history_clear_payload(self.hass, {**self.identity, "conversation_scope": scope}, headers=self.headers)
            self.assertEqual(status, expected, result)
        cleared, status = await self.handlers.async_handle_ask_dj_history_clear_payload(self.hass, self.identity, headers=self.headers)
        self.assertEqual(status, 200, cleared)
        state, status = await self.handlers.async_handle_ask_dj_history_state_payload(self.hass, self.identity, headers=self.headers)
        self.assertEqual(status, 200, state)
        self.assertTrue(state["ask_dj_clear_required"])
        self.assertEqual(state["clear_revision"], cleared["clear_revision"])

    async def test_raw_ram_context_does_not_gain_archive_rights_on_message_followup(self):
        self.reply = "A RAM-only discussion of Brian Eno."
        raw, status = await self.handlers.async_handle_ask_dj_message_payload(self.hass, {**self.identity, "client_message_id": "raw", "text": "Who is Brian Eno?", "language": "en", "audio_response": "never"}, headers=self.headers, persist_history=False)
        self.assertEqual(status, 200, raw)
        self.assertFalse(raw["history_persisted"])
        follow, status = await self.request("What influence did he have?", identifier="raw-follow")
        self.assertEqual(status, 200, follow)
        self.assertFalse(follow["history_persisted"])
        self.assertIn("RAM-only", json.dumps(self.prompts[-1]))
        self.assertEqual((await self.history.async_history("profile:profile-a"))["messages"], [])
        topic, status = await self.request("Who is Miles Davis?", identifier="fresh-independent-topic")
        self.assertEqual(status, 200, topic)
        self.assertEqual(self.prompts[-1]["recent_turns"], [])
        self.assertEqual(len((await self.history.async_history("profile:profile-a"))["messages"]), 2)

    async def test_five_language_open_wishes_are_readonly_search_not_play_authority(self):
        from custom_components.djconnect.domain.profile import ProfilePreferences
        await self.handlers.profile_storage(self.hass).async_update_profile("profile-a", preferences=ProfilePreferences(default_backend_id="source-spotify"))
        self.runtime.config["music_backend"] = "spotify_direct"
        examples = (("en", "I'm in the mood for some jazz"), ("nl", "Ik heb zin in jazz"), ("de", "Ich hätte gern etwas Jazz"), ("fr", "J’ai envie de jazz"), ("es", "Me apetece escuchar jazz"))
        async def search(*args, **kwargs):
            return {"tracks": [{"uri": "spotify:track:0123456789abcdefghijkL", "title": "Synthetic", "artist": "Synthetic performer"}]}
        async def command(*args, **kwargs):
            raise AssertionError("An open preference is not playback permission")
        self.reply = json.dumps({"text": "Fixture search request", "intent": "lookup", "query": "jazz"})
        with patch.object(self.core, "_spotify_track_search", search), patch.object(self.core, "run_music_command", command):
            for i, (language, text) in enumerate(examples):
                result, status = await self.request(text, identifier=f"wish-{i}", language=language)
                self.assertEqual(status, 200, result)
                self.assertIn("result_set", result, result)
                self.assertEqual(self.prompts[-1]["requested_operation"], "lookup")
        self.assertEqual(len(self.prompts), 5)

    async def test_clear_storage_failure_is_typed_and_preserves_messages_and_window(self):
        await self.request("Who is Brian Eno?")
        snapshot = deepcopy(self.history.data)
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        generation, messages = frame.generation, deepcopy(frame.messages)
        async def fail(*args, **kwargs):
            raise OSError("Synthetic storage refusal")
        with patch.object(self.history._store, "async_save", fail):
            result, status = await self.handlers.async_handle_ask_dj_history_clear_payload(self.hass, self.identity, headers=self.headers)
        self.assertEqual(status, 503, result)
        self.assertEqual(result["error"], "history_storage_unavailable")
        self.assertEqual(self.history.data, snapshot)
        self.assertEqual(frame.generation, generation)
        self.assertEqual(frame.messages, messages)

    async def test_invalid_structured_model_output_has_no_tool_or_archive_commit(self):
        async def search(*args, **kwargs):
            raise AssertionError("Malformed output cannot grant lookup or playback")
        for i, reply in enumerate(('["jazz"]', '```json\n{"intent":', '{"intent":"lookup","query":"spotify:track:unsafe"}')):
            self.reply = reply
            with patch.object(self.core, "_spotify_track_search", search):
                result, status = await self.request("Explain jazz", identifier=f"invalid-model-{i}")
            self.assertEqual(status, 502, result)
            self.assertEqual(result["error"], "conversation_model_response_invalid")
        self.assertEqual((await self.history.async_history("profile:profile-a"))["messages"], [])

    async def test_malformed_lookup_retry_is_bounded_readonly_and_keeps_invalid_output_out(self):
        calls, lookups = [], []
        async def agent(_hass, data, **kwargs):
            calls.append(data["text"])
            reply = '{"text":"BROKEN_PRIVATE_RESULT"},"intent":"lookup"}' if len(calls) == 1 else '{"intent":"lookup","query":"acoustic jazz"}'
            return {"response": {"speech": {"plain": {"speech": reply}}}}
        async def search(*args, **kwargs):
            lookups.append(True)
            return {"success": True, "tracks": [{"uri": "spotify:track:" + "a" * 22, "title": "Synthetic track", "artist": "Synthetic artist"}]}
        with patch.object(self.pipeline, "_call_conversation_process_transport", agent), patch.object(self.core, "_spotify_track_search", search):
            result, status = await self.request("Suggest acoustic jazz songs to search for, keeping playback unchanged.", identifier="format-retry")
        self.assertEqual(status, 200, result)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(lookups), 1)
        self.assertNotIn("BROKEN_PRIVATE_RESULT", calls[1])
        self.assertEqual(result["conversation"]["metrics"]["agent_calls"], 2)
        self.assertEqual(len((await self.history.async_history("profile:profile-a"))["messages"]), 2)

        self.reply = '{"intent":'
        self.prompts.clear()
        result, status = await self.request("Suggest live jazz songs to search for, keeping playback unchanged.", identifier="format-retry-fails")
        self.assertEqual(status, 502, result)
        self.assertEqual(len(self.prompts), 2)
        self.assertEqual(len((await self.history.async_history("profile:profile-a"))["messages"]), 2)

    async def test_model_query_cannot_replace_a_biography_answer_or_grant_a_lookup(self):
        calls = []
        async def agent(_hass, data, **kwargs):
            calls.append(data["text"])
            reply = '{"intent":"lookup","query":"Miles Davis"}' if len(calls) == 1 else "Miles Davis was an American jazz trumpeter and bandleader."
            return {"response": {"speech": {"plain": {"speech": reply}}}}
        async def search(*args, **kwargs):
            raise AssertionError("A biography request grants no catalog lookup")
        with patch.object(self.pipeline, "_call_conversation_process_transport", agent), patch.object(self.core, "_spotify_track_search", search):
            result, status = await self.request("Who is Miles Davis?", identifier="answer-not-query")
        self.assertEqual(status, 200, result)
        self.assertIn("trumpeter", result["text"])
        self.assertNotIn("result_set", result)
        self.assertEqual(len(calls), 2)

    async def test_clear_while_agent_pending_rejects_response_and_future_context(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {"response": {"speech": {"plain": {"speech": "cleared answer"}}}}

        with patch.object(self.pipeline, "_call_conversation_process_transport", delayed):
            task = asyncio.create_task(self.request("A private music question"))
            await asyncio.wait_for(entered.wait(), 2)
            await self.history.async_clear("profile:profile-a")
            release.set()
            result, status = await task
        self.assertEqual(status, 409, result)
        self.assertEqual((await self.history.async_history("profile:profile-a"))["messages"], [])
        _, status = await self.request("Another question", identifier="after-clear")
        self.assertEqual(status, 200)
        self.assertEqual(self.prompts[-1]["recent_turns"], [])

    async def test_duplicate_inflight_joins_and_different_question_is_busy(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {"response": {"speech": {"plain": {"speech": "one accepted answer"}}}}

        with patch.object(self.pipeline, "_call_conversation_process_transport", delayed):
            first = asyncio.create_task(self.request("An open music question"))
            await asyncio.wait_for(entered.wait(), 2)
            duplicate = asyncio.create_task(self.request("An open music question"))
            busy, status = await self.request("Another open question", identifier="other")
            self.assertEqual(status, 409, busy)
            self.assertEqual(busy["error"], "conversation_busy")
            release.set()
            a, b = await asyncio.gather(first, duplicate)
        self.assertEqual(a, b)
        self.assertEqual(
            len((await self.history.async_history("profile:profile-a"))["messages"]), 2
        )

    async def test_private_mode_has_usable_short_window_without_store_body(self):
        result, status = await self.request("Who is Brian Eno?", privacy_mode="private")
        self.assertEqual(status, 200, result)
        self.assertFalse(result["history_persisted"])
        self.assertEqual((await self.history.async_history("profile:profile-a"))["messages"], [])
        result, status = await self.request(
            "What influence did he have?", identifier="private-followup", privacy_mode="private"
        )
        self.assertEqual(status, 200, result)
        self.assertIn("Brian Eno", json.dumps(self.prompts[-1]))

    async def test_expired_or_other_thread_choices_fail_and_never_research(self):
        frame = self.history.dialogue.frame("profile:profile-a", "default", "seed")
        # No actual shown/current set exists; an ordinal cannot mint or re-search one.
        result, status = await self.request("the second")
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"], "choice_expired")
        self.assertEqual(self.prompts, [])
        self.assertIsNone(frame.result_set)

    async def test_opaque_effect_receipt_survives_clear_and_reload_and_fails_closed(self):
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager

        digest = "d" * 64
        await self.history.async_reserve_dialogue_effect("profile:profile-a", "effect-id", digest)
        await self.history.async_clear("profile:profile-a")
        reloaded = AskDJHistoryManager(store=self.history._store)
        await reloaded.async_load()
        with self.assertRaises(self.dialogue.DialogueError) as caught:
            await reloaded.async_reserve_dialogue_effect("profile:profile-a", "effect-id", digest)
        self.assertEqual(caught.exception.code, "action_outcome_uncertain")
        encoded = json.dumps(reloaded.data)
        self.assertNotIn("effect-id", encoded)
        self.assertNotIn("spotify:", encoded)
        state = reloaded._user_state("profile:profile-a")
        state["dialogue_effect_receipts"] = {f"{i:064x}": "d" * 64 for i in range(1000)}
        with self.assertRaises(self.dialogue.DialogueError) as full:
            await reloaded.async_reserve_dialogue_effect("profile:profile-a", "new-effect", digest)
        self.assertEqual(full.exception.code, "action_receipt_capacity")

    async def test_prompt_caps_and_source_rights(self):
        source = {
            "archive_basis": "cc0_normalized_fields_v1",
            "text": "Spotify private catalog",
            "source_attribution": {
                "provider": "Spotify",
                "license": "CC0-1.0",
                "url": "https://open.spotify.com/track/x",
            },
        }
        self.assertEqual(self.dialogue.model_source(source), {})
        result, status = await self.request(
            "Who is Brian Eno?", mood=75, dj_style="late_night", dj_persona="radio_dj"
        )
        self.assertEqual(status, 200, result)
        style = result["conversation"]["style"]
        self.assertEqual(style["persona"], "radio_dj")
        self.assertEqual(style["mood"], "energy")
        self.assertLessEqual(result["conversation"]["metrics"]["prompt_bytes"], 24 * 1024)
        self.assertNotIn("synthetic-fixture-token", json.dumps(self.prompts))

    async def test_ram_capacity_ttl_and_pending_staging(self):
        clock = [0.0]
        owner = self.dialogue.DialogueState(clock=lambda: clock[0])
        for i in range(32):
            for t in range(4):
                owner.frame(f"owner-{i}", str(t), "generation")
        with self.assertRaises(self.dialogue.DialogueError):
            owner.frame("owner-overflow", "default", "g")
        clock[0] = 1201
        self.assertIsNotNone(owner.frame("new-owner", "default", "g"))
        self.assertEqual(len(owner.owners), 1)
        self.assertEqual(len(owner.owners["new-owner"]), 1)

    async def test_failed_response_does_not_activate_pending_confirmation(self):
        async def failed(h, r, p, **kwargs):
            await self.core._store_pending_followup(
                r,
                p,
                question="proposed only",
                proposed_intent="play",
                proposed_action="ask_dj_play_recommendation",
                proposed_payload={"uri": "spotify:track:" + "a" * 22},
            )
            return {"success": False, "error": "fixture_generation_failed"}

        with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", failed):
            result, _ = await self.request("An open music question")
        self.assertFalse(result["success"])
        self.assertIsNone(self.history.dialogue.owners["profile:profile-a"]["default"].pending)

    async def test_runtime_replacement_fences_original_inflight_delegate(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {"response": {"speech": {"plain": {"speech": "old runtime answer"}}}}

        with patch.object(self.pipeline, "_call_conversation_process_transport", delayed):
            task = asyncio.create_task(self.request("An open music question"))
            await asyncio.wait_for(entered.wait(), 2)
            from copy import copy

            replacement = copy(self.runtime)
            self.hass.data["djconnect"].update({"runtime": replacement, "owner-entry": replacement})
            release.set()
            result, status = await task
        self.assertEqual(status, 409, result)
        self.assertEqual((await self.history.async_history("profile:profile-a"))["messages"], [])

    async def test_live_only_followup_keeps_subject_without_archiving(self):
        session, moment, _target = await self.selected_credit()
        context = {
            "session_id": session.session_id,
            "selected_moment": {"session_id": session.session_id, "moment_id": moment.moment_id},
        }
        first, status = await self.request("Who is that?", context=context)
        self.assertEqual(status, 200, first)
        self.assertFalse(first["history_persisted"])
        second, status = await self.request(
            "What influence did he have?",
            identifier="live-followup",
            context={"session_id": session.session_id},
        )
        self.assertEqual(status, 200, second)
        self.assertFalse(second["history_persisted"])
        self.assertIn("Brian Eno", json.dumps(self.prompts[-1]["relevant_subjects"]))
        self.assertTrue(self.prompts[-1]["recent_turns"])
        self.assertEqual((await self.history.async_history("profile:profile-a"))["messages"], [])

    async def test_explicit_band_articles_override_stale_chip_in_five_languages(self):
        for i, (language, question) in enumerate(
            (
                ("en", "Tell me about the Beatles"),
                ("nl", "Vertel me over de Beatles"),
                ("de", "Erzähl mir über die Beatles"),
                ("fr", "Parle-moi de la carrière des Beatles"),
                ("es", "¿Quién es David Bowie?"),
            )
        ):
            result, status = await self.request(
                question,
                identifier=f"new-band-{i}",
                language=language,
                context={"selected_entry": {"session_id": "gone", "entry_id": "gone"}},
            )
            self.assertEqual(status, 200, result)
            self.assertEqual(self.prompts[-1]["context"], {})
            self.assertEqual(self.prompts[-1]["recent_turns"], [])
            self.assertNotIn("selected_entry", result["conversation"]["context"])

    async def test_selected_choice_survives_control_then_play_in_five_languages(self):
        for i, (language, selection, play_text) in enumerate(
            (
                ("en", "the second", "play it"),
                ("nl", "de tweede", "speel af"),
                ("de", "die zweite", "spiel ab"),
                ("fr", "le deuxième", "mets-le"),
                ("es", "el segundo", "reprodúcelo"),
            )
        ):

            async def found(*args, **kwargs):
                actions = [
                    {
                        "kind": "track",
                        "title": f"Fixture {j}",
                        "uri": "spotify:track:" + str(j) * 22,
                    }
                    for j in range(3)
                ]
                return {
                    "success": True,
                    "text": "Actual provider-shaped order",
                    "playback_actions": actions,
                }

            with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", found):
                result, status = await self.request(
                    "Find versions", identifier=f"found-{i}", language=language
                )
            self.assertEqual(status, 200, result)
            chosen, status = await self.request(
                selection, identifier=f"selected-{i}", language=language
            )
            self.assertEqual(status, 200, chosen)
            self.assertEqual(
                chosen["selected_action_id"], result["result_set"]["items"][1]["action_id"]
            )

            async def control(*args, **kwargs):
                return {"success": True, "text": "Quieter"}

            with patch.object(self.core, "_handle_action", control):
                await self.request("Zet zachter", identifier=f"volume-{i}", language=language)
            dispatched = []

            async def provider_effect(h, r, action, payload):
                await self.dialogue.guard_effect_dispatch()
                dispatched.append(action["uri"])
                return {
                    "success": True,
                    "text": "Provider dispatch fixture",
                    "action_outcome": "dispatched",
                }

            from custom_components.djconnect import http

            with patch.object(http, "_handle_ask_dj_play_recommendation", provider_effect):
                played, status = await self.request(
                    play_text, identifier=f"play-{i}", language=language
                )
            self.assertEqual(status, 200, played)
            self.assertEqual(dispatched, ["spotify:track:" + "1" * 22])
            self.assertEqual(played["selected_action_id"], chosen["selected_action_id"])
        self.assertEqual(self.prompts, [])

    async def test_clear_during_actual_adapter_token_wait_prevents_effect_and_receipt(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        entered, release = asyncio.Event(), asyncio.Event()
        dispatched = []
        backend = object.__new__(SpotifyBackend)
        backend.hass, backend.runtime = self.hass, self.runtime

        class Transport:
            def request(self, *args, **kwargs):
                dispatched.append(args)
                raise AssertionError("A revoked action must never reach the network")

        backend.session = Transport()

        async def token(**kwargs):
            entered.set()
            await release.wait()
            return "SYNTHETIC_TOKEN_NOT_SENT"

        backend._access_token = token

        async def control(*args, **kwargs):
            await backend.pause()
            return {"success": True, "text": "Paused"}

        with patch.object(self.core, "_handle_action", control):
            task = asyncio.create_task(self.request("Pause", identifier="delayed-token"))
            await asyncio.wait_for(entered.wait(), 2)
            await self.history.async_clear("profile:profile-a")
            release.set()
            result, status = await task
        self.assertEqual(status, 409, result)
        self.assertEqual(dispatched, [])
        self.assertEqual(
            self.history._user_state("profile:profile-a").get("dialogue_effect_receipts", {}), {}
        )

    async def test_double_cancellation_settles_receipt_write_before_next_writer(self):
        entered, release = asyncio.Event(), asyncio.Event()
        store = self.history._store
        save = store.async_save
        calls = []

        async def delayed(data):
            calls.append(deepcopy(data))
            if len(calls) == 1:
                entered.set()
                await release.wait()
            await save(data)

        with patch.object(store, "async_save", delayed):
            task = asyncio.create_task(
                self.history.async_reserve_dialogue_effect(
                    "profile:profile-a", "cancelled-effect", "d" * 64
                )
            )
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            retry = asyncio.create_task(
                self.history.async_reserve_dialogue_effect(
                    "profile:profile-a", "cancelled-effect", "d" * 64
                )
            )
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertFalse(retry.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            with self.assertRaises(self.dialogue.DialogueError):
                await retry
        self.assertEqual(len(calls), 1)
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager

        reloaded = AskDJHistoryManager(store=store)
        with self.assertRaises(self.dialogue.DialogueError):
            await reloaded.async_reserve_dialogue_effect(
                "profile:profile-a", "cancelled-effect", "d" * 64
            )

    async def detail(self, reference, *, language="en", **options):
        return await self.handlers.async_handle_track_insight_payload(
            self.hass,
            {**self.identity, "track_insight_target": reference, "language": language, **options},
            headers=self.headers,
        )

    async def test_published_navigation_exact_target_and_shared_full_cache_after_a_to_b(self):
        session, moment, _entry = await self.selected_credit()
        before = len(session.broadcast.state.dj_moments)
        publication = session.broadcast.native_delivery()
        admitted = next(a for a in publication["admissions"] if a["moment_id"] == moment.moment_id)
        action = admitted["navigation_actions"][0]
        self.assertEqual(action["target"], "track_insight")
        self.assertEqual(admitted["executable_actions"], [])
        self.assertEqual(moment.as_dict()["actions"], [])
        self.assertNotIn("open_screen", json.dumps(moment.as_dict()))
        await self.fixture.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity="spotify:track:" + "1" * 22,
            title="B different version",
            artist="B performer",
            duration_ms=300000,
            position_ms=1000,
        )
        self.runtime.device_status["demo_mode"] = True
        prompts = []

        async def agent(hass, data, **kwargs):
            prompts.append(data["text"])
            self.assertNotIn("Synthetic performer", data["text"])
            self.assertNotIn("spotify:", data["text"])
            return {
                "response": {
                    "speech": {
                        "plain": {
                            "speech": json.dumps(
                                {
                                    "summary": "Qualified composer context",
                                    "full_text": "Composer credit with labelled interpretation.",
                                    "listening_cues": ["Optional texture listening."],
                                }
                            )
                        }
                    }
                }
            }

        with patch.object(self.pipeline, "_call_conversation_process_transport", agent):
            first, status = await self.detail(action["reference"])
            self.assertEqual(status, 200, first)
            second, status = await self.detail(action["reference"])
            self.assertEqual(status, 200, second)
        self.assertEqual(len(prompts), 1)
        self.assertFalse(first["cache"]["hit"])
        self.assertTrue(second["cache"]["hit"])
        for result in (first, second):
            self.assertEqual(result["track"]["title"], "Synthetic work")
            self.assertEqual(result["subject"]["media_identity"], moment.source_fact.media_identity)
            self.assertFalse(result["track"]["is_playing"])
            self.assertIsNone(result["track"]["progress_ms"])
            self.assertIsNone(result["analysis"]["energy"])
            self.assertEqual(result["analysis"]["verified_context"], moment.content)
            self.assertNotIn("_owner_scope", result["track"])
        self.assertEqual(len(session.broadcast.state.dj_moments), before)

    async def test_target_foreign_expired_and_session_end_fail_without_fallback(self):
        session, moment, _ = await self.selected_credit()
        from custom_components.djconnect.track_insight_target import resolve_target

        ref = {
            "schema_version": 1,
            "session_id": session.session_id,
            "moment_id": moment.moment_id,
            "action_id": "insight-" + moment.moment_id,
        }
        from custom_components.djconnect.track_insight import TrackInsightError

        with self.assertRaises(TrackInsightError):
            await resolve_target(
                self.hass,
                self.runtime,
                {"track_insight_target": ref},
                owner_profile_id="profile-other",
            )
        from custom_components.djconnect import track_insight_target

        now = track_insight_target.time.monotonic()
        with patch.object(track_insight_target.time, "monotonic", return_value=now + 601):
            result, status = await self.detail(ref)
            self.assertEqual(status, 410, result)
        await self.fixture.manager.async_end(
            owner_profile_id="profile-a", session_id=session.session_id
        )
        result, status = await self.detail(ref)
        self.assertEqual(status, 410, result)
        self.assertEqual(self.prompts, [])

    async def test_target_fetch_stays_a_during_track_change_but_end_discards_cache(self):
        session, moment, _ = await self.selected_credit()
        ref = {
            "schema_version": 1,
            "session_id": session.session_id,
            "moment_id": moment.moment_id,
            "action_id": "insight-" + moment.moment_id,
        }
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {
                "response": {
                    "speech": {
                        "plain": {
                            "speech": '{"summary":"Credit context","full_text":"Interpreted context."}'
                        }
                    }
                }
            }

        with patch.object(self.pipeline, "_call_conversation_process_transport", delayed):
            task = asyncio.create_task(self.detail(ref))
            await asyncio.wait_for(entered.wait(), 3)
            await self.fixture.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=session.session_id,
                state="playing",
                media_identity="spotify:track:" + "2" * 22,
                title="B",
                artist="Other",
                duration_ms=300000,
                position_ms=0,
            )
            release.set()
            result, status = await task
        self.assertEqual(status, 200, result)
        self.assertEqual(result["track"]["title"], "Synthetic work")
        # A cache variant for a new language really fetches; a closed Session cannot commit it.
        entered.clear()
        release.clear()
        with patch.object(self.pipeline, "_call_conversation_process_transport", delayed):
            task = asyncio.create_task(self.detail(ref, language="nl"))
            await asyncio.wait_for(entered.wait(), 3)
            await self.fixture.manager.async_end(
                owner_profile_id="profile-a", session_id=session.session_id
            )
            release.set()
            result, status = await task
        self.assertEqual(status, 410, result)
        self.assertEqual(len(getattr(self.runtime, "track_insight_cache", {})), 1)

    async def test_exact_cache_identity_retains_case_sensitive_recording_ids(self):
        from custom_components.djconnect.track_insight import _cache_key, TrackInsightCache

        common = {
            "title": "Same title",
            "artist": "Same artist",
            "album": "Same release",
            "_owner_scope": "owner",
        }
        a = {
            **common,
            "uri": "spotify:track:" + "A" * 22,
            "media_identity": "spotify:track:" + "A" * 22,
        }
        b = {
            **common,
            "uri": "spotify:track:" + "a" * 22,
            "media_identity": "spotify:track:" + "a" * 22,
        }
        self.assertNotEqual(_cache_key(a), _cache_key(b))
        cache = TrackInsightCache(self.runtime)
        cache.set(_cache_key(a), {"track": a, "analysis": {"summary": "A edition"}, "cache": {}})
        self.assertIsNone(cache.get(_cache_key(b)))
        self.assertEqual(cache.get(_cache_key(a))["analysis"]["summary"], "A edition")

    async def test_explicit_other_track_keeps_existing_route_with_current_qualified_moment(self):
        await self.selected_credit()
        result, status = await self.handlers.async_handle_track_insight_payload(
            self.hass,
            {
                **self.identity,
                "title": "B explicit version",
                "artist": "B explicit performer",
                "language": "en",
            },
            headers=self.headers,
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["track"]["title"], "B explicit version")
        self.assertEqual(result["track"]["artist"], "B explicit performer")
        self.assertNotIn("subject", result)
        self.assertIsNone(result["analysis"]["energy"])
        self.assertEqual(self.prompts, [])

    async def test_target_pairing_withdrawal_during_fetch_discards_detail_and_cache(self):
        session, moment, _ = await self.selected_credit()
        ref = {
            "schema_version": 1,
            "session_id": session.session_id,
            "moment_id": moment.moment_id,
            "action_id": "insight-" + moment.moment_id,
        }
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {
                "response": {
                    "speech": {
                        "plain": {"speech": '{"summary":"Context","full_text":"Interpreted."}'}
                    }
                }
            }

        with patch.object(self.pipeline, "_call_conversation_process_transport", delayed):
            task = asyncio.create_task(self.detail(ref))
            await asyncio.wait_for(entered.wait(), 3)
            self.runtime.authorize_device_request = lambda *args, **kwargs: False
            release.set()
            result, status = await task
        self.assertEqual(status, 401, result)
        self.assertEqual(getattr(self.runtime, "track_insight_cache", {}), {})

    async def test_choice_expiring_during_receipt_never_reaches_actual_adapter(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        tick = [self.history.dialogue.clock()]
        self.history.dialogue.clock = lambda: tick[0]

        async def found(*args, **kwargs):
            return {
                "success": True,
                "text": "Shown result",
                "playback_actions": [
                    {"kind": "track", "uri": "spotify:track:" + "1" * 22, "title": "Frozen version"}
                ],
            }

        with patch.object(self.core, "_handle_informational", found):
            shown, status = await self.request(
                "Explain a shown music selection", identifier="ttl-shown"
            )
        self.assertEqual(status, 200, shown)
        frame = self.history.dialogue.owners["profile:profile-a"]["default"]
        self.assertIsNotNone(frame.result_set)
        original = self.history.async_reserve_dialogue_effect

        async def delayed_reservation(*args, **kwargs):
            await original(*args, **kwargs)
            tick[0] = frame.result_set["deadline"] + 1

        backend = object.__new__(SpotifyBackend)
        backend.hass = self.hass
        backend.runtime = self.runtime
        sent = []

        class Transport:
            def request(self, *args, **kwargs):
                sent.append(args)
                raise AssertionError("Expired result must never reach provider dispatch")

        backend.session = Transport()

        async def token(**kwargs):
            return "SYNTHETIC_NEVER_SENT"

        backend._access_token = token

        async def perform(hass, runtime, action, payload):
            await backend._request_with_token(
                "PUT",
                "/me/player/play",
                json={"uris": [action["uri"]]},
                expected_empty=True,
                force_refresh=False,
                retry_on_unauthorized=False,
            )
            return {"success": True, "text": "Unreachable dispatch"}

        from custom_components.djconnect import http

        with (
            patch.object(self.history, "async_reserve_dialogue_effect", delayed_reservation),
            patch.object(http, "_handle_ask_dj_play_recommendation", perform),
        ):
            result, status = await self.request("Play the first", identifier="ttl-effect")
        self.assertEqual(status, 409, result)
        self.assertEqual(result["error"], "choice_expired")
        self.assertEqual(sent, [])

    async def test_late_source_read_owner_revocation_rolls_back_accepted_exchange(self):
        session, moment, reference = await self.selected_credit()
        from custom_components.djconnect.session_conversation import query_service

        query = query_service(self.hass, self.history)
        original = query.async_open_entry
        calls = [0]

        async def late_read(*args, **kwargs):
            result = await original(*args, **kwargs)
            calls[0] += 1
            # Trigger only after the actual Store exchange has been staged/saved.
            saved = await self.history.async_saved_exchange("profile:profile-a", "late-owner")
            if saved is not None:
                self.runtime.authorize_device_request = lambda *args, **kwargs: False
            return result

        with patch.object(query, "async_open_entry", late_read):
            result, status = await self.request(
                "Who is that?",
                identifier="late-owner",
                context={"session_id": session.session_id, "selected_entry": reference},
            )
        self.assertEqual(status, 401, result)
        self.assertIsNone(
            await self.history.async_saved_exchange("profile:profile-a", "late-owner")
        )
        entries = await self.fixture.queries.async_timeline_page("profile-a", session.session_id)
        self.assertFalse(
            any(e["kind"] in {"conversation_user", "conversation_dj"} for e in entries["entries"])
        )

    async def test_real_pre_dispatch_failure_is_retryable_without_dna(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        backend = object.__new__(SpotifyBackend)
        backend.hass = self.hass
        backend.runtime = self.runtime
        attempts = [0]

        async def token(**kwargs):
            attempts[0] += 1
            if attempts[0] == 1:
                raise RuntimeError("Explicit token-provider fixture fails before any request")
            return "SYNTHETIC_FIXTURE_TOKEN"

        backend._access_token = token
        sent = []

        class Response:
            status = 204

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def text(self):
                return ""

        class Transport:
            def request(self, method, *args, **kwargs):
                sent.append(method)
                return Response()

        backend.session = Transport()

        async def control(*args, **kwargs):
            try:
                await backend.pause()
            except RuntimeError:
                return {
                    "success": True,
                    "text": "Playback could not be requested.",
                    "error": "playback_failed",
                }
            return {
                "success": True,
                "text": "Playback request sent.",
                "action_outcome": {"state": "dispatched"},
            }

        with patch.object(self.core, "_handle_action", control):
            failed, status = await self.request("Pause", identifier="pre-failed")
            self.assertEqual(status, 200, failed)
            self.assertEqual(sent, [])
            frame = self.history.dialogue.owners["profile:profile-a"]["default"]
            self.assertFalse(frame.retry["uncertain"])
            self.assertEqual(
                self.history._user_state("profile:profile-a").get("dialogue_effect_receipts", {}),
                {},
            )
            retried, status = await self.request("Retry", identifier="pre-retry")
        self.assertEqual(status, 200, retried)
        self.assertEqual(sent, ["PUT"])
        self.assertEqual(attempts[0], 2)
        self.assertIsNone(frame.retry)

    async def test_unknown_actual_dispatch_outcome_cannot_be_replayed_by_retry(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        backend = object.__new__(SpotifyBackend)
        backend.hass = self.hass
        backend.runtime = self.runtime

        async def token(**kwargs):
            return "SYNTHETIC_FIXTURE_TOKEN"

        backend._access_token = token
        sent = []

        class Transport:
            def request(self, method, *args, **kwargs):
                sent.append(method)
                raise TimeoutError("Explicit external transport fixture loses the response")

        backend.session = Transport()

        async def control(*args, **kwargs):
            try:
                await backend.pause()
            except TimeoutError:
                return {"success": True, "text": "Outcome unknown.", "error": "playback_failed"}
            raise AssertionError("Lost dispatch cannot be acknowledged")

        with patch.object(self.core, "_handle_action", control):
            failed, status = await self.request("Pause", identifier="unknown-effect")
            self.assertEqual(status, 200, failed)
            retried, status = await self.request("Retry", identifier="unknown-retry")
        self.assertEqual(status, 409, retried)
        self.assertEqual(retried["error"], "action_outcome_uncertain")
        self.assertEqual(sent, ["PUT"])


if __name__ == "__main__":
    unittest.main()
