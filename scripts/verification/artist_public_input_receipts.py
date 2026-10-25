"""Evaluation-only, bounded public SDK inputs captured BEFORE provider awaits.

The literal commitment verifier is independent of the runtime draft decoder.
No enclosing prompt, question, history, household projection or authority leaves
this boundary. These receipts prove original input membership, never truth.
"""
import hashlib
import json
import re

LANGUAGES = ('en', 'nl', 'de', 'fr', 'es')
EXPECTED = {'catalogue-listen.artist-' + language: language for language in LANGUAGES}
DOMAIN = b'DJC_ARTIST_LITERAL_ANCHOR_V1\0'
HASH = re.compile('[a-f0-9]{64}')
PUBLIC_KEYS = {
    'schema_version', 'resolved_public_subject', 'status', 'sources', 'editorial_focus',
    'biographical_date_events', 'provider', 'title', 'url', 'kind', 'language',
    'fetched_at', 'expires_at', 'license', 'revision_url', 'wikidata_id', 'content_hash',
    'claim_scope', 'untrusted_excerpt', 'source_anchors', 'evidence_schema',
    'literal_passages', 'original_document_hash', 'evidence_spans', 'text', 'id',
    'original_range', 'source_id', 'episode_span_ids', 'authority', 'identity_binding',
    'name', 'page_url', 'identity_context_ids', 'pronoun_policy', 'schema', 'event',
    'claim', 'actor', 'group', 'group_id', 'year', 'evidence_id', 'quote',
    'state', 'wikipedia', 'web', 'requests', 'reason',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False).encode('utf-8')


def _public_tree(value):
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > 4096 or depth > 16:
            raise ValueError('public_sdk_tree_bound')
        if type(item) is dict:
            if not set(item) <= PUBLIC_KEYS:
                raise ValueError('non_public_sdk_field')
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if any((ord(char) < 32 and char != '\n') or 0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise ValueError('public_sdk_control_character')
        elif type(item) is not int:
            raise ValueError('public_sdk_non_literal_type')


def _strings(value, *, maximum=256, count=32):
    if (type(value) is not list or len(value) > count
            or any(type(item) is not str or not 1 <= len(item.encode()) <= maximum for item in value)):
        raise ValueError('public_sdk_string_list')


def _research_shape(research):
    # A vocabulary shared across nested objects is NOT a schema: an authority
    # object at the root, for example, must not acquire editorial-field rights.
    if (type(research) is not dict or not {'schema_version', 'status', 'sources'} <= set(research)
            or set(research) - {'schema_version', 'resolved_public_subject', 'status', 'sources',
                'editorial_focus', 'biographical_date_events'}):
        raise ValueError('public_sdk_research_fields')
    if 'resolved_public_subject' in research and (
            type(research['resolved_public_subject']) is not str or not 2 <= len(research['resolved_public_subject']) <= 120):
        raise ValueError('public_sdk_subject')
    if 'editorial_focus' in research:
        focus = research['editorial_focus']
        if type(focus) is not dict:
            raise ValueError('public_sdk_focus')
        if focus.get('kind') == 'documented_artist_episode':
            if (set(focus) != {'kind', 'source_id', 'episode_span_ids', 'authority'}
                    or type(focus['source_id']) is not str or not HASH.fullmatch(focus['source_id'])
                    or focus['authority'] != 'telling_focus_only_full_original_context_remains_evidence'):
                raise ValueError('public_sdk_episode_focus')
        elif focus.get('kind') == 'documented_person_episode':
            if (set(focus) != {'schema_version', 'kind', 'identity_binding', 'episode_span_ids',
                    'identity_context_ids', 'authority', 'pronoun_policy'}
                    or type(focus['schema_version']) is not int or focus['schema_version'] != 2
                    or focus['authority'] != 'editorial_only_full_corpus_remains_admitted'
                    or focus['pronoun_policy'] != 'independent_full_context_resolution_required'
                    or type(focus['identity_binding']) is not dict
                    or set(focus['identity_binding']) != {'name', 'source_id', 'page_url'}
                    or any(type(value) is not str or not 1 <= len(value) <= 2048 for value in focus['identity_binding'].values())):
                raise ValueError('public_sdk_person_focus')
            _strings(focus['identity_context_ids'], maximum=512)
        else:
            raise ValueError('public_sdk_unknown_focus')
        _strings(focus['episode_span_ids'], maximum=512)
    if 'biographical_date_events' in research:
        events = research['biographical_date_events']
        fields = {'schema', 'event', 'actor', 'group', 'group_id', 'year', 'source_id', 'evidence_id', 'quote'}
        if (type(events) is not list or len(events) > 8 or any(type(event) is not dict
                or set(event) != fields or any(type(value) is not str or not 1 <= len(value) <= 1200
                    for value in event.values()) or event['schema'] != 'biographical_event_v1'
                or event['event'] not in {'group_founded', 'member_joined'} for event in events)):
            raise ValueError('public_sdk_biographical_shape')
    source_strings = {'provider', 'title', 'url', 'kind', 'language', 'fetched_at', 'expires_at',
        'license', 'revision_url', 'wikidata_id', 'content_hash', 'claim_scope', 'untrusted_excerpt',
        'evidence_schema', 'original_document_hash'}
    if type(research.get('sources')) is not list:
        raise ValueError('public_sdk_sources')
    for source in research['sources']:
        if (type(source) is not dict or set(source) - source_strings - {'source_anchors', 'literal_passages', 'evidence_spans'}
                or any(type(value) is not str for key, value in source.items() if key in source_strings)):
            raise ValueError('public_sdk_source_fields')
        if 'source_anchors' in source:
            _strings(source['source_anchors'], maximum=1200, count=24)
        for field in ('literal_passages', 'evidence_spans'):
            if field not in source:
                continue
            values = source[field]
            if type(values) is not list or len(values) > 256:
                raise ValueError('public_sdk_passage_list')
            for value in values:
                required = {'text', 'original_range'} if field == 'literal_passages' else {'id', 'text'}
                if (type(value) is not dict or not required <= set(value)
                        or set(value) - required - ({'original_range'} if field == 'evidence_spans' else set())
                        or type(value['text']) is not str
                        or (field == 'evidence_spans' and type(value['id']) is not str)):
                    raise ValueError('public_sdk_passage_fields')
                if 'original_range' in value:
                    bounds = value['original_range']
                    if (type(bounds) is not list or len(bounds) != 2 or any(type(n) is not int for n in bounds)
                            or not 0 <= bounds[0] < bounds[1] or bounds[1] - bounds[0] != len(value['text'])):
                        raise ValueError('public_sdk_passage_range')


def _spans(research):
    _public_tree(research)
    _research_shape(research)
    if (type(research) is not dict or type(research.get('schema_version')) is not int
            or research['schema_version'] != 3 or type(research.get('sources')) is not list
            or not 1 <= len(research['sources']) <= 8):
        raise ValueError('public_sdk_schema')
    status = research.get('status')
    if (type(status) is not dict or not {'state', 'wikipedia', 'web', 'requests'} <= set(status)
            or set(status) - {'state', 'wikipedia', 'web', 'requests', 'reason'}
            or status['state'] not in {'available', 'partial', 'unavailable'}
            or status['wikipedia'] not in {'fetched', 'unavailable'}
            or status['web'] not in {'fetched', 'unavailable'}
            or type(status['requests']) is not int or not 0 <= status['requests'] <= 12
            or ('reason' in status and status['reason'] != 'public_research_deadline')):
        raise ValueError('public_sdk_status_shape')
    result, identifiers = {}, {}
    for source in research['sources']:
        if type(source) is not dict or not isinstance(source.get('content_hash'), str) or not HASH.fullmatch(source['content_hash']):
            raise ValueError('public_sdk_source_hash')
        spans = source.get('evidence_spans')
        if type(spans) is not list or not 1 <= len(spans) <= 256:
            raise ValueError('public_sdk_missing_original_spans')
        for span in spans:
            if (type(span) is not dict or not {'id', 'text'} <= set(span)
                    or set(span) - {'id', 'text', 'original_range'}
                    or type(span['id']) is not str or not 1 <= len(span['id']) <= 512
                    or type(span['text']) is not str or not span['text']):
                raise ValueError('public_sdk_original_span')
            identity = (source['content_hash'], span['id'])
            previous = identifiers.get(span['id'])
            if previous is not None and previous != (identity, span['text']):
                raise ValueError('public_sdk_ambiguous_span')
            identifiers[span['id']] = (identity, span['text'])
            result[identity] = span['text']
        # Actual schema3 paragraph sources commit the entire joined excerpt.
        # Generation omits the duplicate excerpt, assessment retains it.
        excerpt = '\n'.join(span['text'] for span in spans)
        if (source.get('evidence_schema') != 'original_paragraphs_v1'
                or hashlib.sha256(excerpt.encode()).hexdigest() != source['content_hash']
                or ('untrusted_excerpt' in source and source['untrusted_excerpt'] != excerpt)):
            raise ValueError('public_sdk_source_content_mismatch')
    if len(result) > 256 or sum(len(text.encode()) for text in result.values()) > 65536:
        raise ValueError('public_sdk_span_budget')
    return result


def resolved_literal_commitments(research, anchors):
    """Recompute unique codepoint commitments from ACTUALLY SENT public inputs.

    Returned ranges are recomputed diagnostics, not fields claimed to have been
    sent to the model. Exact compact {id,literal} inputs stay separately retained.
    """
    spans = _spans(research)
    if type(anchors) is not list or not 1 <= len(anchors) <= 32:
        raise ValueError('public_sdk_literal_count')
    result, seen, total = [], set(), 0
    for anchor in anchors:
        if (type(anchor) is not dict or set(anchor) != {'id', 'literal'}
                or type(anchor['id']) is not str or not HASH.fullmatch(anchor['id'])
                or anchor['id'] in seen or type(anchor['literal']) is not str
                or not 16 <= len(anchor['literal'].encode()) <= 1280):
            raise ValueError('public_sdk_literal_shape')
        total += len(anchor['literal'].encode())
        matches = []
        for (source_id, evidence_id), text in spans.items():
            start = text.find(anchor['literal'])
            while start >= 0:
                fields = {'source_id': source_id, 'evidence_id': evidence_id, 'start': start,
                    'end': start + len(anchor['literal']), 'literal': anchor['literal'],
                    'literal_sha256': hashlib.sha256(anchor['literal'].encode()).hexdigest()}
                if hashlib.sha256(DOMAIN + canonical(fields)).hexdigest() == anchor['id']:
                    matches.append(fields)
                start = text.find(anchor['literal'], start + 1)
        if len(matches) != 1 or total > 8192:
            raise ValueError('public_sdk_unbound_literal')
        seen.add(anchor['id'])
        result.append(matches[0])
    return result


def append_artist_public_input(records, input_messages, *, case_id):
    """Fail before SDK I/O on unknown case/phase, private fields or oversize data."""
    if case_id not in EXPECTED or len(records) >= 10:
        raise ValueError('public_sdk_unknown_case_or_budget')
    projections = []
    for message in input_messages:
        if type(message) is not dict or message.get('role') != 'user':
            continue
        content = message.get('content', '')
        values = [content] if type(content) is str else [item.get('text', '') for item in content if type(item) is dict] if type(content) is list else []
        for value in values:
            if type(value) is str and '\nData:\n' in value:
                projections.append(json.loads(value.split('\nData:\n', 1)[1]))
    if len(projections) != 1 or type(projections[0]) is not dict:
        raise ValueError('public_sdk_ambiguous_projection')
    projection = projections[0]
    if projection.get('artist_draft_schema') == 'artist_evidence_drafts_v1' and 'drafts' not in projection:
        phase = 'generation'
        research, anchors = projection.get('public_music_research'), projection.get('literal_anchors')
        language = (projection.get('style') or {}).get('language')
        resolved_literal_commitments(research, anchors)
    elif type(projection.get('drafts')) is list and type(projection.get('evidence')) is dict:
        phase = 'assessment'
        research, anchors = projection['evidence'].get('public_music_research'), []
        language = projection.get('language')
        _spans(research)
    else:
        raise ValueError('public_sdk_unknown_artist_phase')
    if language != EXPECTED[case_id] or any(row['case_id'] == case_id and row['phase'] == phase for row in records):
        raise ValueError('public_sdk_locale_or_duplicate')
    body = {'case_id': case_id, 'phase': phase, 'language': language,
        'public_music_research': research, 'literal_anchors': anchors}
    raw = canonical(body)
    frozen = json.loads(raw)
    frozen['sha256'] = hashlib.sha256(raw).hexdigest()
    if len(canonical(frozen)) > 131072 or sum(len(canonical(row)) for row in records) + len(canonical(frozen)) > 4 * 1024 * 1024:
        raise ValueError('public_sdk_receipt_budget')
    records.append(frozen)
    return frozen['sha256']


def artist_public_inputs_complete(report):
    """Exactly original 5x2 witnesses, joined to their actual provider attempts."""
    try:
        records = report['artist_public_inputs']
        if type(records) is not list or len(records) != 10:
            return False
        if (any(len(canonical(row)) > 131072 for row in records)
                or sum(len(canonical(row)) for row in records) > 4 * 1024 * 1024):
            return False
        indexed = {}
        for row in records:
            if type(row) is not dict or set(row) != {'case_id', 'phase', 'language', 'public_music_research', 'literal_anchors', 'sha256'}:
                return False
            case, phase = row['case_id'], row['phase']
            if (case not in EXPECTED or phase not in {'generation', 'assessment'}
                    or row['language'] != EXPECTED[case] or (case, phase) in indexed
                    or row['sha256'] != hashlib.sha256(canonical({k: v for k, v in row.items() if k != 'sha256'})).hexdigest()):
                return False
            spans = _spans(row['public_music_research'])
            if phase == 'generation':
                resolved_literal_commitments(row['public_music_research'], row['literal_anchors'])
            elif row['literal_anchors'] != []:
                return False
            indexed[case, phase] = (row, spans)
        for case in EXPECTED:
            generation, assessment = indexed[case, 'generation'], indexed[case, 'assessment']
            if generation[1] != assessment[1]:
                return False
        witnesses = [call for call in report['model_calls'] if 'artist_public_input_sha256' in call]
        return (len(witnesses) == 10 and sorted((call['case_id'], call['artist_public_input_sha256']) for call in witnesses)
            == sorted((row['case_id'], row['sha256']) for row in records))
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return False
