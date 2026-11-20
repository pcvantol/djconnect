"""Event-specific public photographs inside the existing Session research owner.

No independent scheduler, agent, client URL input or persistent pixel archive.
A sealed acceptance binds fetched bytes, original event and reviewed narration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import hmac
import json
import re
import secrets

from . import artist_photo

BASIS = 'public_live_impression_v1'
LANGUAGES = frozenset({'en', 'nl', 'de', 'fr', 'es'})
_KEY = secrets.token_bytes(32)
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _seal(*values):
    return hmac.digest(_KEY, repr(values).encode(), 'sha256').hex()


def _label(value, maximum=320):
    return (isinstance(value, str) and 0 < len(value) <= maximum
            and value == value.strip() and all(c.isprintable() or c == '\n' for c in value))


def checked(value):
    """Retained shape validation grants no publication or external URL authority."""
    if not isinstance(value, dict) or set(value) != {'schema_version', 'event', 'photos'} or type(value['schema_version']) is not int or value['schema_version'] != 1:
        return None
    event = value['event']
    if (not isinstance(event, dict) or set(event) != {'event_id', 'artist', 'date', 'date_precision', 'venue', 'city', 'relationship'}
            or not all(_label(event[k]) for k in ('event_id', 'artist', 'date', 'venue', 'city'))
            or event['relationship'] not in {'same_artist', 'song_performed', 'exact_recording'}
            or event['date_precision'] not in {'day', 'month', 'year'}):
        return None
    try:
        parsed = date.fromisoformat(event['date'] + {'day':'', 'month':'-01', 'year':'-01-01'}[event['date_precision']])
        if parsed > datetime.now(UTC).date():
            return None
    except ValueError:
        return None
    photos = value['photos']
    if not isinstance(photos, list) or not 1 <= len(photos) <= 3:
        return None
    ids = set()
    for p in photos:
        if (not isinstance(p, dict) or set(p) != {'photo_id', 'revision', 'caption', 'alt_text', 'width', 'height', 'source_url', 'author', 'credit', 'license', 'license_url'}
                or not all(_label(p[k], 4000 if k == 'caption' else 640) for k in ('photo_id','revision','caption','source_url','author','credit','license','license_url'))
                or not re.fullmatch(r'[a-f0-9]{64}', p['revision']) or p['photo_id'] in ids
                or type(p['width']) is not int or type(p['height']) is not int
                or not 512 <= min(p['width'],p['height']) <= max(p['width'],p['height']) <= 4096
                or p['width']*p['height'] > 16_000_000
                or not isinstance(p['alt_text'], dict) or set(p['alt_text']) != LANGUAGES
                or not all(_label(v, 640) for v in p['alt_text'].values())
                or p['license'] not in {v[0] for v in artist_photo.LICENSES.values()}
                or (p['license'],p['license_url']) not in set(artist_photo.LICENSES.values())
                or not p['source_url'].startswith('https://commons.wikimedia.org/wiki/File:')):
            return None
        ids.add(p['photo_id'])
    return value


@dataclass(frozen=True, repr=False)
class Acceptance:
    fact: object
    title: str
    lead: str
    text: str
    payload_json: str
    sources_json: str
    reference_json: str
    locale: str
    persona: str
    mood: str
    signature: str

    def valid(self):
        values = tuple(getattr(self, key) for key in self.__dataclass_fields__ if key != 'signature')
        try:
            return (hmac.compare_digest(self.signature, _seal(*values))
                    and checked(json.loads(self.payload_json)) is not None)
        except (ValueError, TypeError, KeyError):
            return False


class LiveImpressionText(str):
    def __new__(cls, accepted, pixels, mime):
        obj = super().__new__(cls, accepted.text)
        obj.accepted = accepted
        obj.pixels, obj.mime = pixels, mime
        return obj


def admitted(moment):
    proof = getattr(moment, 'live_impression', None)
    return bool(type(proof) is Acceptance and proof.valid()
        and moment.moment_type.value == 'live_impression'
        and moment.knowledge_intent.intent_type.value == 'live_impression'
        and moment.source_fact == proof.fact and moment.title == proof.title
        and moment.summary == proof.lead and moment.content == proof.text
        and moment.presentation_intent.dj_persona.value == proof.persona
        and moment.presentation_intent.source_session_mood == proof.mood)


def projection(moment):
    return json.loads(moment.live_impression.payload_json) if admitted(moment) else None


