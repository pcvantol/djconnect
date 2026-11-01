"""R5 grammar, pure committed read, exact owner/configuration and parity races."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import hashlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from tests.test_profile_storage import MemoryStore, ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain.storage import household_to_storage  # noqa: E402
from custom_components.djconnect import profile_observation  # noqa: E402
from custom_components.djconnect.ask_dj import example_catalogue as catalogue  # noqa: E402
from custom_components.djconnect.ask_dj import help_observation as observer  # noqa: E402
from custom_components.djconnect.ask_dj.help_configuration import entry_configuration_mask  # noqa: E402


class Hass:
    def __init__(self):
        self.data = {}


class Runtime:
    def __init__(self, entry):
        self.entry = entry
        self.device_token = 'SYNTHETIC-ONLY-PAIRING-TOKEN'

    @property
    def config(self):
        raise AssertionError('GET used creating runtime.config')

    def authorize_device_request(self, *args, **kwargs):
        raise AssertionError('GET tried to learn pairing identity')


class HelpObservationTests(unittest.IsolatedAsyncioTestCase):
    def test_original_actual_ha_wire_binds_all_current_products_without_native_claim(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / 'examples/client_contracts/ask_dj_help_context_v1/actual-ha-wire.json').read_text())
        self.assertEqual(fixture['status'], 'PASS')
        self.assertEqual(len(fixture['source_hashes']), 298)
        for path, digest in fixture['source_hashes'].items():
            self.assertEqual(hashlib.sha256((root / path).read_bytes()).hexdigest(), digest, path)
        self.assertEqual(hashlib.sha256((root / fixture['harness']).read_bytes()).hexdigest(), fixture['harness_sha256'])
        self.assertEqual(len(fixture['cases']), 18)
        self.assertEqual({len(row['response_body']['eligible_entry_ids']) for row in fixture['cases']
                          if row['response_body'].get('available')}, {0, 9, 10, 14})
        self.assertEqual(fixture['model_calls'], 0)
        self.assertEqual(fixture['external_provider_calls'], 0)
        for field in ('installed', 'native', 'operator_or_provider_activation'):
            self.assertEqual(fixture[field], 'NOT_RUN')

    def test_public_postman_example_uses_exact_r5_get_without_execution_or_profile_body(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        collection = json.loads((root / 'examples/djconnect.postman_collection.json').read_text())
        def requests(items):
            for item in items:
                if 'item' in item:
                    yield from requests(item['item'])
                elif item.get('request'):
                    yield item['request']
        request = next(r for r in requests(collection['item'])
            if '/ask_dj/help-context?' in r['url']['raw'])
        self.assertEqual(request['method'], 'GET')
        self.assertNotIn('body', request)
        query = {q['key']: q['value'] for q in request['url']['query'] if not q.get('disabled')}
        self.assertEqual(set(query), observer.REQUIRED)
        self.assertEqual({h['key']: h['value'] for h in request['header']}['Cache-Control'], 'no-store')

    def query(self, **changes):
        pin = catalogue.capability()
        result = dict(schema_version='1', request_id='12345678-1234-4234-8234-123456789abc',
            surface='ask_dj', language='nl', catalogue_id=pin['catalogue_id'],
            catalogue_revision=str(pin['revision']), catalogue_sha256=pin['sha256'])
        result.update(changes)
        return result

    def decoded(self, **changes):
        return observer.decode_query(urlencode(self.query(**changes)).encode())

    async def fixture(self):
        # A synthetic owner uses the actual immutable Household/storage model.
        # This manual bootstrap is a unit vector, not real HA lifecycle proof.
        staged = ProfilePlatformStorage(store=MemoryStore())
        await staged.async_upsert_music_backend('spotify_direct', BackendProvider.SPOTIFY_DIRECT,
                                               display_name='Synthetic backend')
        profile = await staged.async_create_profile('Synthetic owner', profile_id='owner',
                                                   default_backend_id='spotify_direct')
        await staged.async_upsert_music_account('source-account', 'spotify_direct',
            kind=MusicAccountKind.PERSONAL, linked_profile_ids=frozenset({'owner'}),
            display_name='Synthetic account')
        await staged.async_update_profile('owner', preferences=replace(
            profile.preferences, default_music_account_id='source-account'))
        device = 'djconnect-ios-ABCDEF123456'
        await staged.async_upsert_device(device, 'ios', linked_profile_id='owner')
        hass = Hass()
        profile_observation.bootstrap_from_integration_setup(hass)
        manager = ProfilePlatformStorage(hass, store=MemoryStore(household_to_storage(staged.household)))
        profile_observation.publish_manager(hass, hass.data['djconnect'], manager)
        await manager.async_load()
        entry = SimpleNamespace(entry_id='selected-entry', domain='djconnect', disabled_by=None,
            state=SimpleNamespace(value='loaded'), options={}, data={
                'device_id': device, 'client_type': 'ios', 'music_backend': 'spotify_direct',
                'music_account_id': 'source-account', 'spotify_refresh_token': 'SYNTHETIC-SOURCE-GRANT'})
        runtime = Runtime(entry)
        hass.data['djconnect'][entry.entry_id] = runtime
        hass.config_entries = SimpleNamespace(async_entries=lambda _: [entry])
        headers = {'Authorization': 'Bearer ' + runtime.device_token, 'X-DJConnect-Device-ID': device}
        return hass, manager, runtime, headers

    def published(self):
        data = catalogue.catalogue()
        data['status'] = 'qualified_v1'
        for row in data['entries']:
            row['publication'] = 'qualified_v1'
            for language in ('en', 'nl'):
                row['qualification'][language] = {'state': 'qualified_owner_route', 'route': row['route']}
        return patch.object(catalogue, '_CATALOGUE', data)

    def test_exact_query_single_decode_and_rejection_before_dictionary(self):
        raw = urlencode(self.query()).encode()
        self.assertIsInstance(observer.decode_query(raw)['catalogue_revision'], int)
        scoped = self.query(surface='active_session', session_id='synthetic+A%2F')
        self.assertEqual(observer.decode_query(urlencode(scoped).encode())['session_id'], 'synthetic+A%2F')
        negatives = [raw + b'&catalogue_revision=1', raw + b'&catalogue_%72evision=1',
            raw + b'&other=1', raw + b'&session_id=%GG', raw + b'&session_id=%',
            raw + b'&session_id=%ff', raw + b'&session_id=', raw + b'&session_id=%00',
            raw + b'&session_id=%E2%80%8B', raw + b'&session_id=+bad',
            raw + b'&session_id=' + b'a' * 257, b'a' * 4097, b'']
        for key, values in {'catalogue_revision': ['0', '01', '1.0', '1e0', '１', '2147483648'],
            'language': ['NL', 'nl-NL', ''], 'surface': ['session', 'ASK_DJ'],
            'request_id': ['12345678-1234-1234-8234-123456789abc', 'BAD'],
            'catalogue_sha256': ['A' * 64, 'a' * 63]}.items():
            for value in values:
                changed = self.query()
                changed[key] = value
                negatives.append(urlencode(changed).encode())
        for value in negatives:
            with self.subTest(raw=value), self.assertRaises(ValueError):
                observer.decode_query(value)
        with self.assertRaises(ValueError):
            observer.decode_query(raw, has_body=True)
        with self.assertRaises(ValueError):
            self.decoded(surface='active_session')

    async def test_global_read_is_detached_and_does_not_borrow_an_active_session(self):
        hass, manager, runtime, headers = await self.fixture()
        class NeverBorrow:
            def current_active(self, *args):
                raise AssertionError('global Help borrowed a Session')
        hass.data['djconnect']['session_runtime_manager'] = NeverBorrow()
        before = (dict(hass.data), dict(hass.data['djconnect']), dict(vars(runtime)),
                  dict(vars(manager)), manager._observation_owner().revision)
        with self.published(), patch(
                'custom_components.djconnect.ask_dj.help_configuration.loaded_model_configuration', return_value=False):
            result = observer.observe(hass, headers, self.decoded())
            self.assertTrue(result['available'])
            self.assertIsNone(result['session_id'])
            self.assertIsNone(result['track_id'])
            self.assertEqual(result['eligible_entry_ids'], [
                'discover.artist_albums', 'discover.artist_tracks', 'discover.playlists', 'discover.recent',
                'listen.outputs', 'listen.queue'])
            self.assertEqual(set(result), {'schema_version', 'request_id', 'surface', 'language',
                'session_id', 'track_id', 'catalogue', 'available', 'observation_id', 'eligible_entry_ids'})
            self.assertEqual(len(result['catalogue']), 5)
            json.dumps(result, allow_nan=False)
            second = observer.observe(hass, headers, self.decoded())
            self.assertNotEqual(result['observation_id'], second['observation_id'])
        after = (dict(hass.data), dict(hass.data['djconnect']), dict(vars(runtime)),
                 dict(vars(manager)), manager._observation_owner().revision)
        self.assertEqual(before, after)

    async def test_current_request_pin_mismatch_returns_null_never_an_adoption_offer(self):
        hass, _, _, headers = await self.fixture()
        with self.published():
            query = self.decoded()
            query['catalogue_revision'] += 1
            result = observer.observe(hass, headers, query)
        self.assertFalse(result['available'])
        self.assertIsNone(result['catalogue'])
        self.assertIsNone(result['observation_id'])
        self.assertEqual(result['eligible_entry_ids'], [])

    async def test_unknown_auth_duplicate_identity_or_headers_no_learning_or_private_echo(self):
        hass, _, runtime, headers = await self.fixture()
        for changed in ({}, {**headers, 'Authorization': 'Bearer wrong'},
                        {**headers, 'X-DJConnect-Device-ID': 'djconnect-123456'},
                        {**headers, 'X-DJConnect-Client-Type': 'macos'}):
            with self.assertRaises(PermissionError):
                observer.observe(hass, changed, self.decoded())
        class DuplicateHeaders(dict):
            def getall(self, key, default):
                value = self.get(key)
                return [value, value] if key == 'Authorization' else [value]
        duplicate = DuplicateHeaders(headers)
        with self.assertRaises(PermissionError):
            observer.observe(hass, duplicate, self.decoded())
        original = runtime.entry
        other = deepcopy(original)
        other.entry_id = 'duplicate-entry'
        hass.data['djconnect'][other.entry_id] = Runtime(other)
        hass.config_entries.async_entries = lambda _: [original, other]
        with self.assertRaises(PermissionError):
            observer.observe(hass, headers, self.decoded())

    async def test_unknown_foreign_null_string_session_is_closed_not_omitted(self):
        hass, _, _, headers = await self.fixture()
        manager = SimpleNamespace(_lock=asyncio.Lock(), _pending_settings_confirmations={},
                                  _visual_ending=set(), current_active=lambda _: None)
        hass.data['djconnect']['session_runtime_manager'] = manager
        with self.published():
            for value in ('null', 'None', 'foreign-session'):
                result = observer.observe(hass, headers, self.decoded(session_id=value))
                self.assertEqual(result['session_id'], value)
                self.assertFalse(result['available'])
                self.assertEqual(result['eligible_entry_ids'], [])

    async def test_pending_and_missing_storage_remain_closed_without_read_repair(self):
        hass, manager, _, headers = await self.fixture()
        owner = manager._observation_owner()
        with self.published():
            owner.pending += 1
            result = observer.observe(hass, headers, self.decoded())
            self.assertFalse(result['available'])
            owner.pending -= 1
            del hass.data['djconnect'][profile_observation.STORE_KEY]
            before = dict(hass.data['djconnect'])
            result = observer.observe(hass, headers, self.decoded())
            self.assertFalse(result['available'])
            self.assertEqual(hass.data['djconnect'], before)

    async def test_supported_provider_transfer_and_stale_reference_are_not_help_readiness(self):
        hass, _, runtime, headers = await self.fixture()
        domain = hass.data['djconnect']
        with self.published():
            domain['retired_provider_transfer_entries'] = {runtime.entry.entry_id}
            self.assertFalse(observer.observe(hass, headers, self.decoded())['available'])
            domain['retired_provider_transfer_entries'].clear()
            runtime.entry.options = {'profile_backend_entry_id': 'stale-provider',
                                     'music_account_id': 'source-account'}
            self.assertFalse(observer.observe(hass, headers, self.decoded())['available'])
            runtime.entry.options = {'profile_backend_entry_id': runtime.entry.entry_id,
                                     'music_account_id': 'another-account'}
            self.assertFalse(observer.observe(hass, headers, self.decoded())['available'])


    def test_final_original_media_and_forecast_expiry_after_projection_is_closed(self):
        from custom_components.djconnect.session_forecast import ForecastProjection
        for expired in (False, True):
            clock = [29.999]
            source = dict(backend_id='spotify_direct', music_account_id='account',
                          provider_entry_id='provider', provider_account_id='upstream')
            playback = SimpleNamespace(item_id='original-item', updated_at=datetime.now(UTC).isoformat(),
                title='Synthetic title', artist='Synthetic artist', album='Synthetic album', state='playing')
            opportunity = SimpleNamespace(item_id=playback.item_id, last_observed_monotonic=0)
            forecast = ForecastProjection('own-session')
            forecast.context_item_id = playback.item_id
            forecast.value = {'state': 'ready', 'imagery': [],
                              'valid_until': (datetime.now(UTC) + timedelta(seconds=100)).isoformat()}
            forecast.deadline = forecast.observation_deadline = 100
            forecast.observation_wall_deadline = forecast.wall_clock() + 100
            def now():
                if expired:
                    clock[0] = 30.001
                return clock[0]
            forecast.clock = now
            active = SimpleNamespace(session_id='own-session', owner_profile_id='owner',
                runtime_state='active', music_backend='spotify_direct',
                broadcast=SimpleNamespace(state=SimpleNamespace(playback=playback),
                                          content_pending=False, forecast=forecast),
                settings_generation='original', settings_revision=0,
                mood_revision=0, presence_revision=0, persona_revision=0)
            manager = SimpleNamespace(_lock=asyncio.Lock(), _pending_settings_confirmations={},
                _visual_ending=set(), current_active=lambda _: active,
                _history_source_contexts={'own-session': source},
                _intra_track_opportunities={'owner': opportunity}, _monotonic_source=lambda: clock[0])
            result = {}
            _, current = observer._session_context({'session_runtime_manager': manager},
                'owner', 'own-session', source, result)
            self.assertEqual(current(), not expired)

    async def test_prepared_wire_and_typed_help_revoke_at_final_projection_fence(self):
        hass, manager, _, headers = await self.fixture()
        with self.published():
            prepared = observer.observe(hass, headers, self.decoded())
            self.assertTrue(prepared['available'])
            self.assertTrue(prepared.final_check())
            manager._household = manager._household
            self.assertFalse(prepared.final_check())
            closed = prepared.closed()
            self.assertFalse(closed['available'])
            self.assertIsNone(closed['track_id'])
            self.assertEqual(closed['eligible_entry_ids'], [])

    async def test_final_profile_stamp_rejects_a_to_b_to_a_during_metadata_projection(self):
        hass, manager, _, headers = await self.fixture()
        def changed(*args):
            original = manager._household
            manager._household = replace(original, display_name='temporary')
            manager._household = original
            return entry_configuration_mask(None, {})
        with self.published(), patch(
                'custom_components.djconnect.ask_dj.help_configuration.entry_configuration_mask', side_effect=changed):
            result = observer.observe(hass, headers, self.decoded())
        self.assertFalse(result['available'])

    async def test_typed_help_uses_equal_committed_base_and_preserves_free_send_independence(self):
        from custom_components.djconnect.ask_dj.dialogue import current_turn
        hass, _, runtime, headers = await self.fixture()
        turn = SimpleNamespace(scope='profile:owner', session_id='')
        token = current_turn.set(turn)
        try:
            with self.published(), patch(
                    'custom_components.djconnect.ask_dj.help_configuration.loaded_model_configuration', return_value=False):
                result = observer.observe(hass, headers, self.decoded())
                typed = catalogue.help_context(hass, runtime)
                self.assertEqual(result['eligible_entry_ids'], [e['id'] for e in catalogue.eligible(
                    typed, 'ask_dj', 'nl', for_help=True)])
                # No execution handler accepts an observation ID or a catalogue
                # whitelist. This new read changes presentation only.
                from custom_components.djconnect.ask_dj import classify_ask_dj
                self.assertEqual(classify_ask_dj('Speel Radiohead').intent, 'play_music')
        finally:
            current_turn.reset(token)
