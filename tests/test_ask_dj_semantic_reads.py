"""Semantic read plans exercise actual shared-owner routes; not model-quality proof."""

import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class SemanticReadTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = shared.SharedDialogueTest()
        await self.f.asyncSetUp()

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def test_unlisted_typo_is_interpreted_then_answered_from_fresh_provider(self):
        f = self.f
        prompts, reads = [], []

        async def agent(hass, data, **kwargs):
            prompts.append(json.loads(data["text"].split("\nData:\n", 1)[1]))
            return {"response": {"speech": {"plain": {"speech": json.dumps({
                "read": "artist", "reference": "current", "exclude_current": False
            })}}}}

        async def status(hass, runtime, command, *args, **kwargs):
            reads.append(command)
            return {"success": True, "playback": {"uri": "spotify:track:" + "N" * 22,
                    "artist": "Actual provider artist", "title": "Actual provider recording"}}

        with patch.object(f.pipeline, "_call_conversation_process_transport", agent), patch.object(
            f.core, "run_music_command", status
        ):
            answer, code = await f.request("hee wie zingdt er eigelijk wat nu opstaat?")
        self.assertEqual(code, 200, answer)
        self.assertEqual(answer["intent"]["intent"], "current_artist_information")
        self.assertIn("Actual provider artist", answer["text"])
        self.assertEqual(answer["conversation"]["metrics"]["agent_calls"], 1)
        self.assertGreaterEqual(len(reads), 2)
        self.assertEqual(set(reads), {"status"})
        self.assertEqual(set(prompts[0]), {"question", "language", "available"})
        self.assertNotIn("Actual provider", json.dumps(prompts))
        self.assertFalse(answer.get("playback_actions"))
        self.assertFalse(answer["history_persisted"])

    def test_plan_is_closed_duplicate_safe_and_never_an_effect(self):
        from custom_components.djconnect.ask_dj.semantic_reads import parse_plan
        valid = {"read": "artist", "reference": "current", "exclude_current": False}
        self.assertEqual(parse_plan(json.dumps(valid)).read, "artist")
        for raw in (
            '{"read":"artist","read":"play","reference":"current","exclude_current":false}',
            json.dumps({**valid, "uri": "spotify:track:" + "N" * 22}),
            json.dumps({**valid, "read": "play"}),
            json.dumps({**valid, "reference": "previous"}),
            json.dumps({**valid, "exclude_current": 0}),
            json.dumps({**valid, "exclude_current": True}),
            "```json\n" + json.dumps(valid) + "\n```",
            "x" * 2049,
        ):
            with self.subTest(raw=raw[:100]):
                self.assertIsNone(parse_plan(raw))

    async def test_reported_short_artist_and_singers_questions_read_context_without_claiming_vocal_roles(self):
        async def source(hass, runtime, command, *args, **kwargs):
            self.assertEqual(command, "status")
            return {"success": True, "playback": {"uri": "spotify:track:" + "N" * 22,
                "artist": "Actual credited artists", "title": "Actual recording"}}
        for index, question in enumerate(("wie is de artiest", "wie zijn de zangers")):
            with self.agent({"read": "artist", "reference": "current", "exclude_current": False}), patch.object(
                self.f.core, "run_music_command", source
            ):
                answer, code = await self.f.request(question, language="nl", identifier="short-artist-" + str(index))
            self.assertEqual(code, 200, answer)
            self.assertIn("Actual credited artists", answer["text"])
            self.assertIn("Actual recording", answer["text"])
            self.assertNotIn("zangers", answer["text"])
            self.assertEqual(self.f.effects, [])

    def agent(self, plan, *, inspect=None):
        async def response(hass, data, **kwargs):
            projection = json.loads(data["text"].split("\nData:\n", 1)[1])
            self.f.prompts.append(projection)
            if inspect:
                await inspect(projection)
            return {"response": {"speech": {"plain": {"speech": json.dumps(plan)}}}}
        return patch.object(self.f.pipeline, "_call_conversation_process_transport", response)

    async def test_selected_recording_survives_unrecognized_wording_and_does_not_use_current(self):
        session = await self.f.fixture.observed_session()
        from custom_components.djconnect.session_conversation import query_service
        page = await query_service(self.f.hass, self.f.history).async_timeline_page(
            "profile-a", session.session_id
        )
        observed = next(e for e in page["entries"] if e["kind"] == "playback_observed")
        context = {"session_id": session.session_id,
                   "selected_entry": {"session_id": session.session_id, "entry_id": observed["entry_id"]}}
        with self.agent({"read": "artist", "reference": "selected", "exclude_current": False}):
            answer, code = await self.f.request("even checken, wie maakt de musiek hierbij eigelijk?",
                                                context=context)
        self.assertEqual(code, 200, answer)
        self.assertIn("Metallica", answer["text"])
        self.assertEqual(answer["conversation"]["context"]["selected_entry"], context["selected_entry"])
        self.assertTrue(self.f.prompts[0]["available"]["selected"])
        self.assertNotIn("Metallica", json.dumps(self.f.prompts))

    async def test_invalid_effect_or_missing_selection_never_dispatches_or_retries(self):
        for index, plan in enumerate((
            {"read": "play", "reference": "current", "exclude_current": False},
            {"read": "artist", "reference": "selected", "exclude_current": False},
            {"read": "artist", "reference": "current", "exclude_current": False, "command": "play"},
        )):
            before = len(self.f.prompts)
            with self.agent(plan):
                answer, code = await self.f.request("hee wie zingdt er eigelijk wat nu opstaat?",
                                                    identifier="invalid-" + str(index))
            self.assertEqual(code, 200, answer)
            self.assertEqual(len(self.f.prompts) - before, 1)
            self.assertEqual(answer["knowledge_basis"], "public_subject_required")
            self.assertFalse(answer.get("playback_actions"))
        self.assertEqual(self.f.effects, [])

    async def test_clear_during_interpretation_rejects_before_read(self):
        async def clear(projection):
            await self.f.history.async_clear("profile:profile-a")
        with self.agent({"read": "artist", "reference": "current", "exclude_current": False}, inspect=clear):
            answer, code = await self.f.request("hee wie zingdt er eigelijk wat nu opstaat?")
        self.assertEqual(code, 409, answer)
        self.assertFalse(answer.get("success"))
        self.assertEqual(self.f.effects, [])

    async def test_session_end_during_interpretation_cannot_rebind_to_new_context(self):
        session = await self.f.fixture.observed_session()
        async def end(projection):
            await self.f.fixture.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        with self.agent({"read": "artist", "reference": "current", "exclude_current": False}, inspect=end):
            answer, code = await self.f.request("hee wie zingdt er eigelijk wat nu opstaat?")
        self.assertEqual(code, 409, answer)
        self.assertEqual(self.f.effects, [])

    async def test_inherited_cc0_subject_does_not_override_semantic_current_artist(self):
        session, moment, selection = await self.f.selected_credit("Brian Eno")
        async def status(hass, runtime, command, *args, **kwargs):
            self.assertEqual(command, "status")
            return {"success": True, "playback": {"uri": "spotify:track:0123456789abcdefghijkL",
                    "artist": "Actual current performer", "title": "Actual current recording"}}
        plan = {"read": "artist", "reference": "current", "exclude_current": False}
        with patch.object(self.f.core, "run_music_command", status), self.agent(plan):
            answer, code = await self.f.request("wie maakt dit nu eigelijk?",
                                                context={"selected_entry": selection}, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertIn("Actual current performer", answer["text"])
        self.assertNotIn("Brian Eno", answer["text"])
        self.assertEqual(len(self.f.prompts), 1)
        self.assertIn("read_context_available", self.f.prompts[0])
        self.assertEqual(answer["conversation"]["metrics"]["agent_calls"], 1)

    async def test_no_session_to_new_session_during_forecast_interpretation_is_rejected(self):
        async def start(projection):
            await self.f.fixture.observed_session()
        with self.agent({"read": "forecast", "reference": "none", "exclude_current": False}, inspect=start):
            answer, code = await self.f.request("hoe ziet jouw dj plan voor dit luisterblok eruit?")
        self.assertEqual(code, 409, answer)
        self.assertEqual(answer["error"], "session_context_changed")
        self.assertEqual(self.f.effects, [])

    def test_golden_case_vocabulary_never_becomes_runtime_recognition(self):
        from scripts.verification.askdj_semantic_read_golden import cases
        from custom_components.djconnect.ask_dj.dialogue import requests_lookup
        from custom_components.djconnect.ask_dj.public_research import explicit_public_subject, safe_subject
        from collections import Counter
        rows = cases()
        self.assertEqual(Counter(c["language"] for c in rows), dict.fromkeys(("en", "nl", "de", "fr", "es"), 11))
        for case in rows:
            self.assertEqual(self.f.core.classify_ask_dj(case["question"]).intent, "ask_music_info", case)
            self.assertFalse(requests_lookup(case["question"]), case)
            named = explicit_public_subject(case["question"])
            if case["unqualified_subject_capture"]:
                self.assertTrue(named, case)
                self.assertFalse(safe_subject(named), case)
            else:
                self.assertFalse(named, case)

    async def test_question_clause_captured_as_name_does_not_block_semantic_interpretation(self):
        from scripts.verification.askdj_semantic_read_golden import cases
        async def status(hass, runtime, command, *args, **kwargs):
            return {"success": True, "playback": {"uri": "spotify:track:" + "N" * 22,
                    "artist": "Actual performer", "title": "Actual recording"}}
        with patch.object(self.f.core, "run_music_command", status), self.agent(
            {"read": "artist", "reference": "current", "exclude_current": False}
        ):
            for case in (c for c in cases() if c["unqualified_subject_capture"]):
                answer, code = await self.f.request(case["question"], identifier=case["id"], language=case["language"])
                self.assertEqual(code, 200, answer)
                self.assertIn("Actual performer", answer["text"])
                self.assertEqual(answer["conversation"]["metrics"]["agent_calls"], 1)

    async def test_unqualified_name_capture_keeps_selected_recording(self):
        session = await self.f.fixture.observed_session()
        from custom_components.djconnect.session_conversation import query_service
        page = await query_service(self.f.hass, self.f.history).async_timeline_page("profile-a", session.session_id)
        entry = next(e for e in page["entries"] if e["kind"] == "playback_observed")
        context = {"selected_entry": {"session_id": session.session_id, "entry_id": entry["entry_id"]}}
        with self.agent({"read": "artist", "reference": "selected", "exclude_current": False}):
            answer, code = await self.f.request("Wie is degene die dit hier zo mooi zingt?", context=context, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertIn("Metallica", answer["text"])
        self.assertEqual(answer["conversation"]["context"]["selected_entry"], context["selected_entry"])

    async def test_recording_question_on_artist_only_selection_never_claims_artist_is_a_title(self):
        from custom_components.djconnect import session_facts
        uri = "spotify:track:" + "A" * 22
        manager = self.f.fixture.manager
        session = await manager.async_start(owner_profile_id="profile-a", locale="nl",
                                           selected_mood="groove", music_backend="spotify_direct")
        await manager.async_update_playback_projection(owner_profile_id="profile-a", session_id=session.session_id,
            state="playing", media_identity=uri, title="Recording", artist="Selected group", duration_ms=300000, position_ms=1000)
        fact = session_facts._fact("artist_begin", {"uri": uri}, "artist_story", ["Selected group"] * 5,
            ["Selected group formed in 2000.", "Selected group is opgericht in 2000.",
             "Selected group wurde 2000 gegründet.", "Selected group a été formé en 2000.",
             "Selected group se formó en 2000."], "MusicBrainz",
            "https://musicbrainz.org/artist/11111111-1111-1111-1111-111111111111",
            session_facts.DisplayFactCore("artist_begin", "Selected group", date="2000", precision="year", entity_type="Group"))
        async def facts():
            return {"_qualified_facts": (fact,)}
        moment = await manager.async_process_track_started(owner_profile_id="profile-a", session_id=session.session_id,
            media_identity=uri, insight_provider=facts, require_current_playback=True, allow_initial_facts=True)
        context = {"selected_moment": {"session_id": session.session_id, "moment_id": moment.moment_id}}
        with self.agent({"read": "recording", "reference": "selected", "exclude_current": False}):
            answer, code = await self.f.request("hoe heet het liedjuh hierbij nou?", context=context, language="nl")
        self.assertEqual(code, 200, answer)
        self.assertIn("opname", answer["text"])
        self.assertNotEqual(answer["text"], "Dit is Selected group.")
        self.assertEqual(answer["conversation"]["context"]["selected_moment"], context["selected_moment"])
        self.assertFalse(answer.get("playback_actions"))
