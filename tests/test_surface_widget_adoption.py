"""Real SQL15/lifecycle/service; explicit synthetic pairing/source/owner/crypto.

No actual enrollment, key, remote HTTP, APNs or native device is involved.
"""
import asyncio
from dataclasses import replace
import hashlib
import json
import sys
from types import SimpleNamespace
import unittest
import weakref
import gc
from pathlib import Path
from unittest.mock import patch

from tests import test_surface_issuer_lifecycle as issuer_fixture
from tests.test_surface_issuer_lifecycle import SyntheticEnrolledFixture
from tests.test_surface_issuer_owner import START
from tests.test_profile_dj_settings_persistence import operation
from custom_components.djconnect.surface_issuer_owner import WidgetIssuerOwner
from custom_components.djconnect.surface_push_service import SurfacePushService
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.surface_push_wire import canonical
from custom_components.djconnect.surface_issuer_wire import DOMAIN as ISSUER_DOMAIN
from custom_components.djconnect.const import DOMAIN
from custom_components.djconnect.domain.storage import STORE_KEY


class SyntheticWidgetOwner(SyntheticEnrolledFixture, WidgetIssuerOwner):
    def validate_widget_adoption(self, original, service_capture):
        if (self.service_capture is not None and self.service_capture() is not None
                and service_capture is not self.service_capture()) or not self.valid:
            raise SurfacePushError('synthetic_widget_owner_withdrawn')
        self.service_capture = weakref.ref(service_capture)
        if self.attestation_result is not None:
            return self.attestation_result
        self.validate_live(original)
        if original.owner_binding != service_capture.owner_binding:
            raise SurfacePushError('synthetic_widget_owner_mismatch')


class WidgetAdoptionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = issuer_fixture.IssuerLifecycleTests()
        await self.f.asyncSetUp()
        self.owner = SyntheticWidgetOwner()
        self.owner.service_capture, self.owner.attestation_result = None, None
        self.f.owner = self.f.lifecycle.owner = self.owner
        self.profile = 'synthetic-widget-profile'
        self.identity = {'device_id': 'synthetic-widget-device', 'client_type': 'ios'}
        self.headers = {'Authorization': 'synthetic-paired-only'}
        self.runtime = SimpleNamespace(entry=SimpleNamespace(entry_id='synthetic-entry', modified_at=1))
        self.active = SimpleNamespace(owner_profile_id=self.profile, session_id='synthetic-session',
            broadcast=object(), runtime_state=SimpleNamespace(value='active'))
        self.manager = SimpleNamespace(current_active=lambda owner: self.active,
            _history_source_contexts={})
        self.storage = SimpleNamespace(authority_revision=1,
            resolver=lambda: SimpleNamespace(resolve_bound_device=lambda _: SimpleNamespace(profile_id=self.profile)))
        self.hass = SimpleNamespace(data={DOMAIN: {STORE_KEY: self.storage,
            'session_runtime_manager': self.manager}},
            async_create_background_task=lambda coro, name: asyncio.create_task(coro, name=name))
        self.service = SurfacePushService(self.hass, self.manager, self.f.persistence)
        self.hass.data[DOMAIN]['surface_push_service'] = self.service
        self.paired_valid, self.source_valid = True, True
        self.paired_hook = None
        owner_hash = hashlib.sha256(self.profile.encode()).hexdigest()
        device_hash = hashlib.sha256(self.identity['device_id'].encode()).hexdigest()
        old = self.owner.capture
        fields = {'owner_binding': owner_hash, 'device_binding': device_hash}
        changed = replace(old, **fields)
        policy = json.loads(changed.policy_json)
        scope = hashlib.sha256(canonical([ISSUER_DOMAIN, 'delegation', changed.expected.delegation_id, 1,
            changed.install_id, changed.device_binding, changed.owner_binding, changed.grant_binding,
            changed.source_binding, changed.binding_id, changed.expected.key_thumbprint, policy]).encode()).hexdigest()
        self.owner.capture = replace(changed, expected=replace(changed.expected, scope_digest=scope))
        self.authority = SimpleNamespace(owner=owner_hash, device=device_hash, binding=changed.binding_id,
            validate_now=self.validate_paired)
        async def resolve(hass, identity, headers):
            if self.paired_hook:
                await self.paired_hook()
            self.validate_paired()
            return self.authority
        modules = {
            'custom_components.djconnect.request_auth': SimpleNamespace(
                resolve_runtime=lambda *args: self.runtime,
                authorize_runtime_device_request=lambda *args, **kwargs: self.paired_valid),
            'custom_components.djconnect.forecast_imagery': SimpleNamespace(
                artist_authority=lambda *args, **kwargs: lambda: self.source_valid),
            'custom_components.djconnect.hybrid_service': SimpleNamespace(
                PairedAuthority=SimpleNamespace(resolve=resolve)),
        }
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()

    def validate_paired(self):
        if not self.paired_valid:
            raise SurfacePushError('synthetic_pairing_withdrawn')

    async def asyncTearDown(self):
        await self.service.close()
        self.modules.stop()
        await self.f.asyncTearDown()
        self.f.doCleanups()

    def begin(self):
        return self.service.begin_widget_adoption(self.f.lifecycle, operation(START), self.identity, self.headers)

    async def test_default_empty_has_no_signer_rpc_or_implicit_owner(self):
        self.assertFalse(self.service._purposes)
        self.assertFalse(self.f.transport.calls)
        self.f.lifecycle.owner = SyntheticEnrolledFixture()
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_owner_unavailable'):
            self.begin()
        self.assertFalse(self.f.transport.calls)

    async def test_original_winner_adopted_once_same_object_expiry_and_budget(self):
        h = self.begin()
        p = await self.service.adopt_widget(h)
        self.assertIs(next(iter(self.service._purposes.values())), p)
        self.assertIs(h.lifecycle._retained(h.issuer_handle).purpose, p)
        self.assertEqual((p.original_wall_ms, p.original_monotonic), (START, 100.0))
        object.__setattr__(p, '_event_attempts', 7)
        calls = len(self.f.transport.calls)
        self.f.clock[:] = [START + 180000, 280.0]
        self.assertIs(await self.service.adopt_widget(h), p)
        self.assertEqual(p._event_attempts, 7)
        self.assertEqual(len(self.f.transport.calls), calls)

    async def test_session_end_before_first_task_step_latches_pending(self):
        h = self.begin()
        self.service.invalidate_session(self.profile, self.active.session_id)
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertTrue(h.closed)
        self.assertFalse(self.f.transport.calls)
        self.assertFalse(self.service._purposes)

    async def test_unload_before_paired_await_returns_never_begins_issuer(self):
        h = self.begin()
        async def hook():
            self.service.invalidate_entry('synthetic-entry')
        self.paired_hook = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.lifecycle._attempts)
        self.assertFalse(self.f.transport.calls)
        self.assertIsNone(h.authority)
        self.assertIsNone(h.capture)
        self.assertIsNone(h.task)

    async def test_late_issue_after_session_end_cannot_adopt(self):
        h = self.begin()
        async def hook(action):
            if action == 'issue':
                self.service.invalidate_session(self.profile, self.active.session_id)
        self.f.transport.on_call = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertTrue(h.closed)
        self.assertFalse(self.service._purposes)
        self.assertIsNone(self.f.lifecycle._retained(h.issuer_handle).purpose)

    async def test_local_withdraw_before_scheduling_remote_withdraw_fences_issue(self):
        h = self.begin()
        async def hook(action):
            if action == 'issue':
                self.service.withdraw_widget_adoption(h)
        self.f.transport.on_call = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        # Historical management retains separately validated owner authority.
        result = await self.f.lifecycle.status(h.issuer_handle)
        self.assertFalse(result['available'])
        self.assertFalse(self.service._purposes)

    async def test_explicit_withdraw_retires_adopted_map_before_any_remote_work(self):
        h = self.begin()
        p = await self.service.adopt_widget(h)
        calls = len(self.f.transport.calls)
        self.service.withdraw_widget_adoption(h)
        self.assertFalse(self.service._purposes)
        self.assertEqual(p.bearer, '')
        self.assertEqual(len(self.f.transport.calls), calls)
        await self.f.lifecycle.withdraw(h.issuer_handle, operation(START + 1))
        self.assertEqual(self.f.transport.calls[-1][0], 'withdraw')

    async def test_owner_attestation_none_or_raise_not_truthy_admission(self):
        h = self.begin()
        self.owner.attestation_result = True
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_owner_unavailable'):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.transport.calls)

    async def test_storage_and_entry_aba_revisions_cannot_rearm_original_capture(self):
        for field in ('storage', 'entry'):
            with self.subTest(field=field):
                h = self.begin()
                if field == 'storage':
                    self.storage.authority_revision += 2
                else:
                    self.runtime.entry.modified_at += 2
                with self.assertRaises(SurfacePushError):
                    await self.service.adopt_widget(h)
                self.assertTrue(h.closed)
                self.assertFalse(self.service._purposes)

    async def test_source_or_paired_loss_during_sign_prevents_issue_effect(self):
        h = self.begin()
        async def hook(action):
            if action == 'challenge':
                self.source_valid = False
        self.owner.on_sign = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.transport.calls)
        self.source_valid = True
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)

    async def test_broadcast_replacement_after_issue_is_rejected(self):
        h = self.begin()
        async def hook(action):
            if action == 'issue':
                self.active.broadcast = object()
        self.f.transport.on_call = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertFalse(self.service._purposes)

    async def test_scope_mismatch_before_challenge_does_not_send(self):
        h = self.begin()
        self.authority.binding = 'f' * 64
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_scope_mismatch'):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.transport.calls)

    async def test_cancel_pending_at_original_issue_commit_never_publishes(self):
        h = self.begin()
        original = self.f.journal.complete_issue
        async def commit(*args, **kwargs):
            result = await original(*args, **kwargs)
            asyncio.current_task().cancel()
            return result
        self.f.journal.complete_issue = commit
        with self.assertRaises(asyncio.CancelledError):
            await self.service.adopt_widget(h)
        self.assertFalse(self.service._purposes)
        self.assertTrue(h.closed)

    async def test_original_pending_deadline_not_renewed_after_paired_await(self):
        h = self.begin()
        async def hook():
            self.f.clock[:] = [START + 120000, 220.0]
        self.paired_hook = hook
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_capture_expired'):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.transport.calls)

    async def test_clock_rollback_permanently_fences(self):
        h = self.begin()
        self.f.clock[1] = 99.0
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_clock_invalid'):
            await self.service.adopt_widget(h)
        self.f.clock[1] = 100.0
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)

    async def test_no_lifecycle_clone_or_other_persistence_can_reset_budgets(self):
        self.begin()
        from custom_components.djconnect.surface_issuer_lifecycle import IssuerLifecycle
        clone = IssuerLifecycle(self.owner, self.f.journal, self.f.transport,
            wall=self.f.lifecycle.wall, monotonic=self.f.lifecycle.monotonic)
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_owner_unavailable'):
            self.service.begin_widget_adoption(clone, operation(START), self.identity, self.headers)

    async def test_unknown_issue_outcome_does_not_adopt_or_retry(self):
        h = self.begin()
        async def hook(action):
            if action == 'issue':
                raise OSError('synthetic-lost-issue-response')
        self.f.transport.on_call = hook
        with self.assertRaisesRegex(OSError, 'synthetic-lost-issue-response'):
            await self.service.adopt_widget(h)
        calls = len(self.f.transport.calls)
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertEqual(len(self.f.transport.calls), calls)
        self.assertFalse(self.service._purposes)

    async def test_service_close_pending_sign_no_remote_or_map(self):
        h = self.begin()
        async def hook(action):
            self.service.closed = True
            self.service._widget_adoptions.invalidate()
        self.owner.on_sign = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.transport.calls)
        self.assertFalse(self.service._purposes)

    async def test_new_begin_fences_old_pending_before_first_await(self):
        first = self.begin()
        second = self.begin()
        self.assertTrue(first.closed)
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(first)
        self.assertFalse(self.f.transport.calls)
        self.assertTrue((await self.service.adopt_widget(second)).is_current())

    async def test_real_service_close_cancels_owned_pending_sign_and_clears_handles(self):
        h = self.begin()
        entered = asyncio.Event()
        async def hook(action):
            entered.set()
            await asyncio.Event().wait()
        self.owner.on_sign = hook
        outer = asyncio.create_task(self.service.adopt_widget(h))
        await entered.wait()
        await self.service.close()
        with self.assertRaisesRegex(SurfacePushError, 'surface_unavailable'):
            await outer
        self.assertTrue(h.closed)
        self.assertFalse(self.service._tasks)
        self.assertFalse(self.service._purposes)
        self.assertFalse(self.f.transport.calls)

    async def test_foreign_handle_is_rejected_without_map_or_rpc(self):
        self.begin()
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_original_capture_required'):
            await self.service.adopt_widget(object())
        self.assertFalse(self.f.transport.calls)

    async def test_capacity_retained_handles_no_eviction_to_reset_owner_budget(self):
        from custom_components.djconnect.surface_widget_adoption import MAX_OWNER_HANDLES
        for _ in range(MAX_OWNER_HANDLES):
            h = self.begin()
            self.service.withdraw_widget_adoption(h)
        with self.assertRaisesRegex(SurfacePushError, 'surface_widget_capacity'):
            self.begin()
        self.assertEqual(len(self.service._widget_adoptions._handles), MAX_OWNER_HANDLES)
        self.assertFalse(self.f.transport.calls)

    async def test_pending_lease_not_extended_by_slow_signer(self):
        h = self.begin()
        async def hook(action):
            self.f.clock[:] = [START + 120000, 220.0]
        self.owner.on_sign = hook
        with self.assertRaises(SurfacePushError):
            await self.service.adopt_widget(h)
        self.assertFalse(self.f.transport.calls)
        self.assertTrue(h.closed)

    async def test_withdrawn_replay_handle_releases_live_context_and_paired_headers(self):
        h = self.begin()
        capture_ref = weakref.ref(h.capture)
        self.assertEqual(h.capture.headers, self.headers)
        await self.service.adopt_widget(h)
        self.service.withdraw_widget_adoption(h)
        gc.collect()
        self.assertIsNone(capture_ref())
        self.assertIsNone(h.capture)
        self.assertIsNone(h.authority)
        self.assertIsNone(h.purpose)
        self.assertIsNone(h.task)
        self.assertNotIn(self.active.session_id, repr(h.key))
        self.assertIsNotNone(h.issuer_handle)  # Separate historical management.
        self.assertFalse((await h.lifecycle.status(h.issuer_handle))['available'])

    async def test_session_end_releases_capture_before_task_was_scheduled(self):
        h = self.begin()
        capture_ref = weakref.ref(h.capture)
        self.service.invalidate_session(self.profile, self.active.session_id)
        gc.collect()
        self.assertIsNone(capture_ref())
        self.assertIsNone(h.capture)


class WidgetActualHAContractTests(unittest.TestCase):
    def test_original_actual_ha_widget_source_join_preserves_closed_acceptance_boundary(self):
        root = Path(__file__).resolve().parents[1]
        wire = json.loads((root / 'examples/client_contracts/surface_push_v1/widget-adoption-actual-ha.json').read_text())
        self.assertEqual(wire['ha_sdk_version'], '2026.10.0')
        self.assertEqual(len(wire['source_pins']), 279)
        self.assertIn('custom_components/djconnect/artist_review_words.py', wire['source_pins'])
        for relative, expected in wire['source_pins'].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), expected, relative)
        self.assertEqual(hashlib.sha256((root / wire['harness']).read_bytes()).hexdigest(), wire['harness_sha256'])
        for key in ('pre_scheduling_unload_denied', 'late_paired_authority_scrubbed',
                'original_ES256_and_SQL15_before_RPC', 'once_original_winner_no_renewal'):
            self.assertIs(wire['widget_adoption'][key], True)
        self.assertEqual(wire['widget_adoption']['synthetic_issuer_calls'], ['challenge', 'issue'])
        for key in ('operator_enrollment', 'actual_key_custody', 'installed', 'APNs', 'native'):
            self.assertEqual(wire[key], 'NOT_RUN')
        self.assertEqual(wire['Activity_rights'], 'NOT_ADMITTED')
        self.assertEqual(wire['external_API_calls'], 0)
