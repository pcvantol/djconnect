"""Actual paired HA/Store, original evidence and two-call whole-draft checks.

Only external playback/source/model replies are synthetic. Network-none,
no model credential, no paid calls, no installed/native/content-quality claim.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts/verification')]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import pipeline, playback_request, ask_dj
    from custom_components.djconnect.ask_dj import public_research
    from custom_components.djconnect.ask_dj.dialogue import current_turn
    runtime = hass.data['djconnect']['runtime']
    rows, calls = [], []
    mode, route = '', ''
    original = 'Volbeat is a Danish band.'
    bad = 'Volbeat invented every instrument.'
    frames = ['I am handing you {title} now. {status}',
              'I have made room for {title}. {status}']

    async def source(fetch, url, **kwargs):
        await fetch.guard()
        fetch.requests += 1
        if 'wikipedia.org/w/api.php' in url:
            return 200, json.dumps({'query': {'pages': [{'title': 'Volbeat',
                'extract': '<p>' + original + ' Volbeat performed a concert.</p>', 'pageprops': {'wikibase-shortdesc': 'Danish band'},
                'revisions': [{'revid': 123456}]}]}}), url
        return 404, '', url

    async def playback(hass, runtime, command, *args, **kwargs):
        assert command == 'status', 'NO_PROVIDER_PLAYBACK_EFFECT_ADMITTED'
        return {'success': True, 'playback': {'uri': 'spotify:track:' + 'N' * 22,
            'artist': 'Volbeat', 'title': 'Private current recording'}}

    async def agent(hass, data, **kwargs):
        assert data['agent_id'] == 'history-fixture-agent'
        assert kwargs.get('allow_agent_fallback') is False
        projection = json.loads(data['text'].split('\nData:\n', 1)[1])
        calls.append(projection)
        if set(projection) == {'question', 'language', 'available'}:
            answer = {'read': 'artist_story', 'reference': 'current', 'exclude_current': False}
        elif 'drafts' not in projection:
            if route == 'artist':
                instructions = data['text'].split('\nData:\n', 1)[0]
                assert instructions.startswith('DJConnect output contract: ')
                assert 'JSON envelope' in instructions.split('\n', 1)[0]
                assert projection['answer_form'] == ('Natural prose inside each draft text; '
                    'the outer response follows the Core-owned artist_evidence_drafts_v1 JSON output contract.')
            answer = {'drafts': frames if route == 'frame' else
                      [original + '\x00', bad] if mode == 'control' else
                      [original, bad] if mode.startswith('first_') else [bad, original]}
            if route == 'artist':
                answer = {'schema': 'artist_evidence_drafts_v1', 'drafts': [
                    {'anchors': [anchor['id']], 'text': text} for anchor, text in
                    zip(projection['literal_anchors'][:2], answer['drafts'], strict=True)]}
            elif mode.startswith('slots_'):
                import re
                answer = {'schema': 'playback_slot_drafts_v1', 'drafts': [
                    {'parts': [({'slot': part[1:-1]} if part.startswith('{') else {'literal': part})
                               for part in re.split(r'(\{title\}|\{status\})', text) if part]}
                    for text in frames]}
                if mode == 'slots_bad_second':
                    answer['drafts'][1]['parts'][-1] = {'slot': 'status”'}
        else:
            reviews = []
            for row in projection['drafts']:
                positive = row['index'] == (0 if mode.startswith('first_') else 1) and mode != 'all_false'
                review = {'supported': positive, 'language_ok': True, 'style_ok': True}
                if route == 'artist':
                    span = projection['evidence']['public_music_research']['sources'][0]['evidence_spans'][0]
                    review.update(review_schema='source_id_review_v1', unsupported_claims=[] if positive else [row['text']],
                        claim_checks=[{'text': row['text'], 'kind': 'fact', 'evidence_ids': [span['id']]}])
                    if not positive:
                        review.update(claim_checks=[], temporal_claims=[])
                reviews.append({'index': row['index'], 'sha256': row['sha256'], 'review': review})
            if mode == 'swapped':
                reviews.reverse()
            if mode == 'malformed':
                reviews[-1]['review'].pop('style_ok')
            if mode == 'first_bad_claim':
                reviews[-1]['review']['claim_checks'] = [{'unexpected_nested_field': 'invalid'}]
            if mode == 'first_bad_temporal':
                reviews[-1]['review']['temporal_claims'] = {'not': 'a list'}
            answer = {'draft_reviews': reviews}
        return {'response': {'speech': {'plain': {'speech': json.dumps(answer)}}}}

    with patch.object(pipeline, '_call_conversation_process_transport', agent), \
         patch.object(ask_dj, 'run_music_command', playback), \
         patch.object(public_research.PublicFetch, 'request', source):
        for route in ('frame', 'artist'):
            for mode in (('second', 'all_false', 'swapped', 'malformed', 'slots_second', 'slots_bad_second') if route == 'frame' else
                         ('second', 'all_false', 'swapped', 'malformed', 'first_bad_claim', 'first_bad_temporal', 'control')):
                if route == 'artist':
                    # Each case asks about CURRENT playback, not the previous
                    # accepted public story implicitly selected from history.
                    await history.async_clear('profile:profile-a')
                calls.clear()
                if route == 'frame':
                    brief = playback_request.PlaybackRequestBrief(
                        playback_request.PlaybackAcceptance('local-private-uri', time.monotonic() + 20),
                        'en', 'home_dj', 'groove', 'Local fallback.', ('{title}', '{status}'),
                        'Accepted selection.', 'The submitted selection was observed playing.',
                        (('{title}', 'Local title'), ('{status}', 'Playback is confirmed.')),
                        selection_kind='playlist', playback_state='observed')
                    answer = await pipeline.realize_session_narration(hass, narration=brief,
                        admission=lambda: None, fallback_text=brief.seed, conf=runtime.config)
                    assert str(answer) == (brief.render(frames[1]) if mode in ('second', 'slots_second') else brief.seed)
                    assert len(calls) == (1 if mode == 'slots_bad_second' else 2)
                    assert calls[0]['playback_state'] == 'observed'
                    if len(calls) == 2:
                        assert calls[1]['playback_state'] == 'observed'
                else:
                    answer, code = await request('POST', '/api/djconnect/v1/ask_dj/message', {
                        'client_message_id': 'verified-drafts-' + mode,
                        'text': 'Tell me about this artist', 'language': 'en', 'audio_response': 'never'})
                    if mode == 'control':
                        assert code == 502 and len(calls) == 2, (code, answer)
                        rows.append({'route': route, 'mode': mode, 'calls': len(calls), 'passed': True})
                        continue
                    assert code == 200, (route, mode, code, answer,
                        {'stages': [list(row) for row in calls],
                         'offered_reads': calls[0].get('available') if calls else None})
                    assert answer['is_generated_text'] is (mode == 'second'), answer
                    if mode == 'second':
                        assert answer['text'] == original and answer['knowledge_basis'] == 'fetched_public_music_research_v1'
                    else:
                        assert answer['knowledge_basis'] == 'public_research_unqualified'
                    assert len(calls) == answer['conversation']['metrics']['agent_calls'] == 3
                    assert bad not in json.dumps((await history.async_history('profile:profile-a'))['messages'])
                    assert current_turn.get() is None
                assert 'Private current recording' not in json.dumps(calls)
                rows.append({'route': route, 'mode': mode, 'calls': len(calls), 'passed': True})
    return {'scenario': 'verified_whole_drafts_actual_ha', 'cases': rows,
        'paired_artist_route': True, 'actual_ha_agent_frame_route': True,
        'model_provider_calls': 0, 'provider_playback_effects': 0,
        'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'content_quality': 'NOT_RUN', 'installed': 'NOT_RUN', 'native': 'NOT_RUN'}


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
