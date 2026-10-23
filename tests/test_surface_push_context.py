"""Real context/registry/journal races; paired resolver/relay are synthetic here."""
import asyncio
from dataclasses import replace
import gc
import hashlib
from types import SimpleNamespace
import unittest
import weakref

from tests import test_surface_push_registry as registry_fixture
from custom_components.djconnect.surface_push_context import SurfaceContextContinuations
from custom_components.djconnect.surface_push_contract import SurfacePushError


class SurfaceContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = registry_fixture.SurfaceRegistryTests()
        await self.f.asyncSetUp()
        self.service = SimpleNamespace(closed=False, registry=self.f.registry,
            track_registration=lambda result: None, _purposes={}, preauthorize_context=lambda payload, headers: None)
        self.pause = None
        self.entered = asyncio.Event()
        async def admission(payload, headers):
            original = self.f.admission
            self.entered.set()
            if self.pause is not None:
                await self.pause.wait()
            original.validate()
            return original
        self.service.admission = admission
        self.c = SurfaceContextContinuations(self.service,
            wall=lambda: self.f.clock[0], monotonic=lambda: self.f.clock[1])

    def payload(self, sequence=1):
        intent = self.f.intent(sequence)
        return {**{k:intent.metadata()[k] for k in ('device_id','client_type','session_id','operation_id')},
            'contract_version': 2}

    async def acquire(self, sequence=1):
        return await self.c.acquire(self.payload(sequence), {})

    async def test_original_expiry_and_short_submit_are_separate(self):
        result = await self.acquire()
        self.assertEqual(result['expires_at_ms'], self.f.purpose.original_expiry_ms())
        self.assertEqual(result['context_expires_at_ms'], self.f.clock[0] + 30000)
        self.assertNotEqual(result['expires_at_ms'], result['context_expires_at_ms'])
        self.assertFalse(self.f.calls)
        self.assertIsNone(self.f.store.data)

    async def test_lost_context_same_operation_does_not_renew_or_refund(self):
        body = self.payload()
        first = await self.c.acquire(body, {})
        self.f.clock[0] += 1000
        self.f.clock[1] += 1
        second = await self.c.acquire(body, {})
        self.assertEqual(first, second)
        self.assertEqual(self.c._purposes[0].attempts, 1)
        self.assertEqual(len(self.c._contexts), 1)

    async def test_successful_row_outlives_context_submit_deadline(self):
        context = await self.acquire()
        result = await self.c.register(context['context_handle'], self.f.intent(), {})
        self.assertTrue(result['success'])
        self.assertEqual(result['registration']['expires_at_ms'], context['expires_at_ms'])
        self.f.clock[0] += 31000
        self.f.clock[1] += 31
        self.c._collect()
        row = self.f.registry._entries[result['registration']['registration_id']]
        self.assertTrue(row.live(self.f.clock[0]))
        self.assertIs(row.admission, self.f.admission)
        self.assertEqual(result['purpose_ref'], context['purpose_ref'])
        self.assertEqual(result['operation_id'], context['operation_id'])
        self.assertEqual(result['context_handle'], context['context_handle'])

    async def test_same_operation_replay_recovers_original_credential_once(self):
        context = await self.acquire()
        first = await self.c.register(context['context_handle'], self.f.intent(), {})
        replay = await self.c.register(context['context_handle'], self.f.intent(), {})
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['background_read'], replay['background_read'])
        self.assertEqual(len(self.f.calls), 1)

    async def test_token_rotation_keeps_original_purpose_ref_and_grant_expiry(self):
        a = await self.acquire()
        first = await self.c.register(a['context_handle'], self.f.intent(), {})
        self.f.clock[0] += 1000
        self.f.clock[1] += 1
        b = await self.acquire(2)
        expected = {k:first['registration'][k] for k in ('registration_id','generation','revision')}
        rotated = await self.c.register(b['context_handle'],
            self.f.intent(2, expected_registration=expected, apns_token='b'*64), {})
        self.assertNotEqual(a['context_handle'], b['context_handle'])
        self.assertEqual(a['purpose_ref'], b['purpose_ref'])
        self.assertEqual(rotated['registration']['expires_at_ms'], a['expires_at_ms'])
        self.assertEqual(rotated['registration']['revision'], 2)
        self.assertEqual(len(self.f.calls), 2)

    async def test_equal_valued_new_purpose_is_never_original_continuity(self):
        a = await self.acquire()
        self.f.purpose = replace(self.f.purpose)
        self.f.admission = replace(self.f.admission, purpose=self.f.purpose)
        b = await self.acquire(2)
        self.assertEqual(a['expires_at_ms'], b['expires_at_ms'])
        self.assertNotEqual(a['purpose_ref'], b['purpose_ref'])
        with self.assertRaises(SurfacePushError):
            await self.c.register(a['context_handle'], self.f.intent(), {})
        self.assertFalse(self.f.calls)

    async def test_conflicting_operation_and_digest_cannot_send(self):
        context = await self.acquire()
        with self.assertRaises(SurfacePushError):
            await self.c.register(context['context_handle'], self.f.intent(2), {})
        await self.c.register(context['context_handle'], self.f.intent(), {})
        with self.assertRaises(SurfacePushError):
            await self.c.register(context['context_handle'], self.f.intent(apns_token='b'*64), {})
        self.assertEqual(len(self.f.calls), 1)

    async def test_pending_paired_resolution_is_cancelled_before_any_handle(self):
        self.pause = asyncio.Event()
        task = asyncio.create_task(self.acquire())
        await self.entered.wait()
        self.c.invalidate()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.c._contexts)
        self.assertFalse(self.c._pending)
        self.assertFalse(self.f.calls)

    async def test_late_paired_register_cannot_restore_retired_capture(self):
        context = await self.acquire()
        self.entered.clear()
        self.pause = asyncio.Event()
        task = asyncio.create_task(self.c.register(context['context_handle'], self.f.intent(), {}))
        await self.entered.wait()
        self.c.invalidate()
        self.pause.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        record = self.c._contexts[context['context_handle']]
        self.assertIsNone(record.admission)
        self.assertIsNone(record.task)
        self.assertFalse(self.f.calls)

    async def test_withdrawal_releases_original_admission_but_keeps_tombstone(self):
        context = await self.acquire()
        admission = weakref.ref(self.f.admission)
        self.c.invalidate()
        self.f.admission = None
        gc.collect()
        self.assertIsNone(admission())
        record = self.c._contexts[context['context_handle']]
        self.assertIsNone(record.admission)
        self.assertEqual(record.purpose.attempts, 1)
        self.assertIn(context['operation_id'], self.c._operations)

    async def test_expired_context_cannot_reanchor_after_wall_rollback(self):
        context = await self.acquire()
        self.f.clock[1] += 31
        self.f.clock[0] -= 1
        with self.assertRaises(SurfacePushError):
            await self.c.register(context['context_handle'], self.f.intent(), {})
        self.assertFalse(self.f.calls)
        self.assertEqual(self.c._purposes[0].attempts, 1)

    async def test_expired_submit_during_relay_never_publishes_read_credential(self):
        context = await self.acquire()
        async def delay(action, request):
            self.f.clock[0] += 31000
            self.f.clock[1] += 31
            return self.f.ack(action, request)
        self.f.hook = delay
        with self.assertRaises(SurfacePushError):
            await self.c.register(context['context_handle'], self.f.intent(), {})
        self.assertEqual(len(self.f.calls), 1)
        self.assertTrue(all(not r.read_secret for r in self.f.registry._entries.values()))
        self.assertEqual(next(iter(self.f.registry._entries.values())).expires_ms, context['expires_at_ms'])

    async def test_context_capacity_never_evicts_or_refunds_consumed_history(self):
        for sequence in range(1, 9):
            await self.acquire(sequence)
        self.c.invalidate()
        with self.assertRaises(SurfacePushError):
            await self.acquire(9)
        self.assertEqual(self.c._purposes[0].attempts, 8)
        self.assertEqual(len(self.c._contexts), 8)

    async def test_restart_old_handle_unknown_does_not_mint_purpose(self):
        context = await self.acquire()
        restarted = SurfaceContextContinuations(self.service,
            wall=lambda:self.f.clock[0], monotonic=lambda:self.f.clock[1])
        with self.assertRaises(SurfacePushError):
            await restarted.register(context['context_handle'], self.f.intent(), {})
        self.assertFalse(restarted._purposes)
        self.assertFalse(self.f.calls)

    async def test_wrong_owner_cannot_poison_original_context_or_digest(self):
        context = await self.acquire()
        original = self.f.admission
        self.f.admission = replace(original, owner='9'*64)
        with self.assertRaises(SurfacePushError):
            await self.c.register(context['context_handle'], self.f.intent(apns_token='b'*64), {})
        record = self.c._contexts[context['context_handle']]
        self.assertIsNone(record.closed)
        self.assertIsNone(record.digest)
        self.f.admission = original
        result = await self.c.register(context['context_handle'], self.f.intent(), {})
        self.assertTrue(result['success'])
        self.assertEqual(len(self.f.calls), 1)

    async def test_authenticated_late_context_attempt_cannot_reanchor_on_retry(self):
        body = self.payload()
        original = self.f.admission
        async def late(payload, headers):
            self.f.clock[0] += 31000
            self.f.clock[1] += 31
            return original
        self.service.admission = late
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(body, {})
        record = self.c._operations[body['operation_id']]
        self.assertEqual(record.closed, 'expired')
        self.assertEqual(record.purpose.attempts, 1)
        async def normal(payload, headers):
            return original
        self.service.admission = normal
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(body, {})
        self.assertEqual(record.purpose.attempts, 1)
        self.assertEqual(len(self.c._contexts), 1)
        self.assertFalse(self.f.calls)

    async def test_session_withdrawal_does_not_cancel_other_pending_session(self):
        gate = asyncio.Event()
        both = asyncio.Event()
        count = 0
        original = self.f.admission
        async def paused(payload, headers):
            nonlocal count
            count += 1
            if count == 2:
                both.set()
            await gate.wait()
            return replace(original, session_id=payload['session_id'])
        self.service.admission = paused
        a = self.payload()
        b = {**self.payload(2), 'session_id':'other-session'}
        first = asyncio.create_task(self.c.acquire(a, {}))
        second = asyncio.create_task(self.c.acquire(b, {}))
        await both.wait()
        self.c.invalidate(original.owner, original.session_id)
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(second.done())
        gate.set()
        result = await second
        self.assertTrue(result['available'])

    async def test_cancelled_first_paired_await_keeps_original_submit_clock(self):
        body = self.payload()
        self.pause = asyncio.Event()
        task = asyncio.create_task(self.c.acquire(body, {}))
        await self.entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.c._contexts)
        self.assertIn(body['operation_id'], self.c._starts)
        self.f.clock[0] += 31000
        self.f.clock[1] += 31
        self.pause = None
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(body, {})
        record = self.c._operations[body['operation_id']]
        self.assertEqual(record.closed, 'expired')
        self.assertEqual(record.purpose.attempts, 1)
        self.assertFalse(self.f.calls)


    async def test_late_admission_error_keeps_original_submit_clock(self):
        for error in (SurfacePushError('surface_purpose_unavailable', 503), OSError('offline')):
            with self.subTest(error=type(error).__name__):
                body = self.payload(30 + len(self.c._starts))
                original = self.f.admission
                async def late(payload, headers):
                    self.f.clock[0] += 31000
                    self.f.clock[1] += 31
                    raise error
                self.service.admission = late
                with self.assertRaises(type(error)):
                    await self.c.acquire(body, {})
                self.assertIn(body['operation_id'], self.c._starts)
                async def normal(payload, headers):
                    return original
                self.service.admission = normal
                with self.assertRaises(SurfacePushError):
                    await self.c.acquire(body, {})
                self.assertFalse(self.f.calls)

    async def test_purpose_withdrawal_cancels_only_original_pending_capture(self):
        gate = asyncio.Event()
        both = asyncio.Event()
        count = 0
        device = hashlib.sha256(self.payload()['device_id'].encode()).hexdigest()
        purpose = replace(self.f.purpose, device_binding=device)
        original = replace(self.f.admission, device=device, purpose=purpose)
        other = replace(original.purpose)
        self.service._purposes = {
            (original.owner, original.device, original.binding, original.session_id): original.purpose,
            (original.owner, original.device, original.binding, 'other-session'): other,
        }
        async def paused(payload, headers):
            nonlocal count
            count += 1
            if count == 2:
                both.set()
            await gate.wait()
            return replace(original, session_id=payload['session_id'], purpose=other)
        self.service.admission = paused
        a = self.payload()
        b = {**self.payload(2), 'session_id':'other-session'}
        first = asyncio.create_task(self.c.acquire(a, {}))
        second = asyncio.create_task(self.c.acquire(b, {}))
        await both.wait()
        self.c.invalidate(purpose=original.purpose)
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(second.done())
        gate.set()
        self.assertTrue((await second)['available'])


    async def test_unauthorized_requests_never_reserve_global_context_capacity(self):
        original = self.service.admission
        def denied(payload, headers):
            raise SurfacePushError('unauthorized', 401)
        async def denied_async(payload, headers):
            denied(payload, headers)
        self.service.preauthorize_context = denied
        self.service.admission = denied_async
        for sequence in range(64):
            body = {**self.payload(sequence + 1), 'device_id':'forged-device-' + str(sequence // 8)}
            with self.assertRaises(SurfacePushError) as error:
                await self.c.acquire(body, {})
            self.assertEqual(error.exception.status, 401)
        self.assertFalse(self.c._starts)
        self.assertFalse(self.c._pending)
        self.assertFalse(self.c._contexts)
        self.service.preauthorize_context = lambda payload, headers: None
        self.service.admission = original
        self.assertTrue((await self.acquire(100))['available'])


class ContextActualHAContractTests(unittest.TestCase):
    def test_original_actual_context_and_registered_authority_keep_distinct_deadlines(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        raw = (root / 'examples/client_contracts/surface_push_v2/actual-ha-context-continuation.json').read_text()
        proof = json.loads(raw)
        self.assertNotIn('djcsurface_', raw)
        self.assertEqual(len(proof['source_pins']), 264)
        for relative, expected in proof['source_pins'].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), expected, relative)
        self.assertEqual(hashlib.sha256((root / proof['harness']).read_bytes()).hexdigest(), proof['harness_sha256'])
        context = proof['context_response']
        self.assertEqual(context['contract_version'], 2)
        self.assertEqual(context['operation_id'], proof['context_request']['operation_id'])
        self.assertLess(context['context_expires_at_ms'], context['expires_at_ms'])
        self.assertEqual(context['expires_at_ms'], proof['registration']['expires_at_ms'])
        self.assertEqual(context['expires_at_ms'], proof['background_read_metadata']['expires_at_ms'])
        self.assertTrue(proof['same_operation_context_replay_equal'])
        self.assertEqual(proof['registered_echoes'], {k:context[k] for k in ('context_handle','operation_id','purpose_ref')})
        self.assertEqual(proof['unauthorized_HTTP_context_denials'], 65)
        self.assertEqual(proof['actual_paired_late_errors_preserve_original_clock'], ['503','OSError'])
        for key in ('operator_enrollment', 'actual_key_custody', 'installed', 'APNs', 'native'):
            self.assertEqual(proof[key], 'NOT_RUN')
        self.assertEqual(proof['Activity_rights'], 'NOT_ADMITTED')
