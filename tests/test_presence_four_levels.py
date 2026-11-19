"""Four-level producer discovery, real upgrades and live compatibility fences."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from tests.test_session_runtime import _load_runtime_module
from custom_components.djconnect.domain.profile.dj_settings import DJSettings, SettingsValidationError
from custom_components.djconnect.persistence.schema import apply_migration
from custom_components.djconnect.presence_policy import POLICIES, PresenceLedger


class FourPresenceContractTests(unittest.TestCase):
    def test_current_capability_fixture_and_profile_allow_exact_four(self):
        from custom_components.djconnect.session_presence import capability
        from custom_components.djconnect.capability_contract import _contract_versions
        from custom_components.djconnect.profile_settings import allowed_values, VoicePolicy
        expected = json.loads((Path(__file__).resolve().parents[1] /
            'examples/client_contracts/session_presence_v2/capability.json').read_text())
        self.assertEqual(capability(), expected)
        self.assertEqual(_contract_versions()['active_session_presence'], 2)
        self.assertEqual(_contract_versions()['profile_session_settings'], 3)
        policy = VoicePolicy('p', 'r', (), (), False, 'fixture')
        self.assertEqual(allowed_values(policy)['presence'],
                         ['music_only', 'occasional', 'balanced', 'presenter'])

    def test_only_exact_legacy_alias_is_accepted_without_touching_other_axes(self):
        before = DJSettings(persona='club_dj', mood='party', announcement_output='ha_speaker')
        patch = {'presence': 'talkative'}
        canonical = before.patched(patch)
        self.assertEqual(canonical.as_dict(), {**before.as_dict(), 'presence': 'presenter'})
        self.assertEqual(patch, {'presence': 'talkative'})
        self.assertEqual(DJSettings.from_dict({**before.as_dict(), **patch}), canonical)
        for invalid in ('Talkative', ' talkative', 'chatty', [], True, None):
            with self.subTest(invalid=invalid), self.assertRaises(SettingsValidationError):
                before.patched({'presence': invalid})

    def test_old_debits_remain_binding_after_alias_and_rate_recalibration(self):
        now = [0.0]
        ledger = PresenceLedger(clock=lambda: now[0])
        for index in range(4):
            self.assertTrue(ledger.admits('talkative', 'old-track'))
            ledger.commit('old-track', 40)
            now[0] += 45
        now[0] += 600
        self.assertEqual(ledger.reason('presenter', 'old-track'), 'presence_track_budget')
        self.assertEqual(ledger.reason('talkative', 'old-track'), 'presence_track_budget')
        self.assertEqual(ledger.total_published, 4)

    def test_rolling_caps_and_minimum_intervals_are_ceilings_including_boundary(self):
        for mode, (gap, per_track, rolling) in POLICIES.items():
            with self.subTest(mode=mode):
                now = [0.0]
                ledger = PresenceLedger(clock=lambda: now[0])
                if not per_track:
                    self.assertFalse(ledger.admits(mode, 'track'))
                    continue
                for index in range(rolling):
                    self.assertTrue(ledger.admits(mode, f'track-{index}'))
                    ledger.commit(f'track-{index}', 40)
                    now[0] += gap-0.001
                    self.assertFalse(ledger.admits(mode, 'next'))
                    now[0] += 0.001
                self.assertEqual(ledger.reason(mode, 'next'), 'presence_rolling_budget')
                now[0] = 600
                self.assertTrue(ledger.admits(mode, 'next'))


class FourPresenceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is not None:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const
        else:
            sys.modules.pop('custom_components.djconnect.const', None)

    async def legacy(self):
        manager = self.core.SessionRuntimeManager()
        active = await manager.async_start(owner_profile_id='owner', selected_mood='party')
        events = []
        await manager.async_subscribe(owner_profile_id='owner', session_id=active.session_id,
                                      callback=events.append)
        active = replace(active, selected_presence='talkative', presence_revision=7)
        manager._active_by_profile['owner'] = active
        active.broadcast.state = replace(active.broadcast.state,
                                          selected_presence='talkative', presence_revision=7)
        active.presence_ledger.commit('old-track', 40)
        return manager, active, events

    def test_live_migration_once_preserves_debits_flow_and_acceptance_revisions(self):
        async def scenario():
            manager, old, events = await self.legacy()
            ledger = old.presence_ledger
            debits = bytes(ledger.track_counts), ledger.total_published, ledger.last_at
            flow = old.planner.output.session_flow
            self.assertEqual(old.as_dict()['selected_presence'], 'presenter')
            self.assertEqual(old.broadcast.as_dict()['session']['selected_presence'], 'presenter')
            self.assertIs(manager.current_active('owner'), old)  # Pure final-authority fence.
            active = await manager.async_get_active('owner')
            self.assertEqual((active.selected_presence, active.presence_revision), ('presenter', 8))
            self.assertIs(active.presence_ledger, ledger)
            self.assertEqual((bytes(ledger.track_counts), ledger.total_published, ledger.last_at), debits)
            self.assertEqual((active.session_id, active.settings_revision, active.defaults_revision),
                             (old.session_id, old.settings_revision, old.defaults_revision))
            self.assertIs(active.planner.output.session_flow, flow)
            self.assertFalse(old.publication_context_is_current())
            self.assertIs(await manager.async_get_active('owner'), active)
            changes = [e for e in events if e.get('event_type') == 'presence_changed']
            self.assertEqual(len(changes), 1, events)
        asyncio.run(scenario())

    def test_migrated_revision_fences_inflight_provider_without_spending(self):
        async def scenario():
            manager = self.core.SessionRuntimeManager()
            active = await manager.async_start(owner_profile_id='owner', selected_mood='party')
            active = await manager.async_update_presence(owner_profile_id='owner',
                session_id=active.session_id, selected_presence='presenter')
            entered, release = asyncio.Event(), asyncio.Event()
            async def delayed():
                entered.set()
                await release.wait()
                return {'track': {'title': 'Fixture', 'artist': 'Fixture artist'},
                        'analysis': {'summary': 'Fixture', 'full_text': 'Fixture context'}}
            task = asyncio.create_task(manager.async_process_track_started(owner_profile_id='owner',
                session_id=active.session_id, insight_provider=delayed))
            await asyncio.wait_for(entered.wait(), 2)
            # Simulate the retained pre-upgrade state while work is suspended.
            legacy = replace(active, selected_presence='talkative')
            manager._active_by_profile['owner'] = legacy
            active.broadcast.state = replace(active.broadcast.state, selected_presence='talkative')
            current = await manager.async_get_active('owner')
            self.assertEqual(current.presence_revision, active.presence_revision+1)
            release.set()
            self.assertIsNone(await task)
            self.assertEqual(current.presence_ledger.total_published, 0)
            self.assertEqual(current.broadcast.state.dj_moments, ())
        asyncio.run(scenario())

    def test_unauthorized_write_does_not_migrate_and_old_cas_requires_readback(self):
        async def scenario():
            manager, old, _ = await self.legacy()
            with self.assertRaises(PermissionError):
                await manager.async_update_presence(owner_profile_id='owner', session_id=old.session_id,
                    selected_presence='talkative', expected_revision=7, authorize=lambda: False)
            self.assertIs(manager.current_active('owner'), old)
            with self.assertRaises(self.core.PresenceRevisionConflictError) as caught:
                await manager.async_update_presence(owner_profile_id='owner', session_id=old.session_id,
                    selected_presence='talkative', expected_revision=7, authorize=lambda: True)
            self.assertEqual(caught.exception.active.selected_presence, 'presenter')
            result = await manager.async_update_presence(owner_profile_id='owner', session_id=old.session_id,
                selected_presence='talkative', expected_revision=8, authorize=lambda: True)
            self.assertEqual((result.selected_presence, result.presence_revision), ('presenter', 8))
        asyncio.run(scenario())


class FourPresenceDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_v9_upgrade_reopen_preserves_completed_rows_receipts_and_revisions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'v9.sqlite'
            provider = SQLitePersistenceProvider()
            await provider.async_open(str(path))
            for version in range(1, 10):
                await provider.async_run_transaction(lambda tx, v=version: apply_migration(tx, v))
            values = {**DJSettings(persona='festival_dj', mood='party').as_dict(), 'presence': 'talkative'}
            original = json.dumps(values, sort_keys=True)
            receipt = json.dumps({'snapshot': {'defaults': values}, 'accepted': True})
            def seed(tx):
                tx.execute('INSERT INTO djconnect_profile_dj_settings VALUES (?,?,?,?,?)',
                           ('owner', original, 12, 'original-time', 3))
                for status in ('ACTIVE', 'ENDED', 'INTERRUPTED'):
                    tx.execute('INSERT INTO djconnect_persistent_sessions '
                        '(session_id,owner_profile_id,lifecycle_status,created_at,updated_at) VALUES (?,?,?,?,?)',
                        (status, 'owner', status, 'original-time', 'original-time'))
                    tx.execute('INSERT INTO djconnect_session_dj_settings VALUES (?,?,?,?,?,?,?)',
                        (status, 'owner', 'original-generation', original, 8, 12, 'original-time'))
                tx.execute('INSERT INTO djconnect_settings_operations VALUES (?,?,?,?,?,?)',
                           ('op', 'owner', 'binding', 'digest', 999999, receipt))
            await provider.async_run_transaction(seed)
            await provider.async_close()
            service = PersistenceService(path, SQLitePersistenceProvider())
            try:
                for _ in range(2):
                    await service.async_initialize()
                    def read(tx):
                        return (tx.fetchone('SELECT settings,revision,updated_at,contract_version FROM djconnect_profile_dj_settings'),
                            tx.fetchall('SELECT session_id,settings,revision,defaults_revision,updated_at,generation FROM djconnect_session_dj_settings ORDER BY session_id'),
                            tx.fetchone('SELECT receipt FROM djconnect_settings_operations'),
                            tx.fetchone('SELECT COUNT(*) FROM djconnect_schema_migrations WHERE schema_version=10'))
                    profile, sessions, saved, count = await service.async_in_transaction(read)
                    self.assertEqual(json.loads(profile[0]), {**values, 'presence': 'presenter'})
                    self.assertEqual(profile[1:], (12, 'original-time', 3))
                    for sid, body, rev, defaults, at, generation in sessions:
                        if sid == 'ACTIVE':
                            self.assertEqual(json.loads(body), {**values, 'presence': 'presenter'})
                        else:
                            self.assertEqual(body, original)
                        self.assertEqual((rev, defaults, at, generation),
                                         (8, 12, 'original-time', 'original-generation'))
                    self.assertEqual(saved, (receipt,))
                    self.assertEqual(count, (1,))
                    await service.async_close()
            finally:
                await service.async_close()
