"""Actual existing Core projections for the avatar; no native/touch proof."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module

ROOT = Path(__file__).resolve().parents[1]


def scenario_helper():
    path = ROOT / 'tools/verification/persona_avatar_signals.py'
    spec = importlib.util.spec_from_file_location('djc_avatar_signals', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PersonaAvatarProducerSignalTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_original_signal_derivative_matches_actual_core_trace(self):
        produced = await scenario_helper().build(self.runtime)
        fixture = ROOT / 'examples/client_contracts/persona_living_avatar_v1/existing-signals.json'
        self.assertEqual(produced, json.loads(fixture.read_text()))
        self.assertEqual(produced['touch_reactions'], 'NOT_IMPLEMENTED_NOT_ADVERTISED')
        self.assertEqual(produced['native'], 'NOT_RUN')

    async def test_four_personas_four_moods_five_locales_keep_identity_axes_independent(self):
        for persona in self.runtime.DJPersona:
            for mood in ('chill', 'groove', 'energy', 'party'):
                for language in ('en', 'nl', 'de', 'fr', 'es'):
                    with self.subTest(persona=persona.value, mood=mood, language=language):
                        manager = self.runtime.SessionRuntimeManager()
                        session = await manager.async_start(owner_profile_id='synthetic-owner',
                            dj_persona=persona, selected_mood=mood, locale=language)
                        snapshot = session.broadcast.as_dict()
                        axis = snapshot['session']
                        self.assertEqual((axis['dj_persona'], axis['selected_mood'], axis['locale']),
                                         (persona.value, mood, language))
                        self.assertEqual(axis['selected_presence'], 'balanced')
                        self.assertEqual((axis['mood_revision'], axis['persona_revision'], axis['presence_revision']), (0, 0, 0))
                        self.assertIsNone(snapshot['native_delivery']['current_moment_id'])
                        self.assertIsNone(snapshot['native_delivery']['current_silence_moment_id'])
                        self.assertEqual(snapshot['session_speech']['moments'], [])

    async def test_old_session_cannot_publish_silence_into_replacement(self):
        manager = self.runtime.SessionRuntimeManager()
        old = await manager.async_start(owner_profile_id='synthetic-owner', selected_mood='chill')
        silence = old.moment_engine.create_silence(session_id=old.session_id,
            selected_mood=old.selected_mood, persona=old.dj_persona, locale=old.locale,
            reason='synthetic_late_silence')
        await manager.async_end(owner_profile_id='synthetic-owner', session_id=old.session_id)
        current = await manager.async_start(owner_profile_id='synthetic-owner', selected_mood='party')
        old.publish_moment(silence)
        self.assertNotEqual(old.session_id, current.session_id)
        self.assertIsNone(current.broadcast.as_dict()['native_delivery']['current_silence_moment_id'])
        self.assertEqual(current.broadcast.state.dj_moments, ())
        self.assertIsNone(old.broadcast.as_dict()['native_delivery']['current_moment_id'])
        self.assertEqual(current.selected_mood, 'party')

    async def test_silence_is_not_missing_moment_and_never_acquires_speech(self):
        manager = self.runtime.SessionRuntimeManager()
        session = await manager.async_start(owner_profile_id='synthetic-owner', selected_mood='groove')
        await manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=session.session_id, state='playing', media_identity='spotify:track:'+'A'*22,
            title='Synthetic track', artist='Synthetic artist', duration_ms=180000, position_ms=1000)
        session = await manager.async_update_presence(owner_profile_id='synthetic-owner',
            session_id=session.session_id, selected_presence='music_only', expected_revision=0)
        before = session.broadcast.as_dict()
        silence = session.moment_engine.create_silence(session_id=session.session_id,
            selected_mood=session.selected_mood, persona=session.dj_persona, locale=session.locale,
            reason='synthetic_intentional_space')
        session.publish_moment(silence)
        after = session.broadcast.as_dict()
        self.assertIsNone(before['native_delivery']['current_silence_moment_id'])
        self.assertEqual(after['native_delivery']['current_silence_moment_id'], silence.moment_id)
        self.assertIsNone(after['native_delivery']['current_moment_id'])
        self.assertEqual(after['session_speech']['moments'], [])
        admission = next(a for a in after['native_delivery']['admissions'] if a['moment_id'] == silence.moment_id)
        self.assertEqual(admission['qualification'], 'intentional_silence')
        self.assertEqual(session.selected_presence, 'music_only')
        self.assertEqual(session.presence_ledger.total_published, 0)

    async def test_snapshot_repeated_reads_do_not_create_animation_or_reaction_side_effects(self):
        manager = self.runtime.SessionRuntimeManager()
        session = await manager.async_start(owner_profile_id='synthetic-owner', selected_mood='groove')
        events = []
        await manager.async_subscribe(owner_profile_id='synthetic-owner',
            session_id=session.session_id, callback=events.append)
        before = session.broadcast.delivery_sequence, session.planner.output.session_flow.flow_revision, len(events)
        for _ in range(10):
            snapshot = session.broadcast.as_dict()
            self.assertNotIn('avatar_activity', snapshot)
            self.assertNotIn('persona_reaction', snapshot)
        self.assertEqual(before, (session.broadcast.delivery_sequence,
            session.planner.output.session_flow.flow_revision, len(events)))
        self.assertEqual(session.presence_ledger.total_published, 0)

    async def test_announcement_provenance_requires_current_native_authority(self):
        from tests.test_session_playback_narration import PlaybackNarrationTests
        from custom_components.djconnect.native_moment_delivery import admission

        fixture = PlaybackNarrationTests()
        fixture.runtime = self.runtime
        manager, session, media, insight = await fixture.current()
        moment = await manager.async_process_track_started(owner_profile_id='owner',
            session_id=session.session_id, media_identity=media,
            require_current_playback=True, insight_provider=insight)
        snapshot = session.broadcast.as_dict()
        native = snapshot['native_delivery']
        self.assertEqual(native['current_moment_id'], moment.moment_id)
        payload = next(m for m in snapshot['dj_moments'] if m['moment_id'] == moment.moment_id)
        self.assertEqual(payload['type'], 'track')
        self.assertEqual(payload['knowledge_intent']['type'], 'track_context')
        self.assertEqual(payload['generation_metadata']['context_source'], 'observed_playback')
        self.assertEqual(payload['source_references'], ['spotify_playback_status'])
        original = moment.as_dict()
        boundary = session.broadcast._moment_delivery_boundaries[moment.moment_id]
        # Public-looking metadata cannot replace the actual producer proof.
        denied = admission(replace(moment, observed_playback=None), boundary,
            session_id=session.session_id, active=True, flow_ids={moment.moment_id},
            playback_item_id=moment.observed_playback.item_id, playing=True,
            now=boundary.published_monotonic)
        self.assertEqual(denied['qualification'], 'unqualified')
        with patch('time.monotonic', return_value=moment.observed_playback.observed_at + 31):
            expired = session.broadcast.as_dict()['native_delivery']
        self.assertIsNone(expired['current_moment_id'])
        self.assertEqual(moment.as_dict(), original)
        await manager.async_end(owner_profile_id='owner', session_id=session.session_id)

    def test_touch_capability_is_not_inferred_from_existing_speech_or_ask_dj(self):
        from tests.test_http_voice_helpers import install_http_stubs
        install_http_stubs()
        from custom_components.djconnect.hybrid_service import ACTION_OPERATIONS
        from custom_components.djconnect.session_speech import capability
        self.assertNotIn('session/persona/reaction', ACTION_OPERATIONS)
        self.assertNotIn('persona_reaction', capability())
        self.assertIn('silence', capability()['excluded_moment_types'])
