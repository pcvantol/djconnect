"""Actual context producer; paired admission/issuer/relay seams are synthetic."""
from dataclasses import dataclass, replace
from fractions import Fraction
import asyncio
import gc
import hashlib
from types import SimpleNamespace
import unittest
import weakref

from tests import test_surface_push_registry as registry_fixture
from custom_components.djconnect.surface_push_context import SurfaceContextContinuations
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.surface_push_wire import canonical


@dataclass
class _SyntheticRuntimeWitness:
    entry: object = None


class OriginalClockProducerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = registry_fixture.SurfaceRegistryTests()
        await self.f.asyncSetUp()
        device = hashlib.sha256(self.f.payload['device_id'].encode()).hexdigest()
        self.f.purpose = replace(self.f.purpose, device_binding=device)
        self.f.admission = replace(self.f.admission, device=device, purpose=self.f.purpose)
        self.service = SimpleNamespace(closed=False, registry=self.f.registry,
            track_registration=lambda result: None, _purposes={},
            preauthorize_context=lambda payload, headers: None)
        async def admission(payload, headers):
            self.f.admission.validate()
            return self.f.admission
        self.service.admission = admission
        self.normal_admission = admission
        self.c = SurfaceContextContinuations(self.service,
            wall=self.f.purpose.wall, monotonic=self.f.purpose.monotonic)
        self.service.contexts = self.c
        self.attach(self.f.purpose)

    def attach(self, purpose):
        self.f.purpose = purpose
        self.f.admission = replace(self.f.admission, purpose=purpose)
        a = self.f.admission
        self.service._purposes = {(a.owner, a.device, a.binding, a.session_id): purpose}

    def payload(self, sequence=1):
        metadata = self.f.intent(sequence).metadata()
        return {**{k: metadata[k] for k in
            ('device_id', 'client_type', 'session_id', 'operation_id')},
            'contract_version': 3}

    def lifetime(self, milliseconds):
        import json
        policy = json.loads(self.f.purpose.policy_json)
        policy['original_grant_expires_at_ms'] = self.f.clock[0] + milliseconds
        self.attach(replace(self.f.purpose, policy_json=canonical(policy)))

    async def first_error(self, payload):
        async def unavailable(*args):
            raise SurfacePushError('surface_unavailable', 503)
        self.service.admission = unavailable
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})
        self.service.admission = self.normal_admission

    async def test_closed_context_reply_is_outer_version_three(self):
        reply = await self.c.acquire(self.payload(), {})
        self.assertEqual(reply['contract_version'], 3)
        self.assertEqual(len(reply), 11)
        self.assertIs(type(reply['purpose_remaining_at_original_start_ms']), int)

    async def test_budget_uses_original_grant_not_late_object_construction(self):
        self.lifetime(1000)
        self.f.clock[0] += 700
        self.f.clock[1] = .7
        # A newly constructed object still carries its admitted original anchors.
        self.attach(replace(self.f.purpose))
        self.f.clock[0] += 100
        self.f.clock[1] = .8
        reply = await self.c.acquire(self.payload(), {})
        self.assertEqual(reply['purpose_remaining_at_original_start_ms'], 199)
        self.assertEqual(reply['context_remaining_at_original_start_ms'], 199)

    async def test_already_known_wall_bound_caps_original_mono_budget(self):
        self.lifetime(1_000_000)
        self.f.clock[0] += 999_500
        self.f.clock[1] = .8
        reply = await self.c.acquire(self.payload(), {})
        self.assertEqual(reply['purpose_remaining_at_original_start_ms'], 500)
        self.assertEqual(reply['context_remaining_at_original_start_ms'], 500)

    async def test_late_503_does_not_recapture_equal_field_successor_root(self):
        payload = self.payload()
        await self.first_error(payload)
        self.attach(replace(self.f.purpose))
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})
        self.assertFalse(self.f.calls)

    async def test_absent_original_root_cannot_be_admitted_after_late_error(self):
        payload = self.payload()
        self.service._purposes = {}
        await self.first_error(payload)
        self.attach(self.f.purpose)
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})
        self.assertFalse(self.f.calls)

    async def test_lost_weak_root_does_not_become_a_new_initial_operation(self):
        payload = self.payload()
        root = weakref.ref(self.f.purpose)
        await self.first_error(payload)
        self.attach(replace(self.f.purpose))
        gc.collect()
        self.assertIsNone(root())
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})

    async def test_final_server_addition_never_rounds_submit_deadline_up(self):
        self.lifetime(937)
        origin = float(2**48)
        self.f.clock[1] = origin
        self.attach(replace(self.f.purpose, original_monotonic=origin))
        reply = await self.c.acquire(self.payload(), {})
        actual = self.c._contexts[reply['context_handle']].mono_deadline
        self.assertLessEqual(Fraction(actual) - Fraction(origin), Fraction(937, 1000))
        self.assertGreater(actual, origin)

    async def test_repeated_reply_preserves_original_remaining_fields(self):
        payload = self.payload()
        first = await self.c.acquire(payload, {})
        self.f.clock[0] += 1000
        self.f.clock[1] += 1
        second = await self.c.acquire(payload, {})
        self.assertEqual(first, second)
        self.assertEqual(first['purpose_remaining_at_original_start_ms'], 28_800_000)
        self.assertEqual(first['context_remaining_at_original_start_ms'], 30_000)
        self.assertEqual(self.c._purposes[0].attempts, 1)

    async def test_non_none_runtime_witness_is_captured_weakly_before_await(self):
        # The genuine HA Runtime class is a separate actual SDK qualification.
        runtime = _SyntheticRuntimeWitness()
        self.service.preauthorize_context = lambda payload, headers: runtime
        self.f.admission = replace(self.f.admission, runtime=runtime)
        reply = await self.c.acquire(self.payload(), {})
        start = self.c._starts[reply['operation_id']]
        self.assertIs(start.runtime(), runtime)
        self.assertTrue(reply['available'])

    async def test_equal_runtime_replacement_cannot_cross_original_capture(self):
        runtime = [_SyntheticRuntimeWitness()]
        self.service.preauthorize_context = lambda payload, headers: runtime[0]
        self.f.admission = replace(self.f.admission, runtime=runtime[0])
        payload = self.payload()
        await self.first_error(payload)
        previous = weakref.ref(runtime[0])
        runtime[0] = _SyntheticRuntimeWitness()
        self.f.admission = replace(self.f.admission, runtime=runtime[0])
        gc.collect()
        self.assertIsNone(previous())
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})

    async def test_clock_callable_replacement_is_not_same_domain_evidence(self):
        payload = self.payload()
        await self.first_error(payload)
        self.c.monotonic = lambda: self.f.clock[1]
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})

    async def test_qualified_root_on_a_different_clock_is_closed(self):
        self.attach(replace(self.f.purpose, monotonic=lambda: self.f.clock[1]))
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(self.payload(), {})

    async def test_first_await_cancellation_cannot_attach_successor_root(self):
        entered = asyncio.Event()
        async def pending(*args):
            entered.set()
            await asyncio.Event().wait()
        self.service.admission = pending
        payload = self.payload()
        task = asyncio.create_task(self.c.acquire(payload, {}))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.attach(replace(self.f.purpose))
        self.service.admission = self.normal_admission
        with self.assertRaises(SurfacePushError):
            await self.c.acquire(payload, {})
        self.assertFalse(self.f.calls)

    async def test_late_401_and_oserror_keep_the_original_root_and_clock(self):
        for index, error in enumerate((SurfacePushError('unauthorized', 401), OSError('offline'))):
            with self.subTest(error=type(error).__name__):
                payload = self.payload(index + 1)
                async def unavailable(*args):
                    self.f.clock[0] += 100
                    self.f.clock[1] += .1
                    raise error
                self.service.admission = unavailable
                with self.assertRaises(type(error)):
                    await self.c.acquire(payload, {})
                self.attach(replace(self.f.purpose))
                self.service.admission = self.normal_admission
                with self.assertRaises(SurfacePushError):
                    await self.c.acquire(payload, {})
        self.assertFalse(self.f.calls)

    async def test_legacy_purpose_does_not_round_original_deadline_up(self):
        self.lifetime(3000)
        origin = float(2**53)
        self.attach(replace(self.f.purpose, original_monotonic=origin))
        # Integer samples are admitted by the legacy clock type domain. A float
        # sum rounds origin+3 to origin+4 and wrongly accepts the exact expiry.
        self.f.clock[1] = int(origin) + 3
        with self.assertRaises(SurfacePushError):
            self.f.purpose.authorize('status', {key: getattr(self.f.purpose, key)
                for key in ('binding_id', 'device_binding', 'owner_binding')})


if __name__ == '__main__':
    unittest.main()


class OriginalClockActualHAProofTests(unittest.TestCase):
    def test_new_v3_actual_fixture_matches_current_product_and_harness(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / 'examples/client_contracts/surface_push_v3/actual-ha-original-clock-context.json').read_text())
        self.assertEqual(proof['contract_version'], 3)
        self.assertEqual(proof['ha_sdk_version'], '2026.10.0')
        self.assertEqual(len(proof['source_pins']), 279)
        self.assertIn('custom_components/djconnect/artist_review_words.py', proof['source_pins'])
        for relative, digest in proof['source_pins'].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest, relative)
        self.assertEqual(hashlib.sha256((root / proof['harness']).read_bytes()).hexdigest(), proof['harness_sha256'])
        self.assertTrue(all(proof['checks'].values()))
        for reply in proof['context_replies']:
            self.assertEqual(reply['contract_version'], 3)
            self.assertEqual(len(reply), 11)
            self.assertGreater(reply['context_remaining_at_original_start_ms'], 0)
            self.assertLessEqual(reply['context_remaining_at_original_start_ms'], 30000)
            self.assertLessEqual(reply['context_remaining_at_original_start_ms'], reply['purpose_remaining_at_original_start_ms'])
        for key in ('operator_enrollment', 'actual_key_custody', 'installed', 'APNs', 'native'):
            self.assertEqual(proof[key], 'NOT_RUN')
        self.assertEqual(proof['qualified_client_clock_rate_suspend_domain'], 'OPEN')
        self.assertEqual(proof['Activity_rights'], 'NOT_ADMITTED')
        self.assertEqual(proof['external_API_calls'], 0)
