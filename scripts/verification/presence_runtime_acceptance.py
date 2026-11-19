"""Bounded actual isolated HA policy traces, synthetic qualified provider data."""
from __future__ import annotations
import asyncio
from dataclasses import replace
import resource
import time

from custom_components.djconnect.presence_policy import POLICIES
from custom_components.djconnect.session_runtime import DJPersona
from custom_components.djconnect.session_facts import catalog_facts, recording_facts, artist_facts, work_facts


def source_pool(number):
    suffix = f'{number:022d}'
    catalog = {'uri':'spotify:track:'+suffix,'title':f'Fixture recording {number}',
               'artist':f'Fixture artist {number}','album_name':f'Fixture edition {number}',
               'album_uri':'spotify:album:'+suffix,'release_date':'2001-03-04','release_date_precision':'day'}
    ident = f'00000000-0000-0000-0000-{number:012d}'
    facts = (*catalog_facts(catalog), *recording_facts(catalog, {'id':ident,'relations':[
        {'type':'producer','target-type':'artist','artist':{'name':f'Fixture producer {number}'}}]}),
        *artist_facts(catalog, {'id':ident,'name':catalog['artist'],'type':'Person','life-span':{'begin':'1960-01-02'}}),
        *work_facts(catalog, {'relations':[{'type':'performance','target-type':'work','work':{'id':ident,
         'relations':[{'type':'composer','target-type':'artist','artist':{'name':f'Fixture composer {number}'}}]}}]}))
    return catalog, facts


async def qualify(client, manager, clock, identity, headers):
    started = time.monotonic()
    rows = {}
    peak_tasks = 0
    async def start(mode, mood='groove', persona=DJPersona.RADIO_DJ):
        await manager.async_end(owner_profile_id='profile-a')
        session = await manager.async_start(owner_profile_id='profile-a',selected_mood=mood,dj_persona=persona,
                                           locale='nl',elapsed_time_source=clock.monotonic)
        response = await client.post('/api/djconnect/v1/session/presence',headers=headers,json={**identity,
            'contract_version':1,'session_id':session.session_id,'selected_presence':mode,'expected_presence_revision':0})
        assert response.status == 200
        return await manager.async_get_active('profile-a')

    async def trace(session, tracks, *, poor=False):
        nonlocal peak_tasks
        events=[]
        await manager.async_subscribe(owner_profile_id='profile-a',session_id=session.session_id,callback=events.append)
        publications=[]
        reasons={}
        for index in range(tracks):
            clock.advance(30)
            catalog,facts=source_pool(index+1)
            if poor:
                facts=tuple(replace(f,media_identity='wrong-current-track') for f in facts)
            async def insight():
                return {'_qualified_facts':facts}
            for position in range(0,151000,15000):
                if position:
                    clock.advance(15)
                await manager.async_update_playback_projection(owner_profile_id='profile-a',session_id=session.session_id,
                    state='playing',media_identity=catalog['uri'],title=catalog['title'],artist=catalog['artist'],
                    album=catalog['album_name'],duration_ms=180000,position_ms=position)
                if position==0:
                    moment=await manager.async_process_track_started(owner_profile_id='profile-a',session_id=session.session_id,
                        insight_provider=insight,media_identity=catalog['uri'],require_current_playback=True,allow_initial_facts=True)
                else:
                    moment=await manager.async_maybe_publish_intra_track_moment(owner_profile_id='profile-a',session_id=session.session_id,media_identity=catalog['uri'])
                if moment and moment.moment_type.value!='silence':
                    publications.append({'elapsed_seconds':index*180+position/1000,'type':moment.moment_type.value,
                        'source_url':dict(moment.source_attribution).get('url'),'read_seconds':moment.presentation_intent.maximum_duration_seconds})
                reason=session.presence_ledger.suppression_reason
                if reason:
                    reasons[reason]=reasons.get(reason,0)+1
                peak_tasks=max(peak_tasks,len(asyncio.all_tasks()))
                assert len(session.presence_ledger.publications)<=16
                assert len(session.presence_ledger.track_counts)==65536
        canonical=[m for m in session.broadcast.state.dj_moments if m.moment_type.value!='silence']
        assert len(canonical)==len(publications)==session.presence_ledger.total_published
        assert sum(e['event_type']=='dj_moment_published' and e['payload'].get('dj_moment',{}).get('moment_type')!='silence' for e in events)==len(publications)
        return {'count':len(publications),'publications':publications,'suppression_reasons':reasons,
                'rolling_debits':len(session.presence_ledger.publications),'same_session':True}

    for mode in POLICIES:
        session=await start(mode)
        rows[mode]=await trace(session,4)
    assert [r['count'] for r in rows.values()]==[0,2,6,10,16],rows
    orthogonal={}
    for name,mode,mood,persona in [('calm_high','presenter','chill',DJPersona.CLUB_DJ),
                                  ('energetic_low','occasional','energy',DJPersona.FESTIVAL_DJ)]:
        session=await start(mode,mood,persona)
        orthogonal[name]=await trace(session,4)
        current=await manager.async_get_active('profile-a')
        assert current.selected_mood==mood and current.dj_persona is persona and current.selected_presence==mode
    # Hard eligibility and attribution still gate all modes; source-poor stays silent.
    session=await start('presenter')
    poor=await trace(session,1,poor=True)
    assert poor['count']==0
    session=await start('presenter')
    duration_started = time.monotonic()
    longrun=await trace(session,40)
    longrun.update(modeled_minutes=120,track_observations=40,intra_observations=400,
                   real_elapsed_seconds=round(time.monotonic()-duration_started,3),peak_tasks=peak_tasks,
                   process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   fixed_ledger_bytes=65536,retries=0,external_provider_calls=0)
    await manager.async_end(owner_profile_id='profile-a',session_id=session.session_id)
    qualification_seconds = round(time.monotonic()-started,3)
    return {'qualification_elapsed_seconds':qualification_seconds,'qualification':'ISOLATED_HA_RUNTIME_POLICY_PASS','matrix':rows,'orthogonality':orthogonal,
            'source_poor':poor,'duration':longrun,'native':'NOT_RUN','installed':'NOT_RUN','hardware':'NOT_RUN'}
