"""Existing approved relation survives spacing; stale approvals never catch up."""
import asyncio
import copy
from tests import test_discover_narrative_transition as discover


class PresenceTransitionTest(discover.DiscoverNarrativeTests):
    def pending(self):
        manager,session,clock=self.start()
        self.event(manager,session,clock,self.playback('Baseline',1),1)
        self.event(manager,session,clock,self.playback('First Light',2),2)
        playback=self.playback('Second Light',3)
        async def scenario():
            await manager.async_update_playback_projection(owner_profile_id=session.owner_profile_id,session_id=session.session_id,
                state='playing',media_identity=playback['uri'],title=playback['title'],artist=playback['artist'],
                duration_ms=300000,position_ms=0)
            async def provider():
                return self.insight_for(playback,3)
            target=await manager.async_process_track_started(owner_profile_id=session.owner_profile_id,session_id=session.session_id,
                media_identity=playback['uri'],insight_provider=provider,require_current_playback=True)
            self.assertEqual(target.moment_type,self.core.DJMomentType.TRACK)
        asyncio.run(scenario())
        opportunity=manager._intra_track_opportunities[session.owner_profile_id]
        self.assertIsNotNone(opportunity.pending_transition)
        self.assertEqual(self.bridges(session),[])
        return manager,session,clock,playback,opportunity

    def test_readable_future_slot_debits_exactly_once(self):
        manager,session,clock,playback,opportunity=self.pending()
        before=session.presence_ledger.total_published
        async def scenario():
            self.assertIsNone(await manager.async_maybe_publish_intra_track_moment(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,media_identity=playback['uri']))
            clock[0]+=45
            await manager.async_update_playback_projection(owner_profile_id=session.owner_profile_id,session_id=session.session_id,
                state='playing',media_identity=playback['uri'],title=playback['title'],artist=playback['artist'],duration_ms=300000,position_ms=45000)
            moment=await manager.async_maybe_publish_intra_track_moment(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,media_identity=playback['uri'])
            self.assertEqual(moment.moment_type,self.core.DJMomentType.TRANSITION)
            self.assertEqual(session.presence_ledger.total_published,before+1)
            self.assertIsNone(opportunity.pending_transition)
            self.assertIsNone(await manager.async_maybe_publish_intra_track_moment(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,media_identity=playback['uri']))
        asyncio.run(scenario())

    def test_changed_settings_expiry_seek_and_end_discard_without_consumption(self):
        for change in ('presence_aba','mood_aba','persona_aba','expiry','seek','end'):
            with self.subTest(change=change):
                manager,session,clock,playback,opportunity=self.pending()
                count=session.presence_ledger.total_published
                frozen=copy.deepcopy([m.as_dict() for m in session.broadcast.state.dj_moments])
                async def scenario():
                    owner=session.owner_profile_id
                    if change=='presence_aba':
                        for value in ('music_only','balanced'):
                            await manager.async_update_presence(owner_profile_id=owner,session_id=session.session_id,selected_presence=value)
                    elif change=='mood_aba':
                        for value in ('energy','groove'):
                            await manager.async_update_mood(owner_profile_id=owner,session_id=session.session_id,selected_mood=value)
                    elif change=='persona_aba':
                        for value in (self.core.DJPersona.RADIO_DJ,self.core.DJPersona.HOME_DJ):
                            await manager.async_update_persona(owner_profile_id=owner,session_id=session.session_id,dj_persona=value)
                    elif change=='end':
                        await manager.async_end(owner_profile_id=owner,session_id=session.session_id)
                    clock[0]+=100 if change=='expiry' else 45
                    await manager.async_update_playback_projection(owner_profile_id=owner,session_id=session.session_id,
                        state='playing',media_identity=playback['uri'],title=playback['title'],artist=playback['artist'],duration_ms=300000,
                        position_ms=120000 if change=='seek' else 45000)
                    await manager.async_maybe_publish_intra_track_moment(owner_profile_id=owner,session_id=session.session_id,media_identity=playback['uri'])
                    self.assertEqual(self.bridges(session),[])
                    self.assertEqual(session.presence_ledger.total_published,count)
                    self.assertEqual([m.as_dict() for m in session.broadcast.state.dj_moments],frozen)
                asyncio.run(scenario())
