"""Actual paired HA HTTP v1/v2 proof; external research/LLM selection is fixture.

No HA/Core transport, profile, storage, acceptance, source-purpose, grants,
publication or media projection is stubbed. No real-model/native/push claim.
"""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

ANSWER = 'Northline nam Paper Lanterns op met Ada Reed. Zo kijk ik graag even mee achter die naam.'


def verify_source_identity(root, source_hashes, harness_hashes):
    """Reject changed product OR executable qualification bytes before any PASS."""
    assert source_hashes == {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root/'custom_components/djconnect').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}, 'product_source_changed_during_probe'
    assert harness_hashes == {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in harness_hashes}, 'qualification_harness_changed_during_probe'


def configure_external_fixtures(calls):
    from custom_components.djconnect import pipeline
    from custom_components.djconnect.ask_dj import public_research
    from custom_components.djconnect.session_facts import SessionFactsResolver
    original_get = SessionFactsResolver._get

    async def knowledge(self, path, params=None, *, wikidata=False):
        if wikidata:
            calls.append({'boundary': 'external_knowledge_fixture', 'path': 'reciprocal_artist_identity'})
            return {'entities': {'Q1': {'id': 'Q1', 'claims': {'P434': [
                {'mainsnak': {'datavalue': {'value': '12345678-1234-1234-1234-123456789abc'}}}]}}}}
        body = await original_get(self, path, params, wikidata=wikidata)
        if path.startswith('artist/'):
            body['relations'].append({'type': 'wikidata', 'url': {'resource': 'https://www.wikidata.org/wiki/Q1'}})
        return body

    async def fetch(self, url, **kwargs):
        await self.guard()
        if self.requests >= public_research.MAX_REQUESTS:
            raise public_research.ResearchUnavailable('public_research_budget')
        self.requests += 1
        parsed = urlsplit(url)
        calls.append({'boundary': 'external_public_research_fixture', 'host': parsed.hostname})
        if parsed.hostname not in {'nl.wikipedia.org', 'en.wikipedia.org'} or parsed.path != '/w/api.php':
            return 404, '', url
        page = {'title': 'Northline', 'pageprops': {'wikibase_item': 'Q1', 'wikibase-shortdesc': 'music group'},
                'revisions': [{'revid': 1234}], 'extract': '<p>Northline is a music group.</p>'
                '<p>Northline recorded <i>Paper Lanterns</i> with Ada Reed.</p>'}
        return 200, json.dumps({'query': {'pages': [page]}}), url

    async def model(hass, data, **kwargs):
        guard = kwargs.get('model_guard')
        if guard:
            guard()
        assessment = data['text'].split('\nData:\n', 1)
        if len(assessment) == 2 and '"answer"' in assessment[1]:
            body = json.loads(assessment[1])
            evidence = body['evidence']['public_music_research']
            span = next(s for s in evidence['sources'][0]['evidence_spans'] if 'Paper Lanterns' in s['text'])
            checks = [{'text': ANSWER.split('. ', 1)[0]+'.', 'kind': 'relationship',
                       'evidence_ids': [span['id']], 'quote': span['text']},
                      {'text': ANSWER.split('. ', 1)[1], 'kind': 'dj_appreciation', 'evidence_ids': [], 'quote': ''}]
            answer = {'supported': True, 'unsupported_claims': [], 'language_ok': True,
                      'style_ok': True, 'temporal_claims': [], 'claim_checks': checks}
            if evidence['schema_version'] == 3:
                answer['review_schema'] = 'source_id_review_v1'
                answer['claim_checks'] = [{k: v for k, v in c.items() if k != 'quote'} for c in checks]
            text = json.dumps(answer)
            kind = 'assessment'
        else:
            text, kind = ANSWER, 'realization'
        calls.append({'boundary': 'external_model_fixture', 'kind': kind})
        return {'response': {'speech': {'plain': {'speech': text}}}}

    SessionFactsResolver._get = knowledge
    public_research.PublicFetch.request = fetch
    # External Assist agent selection/answers are fixtures; authorization closures
    # still revalidate this same selection, real entry/Profile and paired bearer.
    pipeline._assist_context = lambda hass, conf: {'agent_id': 'fixture-agent', 'language': 'nl'}
    pipeline.call_conversation_process_with_agent_retry = model


async def run(*, hass, runtime, client, headers, identity, manager, storage, sid, calls, output, source_hashes,
              harness_hashes):
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from custom_components.djconnect.passive_session import BASE
    from custom_components.djconnect.public_artist_narration import admitted
    await playback_observation_manager(hass).async_stop('profile-a', sid)
    active = manager._active_by_profile['profile-a']
    original = next(m for m in reversed(active.broadcast.state.dj_moments) if m.content == ANSWER)
    assert admitted(original) and original.as_dict()['sources']
    rows = []
    base = {**identity, 'contract_version': 1, 'session_id': sid, 'surface': 'widget'}
    consent = {**base, 'enabled': True, 'os_snapshot_cache': True, 'locked_display': False}

    async def request(path, payload, expected=200):
        response = await client.post(BASE+path, json=payload, headers=headers)
        body = await response.json()
        assert response.status == expected, (path, response.status, body)
        assert response.headers['Cache-Control'] == 'no-store'
        return body

    legacy = await request('/authorize', consent)
    frame = legacy['passive_session']
    assert frame['schema_version'] == 1
    if frame['contribution'] is not None:
        assert frame['contribution']['text'] != ANSWER
        assert frame['contribution']['usage_basis'] in {'runtime_authored_direction', 'cc0_facts_authored_expression'}
    rows.append({'case': 'legacy_vocabulary_preserved', 'response': legacy})
    for version in (True, '2', 0, 3):
        await request('/authorize', {**consent, 'projection_version': version}, 400)
    authorized = await request('/authorize', {**consent, 'projection_version': 2})
    read = {**base, 'projection_version': 2, 'grant_id': authorized['grant_id']}
    await request('/read', {k: v for k, v in read.items() if k != 'projection_version'}, 403)
    await request('/read', {**read, 'projection_version': 1}, 403)
    first = await request('/read', read)
    frame = first['passive_session']
    copy = frame['contribution']
    assert frame['schema_version'] == 2 and copy['text'] == original.content == ANSWER
    assert copy['moment_id'] == original.moment_id and copy['sources'] == original.as_dict()['sources']
    assert copy['expression_license']['id'] == 'CC-BY-SA-4.0'
    assert copy['rights'] == {'passive_cache': True, 'os_snapshot': True, 'external_relay': False, 'watch_replication': False}
    for field in ('contribution_status', 'now_playing_status', 'artwork_status'):
        assert frame[field] == {'state': 'available', 'reason': 'qualified'}, (field, frame[field])
    art = frame['artwork'][0]
    query = {**identity, 'contract_version': '1', 'projection_version': '2', 'surface': 'widget',
             'grant_id': authorized['grant_id']}
    image = await client.get(art['image_path'], params=query, headers=headers)
    pixels = await image.read()
    assert image.status == 200 and pixels.startswith(b'\x89PNG') and image.headers['Cache-Control'] == 'no-store'
    wrong = await client.get(art['image_path'], params={**query, 'projection_version': '1'}, headers=headers)
    assert wrong.status == 403
    rows.append({'case': 'researched_complete_copy_actual_paired_http_and_image', 'response': first,
                 'image_bytes_sha256': hashlib.sha256(pixels).hexdigest()})
    before = (len(calls), len(active.broadcast.state.dj_moments), active.broadcast.delivery_sequence,
              active.presence_ledger.total_published, len(active.broadcast.replay_log))
    for _ in range(20):
        repeated = await request('/read', read)
        assert repeated['passive_session']['revision'] == frame['revision']
        assert repeated['passive_session']['contribution'] == copy
    after = (len(calls), len(active.broadcast.state.dj_moments), active.broadcast.delivery_sequence,
             active.presence_ledger.total_published, len(active.broadcast.replay_log))
    assert before == after
    rows.append({'case': 'twenty_pure_reads', 'before': before, 'after': after})
    activity = await request('/authorize', {**consent, 'projection_version': 2, 'surface': 'live_activity', 'locked_display': True})
    assert activity['passive_session']['contribution'] == copy
    await request('/read', {**read, 'surface': 'live_activity'}, 403)
    rows.append({'case': 'independent_activity_grant_and_exact_copy', 'response': activity})
    silence = active.moment_engine.create_silence(session_id=sid, selected_mood=active.selected_mood,
        persona=active.dj_persona, locale='nl', reason='planned_silence')
    active.publish_moment(silence)  # Actual Runtime publication; opportunity is explicitly controlled in this lab.
    quiet = await request('/read', read)
    assert quiet['passive_session']['contribution'] is None
    assert quiet['passive_session']['contribution_status'] == {'state': 'suppressed', 'reason': 'intentional_silence'}
    assert quiet['passive_session']['now_playing']
    rows.append({'case': 'runtime_silence_http_barrier_preserves_music', 'response': quiet})
    await storage.async_upsert_device(identity['device_id'], 'ios', linked_profile_id='profile-other')
    await storage.async_upsert_device(identity['device_id'], 'ios', linked_profile_id='profile-a')
    await request('/read', read, 403)
    rows.append({'case': 'profile_ABA_rejects_prior_grant', 'http': 403})
    # No paired bearer/grant/device/Profile identifiers in the review artifact.
    def sanitize(value):
        if isinstance(value, dict):
            return {k: ('<redacted>' if k in {'grant_id', 'binding_id', 'generation'} else sanitize(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [sanitize(v) for v in value]
        return value
    root = Path(os.environ.get('DJC_SOURCE_ROOT', '/candidate'))
    verify_source_identity(root, source_hashes, harness_hashes)
    report = {'contract_version': 1, 'projection_version': 2, 'ordinary_pairing': True,
              'real_ha_http_runtime_storage_and_acceptance': True,
              'fixtures': ['external Spotify/knowledge/CDN', 'external public research', 'external Assist agent selection/model answers'],
              'source_hashes': source_hashes, 'harness_hashes': harness_hashes,
              'begin_end_sources_equal': True, 'cases': sanitize(rows),
              'actual_model_native_installed_background_voice': 'NOT_RUN'}
    (output/'passive-public-v2.http.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'passive_v2_cases': len(rows), 'status': 'PASS', 'background_native': 'OPEN'}), flush=True)
