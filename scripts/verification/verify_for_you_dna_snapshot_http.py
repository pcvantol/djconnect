"""Paired real-HA cached For-you basis across an unrelated original Store save."""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/verification')]
from verify_session_for_you_http import qualify as base_qualify  # noqa: E402


async def qualify(hass, manager, history, request, client):
    examples = []

    async def after(hass, manager, history, request, state):
        cases = {}
        runtime = hass.data['djconnect']['owner-entry']
        memory = runtime.memory
        for locale in ('en', 'nl'):
            previous = manager.current_active('profile-a')
            if previous:
                await manager.async_end(owner_profile_id='profile-a', session_id=previous.session_id)
            state.update(active=True, playing=False, track=None, effects=[], reads=[], tracks={})
            start, status = await request('POST', '/api/djconnect/v1/session/start',
                {'mood': 'groove', 'language': locale})
            assert status == 201 and start['for_you']['state'] == 'available', start
            offer = start['for_you']
            active = manager.current_active('profile-a')
            admission = active.broadcast.first_play_offer['_admission']
            wall, mono = admission.wall_deadline, admission.deadline
            entered, release = asyncio.Event(), asyncio.Event()
            original_save = memory._store.async_save
            original_reader = memory.loaded_genre_seed_snapshot
            reads = []

            async def pending(data):
                entered.set()
                await release.wait()
                await original_save(data)

            def reader(*args, **kwargs):
                reads.append(True)
                return original_reader(*args, **kwargs)

            memory.data['memories']['profile:profile-a']['last_seen'] = 'declared-unrelated-metadata'
            provider_reads = list(state['reads'])
            with patch.object(memory._store, 'async_save', pending):
                task = asyncio.create_task(memory.async_save())
                await entered.wait()
                try:
                    with patch.object(memory, 'loaded_genre_seed_snapshot', reader):
                        for _ in range(3):
                            current, status = await request('GET', '/api/djconnect/v1/session/active')
                            assert status == 200 and current['for_you']['state'] == 'available', current
                            actual = current['for_you']
                            assert actual['actions_available']
                            assert actual['offer_id'] == offer['offer_id']
                            assert actual['result_set']['items'] == offer['result_set']['items']
                            assert actual['expires_in'] <= offer['expires_in']
                            assert current['first_play_action']['available']
                    assert not reads, 'cached poll minted a new snapshot instead of comparing the original'
                    assert original_reader('profile-a', limit=20) is None, 'new pending basis must remain denied'
                    admission.guard()
                    assert (admission.wall_deadline, admission.deadline) == (wall, mono)
                    assert not state['effects'] and state['reads'] == provider_reads
                finally:
                    release.set()
                    await task
            item = offer['result_set']['items'][0]
            result, status = await request('POST', '/api/djconnect/v1/ask_dj/message', {
                'client_message_id': 'original-committed-dna-'+locale, 'text': item['title'],
                'language': locale, 'audio_response': 'never',
                'conversation_context': offer['conversation_context'],
                'choice_action': {'result_set_id': offer['result_set']['result_set_id'],
                    'action_id': item['action_id'], 'operation': 'select'}})
            assert status == 200 and result['action_outcome']['readback_confirmed'], result
            assert len(state['effects']) == 1
            cases[locale+'_original_committed_basis_during_unrelated_save_no_new_basis_or_effect'] = 'PASS'
            cases[locale+'_original_choice_after_metadata_save_same_lease_once'] = 'PASS'
            examples.append({'language': locale, 'original_offer': offer,
                'during_save': current['for_you'], 'original_choice_response': result,
                'synthetic_effects': list(state['effects']), 'new_snapshots_on_poll': len(reads),
                'original_deadlines_unchanged': (admission.wall_deadline, admission.deadline) == (wall, mono)})
        return cases

    result = await base_qualify(hass, manager, history, request, client, after=after)
    result.update(dna_snapshot_examples=examples,
        qualification='ACTUAL_ISOLATED_HA_CACHED_ORIGINAL_DNA_DURING_STORE_SAVE_SYNTHETIC_PROVIDER_ONLY',
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return result


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
