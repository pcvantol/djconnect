"""Synthetic original Broadcast, real registry/journal; no progress push loop."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import unittest

from tests import test_surface_push_registry as fixture
from custom_components.djconnect.surface_push_service import SurfacePushService


class Broadcast:
    def __init__(self):
        self.callbacks = {}
        self.counter = 0
    def register_subscription(self,callback):
        self.counter += 1
        self.callbacks[str(self.counter)] = callback
        return str(self.counter)
    def unsubscribe(self,key):
        self.callbacks.pop(key,None)
    def emit(self,kind):
        for callback in tuple(self.callbacks.values()):
            callback({'event_type':kind,'payload':{'never_retained':'synthetic-private'}})


class SurfaceBroadcastTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = fixture.SurfaceRegistryTests()
        await self.f.asyncSetUp()
        self.broadcast = Broadcast()
        self.frame = {'state':'active','mood':{'value':'chill','revision':1},
            'presence':'balanced','persona':'warm','now_playing':None,'contribution':None}
        self.f.admission = replace(self.f.admission,broadcast=self.broadcast,projection=lambda:deepcopy(self.frame))
        self.service = SurfacePushService(SimpleNamespace(
            async_create_background_task=lambda coro,name:asyncio.create_task(coro,name=name)),SimpleNamespace(),None)
        self.service.registry = self.f.registry
        self.response = await self.f.registry.register(self.f.intent(),self.f.admission)
        self.service.track_registration(self.response)
        async def ack(action,request):
            reply = self.f.ack('register',{**request,'expires_at_ms':self.response['registration']['expires_at_ms']})
            reply.update(operation_state='provider_accepted',provider_status=200)
            return reply
        self.f.hook = ack

    async def asyncTearDown(self):
        await self.service.close()

    async def finish(self):
        for _ in range(5):
            tasks = tuple(self.service._tasks)
            if not tasks:
                return
            await asyncio.gather(*tasks,return_exceptions=True)
            await asyncio.sleep(0)
        self.fail('background producer did not quiesce')

    async def test_initial_snapshot_replay_and_progress_do_not_send_or_resubscribe(self):
        replay = await self.f.registry.register(self.f.intent(),self.f.admission)
        self.service.track_registration(replay)
        for i in range(100):
            self.frame['as_of'] = str(i)
            self.frame['delivery_sequence'] = i
            self.broadcast.emit('playback_progress')
            self.broadcast.emit('playback_changed')
        await self.finish()
        self.assertEqual(len(self.f.calls),1)
        self.assertEqual(len(self.broadcast.callbacks),1)
        self.assertEqual(self.broadcast.counter,1)

    async def test_one_real_change_sends_only_signal_keeps_original_grant_deadline(self):
        self.frame['mood'] = {'value':'energy','revision':2}
        self.broadcast.emit('mood_changed')
        await self.finish()
        self.assertEqual([a for a,_ in self.f.calls],['register','event'])
        body = self.f.calls[-1][1]
        self.assertEqual(body['event'],'widget_reload')
        self.assertNotIn('mood',body)
        self.assertNotIn('never_retained',repr(self.service._signals))
        self.assertEqual(self.f.registry._entries[self.response['registration']['registration_id']].expires_ms,
            self.response['registration']['expires_at_ms'])
        self.broadcast.emit('mood_changed')
        await self.finish()
        self.assertEqual(len(self.f.calls),2)

    async def test_inflight_changes_coalesce_to_one_later_original_operation(self):
        entered,finish = asyncio.Event(),asyncio.Event()
        original = self.f.hook
        async def wait(action,body):
            if len(self.f.calls)==2:
                entered.set()
                await finish.wait()
            return await original(action,body)
        self.f.hook = wait
        self.frame['persona'] = 'new-one'
        self.broadcast.emit('persona_changed')
        await entered.wait()
        for name in ('new-two','new-three','new-four'):
            self.frame['persona'] = name
            self.broadcast.emit('persona_changed')
        self.assertEqual(len(self.service._tasks),1)
        finish.set()
        await self.finish()
        self.assertEqual([a for a,_ in self.f.calls],['register','event','event'])
        self.assertNotEqual(self.f.calls[1][1]['operation_id'],self.f.calls[2][1]['operation_id'])

    async def test_owner_loss_latches_and_unsubscribes_even_on_progress(self):
        self.f.valid = False
        self.broadcast.emit('playback_progress')
        self.assertFalse(self.broadcast.callbacks)
        row = next(iter(self.f.registry._entries.values()))
        self.assertEqual(row.read_secret,'')
        self.f.valid = True
        self.frame['persona'] = 'cannot-rearm-original'
        self.broadcast.emit('persona_changed')
        await self.finish()
        self.assertEqual(len(self.f.calls),1)

    async def test_close_removes_subscription_and_cancels_its_single_worker(self):
        entered = asyncio.Event()
        async def wait(action,body):
            entered.set()
            await asyncio.Event().wait()
        self.f.hook = wait
        self.frame['persona'] = 'new-persona'
        self.broadcast.emit('persona_changed')
        await entered.wait()
        await self.service.close()
        self.assertFalse(self.broadcast.callbacks)
        self.assertFalse(self.service._tasks)
        self.assertFalse(self.service._signals)
        self.assertEqual(len(self.f.calls),2)

    async def test_playback_pause_resume_is_semantic_with_identical_recording_metadata(self):
        self.frame['playback_state'] = 'playing'
        self.frame['now_playing'] = {'item_id':'original','track':'Original recording',
            'artist':'Original artist','album':'Original album'}
        # Establish the displayed playing baseline without creating an event.
        self.service._signals[self.response['registration']['registration_id']].last = __import__(
            'custom_components.djconnect.surface_push_events',fromlist=['fingerprint']).fingerprint(self.frame)
        self.frame['playback_state'] = 'paused'
        self.broadcast.emit('playback_changed')
        await self.finish()
        self.frame['playback_state'] = 'playing'
        self.broadcast.emit('playback_changed')
        await self.finish()
        self.assertEqual([a for a,_ in self.f.calls],['register','event','event'])

    async def test_expired_watch_retires_its_map_entry_and_original_metadata(self):
        key = self.response['registration']['registration_id']
        watch = self.service._signals[key]
        self.f.clock[0] = self.response['registration']['expires_at_ms']+1
        self.broadcast.emit('playback_progress')
        self.assertTrue(watch.closed)
        self.assertNotIn(key,self.service._signals)
        self.assertIsNone(watch.row)
        self.assertIsNone(watch.broadcast)
        self.assertFalse(self.broadcast.callbacks)

    async def test_rotation_retires_original_watch_before_first_durable_await(self):
        key = self.response['registration']['registration_id']
        watch = self.service._signals[key]
        old = watch.row
        before = []
        original = self.f.store.async_save
        async def save(data):
            if len(data['records'])>1:
                before.append((old.live(self.f.clock[0]),key in self.service._signals,watch.row is None))
            await original(data)
        self.f.store.async_save = save
        self.f.hook = None  # Original strict registration ACK fixture.
        rotated = await self.f.registry.register(self.f.intent(2,expected_registration={
            k:self.response['registration'][k] for k in ('registration_id','generation','revision')},
            apns_token='b'*64),self.f.admission)
        self.assertTrue(rotated['success'])
        self.assertTrue(before)
        self.assertTrue(all(value==(False,False,True) for value in before))
        self.service.track_registration(rotated)
        self.assertEqual(len(self.broadcast.callbacks),1)
        self.assertEqual(self.service._signals[key].row.revision,2)

    async def test_new_registration_collects_expired_watch_without_any_broadcast_event(self):
        import json
        from custom_components.djconnect.surface_push_wire import canonical
        old_key = self.response['registration']['registration_id']
        old_watch = self.service._signals[old_key]
        self.f.clock[0] = self.response['registration']['expires_at_ms']+1
        policy = json.loads(self.f.purpose.policy_json)
        policy['original_grant_expires_at_ms'] = self.f.clock[0]+600000
        # A separately admitted synthetic issuer object, never a renewal of
        # the old capability; no intervening Broadcast event is emitted.
        purpose = replace(self.f.purpose,delegation_id='synthetic-next-delegation',
            capability_id='synthetic-next-capability',scope_digest='e'*64,
            policy_json=canonical(policy),original_wall_ms=self.f.clock[0],
            original_monotonic=self.f.clock[1])
        admission = replace(self.f.admission,purpose=purpose)
        self.f.hook = None
        fresh = await self.f.registry.register(self.f.intent(2),admission)
        self.service.track_registration(fresh)
        self.assertNotEqual(fresh['registration']['registration_id'],old_key)
        self.assertNotIn(old_key,self.service._signals)
        self.assertTrue(old_watch.closed)
        self.assertIsNone(old_watch.row)
        self.assertIsNone(old_watch.broadcast)
        self.assertEqual(len(self.service._signals),1)
        self.assertEqual(len(self.broadcast.callbacks),1)
