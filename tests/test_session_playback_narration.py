"""Observed current metadata → one ordinary Planner/Moment opportunity."""
import asyncio
import copy
import sys
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module


class PlaybackNarrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is None:
            sys.modules.pop('custom_components.djconnect.const', None)
        else:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    async def current(self, locale='en', persona=None, *, mismatch=False):
        r = self.runtime
        manager = r.SessionRuntimeManager()
        active = await manager.async_start(owner_profile_id='owner', selected_mood='groove',
            locale=locale, dj_persona=persona or r.DJPersona.HOME_DJ)
        # This short-slot mechanism probe explicitly selects Presenter.
        active = await manager.async_update_presence(owner_profile_id=active.owner_profile_id,
            session_id=active.session_id, selected_presence="presenter")
        async def insight():
            return {'track': {'title': 'Wrong recording' if mismatch else 'Actual recording',
                              'artist': 'Actual artist', 'album': 'Actual edition'},
                    'analysis': {'summary': 'Unmeasured', 'full_text': 'No measured analysis.',
                                 'basis': 'unmeasured_metadata_only_v1'}}
        for index in ('A', 'B'):
            media = 'spotify:track:' + index * 22
            await manager.async_update_playback_projection(owner_profile_id='owner', session_id=active.session_id,
                state='playing', media_identity=media, title='Actual recording', artist='Actual artist',
                album='Actual edition', duration_ms=300000, position_ms=0)
            if index == 'A':
                self.assertIsNone(await manager.async_process_track_started(owner_profile_id='owner',
                    session_id=active.session_id, media_identity=media, require_current_playback=True,
                    insight_provider=insight))
        return manager, active, media, insight

    def test_twenty_connected_persona_language_opportunities_preserve_planner_silence_and_shared_budget(self):
        async def scenario():
            r = self.runtime
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                versions = []
                for persona in r.DJPersona:
                    manager, active, media, insight = await self.current(locale, persona)
                    events = []
                    await manager.async_subscribe(owner_profile_id='owner', session_id=active.session_id,
                        callback=events.append)
                    moment = await manager.async_process_track_started(owner_profile_id='owner',
                        session_id=active.session_id, media_identity=media, require_current_playback=True,
                        insight_provider=insight)
                    self.assertIsNotNone(moment)
                    from tests.speech_capture import capture
                    capture('playback-runtime-opportunities', {'locale': locale, 'persona': persona.value,
                        'moment': moment.as_dict(), 'scope': 'Actual Runtime opportunity including intended Silence/Direction priority.'})
                    if persona is r.DJPersona.CLUB_DJ:
                        self.assertEqual(moment.moment_type, r.DJMomentType.SILENCE)
                        self.assertEqual(dict(moment.generation_metadata)['reason'], 'planned_silence')
                        self.assertEqual(active.presence_ledger.total_published, 0)
                        await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                        continue
                    if persona is r.DJPersona.FESTIVAL_DJ:
                        self.assertEqual(moment.moment_type, r.DJMomentType.SESSION)
                        self.assertEqual(dict(moment.generation_metadata)['direction'], 'building_energy')
                        self.assertEqual(active.presence_ledger.total_published, 1)
                        await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                        continue
                    self.assertEqual(moment.moment_type, r.DJMomentType.TRACK,
                        (locale, persona, moment.as_dict(), active.planning_coordinator.last_fallback_reason))
                    self.assertEqual(moment.presentation_intent.dj_persona, persona)
                    self.assertIn('Actual recording', moment.content)
                    self.assertIn('Actual artist', moment.content)
                    self.assertEqual(moment.observed_playback.item_id, active.broadcast.state.playback.item_id)
                    self.assertEqual(active.presence_ledger.total_published, 1)
                    versions.append(moment.content)
                    admission = next(a for a in active.broadcast.native_delivery()['admissions']
                        if a['moment_id'] == moment.moment_id)
                    self.assertEqual(admission['qualification'], 'qualified')
                    self.assertTrue(admission['current_display_allowed'])
                    self.assertFalse(admission['active_flow_display_allowed'])
                    self.assertTrue(admission['requires_spotify_attribution'])
                    self.assertEqual(dict(moment.source_attribution)['url'], 'https://open.spotify.com/track/' + 'B'*22)
                    self.assertIsNone(await manager.async_process_track_started(owner_profile_id='owner',
                        session_id=active.session_id, media_identity=media, require_current_playback=True,
                        insight_provider=insight))
                    self.assertEqual(active.presence_ledger.total_published, 1)
                    before = moment.as_dict()
                    await manager.async_update_persona(owner_profile_id='owner', session_id=active.session_id,
                        dj_persona=r.DJPersona.FESTIVAL_DJ)
                    self.assertEqual(moment.as_dict(), before)
                    await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                self.assertEqual(len(set(versions)), 2, locale)
        asyncio.run(scenario())

    def test_all_four_personas_have_two_exact_knowledge_realizations_without_committing_style_on_preview(self):
        async def scenario():
            r = self.runtime
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                versions = []
                for persona in r.DJPersona:
                    manager, active, media, insight = await self.current(locale, persona)
                    opportunity = manager._intra_track_opportunities['owner']
                    playback = active.broadcast.state.playback
                    proof = r.ObservedPlaybackNarration(playback.item_id, playback.title, playback.artist,
                        playback.source_url, opportunity.last_observed_monotonic, locale)
                    raw = await insight()
                    raw['_observed_playback'] = proof
                    intent = r.KnowledgeIntent(r.KnowledgeIntentType.TRACK_CONTEXT, 'Approved current context.')
                    knowledge = await active.knowledge_engine.async_assemble_track_context(intent=intent, raw_insight=raw)
                    engine = r.DJMomentEngine()
                    moment = engine.create_track_context(session_id=active.session_id, knowledge_intent=intent,
                        selected_mood='groove', persona=persona, locale=locale, insight=knowledge.as_insight())
                    self.assertEqual(moment.moment_type, r.DJMomentType.TRACK)
                    from tests.speech_capture import capture
                    capture('playback-knowledge-previews', {'locale': locale, 'persona': persona.value,
                        'moment': moment.as_dict(), 'scope': 'Actual Knowledge/Moment realization preview, not publication or native speech.'})
                    self.assertEqual(engine._expression_forms, ())
                    self.assertEqual(active.presence_ledger.total_published, 0)
                    versions.append(moment.content)
                    from custom_components.djconnect.context_expression import playback_copy
                    alternate = playback_copy(locale=locale, persona=persona.value, form=1,
                        title=playback.title, artist=playback.artist)
                    self.assertNotEqual(moment.content, alternate)
                    self.assertIn(playback.title, alternate)
                    self.assertIn(playback.artist, alternate)
                    await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                self.assertEqual(len(set(versions)), 4, locale)
        asyncio.run(scenario())

    def test_missing_or_mismatching_observation_never_mints_an_announcement(self):
        async def scenario():
            r = self.runtime
            manager, active, media, insight = await self.current(mismatch=True)
            moment = await manager.async_process_track_started(owner_profile_id='owner',
                session_id=active.session_id, media_identity=media, require_current_playback=True,
                insight_provider=insight)
            self.assertTrue(moment is None or moment.moment_type is r.DJMomentType.SILENCE)
            self.assertEqual(active.presence_ledger.total_published, 0)
            await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
            manager, active, media, insight = await self.current()
            await manager.async_update_presence(owner_profile_id='owner', session_id=active.session_id,
                selected_presence='music_only')
            self.assertIsNone(await manager.async_process_track_started(owner_profile_id='owner',
                session_id=active.session_id, media_identity=media, require_current_playback=True,
                insight_provider=insight))
            self.assertEqual(active.presence_ledger.total_published, 0)
            await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
        asyncio.run(scenario())

    def test_native_expiry_and_tampering_cannot_renew_original_current_only_proof(self):
        async def scenario():
            from custom_components.djconnect.native_moment_delivery import admission
            manager, active, media, insight = await self.current()
            moment = await manager.async_process_track_started(owner_profile_id='owner',
                session_id=active.session_id, media_identity=media, require_current_playback=True,
                insight_provider=insight)
            boundary = active.broadcast._moment_delivery_boundaries[moment.moment_id]
            def check(value, now):
                return admission(value, boundary, session_id=active.session_id, active=True,
                    flow_ids={moment.moment_id}, playback_item_id=moment.observed_playback.item_id,
                    playing=True, now=now)
            before = copy.deepcopy(moment.as_dict())
            self.assertEqual(check(moment, moment.observed_playback.observed_at+31)['qualification'], 'expired')
            changed = replace(moment, content=moment.content+' Invented additional claim.')
            self.assertEqual(check(changed, boundary.published_monotonic)['qualification'], 'unqualified')
            self.assertEqual(moment.as_dict(), before)
            await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
        asyncio.run(scenario())

    def test_knowledge_preserves_unmeasured_basis_for_unqualified_and_expired_genre(self):
        async def scenario():
            from custom_components.djconnect import session_facts
            r = self.runtime
            media = 'spotify:track:'+'B'*22
            proof = {'source': 'spotify_playback_status', 'backend': 'spotify_direct',
                'media_identity': media, 'title': 'Actual recording', 'artist': 'Actual artist',
                'artist_ids': ['Z'*22], 'genres': ['ambient'], 'is_playing': True,
                'genre_source_expires_at': time.monotonic()+1800}
            fact = session_facts.observed_genre_facts(proof, media_identity=media,
                title='Actual recording', artist='Actual artist')[0]
            for source in (None, replace(fact, source_expires_at=time.monotonic()-1)):
                engine = r.DJKnowledgeEngine()
                raw = {'track': {'title': 'Actual recording', 'artist': 'Actual artist',
                    'genres': ['ambient']}, 'analysis': {'summary': 'Unmeasured',
                    'full_text': 'No measured analysis.', 'basis': 'unmeasured_metadata_only_v1'}}
                if source is not None:
                    raw['_qualified_genre_fact'] = source
                intent = r.KnowledgeIntent(r.KnowledgeIntentType.GENRE_STORY, 'Existing genre opportunity')
                knowledge = await engine.async_assemble_track_context(intent=intent, raw_insight=raw)
                self.assertEqual(dict(knowledge.analysis)['basis'], 'unmeasured_metadata_only_v1')
                result = r.DJMomentEngine().create_track_context(session_id='session', knowledge_intent=intent,
                    selected_mood='groove', persona=r.DJPersona.HOME_DJ, locale='en',
                    insight=knowledge.as_insight())
                self.assertEqual(result.moment_type, r.DJMomentType.SILENCE)
        asyncio.run(scenario())

    def test_existing_exact_id_genre_evidence_uses_fact_native_and_speech_qualification(self):
        async def scenario():
            from custom_components.djconnect import session_speech
            r = self.runtime
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                versions = []
                for persona in r.DJPersona:
                    manager, active, media, insight = await self.current(locale, persona)
                    async def status_genre():
                        raw = await insight()
                        raw['track']['genres'] = ['ambient']
                        raw['_session_narrative_evidence'] = {'source': 'spotify_playback_status',
                            'backend': 'spotify_direct', 'media_identity': media,
                            'artist_ids': ['Z'*22], 'genres': ['ambient'], 'is_playing': True,
                            'genre_source_expires_at': time.monotonic()+1800,
                            'title': 'Actual recording', 'artist': 'Actual artist'}
                        return raw
                    moment = await manager.async_process_track_started(owner_profile_id='owner',
                        session_id=active.session_id, media_identity=media, require_current_playback=True,
                        insight_provider=status_genre)
                    if persona in {r.DJPersona.CLUB_DJ, r.DJPersona.FESTIVAL_DJ}:
                        self.assertEqual(moment.moment_type,
                            r.DJMomentType.SILENCE if persona is r.DJPersona.CLUB_DJ else r.DJMomentType.SESSION)
                        await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                        continue
                    self.assertEqual(moment.moment_type, r.DJMomentType.GENRE, (locale, persona, moment.as_dict()))
                    self.assertEqual(moment.source_fact.key, 'genre_context')
                    self.assertEqual(dict(moment.source_attribution)['url'], 'https://open.spotify.com/artist/'+'Z'*22)
                    self.assertEqual(active.presence_ledger.total_published, 1)
                    descriptor = session_speech.moment_projection(active.broadcast, moment)
                    self.assertTrue(descriptor['manual_allowed'], descriptor)
                    self.assertEqual(''.join(s['text'] for s in descriptor['segments']), moment.content)
                    versions.append(moment.content)
                    await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                self.assertEqual(len(set(versions)), 2, locale)
        asyncio.run(scenario())

    def test_name_only_genre_fallback_without_exact_status_evidence_stays_silent(self):
        async def scenario():
            manager, active, media, insight = await self.current()
            async def name_search_genre():
                raw = await insight()
                raw['track']['genres'] = ['ambient']
                return raw
            moment = await manager.async_process_track_started(owner_profile_id='owner',
                session_id=active.session_id, media_identity=media, require_current_playback=True,
                insight_provider=name_search_genre)
            self.assertTrue(moment is None or moment.moment_type is self.runtime.DJMomentType.SILENCE)
            self.assertEqual(active.presence_ledger.total_published, 0)
            await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
        asyncio.run(scenario())

    def test_existing_discover_genre_track_relation_gets_fresh_current_only_speech_proof(self):
        r = self.runtime
        clock = [100.0]
        async def scenario():
            from custom_components.djconnect import session_speech
            manager = r.SessionRuntimeManager(monotonic_source=lambda: clock[0])
            active = await manager.async_start(owner_profile_id='owner', selected_mood='groove',
                locale='en', session_start_strategy=r.SessionStartStrategy.DISCOVER,
                elapsed_time_source=lambda: clock[0])
            # This short-slot mechanism probe explicitly selects Presenter.
            active = await manager.async_update_presence(owner_profile_id=active.owner_profile_id,
                session_id=active.session_id, selected_presence="presenter")
            moments = []
            for number, title in ((1, 'Baseline'), (2, 'First Light'), (3, 'Second Light')):
                media = 'spotify:track:'+str(number).zfill(22)
                await manager.async_update_playback_projection(owner_profile_id='owner', session_id=active.session_id,
                    state='playing', media_identity=media, title=title, artist='Example Artist',
                    duration_ms=300000, position_ms=0)
                async def existing_status():
                    return {'track': {'title': title, 'artist': 'Example Artist', 'genres': ['ambient'], 'backend': 'spotify_direct'},
                        'analysis': {'summary': 'Unmeasured', 'full_text': 'No measured analysis.',
                            'basis': 'unmeasured_metadata_only_v1'},
                        '_session_narrative_evidence': {'source': 'spotify_playback_status', 'backend': 'spotify_direct',
                            'media_identity': media, 'title': title, 'artist': 'Example Artist',
                            'artist_ids': ['Z'*22], 'genres': ['ambient'], 'is_playing': True,
                            'genre_source_expires_at': time.monotonic()+1800}}
                moment = await manager.async_process_track_started(owner_profile_id='owner', session_id=active.session_id,
                    media_identity=media, insight_provider=existing_status, require_current_playback=True)
                moments.append(moment)
                if number == 2:
                    self.assertIsNotNone(active.planner.discover_narrative_line,
                        (moment.as_dict(), active.planner.discover_event_number))
                if number < 3:
                    clock[0] += 90
            self.assertIsNone(moments[0])
            self.assertEqual(moments[1].moment_type, r.DJMomentType.GENRE)
            self.assertEqual(moments[2].moment_type, r.DJMomentType.TRACK, moments[2].as_dict())
            old = moments[2].observed_playback.observed_at
            self.assertIsNotNone(manager._intra_track_opportunities['owner'].pending_transition)
            actual_approval = manager._intra_track_opportunities['owner'].pending_transition[0]
            clock[0] += 45
            await manager.async_update_playback_projection(owner_profile_id='owner', session_id=active.session_id,
                state='playing', media_identity=media, title=title, artist='Example Artist',
                duration_ms=300000, position_ms=45000)
            await manager.async_maybe_publish_intra_track_moment(owner_profile_id='owner',
                session_id=active.session_id, media_identity=media)
            relations = [m for m in active.broadcast.state.dj_moments if m.moment_type is r.DJMomentType.TRANSITION]
            self.assertEqual(len(relations), 1)
            relation = relations[0]
            self.assertIsNotNone(relation.genre_transition)
            self.assertEqual(moments[2].observed_playback.observed_at, old)
            self.assertEqual(relation.genre_transition.current.observed_at, clock[0])
            self.assertEqual(active.presence_ledger.total_published, 3)
            speech = session_speech.moment_projection(active.broadcast, relation)
            self.assertTrue(speech['manual_allowed'], speech)
            self.assertEqual(''.join(s['text'] for s in speech['segments']), relation.content)
            self.assertIn('First Light', relation.content)
            self.assertIn('Second Light', relation.content)
            self.assertEqual(len(speech['attribution']), 1)
            self.assertIn('url_previous', speech['attribution'][0])
            self.assertFalse(session_speech.moment_projection(active.broadcast, moments[2])['manual_allowed'])
            matrix = []
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                copies = []
                for persona in r.DJPersona:
                    engine = r.DJMomentEngine(moments=(moments[1], moments[2]))
                    preview = engine.create_transition(session_id=active.session_id, approval=actual_approval,
                        selected_mood='groove', persona=persona, locale=locale,
                        current_observed=replace(relation.genre_transition.current, locale=locale))
                    self.assertEqual(preview.moment_type, r.DJMomentType.TRANSITION)
                    self.assertIsNotNone(preview.genre_transition)
                    self.assertEqual(preview.genre_transition.context(), relation.genre_transition.context())
                    self.assertEqual(dict(preview.source_attribution), dict(relation.source_attribution))
                    self.assertEqual(active.presence_ledger.total_published, 3)
                    copies.append(preview.content)
                    matrix.append({'locale': locale, 'persona': persona.value, 'moment': preview.as_dict()})
                self.assertEqual(len(set(copies)), 4, locale)
            import os
            import json
            from pathlib import Path
            if capture := os.environ.get('DJC_SPEECH_MATRIX_CAPTURE_DIR'):
                (Path(capture)/'genre-transition-speech-matrix.json').write_text(json.dumps({
                    'scope': 'One actual Runtime/Planner/Knowledge/Moment/Flow/Broadcast sequence with simulated elapsed time; twenty production Moment Engine realizations reuse its real approval/proofs, not twenty independent Runtime acceptances.',
                    'connected_moments': [m.as_dict() for m in (*moments[1:], relation)],
                    'preview_matrix': matrix}, ensure_ascii=False, indent=2)+'\n')
            await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
        with patch('time.monotonic', lambda: clock[0]):
            asyncio.run(scenario())
