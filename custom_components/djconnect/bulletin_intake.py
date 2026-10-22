"""Fixed public feed intake for #1291; never a publication or model scheduler.

Only short RSS/Atom metadata enters bounded RAM. No article fetch, credentials,
Profile preferences, renderer, tool invocation or DJ Moment publication here.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import math
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

WINDOW_SECONDS = 1800
POLL_SECONDS = 300
MAX_BYTES = 524288
MAX_ITEMS = 64
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True)
class FeedSource:
    source_id: str
    title: str
    url: str
    article_hosts: tuple[str, ...]
    license: str
    rights_url: str


# Verified official publisher catalogues and actual XML on 2026-10-22.
# No caller-supplied sources, categories or URLs. No images/full articles.
SOURCES = (
    FeedSource("cbs", "CBS", "https://www.cbs.nl/nl-nl/rss-feeds/alle-nieuwsberichten",
        ("www.cbs.nl",), "CC-BY-4.0", "https://www.cbs.nl/nl-nl/over-ons/website/copyright"),
    FeedSource("knmi", "KNMI", "https://cdn.knmi.nl/knmi/xml/rss/rss_KNMInieuwsberichten.xml",
        ("www.knmi.nl",), "CC0-1.0", "https://www.knmi.nl/copyright"),
    FeedSource("nasa", "NASA", "https://www.nasa.gov/news-release/feed/",
        ("www.nasa.gov", "science.nasa.gov"), "NASA-media-guidelines",
        "https://www.nasa.gov/nasa-brand-center/images-and-media/"),
    FeedSource("eea", "European Environment Agency",
        "https://www.eea.europa.eu/en/newsroom/rss-feeds/eeas-press-releases-rss/rss.xml",
        ("www.eea.europa.eu",), "CC-BY-4.0", "https://www.eea.europa.eu/en/legal-notice"),
    FeedSource("eurostat", "Eurostat",
        "https://ec.europa.eu/eurostat/en/search?p_p_id=estatsearchportlet_WAR_estatsearchportlet"
        "&p_p_lifecycle=2&p_p_state=maximized&p_p_mode=view&p_p_resource_id=atom"
        "&_estatsearchportlet_WAR_estatsearchportlet_collection=CAT_PREREL",
        ("ec.europa.eu",), "CC-BY-4.0", "https://ec.europa.eu/eurostat/help/copyright-notice"),
)


class IntakeError(ValueError):
    """Static content-free rejection; never log a feed body."""


def _clock(now):
    if type(now) not in (float, int) or not math.isfinite(now) or now <= 0:
        raise IntakeError("invalid_bulletin_clock")
    return now


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "br", "div", "li"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value, limit):
    if type(value) is not str or len(value) > 16000:
        return ""
    parser = _Text()
    parser.feed(value)
    text = " ".join("".join(parser.parts).split())
    # Reject, rather than truncate into a different factual statement.
    return text if len(text) <= limit and not any(ord(c) < 32 for c in text) else ""


def publication_time(value):
    """Never substitute observation/update time for an absent publication date."""
    if type(value) is not str or not 1 <= len(value) <= 100:
        raise IntakeError("invalid_bulletin_date")
    try:
        if re.match(r"\d{4}-\d\d-\d\dT", value):
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            # CBS uses the explicit RFC822 offset spelling +02:00.
            value = re.sub(r"([+-]\d\d):(\d\d)$", r"\1\2", value.strip())
            stamp = parsedate_to_datetime(value)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        return stamp.astimezone(timezone.utc).timestamp()
    except (ValueError, TypeError, OverflowError):
        raise IntakeError("invalid_bulletin_date") from None


def article_url(value, source):
    if type(value) is not str or not 1 <= len(value) <= 2048 or any(c.isspace() for c in value):
        raise IntakeError("invalid_bulletin_link")
    try:
        u = urlsplit(value)
        if (u.scheme != "https" or u.hostname not in source.article_hosts
                or u.username is not None or u.password is not None or u.port not in (None, 443)
                or u.fragment or "\\" in value):
            raise ValueError
        query = urlencode(sorted((k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")))
        return urlunsplit(("https", u.hostname, u.path or "/", query, ""))
    except ValueError:
        raise IntakeError("invalid_bulletin_link") from None


@dataclass(frozen=True)
class NewsItem:
    source_id: str
    source_title: str
    source_url: str
    guid: str
    title: str
    description: str
    published_at: float
    observed_at: float
    fingerprint: str
    license: str
    monotonic_deadline: float

    def fresh(self, now, *, monotonic=None):
        elapsed = time.monotonic() if monotonic is None else monotonic
        return (self.published_at <= _clock(now) < self.published_at + WINDOW_SECONDS
            and math.isfinite(elapsed) and elapsed < self.monotonic_deadline)


class _SafeTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.nodes = self.depth = 0

    def doctype(self, name, pubid, system):
        raise IntakeError("bulletin_xml_dtd_forbidden")

    def start(self, tag, attrs):
        self.nodes += 1
        self.depth += 1
        if self.nodes > 8000 or self.depth > 24:
            raise IntakeError("bulletin_xml_complexity")
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        return result


def parse_feed(source, body, *, now, monotonic=None):
    """Parse a fixed publisher's metadata, rejecting unknown XML and dates."""
    _clock(now)
    anchor = time.monotonic() if monotonic is None else monotonic
    if type(anchor) not in (int, float) or not math.isfinite(anchor) or anchor < 0:
        raise IntakeError("invalid_bulletin_clock")
    if source not in SOURCES or type(body) is not bytes or len(body) > MAX_BYTES:
        raise IntakeError("invalid_bulletin_feed")
    try:
        root = ET.fromstring(body, parser=ET.XMLParser(target=_SafeTree()))
    except ET.ParseError:
        raise IntakeError("invalid_bulletin_xml") from None
    if root.tag == "rss" and root.find("channel") is not None:
        entries = root.findall("channel/item")
        atom = False
    elif root.tag == ATOM + "feed":
        entries = root.findall(ATOM + "entry")
        atom = True
    else:
        raise IntakeError("invalid_bulletin_feed")
    result, seen = [], set()
    for entry in entries[:MAX_ITEMS]:
        try:
            prefix = ATOM if atom else ""
            title = plain(entry.findtext(prefix + "title"), 240)
            description = plain(entry.findtext(prefix + ("summary" if atom else "description")) or "", 640)
            date = publication_time(entry.findtext(prefix + ("published" if atom else "pubDate")))
            if not date <= now < date + WINDOW_SECONDS or len(title.split()) < 3:
                continue
            if atom:
                links = [e.get("href") for e in entry.findall(ATOM + "link")
                    if e.get("rel", "alternate") == "alternate"]
                link = links[0] if len(links) == 1 else None
            else:
                link = entry.findtext("link")
            link = article_url(link, source)
            guid = entry.findtext(prefix + ("id" if atom else "guid")) or link
            if not 1 <= len(guid) <= 2048:
                continue
            # GUID rotation and tracking URLs never create a fresh story.
            identity = hashlib.sha256(link.encode()).hexdigest()
            if identity in seen:
                continue
            seen.add(identity)
            fingerprint = hashlib.sha256((link + "\n" + title.casefold()).encode()).hexdigest()
            result.append(NewsItem(source.source_id, source.title, link, guid, title,
                description, date, now, fingerprint, source.license,
                anchor + date + WINDOW_SECONDS - now))
        except IntakeError:
            continue
    return tuple(result)


class FeedCollector:
    """Five independent conditional polls; no task, publication or retry loop.

    The lifecycle owner supplies a dedicated no-cookie/no-credential HTTP session
    and calls collect at ordinary technical polling opportunities. Tests inject
    that boundary. Redirects are denied; the fixed KNMI URL is its verified CDN.
    """

    def __init__(self, http, *, monotonic=time.monotonic):
        self.http = http
        self.monotonic = monotonic
        self._state = {}
        self._lock = asyncio.Lock()

    async def collect(self, *, now):
        _clock(now)
        original_monotonic = self.monotonic()
        async with self._lock:
            for source in SOURCES:
                state = self._state.setdefault(source.source_id,
                    {"next": 0, "failures": 0, "etag": "", "modified": "", "items": ()})
                state["items"] = tuple(i for i in state["items"] if i.fresh(now, monotonic=self.monotonic()))
                if now < state["next"]:
                    continue
                state["next"] = now + POLL_SECONDS
                headers = {"Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"}
                for field, name in (("etag", "If-None-Match"), ("modified", "If-Modified-Since")):
                    if state[field]:
                        headers[name] = state[field]
                try:
                    async with asyncio.timeout(8):
                        async with self.http.get(source.url, headers=headers, allow_redirects=False) as response:
                            if response.status == 304:
                                state["failures"] = 0
                                continue  # Keep ORIGINAL observation and publication clocks.
                            if response.status != 200:
                                raise IntakeError("bulletin_feed_http_failure")
                            body = bytearray()
                            async for chunk in response.content.iter_chunked(16384):
                                body.extend(chunk)
                                if len(body) > MAX_BYTES:
                                    raise IntakeError("bulletin_feed_oversized")
                            state["items"] = parse_feed(source, bytes(body), now=now,
                                monotonic=original_monotonic)
                            for field, name in (("etag", "ETag"), ("modified", "Last-Modified")):
                                value = response.headers.get(name, "")
                                state[field] = value if (type(value) is str and len(value) <= 256
                                    and value.isascii() and all(32 <= ord(c) < 127 for c in value)) else ""
                            state["failures"] = 0
                except Exception:  # noqa: BLE001 - contain one publisher; cancellation propagates.
                    state["failures"] = min(4, state["failures"] + 1)
                    state["next"] = now + min(3600, POLL_SECONDS * 2 ** state["failures"])
            return tuple(item for state in self._state.values() for item in state["items"]
                if item.fresh(now, monotonic=self.monotonic()))
