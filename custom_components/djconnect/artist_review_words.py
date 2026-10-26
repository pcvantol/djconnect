"""Lossless answer addresses for the independent artist review, never truth.

The reviewer selects atomic ranges and evidence; Core only resolves immutable
original characters. All existing source, coverage, role and date checks still
run on those characters. This is a new wire, not repair of legacy responses.
"""
from dataclasses import dataclass
import hashlib
import json
import re

SCHEMA = 'source_answer_ids_review_v1'
MAX_WORDS = 512
MAX_CATALOG_BYTES = 16384


def _words(text, index):
    if (type(text) is not str or not text or len(text.encode()) > 8192
            or any((ord(char) < 32 and char != '\n') or 0xD800 <= ord(char) <= 0xDFFF
                   for char in text)):
        raise ValueError('invalid_answer_word_text')
    words = tuple((f'd{index}w{number}', match.start(), match.end())
                  for number, match in enumerate(re.finditer(r'\S+', text)))
    if not 1 <= len(words) <= MAX_WORDS:
        raise ValueError('answer_word_count')
    return words


@dataclass(frozen=True)
class AnswerWordReview:
    """Captured before the first review await; no mutable catalog is retained."""
    texts: tuple[str, ...]
    words: tuple[tuple[tuple[str, int, int], ...], ...]

    @classmethod
    def capture(cls, drafts):
        from .narration_brief import VerifiedDrafts
        if (type(drafts) is not VerifiedDrafts or drafts.batch is not True
                or type(drafts.texts) is not tuple or not 1 <= len(drafts.texts) <= 2):
            raise ValueError('invalid_answer_word_drafts')
        words = tuple(_words(text, index) for index, text in enumerate(drafts.texts))
        if sum(len(text.encode()) for text in drafts.texts) > 8192:
            raise ValueError('answer_word_text_budget')
        captured = cls(drafts.texts, words)
        catalogs = [row['answer_words'] for row in captured.records()]
        if len(json.dumps(catalogs, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_CATALOG_BYTES:
            raise ValueError('answer_word_catalog_budget')
        return captured

    def records(self):
        return [{'index': index, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                 'text': text, 'answer_words': [[identifier, text[start:end]]
                     for identifier, start, end in words]}
                for index, (text, words) in enumerate(zip(self.texts, self.words, strict=True))]

    def prompt(self, prompt, drafts):
        """Keep whole original text and evidence visible, adding only addresses."""
        from .narration_brief import draft_review_prompt
        if self != type(self).capture(drafts):
            raise ValueError('changed_answer_word_drafts')
        prompt = draft_review_prompt(prompt, drafts, text_field='answer')
        instructions, separator, raw = prompt.partition('\nData:\n')
        data = json.loads(raw)
        if not separator or data.get('drafts') != drafts.records():
            raise ValueError('unbound_answer_word_prompt')
        data['drafts'] = self.records()
        return instructions + '\nData:\n' + json.dumps(data, ensure_ascii=False, allow_nan=False)

    def decode(self, response, drafts):
        """Validate the entire batch before handing any verdict to old guards."""
        from .narration_brief import _draft_object, bound_draft_reviews
        if (self != type(self).capture(drafts) or type(response) is not str
                or len(response.encode()) > 8192):
            raise ValueError('unbound_answer_word_response')
        body = _draft_object(response)
        rows = body.get('draft_reviews') if type(body) is dict else None
        originals = drafts.records()
        if (type(body) is not dict or set(body) != {'draft_reviews'}
                or type(rows) is not list or len(rows) != len(originals)):
            raise ValueError('invalid_answer_word_reviews')
        # Bind ALL rows before decoding any model-selected range.
        for row, original in zip(rows, originals, strict=True):
            if (type(row) is not dict or set(row) != {'index', 'sha256', 'review'}
                    or type(row['index']) is not int or row['index'] != original['index']
                    or row['sha256'] != original['sha256'] or type(row['review']) is not dict):
                raise ValueError('unbound_answer_word_review')
        decoded = []
        required = {'review_schema', 'supported', 'language_ok', 'style_ok',
                    'unsupported_claims', 'claim_checks'}
        for row, text, words in zip(rows, self.texts, self.words, strict=True):
            review = row['review']
            if (not required <= review.keys() or review.keys() - required - {'temporal_claims'}
                    or review['review_schema'] != SCHEMA
                    or any(type(review[key]) is not bool for key in ('supported', 'language_ok', 'style_ok'))
                    or type(review['claim_checks']) is not list or len(review['claim_checks']) > 24):
                raise ValueError('invalid_answer_word_review')
            claims, cursor = [], 0
            addresses = {identifier: number for number, (identifier, _, _) in enumerate(words)}
            for claim in review['claim_checks']:
                if (type(claim) is not dict
                        or set(claim) != {'answer_from', 'answer_to', 'kind', 'evidence_ids'}
                        or type(claim['answer_from']) is not str or type(claim['answer_to']) is not str
                        or claim['answer_from'] not in addresses or claim['answer_to'] not in addresses):
                    raise ValueError('invalid_answer_word_claim')
                first, last = addresses[claim['answer_from']], addresses[claim['answer_to']]
                if first != cursor or last < first:
                    raise ValueError('answer_word_coverage')
                segment = text[words[first][1]:words[last][2]]
                if not 1 <= len(segment) <= 1200:
                    raise ValueError('answer_word_claim_bound')
                claims.append({'text': segment, 'kind': claim['kind'], 'evidence_ids': claim['evidence_ids']})
                cursor = last + 1
            if review['supported'] is True and cursor != len(words):
                raise ValueError('answer_word_coverage')
            decoded.append({**row, 'review': {**review, 'review_schema': 'source_id_review_v1',
                                             'claim_checks': claims}})
        # The legacy canonical validator also closes negative and temporal
        # shapes; its output still needs the unchanged factual/quality guards.
        return bound_draft_reviews(json.dumps({'draft_reviews': decoded}, ensure_ascii=False,
            allow_nan=False), drafts, public_story=True, closed_negative=True)
