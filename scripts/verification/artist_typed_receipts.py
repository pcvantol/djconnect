"""Independent original SDK/schema bindings for the scoped EN/NL typed wire.

This is structural evidence, never a positive content or editorial verdict.
No runtime schema/decoder is imported. Historical raw scopes stay separate.
"""
import hashlib
import json
import re

from scripts.verification.artist_answer_review_receipts import _catalog


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def object_schema(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields),
            'additionalProperties': False}


def expected_schema(marker):
    def text(maximum=1200):
        return {'type': 'string', 'minLength': 1, 'maxLength': maximum}
    def exact(value):
        return {'type': 'integer' if type(value) is int else 'string', 'enum': [value]}
    def array(item, minimum, maximum):
        return {'type': 'array', 'items': item, 'minItems': minimum, 'maxItems': maximum}
    if marker['operation'] == 'artist_generation_v1':
        return object_schema({'schema': exact('artist_evidence_drafts_v1'),
            'drafts': array(object_schema({
                'anchors': array({'type': 'string', 'enum': marker['anchors']}, 1, 3),
                'text': text(8192)}), 1, 1)})
    work = object_schema({key: text() for key in
                          ('claim', 'event_anchor', 'year', 'source_id', 'quote')})
    bio = object_schema({key: exact('biographical_event_v1') if key == 'schema' else text()
        for key in ('schema', 'event', 'claim', 'actor', 'group', 'group_id', 'year',
                    'source_id', 'evidence_id', 'quote')})
    rows = []
    for index, sha, addresses in marker['drafts']:
        address = {'type': 'string', 'maxLength': 16,
                   'pattern': r'^d' + str(index) + r'w(?:0|[1-9][0-9]{0,2})$'}
        rows.append(object_schema({'index': exact(index), 'sha256': exact(sha),
            'review': object_schema({
                'review_schema': exact('source_answer_ids_review_v1'),
                'supported': {'type': 'boolean'}, 'language_ok': {'type': 'boolean'},
                'style_ok': {'type': 'boolean'},
                'unsupported_claims': array(text(), 0, 3),
                'claim_checks': array(object_schema({
                    'answer_from': address, 'answer_to': address,
                    'kind': {'type': 'string', 'enum': ['fact', 'relationship', 'dj_appreciation']},
                    'evidence_ids': array(text(512), 0, 1)}), 0, 24),
                'temporal_claims': array({'anyOf': [work, bio]}, 0, 8)})}))
    return object_schema({'draft_reviews': array(rows[0] if len(rows) == 1 else
        {'anyOf': rows}, len(rows), len(rows))})


def _equivalent(left, right):
    """Required-field order has no meaning; all scalar types and rules do."""
    def normalized(value, key=None):
        if type(value) is dict:
            return {k: normalized(v, k) for k, v in value.items()}
        if type(value) is list:
            values = [normalized(v) for v in value]
            return sorted(values) if key == 'required' else values
        return value
    return canonical(normalized(left)) == canonical(normalized(right))


def complete(report, *, expected_cases):
    try:
        if report.get('artist_typed_transport') != 'PUBLIC_HA_AI_TASK_EN_NL_ARTIST_V1':
            return False
        expected = {(case, operation) for case in expected_cases for operation in
                    ('artist_generation_v1', 'artist_word_review_v1')}
        seen = set()
        for call in report['model_calls']:
            fields = {'structured_artist_operation', 'structured_artist_input'}
            if not fields.intersection(call):
                continue
            if not fields.issubset(call):
                return False
            marker = call['structured_artist_operation']
            if (type(marker) is not dict or set(marker) != {'schema_version', 'operation',
                    'prompt_sha256', 'anchors', 'drafts', 'binding_sha256'}
                    or type(marker['schema_version']) is not int or marker['schema_version'] != 1
                    or marker['operation'] not in {'artist_generation_v1', 'artist_word_review_v1'}
                    or type(marker['prompt_sha256']) is not str
                    or not re.fullmatch('[a-f0-9]{64}', marker['prompt_sha256'])
                    or marker['binding_sha256'] != hashlib.sha256(canonical(
                        {k:v for k,v in marker.items() if k != 'binding_sha256'})).hexdigest()):
                return False
            pair = call['case_id'], marker['operation']
            if pair not in expected or pair in seen or 'structured_playback_generation' in call:
                return False
            seen.add(pair)
            original = call['structured_artist_input']
            if original.get('prompt_sha256') != marker['prompt_sha256']:
                return False
            if marker['operation'] == 'artist_generation_v1':
                anchors = original['literal_anchors']
                if (set(original) != {'prompt_sha256', 'literal_anchors'} or marker['drafts'] != []
                        or not 1 <= len(anchors) <= 32 or marker['anchors'] != [a['id'] for a in anchors]
                        or len(set(marker['anchors'])) != len(anchors)):
                    return False
                source = [r for r in report['artist_public_inputs']
                          if r['case_id'] == call['case_id'] and r['phase'] == 'generation']
                if len(source) != 1 or source[0]['literal_anchors'] != anchors:
                    return False
            else:
                if set(original) != {'prompt_sha256', 'drafts'} or marker['anchors'] != []:
                    return False
                drafts = _catalog(original['drafts'])
                if (canonical(marker['drafts']) != canonical([[r['index'], r['sha256'], [w[0] for w in r['answer_words']]]
                                        for r in drafts])
                        or call['artist_answer_review']['drafts'] != drafts):
                    return False
            expected_format = {'type': 'json_schema', 'strict': True,
                'name': 'djconnect_' + marker['operation'], 'schema': expected_schema(marker)}
            if (not _equivalent(call['structured_output_format'], expected_format)
                    or call.get('provider_tools_absent') is not True
                    or call.get('provider_store_false') is not True
                    or call.get('purpose') is not None):
                return False
        return seen == expected
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return False
