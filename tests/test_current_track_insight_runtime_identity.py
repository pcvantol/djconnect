"""Real Runtime value replacement with explicit synthetic source/provider seams."""
from dataclasses import replace
import importlib
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_config_flow_helpers import install_homeassistant_stubs
from tests.test_spotify_backend import install_backend_stubs
from tests.test_session_runtime import _load_runtime_module
from tests.test_track_insight import Runtime

ROOT = Path(__file__).resolve().parents[1]
URI = 'spotify:track:' + 'A'*22


class CurrentRuntimeValueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        install_homeassistant_stubs()
        install_backend_stubs()
        self.previous = {name: sys.modules.get(name) for name in
            ('custom_components.djconnect.session_runtime', 'custom_components.djconnect.const')}
        self.core, _ = _load_runtime_module()
        # The Runtime test loader supplies only DOMAIN/API_IMAGE constants.
        # This probe loads the actual complete constants for ordinary modules.
        spec = importlib.util.spec_from_file_location('custom_components.djconnect.const',
            ROOT/'custom_components/djconnect/const.py')
        const = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = const
        spec.loader.exec_module(const)
        def restore():
            for name, module in self.previous.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module
        self.addCleanup(restore)
        self.manager = self.core.SessionRuntimeManager()
        self.source = {'backend_id': 'spotify_direct', 'music_account_id': 'synthetic-account',
            'provider_entry_id': 'synthetic-provider', 'provider_account_id': 'synthetic-provider-account'}
        self.active = await self.manager.async_start(owner_profile_id='synthetic-owner',
            music_backend='spotify_direct', history_source_context=self.source)
        self.hass = SimpleNamespace(data={'djconnect': {'session_runtime_manager': self.manager}})
        self.runtime = Runtime()
        self.module = importlib.import_module('custom_components.djconnect.current_track_insight')
        self.imagery = importlib.import_module('custom_components.djconnect.forecast_imagery')
        self.authority = patch.object(self.imagery, 'artist_authority', return_value=lambda: True)
        self.authority.start()
        self.addCleanup(self.authority.stop)

    def original_authority(self):
        return self.module.original_source_authority(self.hass, self.runtime, 'synthetic-owner')

    def progress_value(self):
        original = self.manager.current_active('synthetic-owner')
        updated = self.manager._record_performance_memory('synthetic-owner', original)
        self.assertIsNot(updated, original)
        self.assertIs(updated.broadcast, original.broadcast)
        self.assertEqual(updated.session_id, original.session_id)
        return updated

    async def test_original_source_authority_survives_real_performance_memory_value_replacement(self):
        guard = self.original_authority()
        self.assertTrue(guard())
        self.progress_value()
        self.assertTrue(guard())

    async def test_current_observation_and_repeated_reads_keep_original_frame_during_value_replacement(self):
        test = self
        class ProviderFixture:
            def __init__(self, *_):
                pass
            async def async_observe_current_playback(self):
                test.progress_value()
                return SimpleNamespace(media_identity=URI, state='playing', position_ms=10000,
                    target_name='Synthetic output', title='Synthetic track', artist='Synthetic artist',
                    album='Synthetic album', artwork_url='', duration_ms=180000, is_playing=True)
            async def async_observe_current_genres(self, observed, *, authorize):
                test.progress_value()
                authorize()
                return {}
        spotify = importlib.import_module('custom_components.djconnect.spotify_backend')
        insight = importlib.import_module('custom_components.djconnect.track_insight')
        request = insight.TrackInsightRequest(locale='en')
        with patch.object(spotify, 'SpotifyBackend', ProviderFixture):
            one = await self.module.resolve(self.hass, self.runtime, request,
                owner_profile_id='synthetic-owner', validate_owner=lambda: None)
            deadline, frame = one.original_deadline, one.frame
            await one.verify()
            two = await self.module.resolve(self.hass, self.runtime, request,
                owner_profile_id='synthetic-owner', validate_owner=lambda: None)
            self.assertIs(two.frame, frame)
            self.assertEqual(two.original_deadline, deadline)
            self.assertEqual(two.subject()['observation_id'], one.subject()['observation_id'])

    async def qualified_context(self, authority=None):
        from custom_components.djconnect.session_facts import _fact, DisplayFactCore
        await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, state='playing', media_identity=URI,
            title='Synthetic track', artist='Synthetic artist', album='Synthetic album',
            duration_ms=180000, position_ms=10000)
        fact = _fact('work_composers', {'uri': URI}, 'track_context',
            ['Synthetic composer']*5, ['Synthetic composer is credited as composer.']*5,
            'MusicBrainz', 'https://musicbrainz.org/work/11111111-1111-1111-1111-111111111111',
            DisplayFactCore('work_composers', roles=(('composer', ('Synthetic composer',)),)))
        async def knowledge():
            return {'_qualified_facts': (fact,)}
        await self.manager.async_process_track_started(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, media_identity=URI, insight_provider=knowledge,
            require_current_playback=True, allow_initial_facts=True)
        target = importlib.import_module('custom_components.djconnect.track_insight_target')
        with patch.object(target, 'session_runtime_manager', return_value=self.manager), \
                patch.object(target, 'history_grant_revision', return_value='synthetic-grant-revision'):
            context = target.current_knowledge_context(self.hass, 'synthetic-owner',
                {'_media_identity': URI, 'title': 'Synthetic track', 'artist': 'Synthetic artist'},
                source_authority=authority or self.original_authority())
            self.assertIsNotNone(context)
            return context

    async def test_qualified_current_credit_guard_survives_value_replacement_without_fabricating_measurements(self):
        context = await self.qualified_context()
        target = importlib.import_module('custom_components.djconnect.track_insight_target')
        with patch.object(target, 'history_grant_revision', return_value='synthetic-grant-revision'):
            context[1]()
            self.progress_value()
            context[1]()

    async def test_current_subject_cannot_rearm_after_observed_scope_withdrawal(self):
        from custom_components.djconnect.track_insight import TrackInsightError
        frame = self.module.observe(self.runtime, URI, 'playing', 10000)
        scope = [('original',)]
        subject = self.module.CurrentSubject(runtime=self.runtime, frame=frame, backend=None,
            track={}, validate_owner=None, source_scope=lambda: scope[0], scope=scope[0],
            locale='en', observed=None, original_deadline=time.monotonic()+30)
        subject.guard()
        scope[0] = ('withdrawn',)
        with self.assertRaises(TrackInsightError):
            subject.guard()
        scope[0] = ('original',)
        with self.assertRaises(TrackInsightError):
            subject.guard()

    async def test_verify_conflicting_metadata_latches_real_original_owner_subject(self):
        from custom_components.djconnect.track_insight import TrackInsightError
        original = SimpleNamespace(media_identity=URI, state='playing', position_ms=10000,
            target_name='Synthetic output', title='Original title', artist='Original artist', album='Original album')
        changed = SimpleNamespace(**{**vars(original), 'title': 'Contradictory title', 'album': 'Contradictory album'})
        class BackendFixture:
            async def async_observe_current_playback(self):
                return changed
        authority = self.original_authority()
        def owner():
            if not authority():
                raise PermissionError('synthetic_original_owner_withdrawn')
        def scope():
            return self.module.session_scope(self.manager.current_active('synthetic-owner'))
        frame = self.module.observe(self.runtime, URI, 'playing', 10000, 'Synthetic output')
        subject = self.module.CurrentSubject(runtime=self.runtime, frame=frame, backend=BackendFixture(),
            track={}, validate_owner=owner, source_scope=scope, scope=scope(), locale='en',
            observed=original, original_deadline=time.monotonic()+30)
        subject.guard()
        with self.assertRaises(TrackInsightError):
            await subject.verify()
        self.assertTrue(authority())  # Real Runtime owner/source did not change.
        with self.assertRaises(TrackInsightError):
            subject.guard()

    async def test_current_knowledge_cannot_rearm_original_admission_after_observed_withdrawal(self):
        allowed = [True]
        context = await self.qualified_context(authority=lambda: allowed[0])
        target = importlib.import_module('custom_components.djconnect.track_insight_target')
        # Other synthetic suites reload track_insight; the captured guard keeps
        # its defining module error class. Assert that exact class and code.
        with patch.object(target, 'history_grant_revision', return_value='synthetic-grant-revision'):
            context[1]()
            allowed[0] = False
            with self.assertRaises(target.TrackInsightError) as caught:
                context[1]()
            self.assertEqual(caught.exception.code, 'track_insight_context_changed')
            allowed[0] = True
            with self.assertRaises(target.TrackInsightError) as caught:
                context[1]()
            self.assertEqual(caught.exception.code, 'track_insight_context_changed')

    async def test_original_source_replacement_and_manager_replacement_cannot_revive(self):
        guard = self.original_authority()
        self.hass.data['djconnect']['session_runtime_manager'] = self.core.SessionRuntimeManager()
        self.assertFalse(guard())
        self.hass.data['djconnect']['session_runtime_manager'] = self.manager
        self.assertFalse(guard())
        fresh = self.original_authority()
        self.manager._history_source_contexts[self.active.session_id] = dict(self.source)
        self.assertFalse(fresh())
        self.manager._history_source_contexts[self.active.session_id] = self.source
        self.assertFalse(fresh())

    async def test_each_settings_axis_revision_generation_and_lifecycle_fences_original_authority(self):
        for field in ('mood_revision', 'persona_revision', 'presence_revision', 'settings_revision',
                'defaults_revision', 'settings_generation'):
            with self.subTest(field=field):
                original = self.manager.current_active('synthetic-owner')
                guard = self.original_authority()
                value = getattr(original, field)
                changed = value + 1 if type(value) is int else value + '-changed'
                self.manager._active_by_profile['synthetic-owner'] = replace(original, **{field: changed})
                self.assertFalse(guard())
                self.manager._active_by_profile['synthetic-owner'] = original
                self.assertFalse(guard())
        guard = self.original_authority()
        await self.manager.async_end(owner_profile_id='synthetic-owner', session_id=self.active.session_id)
        self.assertFalse(guard())
        await self.manager.async_start(owner_profile_id='synthetic-owner', history_source_context=self.source)
        self.assertFalse(guard())
