"""Bounded source-qualified current-track facts, never AI-created trivia.

Only exact Spotify catalog metadata, MusicBrainz core CC0 relationships and
Wikidata CC0 descriptions are eligible. Provider payloads remain transient.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
import re
import time
import unicodedata
from typing import Any


LANGUAGES = ("en", "nl", "de", "fr", "es")
USER_AGENT = "DJConnect/4.0 (https://github.com/pcvantol/djconnect; session-knowledge)"
MBID = re.compile(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}")


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


def _fact(
    key: str,
    catalog: dict[str, Any],
    intent: str,
    titles: list[str],
    bodies: list[str],
    provider: str,
    url: str,
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
    roles = {
        "producer": ["Producer", "Producent", "Produzent", "Production", "Producción"],
        "instrument": ["Instruments", "Instrumenten", "Instrumente", "Instruments", "Instrumentos"],
        "vocal": ["Vocals", "Zang", "Gesang", "Voix", "Voces"],
    }
    collected: dict[str, list[str]] = {}
    for relation in recording.get("relations", []):
        if (
            not isinstance(relation, dict)
            or relation.get("target-type") != "artist"
            or relation.get("type") not in roles
        ):
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
    return [
        _fact(
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
        )
    ]


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
        )
    ]


def session_facts_resolver(hass: Any) -> SessionFactsResolver:
    data = hass.data.setdefault("djconnect", {})
    if "session_facts_resolver" not in data:
        data["session_facts_resolver"] = SessionFactsResolver(hass)
    return data["session_facts_resolver"]
