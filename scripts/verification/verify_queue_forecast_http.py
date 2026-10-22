"""Actual isolated HA paired HTTP + backend/observer/runtime queue bulletin chain.

Only external Spotify/CDN responses are synthetic. No HA-dev or device writes.
"""
from __future__ import annotations

import asyncio
import copy
import time

import verify_session_forecast_http as harness
import session_forecast_runtime_acceptance as forecast_lab
from custom_components.djconnect.session_runtime import DJPersona


class QueueForecastLab(forecast_lab.ForecastLab):
    async def provider(self, backend, method, path, **kwargs):
        if path == '/me/player/queue':
            self.calls += 1
            if getattr(self, 'queue_hold', None) is not None:
                self.queue_started.set()
                await self.queue_hold.wait()
            return {'currently_playing': self.raw.get('item'), 'queue':[
                {'type':'track','id':str(i)*22,'uri':'spotify:track:'+str(i)*22,
                 'name':f'{getattr(self, "queue_flavour", "Queue fixture")} {i}', 'duration_ms':300000,
                 'artists':[{'id':forecast_lab.ARTIST,'name':'Queue artist'}]}
                for i in range(1, 6)]}
        if path.startswith('/artists?ids='):
            self.calls += 1
            return {'artists':[{'id':forecast_lab.ARTIST,'genres':['ambient','downtempo']}]}
        return await super().provider(backend, method, path, **kwargs)

    async def qualify(self, client, identity, headers):
        self.owner = {'client':client, 'identity':identity, 'headers':headers}
        rows = []
        for locale in ('en','nl','de','fr','es'):
            texts = []
            for persona in DJPersona:
                await self.start(locale=locale, persona=persona, direct_persona=True)
                await self.step(1)
                await self.settle_art()
                status, body = await self.forecast()
                active = await self.manager.async_get_active('profile-a')
                value = body['forecast']
                assert status == 200 and value['state'] == 'ready', body
                assert 'Queue fixture 1' in value['summary'], value
                assert 'Queue fixture 3' in value['summary'], value
                assert 'Queue fixture 4' not in value['summary'], value
                assert 'ambient' in value['summary'] and 'downtempo' in value['summary']
                assert all(a['role'] == 'current' for a in value['imagery'])
                assert len(value['sections']) == 2
                public = active.broadcast.as_dict(include_owner_only=False)['session_forecast']
                assert 'Queue fixture' not in public['summary']
                assert public['valid_until'] == value['valid_until']
                original = active.broadcast.forecast.deadline
                assert 0 < original - time.monotonic() <= 30
                before = copy.deepcopy((active.planner.as_dict(),
                    {k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'},
                    [m.as_dict() for m in active.broadcast.state.dj_moments], self.calls))
                for _ in range(3):
                    assert (await self.forecast())[1] == body
                after = (active.planner.as_dict(),
                    {k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'},
                    [m.as_dict() for m in active.broadcast.state.dj_moments], self.calls)
                assert before == after
                assert active.broadcast.forecast.deadline == original
                texts.append(value['summary'])
                rows.append({'locale':locale,'persona':persona.value,'HTTP':200,
                             'queue_count':3,'read_effects':0,'original_expiry':True})
            assert len(set(texts)) == 4
        # Two output identities with the same display name cannot share an old queue.
        await self.start()
        await self.step(1)
        await self.settle_art()
        self.queue_flavour = 'Changed output queue'
        self.raw['device']['id'] = 'different-output-same-name'
        observed = self.observer._spotify_sessions['profile-a']
        await self.observer._async_poll_spotify(observed)
        status, changed = await self.forecast()
        assert status == 200 and 'Changed output queue 1' in changed['forecast']['summary'], changed
        self.queue_flavour = 'Between recordings'
        await self.step(2)
        await self.settle_art()
        self.queue_flavour = 'Returned recording queue'
        await self.step(1)
        await self.settle_art()
        status, returned = await self.forecast()
        assert status == 200 and 'Returned recording queue 1' in returned['forecast']['summary'], returned
        self.queue_flavour = 'Queue fixture'
        invalid = await self.invalid_forecast_requests()
        stale = []
        from custom_components.djconnect.domain.storage import STORE_KEY
        for case in ('command', 'authority_revision'):
            await self.start()
            await self.settle_art()
            self.integration.backend_cache.clear()
            self.raw = self.raw_track(1)
            self.queue_hold, self.queue_started = asyncio.Event(), asyncio.Event()
            observed = self.observer._spotify_sessions['profile-a']
            task = asyncio.create_task(self.observer._async_poll_spotify(observed))
            await asyncio.wait_for(self.queue_started.wait(), 5)
            if case == 'command':
                observed.command_revision += 1
            else:
                self.hass.data['djconnect'][STORE_KEY].authority_revision += 1
            self.queue_hold.set()
            await asyncio.wait_for(task, 5)
            self.queue_hold = None
            await self.settle_art()
            status, value = await self.forecast()
            assert status == 200
            assert 'Queue fixture' not in value['forecast']['summary'], (case, value)
            stale.append({'case':case, 'late_queue_discarded':True})
        return {'state':'PASS', 'cases':rows,'invalid_requests':invalid,'stale_results':stale,
                'external_boundary':'Synthetic Spotify/CDN only; real HA pairing/HTTP/backend/observer/Runtime',
                'HA_dev_writes':False,'native_acceptance':'NOT_RUN'}


if __name__ == '__main__':
    forecast_lab.ForecastLab = QueueForecastLab
    asyncio.run(harness.main())
