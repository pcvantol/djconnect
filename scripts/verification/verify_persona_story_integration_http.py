"""Real paired HA/Session/Planner/SQLite; declared source/model wire fixtures.

No external network/model call, installed state or literary quality claim.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT/'scripts/verification')]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import api_handlers, pipeline
    from custom_components.djconnect.narration_brief import qualify as brief_for
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.public_artist_narration import can_research
    from custom_components.djconnect.session_facts import SessionFactsResolver, observed_genre_facts
    from custom_components.djconnect.session_conversation import query_service

    catalog = {'uri': 'spotify:track:'+'A'*22, 'title': 'Fixture song - Live edition',
               'artist': 'Fixture group', 'artist_ids': ['Z'*22]}
    mbid = '00000000-0000-0000-0000-000000000002'
    artist_url = 'https://open.spotify.com/artist/'+'Z'*22
    source_calls, model_calls, rows = [], [], []
    frames = {
        'nl': 'Even bij {artist} blijven: Spotify noemt {genre}. Je hoort {track}.',
        'en': 'A moment with {artist}: Spotify lists {genre}. You are hearing {track}.',
        'de': 'Ein Moment mit {artist}: Spotify nennt {genre}. Du hörst {track}.',
        'fr': 'Un instant avec {artist} : Spotify indique {genre}. Vous écoutez {track}.',
        'es': 'Un momento con {artist}: Spotify indica {genre}. Estás escuchando {track}.',
    }
    mode, selected = ['accepted'], ['nl']

    class PublicWireFixture(SessionFactsResolver):
        async def _get(self, path, params=None, **kwargs):
            source_calls.append(path)
            if path == 'url':
                assert params['resource'] == artist_url
                return {'resource': artist_url, 'relations': [
                    {'target-type': 'artist', 'artist': {'id': mbid}}]}
            if path == 'artist/'+mbid:
                return {'id': mbid, 'name': 'Fixture group', 'type': 'Group',
                    'life-span': {'begin': '1964'}, 'relations': [
                        {'type': 'free streaming', 'url': {'resource': artist_url}},
                        {'type': 'wikidata', 'url': {'resource': 'https://www.wikidata.org/wiki/Q1'}}]}
            assert path == ''
            return {'entities': {'Q1': {'id': 'Q1', 'descriptions': {
                lang: {'value': 'Fixture music group'} for lang in frames},
                'claims': {'P434': [{'rank': 'normal', 'mainsnak': {'datavalue': {'value': mbid}}}]}}}}

    async def transport(hass_arg, data, **kwargs):
        assert hass_arg is hass and data['agent_id'] == 'history-fixture-agent'
        assert kwargs.get('allow_agent_fallback') is False
        prompt = data['text']
        assessment = prompt.startswith('Review this proposed personal DJ contribution.')
        model_calls.append({'declared_synthetic_transport': True, 'assessment': assessment,
                            'locale': selected[0]})
        # Only value-free genre placeholders may reach this writer. No Spotify
        # artist/title/genre values, profile, device or source tuple is exported.
        assert catalog['title'] not in prompt and catalog['artist'] not in prompt
        assert 'folk rock' not in prompt and catalog['uri'] not in prompt
        if mode[0] == 'failure':
            raise OSError('explicit synthetic unavailable writer')
        value = ({'supported': True, 'language_ok': True, 'style_ok': mode[0] != 'rejected'}
                 if assessment else {'text': frames[selected[0]]})
        return {'response': {'speech': {'plain': {'speech': json.dumps(value, ensure_ascii=False)}}}}

    async def no_external(*args, **kwargs):
        pass

    owner = 'profile-a'
    for persona in ('home_dj', 'radio_dj', 'club_dj', 'festival_dj'):
        for locale in frames:
            selected[0] = locale
            active = manager.current_active(owner)
            if active:
                await manager.async_end(owner_profile_id=owner, session_id=active.session_id)
            with patch.object(api_handlers, '_async_generate_initial_session_moment', no_external), \
                    patch.object(PlaybackObservationManager, 'async_start_spotify', no_external):
                started, status = await request('POST', '/api/djconnect/v1/session/start',
                    {'mood': 'groove', 'dj_persona': persona, 'locale': locale})
            assert status == 201, started
            active = manager.current_active(owner)
            sid = active.session_id
            await manager.async_update_presence(owner_profile_id=owner, session_id=sid, selected_presence='presenter')
            await manager.async_update_playback_projection(owner_profile_id=owner, session_id=sid,
                state='playing', media_identity=catalog['uri'], title=catalog['title'], artist=catalog['artist'],
                duration_ms=300000, position_ms=0)
            provider = manager._narration_providers[owner]
            assert provider[0] == sid
            facts = await PublicWireFixture(hass).resolve(catalog, authorize=provider[2])
            assert {f.key for f in facts} == {'artist_begin', 'artist_description'}
            assert all(f.recording_evidence is None and f.work_evidence is None for f in facts)
            assert all(can_research(brief_for(f, locale=locale, persona=persona, mood='groove',
                seed=f.copy_for(locale)[1])) for f in facts)
            # Rich story routing is proved, not fabricated research acceptance.
            genres = observed_genre_facts({'source': 'spotify_playback_status', 'backend': 'spotify_direct',
                'is_playing': True, 'media_identity': catalog['uri'], 'title': catalog['title'],
                'artist': catalog['artist'], 'artist_ids': catalog['artist_ids'], 'genres': ['folk rock'],
                'genre_source_expires_at': time.monotonic()+600}, media_identity=catalog['uri'],
                title=catalog['title'], artist=catalog['artist'])
            async def insight():
                return {'_qualified_facts': genres}
            mode[0] = ('failure' if locale == 'nl' and persona == 'club_dj' else
                       'rejected' if locale == 'nl' and persona == 'festival_dj' else 'accepted')
            before = len(model_calls)
            with patch.object(pipeline, '_call_conversation_process_transport', transport):
                moment = await manager.async_process_track_started(owner_profile_id=owner, session_id=sid,
                    media_identity=catalog['uri'], insight_provider=insight,
                    require_current_playback=True, allow_initial_facts=True)
            count = await persistence_service(hass).async_in_transaction(lambda tx: tx.fetchone(
                "SELECT COUNT(*) AS n FROM djconnect_session_acceptances WHERE session_id=? AND kind='dj_moment'", (sid,)))
            if mode[0] != 'accepted':
                assert moment is None and count[0] == 0 and active.presence_ledger.total_published == 0
                assert 'genre_context' in manager._intra_track_opportunities[owner].used_fact_keys
            else:
                assert moment is not None and count[0] == 1 and active.presence_ledger.total_published == 1
                assert moment.content == brief_for(genres[0], locale=locale, persona=persona,
                    mood='groove', seed='synthetic seed').render(frames[locale])
                assert moment.source_references == ('Spotify',)
            assert 1 <= len(model_calls)-before <= 2
            page = await query_service(hass, history).async_timeline_page(owner, sid)
            assert bool([entry for entry in page['entries'] if entry.get('moment_id')]) == (moment is not None)
            rows.append({'persona': persona, 'locale': locale, 'mode': mode[0],
                         'state': 'PASS', 'accepted_moments': count[0],
                         'declared_synthetic_model_responses': len(model_calls)-before})
    return {'state': 'PASS', 'cases': rows, 'independent_artist_source_reads': len(source_calls),
        'original_request_paths': sorted(set(source_calls)), 'declared_model_boundary_calls': model_calls,
        'external_network_calls': 0, 'paid_model_calls': 0,
        'quality_scope': 'Boundary and connected runtime proof only; no real prose, multisource semantic, installed or audible acceptance.'}


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
