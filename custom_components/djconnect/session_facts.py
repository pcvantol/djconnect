"""Bounded source-qualified current-track facts, never AI-created trivia.

Only exact Spotify catalog metadata, MusicBrainz core CC0 relationships and
Wikidata CC0 descriptions are eligible. Provider payloads remain transient.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace, field
from datetime import date
import re
import time
import unicodedata
from typing import Any


LANGUAGES = ("en", "nl", "de", "fr", "es")
USER_AGENT = "DJConnect/4.0 (https://github.com/pcvantol/djconnect; session-knowledge)"
MBID = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}")

CREDIT_ROLES = {
    "producer": ("Producer", "Producent", "Produzent", "Production", "Producción"),
    "instrument": ("Instruments", "Instrumenten", "Instrumente", "Instruments", "Instrumentos"),
    "vocal": ("Vocals", "Zang", "Gesang", "Voix", "Voces"),
}


@dataclass(frozen=True)
class DisplayFactCore:
    """Normalized immutable display anchors; no raw payload or generated fact."""
    kind: str
    subject: str = ""
    roles: tuple[tuple[str, tuple[str, ...]], ...] = ()
    date: str = ""
    precision: str = ""
    entity_type: str = ""

    def validates(self, fact: QualifiedSessionFact) -> bool:
        if self.kind != fact.key:
            return False
        if self.kind == "recording_credits":
            if (not self.roles or len({r for r, _ in self.roles}) != len(self.roles)
                    or any(r not in CREDIT_ROLES or not names or any(not label(n,160) for n in names)
                           for r,names in self.roles)):
                return False
            contents = tuple((lang," · ".join(
                f"{CREDIT_ROLES[r][index]}: {', '.join(names)}" for r,names in self.roles))
                for index,lang in enumerate(LANGUAGES))
            return contents == fact.contents
        if self.kind == "album_release":
            bodies = (f"Spotify dates this edition of {self.subject} to {self.date}.",
                f"Spotify dateert deze uitgave van {self.subject} op {self.date}.",
                f"Spotify datiert diese Ausgabe von {self.subject} auf {self.date}.",
                f"Spotify date cette édition de {self.subject} de {self.date}.",
                f"Spotify fecha esta edición de {self.subject} en {self.date}.")
            return bool(label(self.subject) and qualified_date(self.date,self.precision)
                        and tuple(zip(LANGUAGES,bodies)) == fact.contents)
        if self.kind == "artist_begin":
            if not label(self.subject) or not qualified_date(self.date,self.precision):
                return False
            if self.entity_type == "Person":
                bodies = (f"Birth date of {self.subject}: {self.date}.", f"Geboortedatum van {self.subject}: {self.date}.",
                    f"Geburtsdatum von {self.subject}: {self.date}.", f"Date de naissance de {self.subject} : {self.date}.",
                    f"Fecha de nacimiento de {self.subject}: {self.date}.")
            elif self.entity_type == "Group":
                bodies = (f"{self.subject} formed in {self.date}.", f"{self.subject} is opgericht in {self.date}.",
                    f"{self.subject} wurde {self.date} gegründet.", f"{self.subject} a été formé en {self.date}.",
                    f"{self.subject} se formó en {self.date}.")
            else:
                return False
            return tuple(zip(LANGUAGES,bodies)) == fact.contents
        if self.kind == "work_composers":
            if len(self.roles) != 1 or self.roles[0][0] != "composer" or not self.roles[0][1]:
                return False
            names = ", ".join(self.roles[0][1])
            bodies = (f"Composers of the work behind this recording: {names}.",
                f"Componisten van het werk achter deze opname: {names}.",
                f"Komponisten des Werks hinter dieser Aufnahme: {names}.",
                f"Compositeurs de l’œuvre de cet enregistrement : {names}.",
                f"Compositores de la obra de esta grabación: {names}.")
            return all(label(n,160) for n in self.roles[0][1]) and tuple(zip(LANGUAGES,bodies)) == fact.contents
        return False


@dataclass(frozen=True)
class ProducerCredit:
    contributor_id: str
    name: str
    role: str = "producer"
    qualifications: tuple[str, ...] = ()

    def eligible(self) -> bool:
        return bool(MBID.fullmatch(self.contributor_id) and label(self.name, 160)
                    and self.role == "producer" and not self.qualifications)


@dataclass(frozen=True)
class RecordingCreditEvidence:
    """Minimal proof, never historical playback or generated card text."""
    recording_id: str
    media_identity: str
    title: str
    producers: tuple[ProducerCredit, ...]
    source_url: str
    observed_at: float

    def eligible(self, now: float) -> bool:
        return bool(MBID.fullmatch(self.recording_id)
                    and re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", self.media_identity)
                    and label(self.title, 160)
                    and self.source_url == "https://musicbrainz.org/recording/" + self.recording_id
                    and 0 <= now - self.observed_at <= 1800
                    and self.producers and all(p.eligible() for p in self.producers)
                    and len({p.contributor_id for p in self.producers}) == len(self.producers))


def label(value: Any, limit: int = 320) -> str:
    text = str(value or "").strip()
    return text if 0 < len(text) <= limit and not any(ord(c) < 32 for c in text) else ""


def match_name(value: Any) -> str:
    return unicodedata.normalize("NFKC", label(value)).casefold()


def qualified_date(value: Any, precision: Any) -> str:
    text = str(value or "")
    patterns = {"year": r"\d{4}", "month": r"\d{4}-\d{2}", "day": r"\d{4}-\d{2}-\d{2}"}
    if not re.fullmatch(patterns.get(str(precision), r"(?!)"), text):
        return ""
    try:
        date.fromisoformat(text + {"year": "-01-01", "month": "-01", "day": ""}[str(precision)])
    except ValueError:
        return ""
    return text


@dataclass(frozen=True)
class QualifiedSessionFact:
    """Normalized internal evidence; only text and attribution enter Broadcast."""

    key: str
    media_identity: str
    intent: str
    summaries: tuple[tuple[str, str], ...]
    contents: tuple[tuple[str, str], ...]
    provider: str
    source_url: str
    license: str
    observed_at: float
    recording_evidence: RecordingCreditEvidence | None = None
    display_core: DisplayFactCore | None = None

    def copy_for(self, locale: str) -> tuple[str, str] | None:
        lang = locale[:2].lower()
        summary, content = dict(self.summaries).get(lang), dict(self.contents).get(lang)
        return (summary, content) if summary and content else None

    def eligible(self, media_identity: str, now: float) -> bool:
        # Qualification is field/provider/intent specific. Relevance must never
        # widen the narrow visual-only producer contract.
        fields = {
            "album_release": ("Spotify", "album_story", "Spotify metadata display", r"https://open\.spotify\.com/album/[A-Za-z0-9]{22}"),
            "recording_credits": ("MusicBrainz", "track_context", "CC0-1.0", r"https://musicbrainz\.org/recording/" + MBID.pattern),
            "work_composers": ("MusicBrainz", "track_context", "CC0-1.0", r"https://musicbrainz\.org/work/" + MBID.pattern),
            "artist_begin": ("MusicBrainz", "artist_story", "CC0-1.0", r"https://musicbrainz\.org/artist/" + MBID.pattern),
            "artist_description": ("Wikidata", "artist_story", "CC0-1.0", r"https://www\.wikidata\.org/wiki/Q[1-9]\d*"),
        }
        qualified = fields.get(self.key)
        return bool(
            qualified is not None
            and (self.provider, self.intent, self.license) == qualified[:3]
            and re.fullmatch(qualified[3], self.source_url)
            and re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", media_identity)
            and self.media_identity == media_identity
            and 0 <= now - self.observed_at <= 1800
        )


@dataclass(frozen=True)
class SharedProducerFact(QualifiedSessionFact):
    """Closed derived visual relationship; not an ordinary provider field."""
    previous_evidence: RecordingCreditEvidence | None = None
    producer_id: str = ""

    @property
    def relation_key(self) -> tuple[str, str, str]:
        if self.recording_evidence is None or self.previous_evidence is None:
            return ("", "", "")
        a, b = sorted((self.recording_evidence.recording_id, self.previous_evidence.recording_id))
        return a, b, self.producer_id

    def eligible(self, media_identity: str, now: float) -> bool:
        current, previous = self.recording_evidence, self.previous_evidence
        if (self.key != "shared_producer" or self.intent != "track_context"
                or (self.provider, self.license) != ("MusicBrainz", "CC0-1.0")
                or current is None or previous is None
                or not current.eligible(now) or not previous.eligible(now)
                or current.media_identity != media_identity or self.media_identity != media_identity
                or current.media_identity == previous.media_identity
                or current.recording_id == previous.recording_id
                or self.source_url != current.source_url
                or self.observed_at != current.observed_at):
            return False
        a = next((p for p in current.producers if p.contributor_id == self.producer_id), None)
        b = next((p for p in previous.producers if p.contributor_id == self.producer_id), None)
        return bool(a and b and a == b and self.summaries == _shared_copy(current, previous, a)[0]
                    and self.contents == _shared_copy(current, previous, a)[1])


def _shared_copy(current: RecordingCreditEvidence, previous: RecordingCreditEvidence,
                 producer: ProducerCredit) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    name, title, earlier = producer.name, current.title, previous.title
    titles = ["Shared producer", "Dezelfde producer", "Gemeinsamer Produzent",
              "Même producteur", "Mismo productor"]
    bodies = [
        f"{name} is credited as a producer on {title}, as on the earlier recording {earlier}.",
        f"{name} staat als producer vermeld bij {title}, net als bij de eerder besproken opname {earlier}.",
        f"{name} ist bei {title} als Produzent genannt, ebenso bei der zuvor besprochenen Aufnahme {earlier}.",
        f"{name} figure comme producteur sur {title}, comme sur l’enregistrement évoqué précédemment, {earlier}.",
        f"{name} figura como productor de {title}, al igual que en la grabación comentada antes, {earlier}.",
    ]
    return tuple(zip(LANGUAGES, titles)), tuple(zip(LANGUAGES, bodies))


def shared_producer_fact(current: RecordingCreditEvidence, previous: RecordingCreditEvidence,
                         now: float) -> SharedProducerFact | None:
    if not current.eligible(now) or not previous.eligible(now):
        return None
    candidates = sorted((p for p in current.producers if p in previous.producers),
                        key=lambda p: p.contributor_id)
    for producer in candidates:
        titles, bodies = _shared_copy(current, previous, producer)
        fact = SharedProducerFact("shared_producer", current.media_identity, "track_context",
            titles, bodies, "MusicBrainz", current.source_url, "CC0-1.0", current.observed_at,
            recording_evidence=current, previous_evidence=previous, producer_id=producer.contributor_id)
        if fact.eligible(current.media_identity, now):
            return fact
    return None


@dataclass
class PublishedRecordingContext:
    """One Runtime's three observed tracks and published-only credit proofs."""
    observed_tracks: list[str] = field(default_factory=list)
    credits: dict[str, RecordingCreditEvidence] = field(default_factory=dict)
    used_relations: set[tuple[str, str, str]] = field(default_factory=set)
    connected_tracks: set[str] = field(default_factory=set)

    def observe(self, media_identity: str, now: float) -> None:
        if media_identity in self.observed_tracks:
            self.observed_tracks.remove(media_identity)
        self.observed_tracks.append(media_identity)
        self.observed_tracks[:] = self.observed_tracks[-3:]
        self.credits = {key: value for key, value in self.credits.items()
                        if key in self.observed_tracks and value.eligible(now)}

    def commit(self, fact: QualifiedSessionFact, now: float) -> None:
        evidence = fact.recording_evidence
        if (fact.key in {"recording_credits", "shared_producer"} and fact.eligible(fact.media_identity, now)
                and evidence and evidence.eligible(now) and evidence.media_identity == fact.media_identity
                and evidence.source_url == fact.source_url and evidence.observed_at == fact.observed_at
                and fact.media_identity in self.observed_tracks):
            self.credits[fact.media_identity] = evidence
        if isinstance(fact, SharedProducerFact) and fact.eligible(fact.media_identity, now):
            self.used_relations.add(fact.relation_key)
            self.connected_tracks.add(fact.media_identity)

    def candidate(self, facts: tuple[QualifiedSessionFact, ...], media_identity: str,
                  now: float) -> SharedProducerFact | None:
        if media_identity in self.connected_tracks:
            return None
        current = [f.recording_evidence for f in facts if f.key == "recording_credits"
                   and f.eligible(media_identity, now) and f.recording_evidence
                   and f.recording_evidence.media_identity == media_identity
                   and f.recording_evidence.source_url == f.source_url
                   and f.recording_evidence.observed_at == f.observed_at]
        # Multiple conflicting proofs of the current recording fail closed.
        if not current or any(c != current[0] for c in current):
            return None
        for identity in reversed(self.observed_tracks):
            previous = self.credits.get(identity)
            if previous is not None:
                fact = shared_producer_fact(current[0], previous, now)
                if fact and fact.relation_key not in self.used_relations:
                    return fact
        return None

    def clear(self) -> None:
        self.observed_tracks.clear()
        self.credits.clear()
        self.used_relations.clear()
        self.connected_tracks.clear()


def _fact(
    key: str,
    catalog: dict[str, Any],
    intent: str,
    titles: list[str],
    bodies: list[str],
    provider: str,
    url: str,
    core: DisplayFactCore | None = None,
) -> QualifiedSessionFact:
    return QualifiedSessionFact(
        key,
        catalog["uri"],
        intent,
        tuple(zip(LANGUAGES, titles)),
        tuple(zip(LANGUAGES, bodies)),
        provider,
        url,
        "Spotify metadata display" if provider == "Spotify" else "CC0-1.0",
        time.monotonic(),
        display_core=core,
    )


def catalog_facts(catalog: dict[str, Any]) -> list[QualifiedSessionFact]:
    uri = str(catalog.get("uri") or "")
    if not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", uri):
        return []
    album, album_uri = label(catalog.get("album_name")), str(catalog.get("album_uri") or "")
    released = qualified_date(catalog.get("release_date"), catalog.get("release_date_precision"))
    if not album or not released or not re.fullmatch(r"spotify:album:[A-Za-z0-9]{22}", album_uri):
        return []
    return [
        _fact(
            "album_release",
            catalog,
            "album_story",
            [album] * 5,
            [
                f"Spotify dates this edition of {album} to {released}.",
                f"Spotify dateert deze uitgave van {album} op {released}.",
                f"Spotify datiert diese Ausgabe von {album} auf {released}.",
                f"Spotify date cette édition de {album} de {released}.",
                f"Spotify fecha esta edición de {album} en {released}.",
            ],
            "Spotify",
            "https://open.spotify.com/album/" + album_uri.split(":")[-1],
            DisplayFactCore("album_release", album, date=released, precision=str(catalog.get("release_date_precision"))),
        )
    ]


class SessionFactsResolver:
    """One HA-wide rate limiter, no persistent cache or personal source query."""

    def __init__(self, hass: Any) -> None:
        self.hass = hass
        self.lock = asyncio.Lock()
        self.last_request = 0.0
        self.backoff_until = 0.0

    async def _get(
        self, path: str, params: dict[str, str] | None = None, *, wikidata: bool = False
    ) -> dict[str, Any]:
        async with self.lock:
            now = time.monotonic()
            if now < self.backoff_until:
                return {}
            await asyncio.sleep(max(0, 1.1 - (now - self.last_request)))
            self.last_request = time.monotonic()
            url = (
                "https://www.wikidata.org/w/api.php"
                if wikidata
                else "https://musicbrainz.org/ws/2/" + path
            )
            try:
                from aiohttp import ClientTimeout, ClientError
                from homeassistant.helpers.aiohttp_client import async_get_clientsession

                session = async_get_clientsession(self.hass)
                async with session.get(
                    url,
                    params=params or {"fmt": "json"},
                    headers={"User-Agent": USER_AGENT},
                    timeout=ClientTimeout(total=8),
                    allow_redirects=False,
                ) as response:
                    if response.status in {429, 503}:
                        retry = response.headers.get("Retry-After", "60")
                        self.backoff_until = time.monotonic() + max(
                            60, min(3600, int(retry) if retry.isdigit() else 60)
                        )
                        return {}
                    if response.status != 200:
                        return {}
                    # Bound response size before parsing; never retain raw responses.
                    if response.content_length and response.content_length > 512_000:
                        return {}
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(16_384):
                        raw.extend(chunk)
                        if len(raw) > 512_000:
                            return {}
                    import json

                    result = json.loads(raw)
                    if isinstance(result, dict) and result.get("error"):
                        self.backoff_until = time.monotonic() + 60
                        return {}
                    return result if isinstance(result, dict) else {}
            except (ValueError, OSError, ClientError, asyncio.TimeoutError):
                return {}

    async def resolve(self, catalog: dict[str, Any]) -> tuple[QualifiedSessionFact, ...]:
        facts = catalog_facts(catalog)
        uri, title, artist = (
            str(catalog.get("uri") or ""),
            label(catalog.get("title")),
            label(catalog.get("artist")),
        )
        isrc = str(catalog.get("isrc") or "").upper()
        if (
            not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", uri)
            or not title
            or not artist
            or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}\d{7}", isrc)
        ):
            return tuple(facts)
        async with asyncio.timeout(35):
            data = await self._get("isrc/" + isrc, {"fmt": "json", "inc": "artist-credits"})
            recordings = data.get("recordings") or []
            # An ISRC reused for multiple recordings is ambiguous, even if one title looks close.
            if len(recordings) != 1 or not isinstance(recordings[0], dict):
                return tuple(facts)
            recording = recordings[0]
            credit = recording.get("artist-credit") or []
            names = [c.get("artist", {}).get("name") for c in credit if isinstance(c, dict)]
            if match_name(recording.get("title")) != match_name(title) or match_name(
                ", ".join(str(n) for n in names)
            ) != match_name(artist):
                return tuple(facts)
            recording_id = str(recording.get("id") or "")
            if not MBID.fullmatch(recording_id):
                return tuple(facts)
            detailed = await self._get(
                "recording/" + recording_id,
                {"fmt": "json", "inc": "artist-credits+artist-rels+work-rels+work-level-rels"},
            )
            if detailed.get("id") != recording_id or match_name(
                detailed.get("title")
            ) != match_name(title):
                return tuple(facts)
            detailed_names = [c.get("artist", {}).get("name") for c in detailed.get("artist-credit", [])
                              if isinstance(c, dict)]
            if match_name(", ".join(str(n) for n in detailed_names)) != match_name(artist):
                return tuple(facts)
            facts.extend(recording_facts(catalog, detailed))
            facts.extend(work_facts(catalog, detailed))
            if len(credit) == 1 and isinstance(credit[0], dict):
                artist_id = str(credit[0].get("artist", {}).get("id") or "")
                if MBID.fullmatch(artist_id):
                    person = await self._get(
                        "artist/" + artist_id, {"fmt": "json", "inc": "url-rels"}
                    )
                    if person.get("id") == artist_id and match_name(
                        person.get("name")
                    ) == match_name(artist):
                        facts.extend(artist_facts(catalog, person))
                        wikidata_ids = {
                            m.group(1)
                            for r in person.get("relations", [])
                            if isinstance(r, dict)
                            and r.get("type") == "wikidata"
                            and (
                                m := re.fullmatch(
                                    r"https?://www.wikidata.org/wiki/(Q\d+)",
                                    str(r.get("url", {}).get("resource") or ""),
                                )
                            )
                        }
                        if len(wikidata_ids) == 1:
                            qid = next(iter(wikidata_ids))
                            entity_data = await self._get(
                                "",
                                {
                                    "action": "wbgetentities",
                                    "ids": qid,
                                    "props": "labels|descriptions|claims",
                                    "languages": "|".join(LANGUAGES),
                                    "format": "json",
                                    "maxlag": "5",
                                },
                                wikidata=True,
                            )
                            entity = entity_data.get("entities", {}).get(qid, {})
                            # Reciprocal MusicBrainz artist ID is mandatory, not a name-only match.
                            ids = {
                                c.get("mainsnak", {}).get("datavalue", {}).get("value")
                                for c in entity.get("claims", {}).get("P434", [])
                                if c.get("rank") != "deprecated"
                            }
                            if ids == {artist_id}:
                                fact = description_fact(catalog, entity, qid)
                                if fact:
                                    facts.append(fact)
        return tuple(facts[:6])


def recording_facts(
    catalog: dict[str, Any], recording: dict[str, Any]
) -> list[QualifiedSessionFact]:
    roles = CREDIT_ROLES
    collected: dict[str, list[str]] = {}
    for relation in recording.get("relations", []):
        if (
            not isinstance(relation, dict)
            or relation.get("target-type") != "artist"
            or relation.get("type") not in roles
        ):
            continue
        if relation.get("type") == "producer" and (
            relation.get("attributes") or relation.get("attribute-values")
            or relation.get("ended") or not isinstance(relation.get("attributes", []), list)
        ):
            # Do not display a restricted producer as an unqualified producer.
            continue
        name = label(relation.get("artist", {}).get("name"), 160)
        if name:
            collected.setdefault(relation["type"], []).append(name)
    if not collected:
        return []
    lines = []
    for index in range(5):
        lines.append(
            " · ".join(
                f"{roles[role][index]}: {', '.join(dict.fromkeys(names))}"
                for role, names in collected.items()
            )
        )
    if any(len(line) > 700 for line in lines):
        return []
    fact = _fact(
            "recording_credits",
            catalog,
            "track_context",
            [
                "Recording credits",
                "Wie werkten mee?",
                "Aufnahme-Credits",
                "Crédits de l’enregistrement",
                "Créditos de la grabación",
            ],
            lines,
            "MusicBrainz",
            "https://musicbrainz.org/recording/" + recording["id"],
            DisplayFactCore("recording_credits", roles=tuple((role,tuple(dict.fromkeys(names))) for role,names in collected.items())),
        )
    # Preserve only source fields, never recover identity from rendered text.
    # Attributes can narrow the producer role; this first slice excludes all.
    producers: dict[str, ProducerCredit] = {}
    conflicts: set[str] = set()
    for relation in recording.get("relations", []):
        if not isinstance(relation, dict) or relation.get("target-type") != "artist" or relation.get("type") != "producer":
            continue
        artist = relation.get("artist")
        if not isinstance(artist, dict):
            continue
        identity, name = str(artist.get("id") or ""), label(artist.get("name"), 160)
        if not MBID.fullmatch(identity):
            continue
        qualifications = relation.get("attributes", [])
        if qualifications or not isinstance(qualifications, list) or relation.get("attribute-values") or relation.get("ended"):
            conflicts.add(identity)
            continue
        producer = ProducerCredit(identity, name)
        if not producer.eligible() or (identity in producers and producers[identity] != producer):
            conflicts.add(identity)
        else:
            producers[identity] = producer
    proof = RecordingCreditEvidence(str(recording.get("id") or ""), str(catalog.get("uri") or ""),
        label(catalog.get("title"), 160), tuple(producers[key] for key in sorted(producers) if key not in conflicts),
        fact.source_url, fact.observed_at)
    recording_names = [c.get("artist", {}).get("name") for c in recording.get("artist-credit", [])
                       if isinstance(c, dict) and isinstance(c.get("artist"), dict)]
    if (proof.eligible(fact.observed_at)
            and match_name(recording.get("title")) == match_name(catalog.get("title"))
            and match_name(", ".join(str(n) for n in recording_names)) == match_name(catalog.get("artist"))):
        fact = replace(fact, recording_evidence=proof)
    return [fact]


def artist_facts(catalog: dict[str, Any], person: dict[str, Any]) -> list[QualifiedSessionFact]:
    begin = str(person.get("life-span", {}).get("begin") or "")
    precision = {4: "year", 7: "month", 10: "day"}.get(len(begin), "")
    if not qualified_date(begin, precision) or person.get("type") not in {"Person", "Group"}:
        return []
    artist = label(person.get("name"))
    person_copy = [
        f"Birth date of {artist}: {begin}.",
        f"Geboortedatum van {artist}: {begin}.",
        f"Geburtsdatum von {artist}: {begin}.",
        f"Date de naissance de {artist} : {begin}.",
        f"Fecha de nacimiento de {artist}: {begin}.",
    ]
    group_copy = [
        f"{artist} formed in {begin}.",
        f"{artist} is opgericht in {begin}.",
        f"{artist} wurde {begin} gegründet.",
        f"{artist} a été formé en {begin}.",
        f"{artist} se formó en {begin}.",
    ]
    return [
        _fact(
            "artist_begin",
            catalog,
            "artist_story",
            [artist] * 5,
            person_copy if person["type"] == "Person" else group_copy,
            "MusicBrainz",
            "https://musicbrainz.org/artist/" + person["id"],
            DisplayFactCore("artist_begin", artist, date=begin, precision=precision, entity_type=person["type"]),
        )
    ]


def description_fact(
    catalog: dict[str, Any], entity: dict[str, Any], qid: str
) -> QualifiedSessionFact | None:
    descriptions = entity.get("descriptions", {})
    texts = [label(descriptions.get(lang, {}).get("value"), 400) for lang in LANGUAGES]
    if not any(texts):
        return None
    artist = label(catalog.get("artist"))
    # Missing translations suppress this card in that locale; never show English as Dutch.
    return _fact(
        "artist_description",
        catalog,
        "artist_story",
        [artist if text else "" for text in texts],
        texts,
        "Wikidata",
        "https://www.wikidata.org/wiki/" + qid,
    )


def work_facts(catalog: dict[str, Any], recording: dict[str, Any]) -> list[QualifiedSessionFact]:
    works = [
        r.get("work")
        for r in recording.get("relations", [])
        if isinstance(r, dict)
        and r.get("target-type") == "work"
        and r.get("type") == "performance"
        and isinstance(r.get("work"), dict)
    ]
    if len(works) != 1:
        return []
    work = works[0]
    work_id = str(work.get("id") or "")
    if not MBID.fullmatch(work_id):
        return []
    composers = list(
        dict.fromkeys(
            label(r.get("artist", {}).get("name"), 160)
            for r in work.get("relations", [])
            if isinstance(r, dict)
            and r.get("target-type") == "artist"
            and r.get("type") == "composer"
        )
    )
    composers = [name for name in composers if name]
    if not composers or len(composers) > 8:
        return []
    names = ", ".join(composers)
    return [
        _fact(
            "work_composers",
            catalog,
            "track_context",
            [
                "Behind the composition",
                "Achter de compositie",
                "Hinter der Komposition",
                "Derrière la composition",
                "Detrás de la composición",
            ],
            [
                f"Composers of the work behind this recording: {names}.",
                f"Componisten van het werk achter deze opname: {names}.",
                f"Komponisten des Werks hinter dieser Aufnahme: {names}.",
                f"Compositeurs de l’œuvre de cet enregistrement : {names}.",
                f"Compositores de la obra de esta grabación: {names}.",
            ],
            "MusicBrainz",
            "https://musicbrainz.org/work/" + work_id,
            DisplayFactCore("work_composers", roles=(("composer",tuple(composers)),)),
        )
    ]


def session_facts_resolver(hass: Any) -> SessionFactsResolver:
    data = hass.data.setdefault("djconnect", {})
    if "session_facts_resolver" not in data:
        data["session_facts_resolver"] = SessionFactsResolver(hass)
    return data["session_facts_resolver"]
