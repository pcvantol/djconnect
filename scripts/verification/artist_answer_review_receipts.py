"""Independent public SDK witness for original answer-address review inputs.

No runtime decoder imports, private question/history, or model-output repair.
This proves wire identity and coverage, not semantic or editorial acceptance.
"""
import hashlib
import json
import re

SCHEMA = 'source_answer_ids_review_v1'


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_answer_review_key')
        result[key] = value
    return result


def _catalog(records):
    if type(records) is not list or not 1 <= len(records) <= 2:
        raise ValueError('answer_review_draft_count')
    total, catalogs, seen = 0, [], set()
    for index, row in enumerate(records):
        if (type(row) is not dict or set(row) != {'index', 'sha256', 'text', 'answer_words'}
                or type(row['index']) is not int or row['index'] != index
                or type(row['text']) is not str or not row['text'] or row['text'] in seen):
            raise ValueError('answer_review_draft_shape')
        text = row['text']
        if any((ord(char) < 32 and char != '\n') or 0xD800 <= ord(char) <= 0xDFFF for char in text):
            raise ValueError('answer_review_control')
        seen.add(text)
        total += len(text.encode())
        if total > 8192 or row['sha256'] != hashlib.sha256(text.encode()).hexdigest():
            raise ValueError('answer_review_original_hash')
        words = [[f'd{index}w{number}', match.group()] for number, match in enumerate(re.finditer(r'\S+', text))]
        if not 1 <= len(words) <= 512 or row['answer_words'] != words:
            raise ValueError('answer_review_original_catalog')
        catalogs.append(words)
    if len(json.dumps(catalogs, ensure_ascii=False, separators=(',', ':')).encode()) > 16384:
        raise ValueError('answer_review_catalog_budget')
    return records


def capture_answer_review(input_messages):
    """Capture original outbound public fields, before awaiting the SDK."""
    found = []
    for message in input_messages:
        if type(message) is not dict or message.get('role') != 'user':
            continue
        content = message.get('content', '')
        values = [content] if type(content) is str else [item.get('text', '') for item in content if type(item) is dict] if type(content) is list else []
        for text in values:
            if type(text) is not str or '\nData:\n' not in text:
                continue
            projection = json.loads(text.split('\nData:\n', 1)[1], object_pairs_hook=_pairs)
            if type(projection.get('drafts')) is list and any('answer_words' in row for row in projection['drafts']):
                found.append(projection['drafts'])
    if not found:
        return None
    if len(found) != 1:
        raise ValueError('ambiguous_answer_review_input')
    return json.loads(json.dumps({'schema': SCHEMA, 'drafts': _catalog(found[0])}, ensure_ascii=False))


def answer_word_reviews_complete(report, *, expected_cases):
    """Join actual original input to raw returned IDs; no model verdict inference."""
    try:
        calls = [call for call in report['model_calls'] if 'artist_answer_review' in call]
        if len(calls) != len(expected_cases) or {call['case_id'] for call in calls} != set(expected_cases):
            return False
        for call in calls:
            witness = call['artist_answer_review']
            if (type(witness) is not dict or set(witness) != {'schema', 'drafts'}
                    or witness['schema'] != SCHEMA or call.get('completed') is not True
                    or call.get('terminal_event') != 'response.completed' or call.get('purpose') is not None):
                return False
            originals = _catalog(witness['drafts'])
            raw = call['generated_text']
            if type(raw) is not str or len(raw.encode()) > 8192:
                return False
            response = json.loads(raw, object_pairs_hook=_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            if type(response) is not dict or set(response) != {'draft_reviews'}:
                return False
            rows = response['draft_reviews']
            if type(rows) is not list or len(rows) != len(originals):
                return False
            for row, original in zip(rows, originals, strict=True):
                if (type(row) is not dict or set(row) != {'index', 'sha256', 'review'}
                        or type(row['index']) is not int or row['index'] != original['index']
                        or row['sha256'] != original['sha256']):
                    return False
                review = row['review']
                required = {'review_schema', 'supported', 'language_ok', 'style_ok', 'unsupported_claims', 'claim_checks'}
                if (type(review) is not dict or not required <= review.keys()
                        or review.keys() - required - {'temporal_claims'} or review['review_schema'] != SCHEMA
                        or any(type(review[key]) is not bool for key in ('supported', 'language_ok', 'style_ok'))
                        or type(review['unsupported_claims']) is not list or len(review['unsupported_claims']) > 3
                        or type(review['claim_checks']) is not list or len(review['claim_checks']) > 24):
                    return False
                if review['supported'] is False:
                    if (set(review) != required | {'temporal_claims'} or review['claim_checks'] != []
                            or review['temporal_claims'] != [] or not 1 <= len(review['unsupported_claims']) <= 3
                            or any(type(claim) is not str or not claim or len(claim.encode()) > 1200
                                or claim not in original['text'] for claim in review['unsupported_claims'])):
                        return False
                    continue
                if review['unsupported_claims'] != []:
                    return False
                words = list(re.finditer(r'\S+', original['text']))
                ids = {pair[0]: index for index, pair in enumerate(original['answer_words'])}
                cursor = 0
                for claim in review['claim_checks']:
                    if (type(claim) is not dict or set(claim) != {'answer_from', 'answer_to', 'kind', 'evidence_ids'}
                            or type(claim['answer_from']) is not str or type(claim['answer_to']) is not str
                            or claim['answer_from'] not in ids or claim['answer_to'] not in ids
                            or claim['kind'] not in ('fact', 'relationship', 'dj_appreciation')
                            or type(claim['evidence_ids']) is not list
                            or len(claim['evidence_ids']) != (0 if claim['kind'] == 'dj_appreciation' else 1)
                            or any(type(value) is not str or not 1 <= len(value) <= 512 for value in claim['evidence_ids'])):
                        return False
                    start, end = ids[claim['answer_from']], ids[claim['answer_to']]
                    if start != cursor or end < start or not 1 <= words[end].end() - words[start].start() <= 1200:
                        return False
                    cursor = end + 1
                if cursor != len(words):
                    return False
        return True
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return False
