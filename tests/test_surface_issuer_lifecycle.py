"""Real disposable SQL, explicitly synthetic owner/RPC and crypto boundary stub.

This suite proves original phase ordering, not operator enrollment or signature
verification. Real software ES256 is qualified separately in isolated actual HA.
"""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from tests.test_profile_dj_settings_persistence import operation
from tests.test_surface_issuer_owner import capture, START
from custom_components.djconnect.surface_issuer_journal import IssuerStageJournal, IssuerStageStore
from custom_components.djconnect.surface_issuer_owner import EnrolledIssuerOwner
from custom_components.djconnect.surface_issuer_transport import IssuerTransport, IssuerHTTPReply, strict_body
from custom_components.djconnect.surface_issuer_lifecycle import IssuerLifecycle
from custom_components.djconnect.surface_push_contract import SurfacePushError


class SyntheticEnrolledFixture(EnrolledIssuerOwner):
    """Test-only explicitly pre-enrolled generation; no real key or operator."""
    def __init__(self):
        self.capture = capture()
        self.original_witness = self.capture.witness
        self.valid, self.status_valid, self.withdraw_valid = True, True, True
        self.valid_result = None
        self.signs = []
        self.on_sign = None

    def capture_live(self, operation_id):
        return replace(self.capture, expected=replace(self.capture.expected, operation_id=operation_id))

    def validate_live(self, original):
        if not self.valid or original.witness is not self.original_witness:
            raise SurfacePushError('synthetic_owner_changed')
        return self.valid_result

    def validate_status(self, original):
        if not self.status_valid or original.witness is not self.original_witness:
            raise SurfacePushError('synthetic_status_changed')

    def validate_withdrawal(self, original):
        if not self.withdraw_valid or original.witness is not self.original_witness:
            raise SurfacePushError('synthetic_withdraw_changed')

    async def sign(self, original, path, message, *, action):
        self.signs.append(action)
        if self.on_sign:
            await self.on_sign(action)
        return 'A' * 86  # Explicit crypto boundary stub only.


class SyntheticTransport(IssuerTransport):
    def __init__(self, test):
        self.test, self.calls, self.on_call = test, [], None
        self.reply_status, self.replayed = 200, False

    async def post_once(self, original, action, envelope, *, guard, deadline):
        guard()
        row = await self.test.row()
        # Actual SQL must already be committed at the remote-effect boundary.
        phase = next(iter(row['records'].values()))['phase']
        self.test.assertEqual(phase, {'challenge': 'challenge_reserved', 'issue': 'issue_reserved',
            'status': phase, 'withdraw': 'withdrawn'}[action])
        self.calls.append((action, envelope['payload']['operation_id']))
        if self.on_call:
            await self.on_call(action)
        # Deliberately allow a late ACK through this stub: the lifecycle must
        # reject it independently, even if a transport forgets its final guard.
        expected = original.expected
        reply = {'contract_version': 1, 'success': True,
            'operation_id': envelope['payload']['operation_id'],
            'delegation_id': expected.delegation_id, 'delegation_revision': 1,
            'expires_at_ms': expected.original_grant_expires_ms, 'state': action,
            'replayed': self.replayed}
        if action == 'challenge':
            reply.update(scope_digest=expected.scope_digest, key_thumbprint=expected.key_thumbprint,
                challenge_id='synthetic_challenge', nonce='A' * 43, expires_at_ms=START + 120000)
        elif action == 'issue':
            reply.update(scope_digest=expected.scope_digest, state='issued',
                capability_id='synthetic_capability', credential='djcs_' + 'A' * 43)
        elif action == 'status':
            reply.update(scope_digest=expected.scope_digest, success=False, state='issued',
                capability_id='synthetic_capability', credential_state='unavailable')
        elif action == 'withdraw':
            reply['state'] = 'withdrawn'
        return IssuerHTTPReply(self.reply_status, reply)


class IssuerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.persistence = PersistenceService(Path(self.directory.name) / 'issuer.sqlite', SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.journal = IssuerStageJournal(IssuerStageStore(self.persistence))
        self.owner = SyntheticEnrolledFixture()
        self.clock = [START, 100.0]
        self.transport = SyntheticTransport(self)
        self.lifecycle = IssuerLifecycle(self.owner, self.journal, self.transport,
            wall=lambda: self.clock[0], monotonic=lambda: self.clock[1])
        self.crypto = patch('custom_components.djconnect.surface_issuer_lifecycle.verify_envelope', return_value=True)
        self.crypto.start()
        self.addCleanup(self.crypto.stop)

    async def asyncTearDown(self):
        await self.persistence.async_close()
        self.directory.cleanup()

    async def row(self):
        row = await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT body FROM djconnect_surface_issuer_journal WHERE singleton=1'))
        return json.loads(row[0])

    def original(self):
        return next(iter(self.lifecycle._attempts.values())).handle

    async def test_actual_commit_precedes_both_signatures_and_requests_same_uuid_original_anchors(self):
        async def before_sign(action):
            row = await self.row()
            self.assertEqual(next(iter(row['records'].values()))['phase'],
                {'challenge': 'challenge_reserved', 'issue': 'issue_reserved'}[action])
        self.owner.on_sign = before_sign
        purpose = await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual(self.owner.signs, ['challenge', 'issue'])
        self.assertEqual(self.transport.calls, [('challenge', operation(START)), ('issue', operation(START))])
        self.assertEqual((purpose.original_wall_ms, purpose.original_monotonic), (START, 100.0))
        self.assertTrue(purpose.is_current())
        raw = json.dumps(await self.row())
        for forbidden in ('djcs_', 'synthetic_delegation', 'synthetic_install', 'nonce', 'credential', 'signature'):
            if forbidden == 'credential':  # phase label is not secret credential material.
                continue
            self.assertNotIn(forbidden, raw)
        self.assertEqual(next(iter((await self.row())['records'].values()))['phase'], 'credential_held')

    async def test_no_default_owner_and_boolean_validation_cannot_admit(self):
        with self.assertRaises(SurfacePushError):
            IssuerLifecycle(True, self.journal, self.transport)
        self.owner.valid_result = True
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual(self.owner.signs, [])
        self.assertEqual(self.transport.calls, [])

    async def test_begin_captures_original_deadline_before_caller_schedules_acquisition(self):
        handle = self.lifecycle.begin(operation(START))
        self.clock[:] = [START + 120000, 220.0]
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(handle)
        self.assertEqual(self.owner.signs, [])
        self.assertEqual(self.transport.calls, [])
        self.assertEqual((await self.row())['records'], {})

    async def test_cloned_or_other_lifecycle_management_handle_is_not_original_admission(self):
        handle = self.lifecycle.begin(operation(START))
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(replace(handle))
        foreign = IssuerLifecycle(self.owner, IssuerStageJournal(IssuerStageStore(self.persistence)),
            self.transport, wall=lambda: self.clock[0], monotonic=lambda: self.clock[1])
        with self.assertRaises(SurfacePushError):
            await foreign.status(handle)
        self.assertEqual(self.transport.calls, [])

    async def test_owner_stop_closes_ram_purpose_and_management_without_another_request(self):
        handle = self.lifecycle.begin(operation(START))
        purpose = await self.lifecycle.acquire(handle)
        self.lifecycle.close()
        self.assertEqual(purpose.bearer, '')
        self.assertFalse(purpose.is_current())
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.status(handle)
        with self.assertRaises(SurfacePushError):
            self.lifecycle.begin(operation(START + 1))
        self.assertEqual([a for a, _ in self.transport.calls], ['challenge', 'issue'])

    async def test_close_during_issue_transport_rejects_late_ack_and_never_rearms(self):
        async def close(action):
            if action == 'issue':
                self.lifecycle.close()
        self.transport.on_call = close
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertTrue(self.lifecycle.closed)
        self.assertIsNone(next(iter(self.lifecycle._attempts.values())).purpose)

    async def test_owner_key_generation_aba_during_signer_rejects_before_network(self):
        async def replace_witness(_):
            self.owner.original_witness = object()
        self.owner.on_sign = replace_witness
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual(self.owner.signs, ['challenge'])
        self.assertEqual(self.transport.calls, [])
        self.assertTrue((await self.row())['records'])

    async def test_slow_signer_cannot_refresh_original_challenge_window(self):
        async def slow(_):
            self.clock[0] += 120000
            self.clock[1] += 120
        self.owner.on_sign = slow
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual(self.transport.calls, [])

    async def test_shorter_original_challenge_monotonic_expiry_even_when_wall_clock_slow(self):
        async def slow_issue(action):
            if action == 'issue':
                self.clock[0] += 500
                self.clock[1] += 120
        self.owner.on_sign = slow_issue
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual([a for a, _ in self.transport.calls], ['challenge'])

    async def test_late_issue_ack_after_concurrent_local_withdraw_never_adopts(self):
        async def withdraw(action):
            if action == 'issue':
                await self.lifecycle.withdraw(self.original(), operation(START + 1))
        self.transport.on_call = withdraw
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        attempt = next(iter(self.lifecycle._attempts.values()))
        self.assertTrue(attempt.closed)
        self.assertIsNone(attempt.purpose)
        self.assertEqual(next(iter((await self.row())['records'].values()))['phase'], 'withdrawn')

    async def test_withdraw_fences_purpose_before_storage_lock_even_already_cancelled(self):
        purpose = await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        async def cancelled_withdraw():
            asyncio.current_task().cancel()
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                pass
            with self.assertRaises(asyncio.CancelledError):
                await self.lifecycle.withdraw(self.original(), operation(START + 1))
            self.assertEqual(purpose.bearer, '')
        await asyncio.create_task(cancelled_withdraw())
        self.assertFalse(purpose.is_current())
        self.assertEqual([a for a, _ in self.transport.calls], ['challenge', 'issue'])

    async def test_lost_response_consumes_identity_new_uuid_and_restart_cannot_reissue(self):
        async def lost(_):
            raise SurfacePushError('synthetic_lost_response')
        self.transport.on_call = lost
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        original_calls = list(self.transport.calls)
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START + 1)))
        fresh = IssuerLifecycle(self.owner, IssuerStageJournal(IssuerStageStore(self.persistence)),
            self.transport, wall=lambda: self.clock[0], monotonic=lambda: self.clock[1])
        with self.assertRaises(SurfacePushError):
            await fresh.acquire(fresh.begin(operation(START + 2)))
        with self.assertRaises(SurfacePushError):
            await fresh.status(self.original())
        self.assertEqual(self.transport.calls, original_calls)

    async def test_duplicate_or_202_never_provides_nonce_or_readiness_or_retry(self):
        self.transport.reply_status = 202
        self.transport.replayed = True
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual([a for a, _ in self.transport.calls], ['challenge'])

    async def test_expired_original_status_then_fresh_withdraw_use_separate_authorities(self):
        purpose = await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        original = self.original()
        self.clock[0] += 3600001
        self.clock[1] += 3600.001
        self.owner.valid = False  # Live admission gone; historical authorities remain.
        self.assertFalse(purpose.is_current())
        self.assertEqual(await self.lifecycle.status(original), {'available': False, 'state': 'issued'})
        self.assertEqual(await self.lifecycle.withdraw(original, operation(self.clock[0])),
            {'available': False, 'state': 'withdrawn'})
        self.assertEqual(self.transport.calls[-2:], [('status', operation(START)),
            ('withdraw', operation(self.clock[0]))])
        self.assertFalse(purpose.is_current())

    async def test_historical_status_or_withdraw_cannot_use_live_admission_as_substitute(self):
        await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.owner.status_valid = False
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.status(self.original())
        self.owner.withdraw_valid = False
        with self.assertRaises(SurfacePushError):
            await self.lifecycle.withdraw(self.original(), operation(START + 1))
        self.assertEqual([a for a, _ in self.transport.calls], ['challenge', 'issue'])

    async def test_signature_failure_never_sends_request(self):
        with patch('custom_components.djconnect.surface_issuer_lifecycle.verify_envelope',
                side_effect=SurfacePushError('synthetic_invalid_signature')):
            with self.assertRaises(SurfacePushError):
                await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        self.assertEqual(self.transport.calls, [])
        self.assertTrue((await self.row())['records'])

    async def test_cancelled_signer_cannot_swallow_cancellation_and_continue(self):
        async def cancelled(_):
            asyncio.current_task().cancel()
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                pass
        self.owner.on_sign = cancelled
        async def run():
            with self.assertRaises(asyncio.CancelledError):
                await self.lifecycle.acquire(self.lifecycle.begin(operation(START)))
        await asyncio.create_task(run())
        self.assertEqual(self.transport.calls, [])


class IssuerStrictResponseTests(unittest.TestCase):
    def test_bounded_unique_utf8_closed_numeric_domain(self):
        self.assertEqual(strict_body(b'{"ok":true}'), {'ok': True})
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.5}',
                b'{"x":9007199254740992}', b'{"x":"\xff"}', b'[]',
                b'{' + b' ' * 8192 + b'}', b'{"x":' * 30 + b'null' + b'}' * 30):
            with self.subTest(raw_size=len(raw)), self.assertRaises(SurfacePushError):
                strict_body(raw)
