"""Once-only widget signals, original grant/deadline, synthetic provider ACK."""
import asyncio
import json
import unittest
from tests import test_surface_push_registry as fixture
from tests.test_transport_operation_journal import identifier
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.surface_push_wire import canonical


class SurfaceEventTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = fixture.SurfaceRegistryTests()
        await self.f.asyncSetUp()
        result = await self.f.registry.register(self.f.intent(),self.f.admission)
        self.coordinate = result['registration']
        self.expected = {k:self.coordinate[k] for k in ('registration_id','generation','revision')}
        self.operation = identifier(self.f.clock[0],3)
        async def relay(action,request):
            if action!='event':
                return self.f.ack(action,request)
            row = next(iter(self.f.journal._state['records'].values()))
            self.assertTrue(row)
            result = self.f.ack('register',{**request,'expires_at_ms':self.coordinate['expires_at_ms']})
            result.update(operation_state='provider_accepted',provider_status=200)
            return result
        self.f.hook = relay

    async def asyncTearDown(self):
        await self.f.registry.close()

    async def signal(self):
        return await self.f.registry.signal_widget(self.f.admission,self.expected,operation_id=self.operation)

    async def test_signal_only_once_no_content_or_deadline_renewal(self):
        result = await self.signal()
        replay = await self.signal()
        self.assertTrue(result['provider_accepted'])
        self.assertTrue(replay['replayed'])
        self.assertTrue(replay['success'])
        events = [body for action,body in self.f.calls if action=='event']
        self.assertEqual(len(events),1)
        self.assertEqual(set(events[0]),{'contract_version','registration_id','generation','revision',
            'operation_id','binding_id','device_binding','owner_binding','event'})
        self.assertEqual(events[0]['event'],'widget_reload')
        self.assertEqual(result['registration']['expires_at_ms'],self.coordinate['expires_at_ms'])
        self.assertEqual(self.f.purpose._event_attempts,1)
        operation = next(r for r in self.f.journal._state['records'].values() if r['operation']=='push/surface/event')
        self.assertEqual(operation['phase'],'confirmed')

    async def test_unknown_provider_outcome_never_resends_or_restores_attempt_budget(self):
        async def lost(action,body):
            return {'success':False,'error':'synthetic-unknown'}
        self.f.hook = lost
        result = await self.signal()
        self.assertFalse(result['success'])
        replay = await self.signal()
        self.assertFalse(replay['success'])
        self.assertEqual(len(self.f.calls),2)  # registration plus one original signal
        self.assertEqual(self.f.purpose._event_attempts,1)

    async def test_revocation_during_wait_does_not_promote_late_provider_ack(self):
        entered,finish = asyncio.Event(),asyncio.Event()
        original = self.f.hook
        async def waiting(action,body):
            if action=='event':
                entered.set()
                await finish.wait()
            return await original(action,body)
        self.f.hook = waiting
        task = asyncio.create_task(self.signal())
        await entered.wait()
        self.f.purpose_valid = False
        finish.set()
        result = await task
        self.assertFalse(result['success'])
        self.assertEqual(result['registration']['state'],'withdrawn')
        self.assertEqual(len(self.f.calls),2)

    async def test_budget_exhaustion_rejects_before_second_signal_effect(self):
        policy = json.loads(self.f.purpose.policy_json)
        policy['max_events'] = 1
        object.__setattr__(self.f.purpose,'policy_json',canonical(policy))  # fixture-only issuer policy
        await self.signal()
        self.operation = identifier(self.f.clock[0],4)
        with self.assertRaisesRegex(SurfacePushError,'surface_event_budget_exhausted'):
            await self.signal()
        self.assertEqual(len(self.f.calls),2)

    async def test_cancellation_is_original_unknown_effect_with_no_replay_send(self):
        entered = asyncio.Event()
        async def waiting(action,body):
            entered.set()
            await asyncio.Event().wait()
        self.f.hook = waiting
        task = asyncio.create_task(self.signal())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        replay = await self.signal()
        self.assertFalse(replay['success'])
        self.assertEqual(len(self.f.calls),2)
        self.assertFalse(self.f.journal._active)

    async def test_event_cannot_smuggle_content_even_with_a_current_widget_purpose(self):
        payload = {"contract_version":1,**self.expected,"operation_id":self.operation,
            "binding_id":self.f.admission.binding,"device_binding":self.f.admission.device,
            "owner_binding":self.f.admission.owner,"event":"widget_reload","title":"private-content"}
        with self.assertRaisesRegex(SurfacePushError,"surface_purpose_scope_mismatch"):
            self.f.purpose.authorize("event",payload)
        self.assertFalse(self.f.purpose.is_current())
        self.assertEqual(len(self.f.calls),1)

    async def test_queued_revoke_before_send_child_prevents_old_event_RPC(self):
        entered,release_event,revoke_local,release_revoke = (asyncio.Event() for _ in range(4))
        original = self.f.journal.transition
        async def transition(key,phase,**kwargs):
            result = await original(key,phase,**kwargs)
            operation = self.f.journal._state['records'][key]['operation']
            if phase=='sent_unknown' and operation=='push/surface/event':
                entered.set()
                await release_event.wait()
            if phase=='sent_unknown' and operation=='push/surface/revoke':
                revoke_local.set()
                await release_revoke.wait()
            return result
        self.f.journal.transition = transition
        event = asyncio.create_task(self.signal())
        await entered.wait()
        revoke = asyncio.create_task(self.f.registry.revoke(self.f.admission,self.expected,
            operation_id=identifier(self.f.clock[0],6),digest='e'*64))
        await asyncio.sleep(0)  # Revoke is queued on the event's original registry lock.
        release_event.set()
        await revoke_local.wait()
        try:
            for _ in range(5):
                await asyncio.sleep(0)
            self.assertFalse([a for a,_ in self.f.calls if a=='event'])
        finally:
            release_revoke.set()
            await asyncio.gather(event,revoke,return_exceptions=True)

    async def test_revoke_withdraws_local_grant_before_first_journal_save_await(self):
        row = self.f.registry._entries[self.expected['registration_id']]
        before = []
        original = self.f.store.async_save
        async def save(data):
            if any(r['operation']=='push/surface/revoke' for r in data['records'].values()):
                before.append(row.live(self.f.clock[0]))
            await original(data)
        self.f.store.async_save = save
        await self.f.registry.revoke(self.f.admission,self.expected,
            operation_id=identifier(self.f.clock[0],6),digest='e'*64)
        self.assertTrue(before)
        self.assertFalse(any(before))
