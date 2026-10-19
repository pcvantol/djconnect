from __future__ import annotations

import re


_MUSIC_COMMAND_PREFIX = re.compile(
    r"^(?:(?:please|alsjeblieft|bitte|por favor|s'il te plaît)\s+)?"
    r"(?:(?:can|could|would) you\s+|(?:kun|wil|zou) je\s+|"
    r"(?:kannst|könntest) du\s+|(?:peux|pourrais)-tu\s+|(?:puedes|podrías)\s+)?"
    r"(?P<verb>put\s+on|speel|start|zet|draai|play|spiel(?:e)?|starte|joue(?:z)?|mets|reproduce|pon)\s+"
    r"(?P<subject>.+)$", re.I)


def music_command_subject(text: str) -> str:
    """Parse a native imperative, preserving its subject; no action authority.

    The Ask DJ speech-act/effect guards still decide whether execution is
    authorized. This is shared parsing, not a catalogue-specific send alias or
    a rewritten prompt to the HA agent.
    """
    match = _MUSIC_COMMAND_PREFIX.fullmatch(str(text or '').strip().rstrip('.!?'))
    return match['subject'].strip() if match else ''


def open_music_request(text: str) -> bool:
    """An indefinite musical/activity subject needs semantic interpretation.

    This is not an effect grant. Quoted proper names and explicit media kinds
    retain the ordinary literal identity fence.
    """
    subject = music_command_subject(text)
    if not subject:
        return False
    if subject[0] in {'"', '“', '„', "'", '‘'}:
        return False
    return bool(re.match(r"^(?:iets|something|some\s+music|music|muziek|etwas|musik|quelque\s+chose|de\s+la\s+musique|algo|m[uú]sica)\b", subject, re.I))


def negated_music_command(text: str) -> bool:
    """Fence native negative imperatives before model/provider work.

    Quoted music names are data, including words like 'not' and 'pas'. Bare
    negative imperatives remain non-executing; a model cannot override them.
    """
    value=str(text or '').strip()
    # Apostrophes inside words (l’album, n’est, Guns N’ Roses) are not quotes.
    value=re.sub(r'''(?<!\w)(?:"[^"\n]*"|“[^”\n]*”|„[^“\n]*“|'[^'\n]*'(?!\w)|‘[^’\n]*’(?!\w))''',
                 'MUSIC_NAME',value)
    leading=re.fullmatch(r"(?:(?:please|bitte|por favor)\s+)?(?:do not|don't|no|ne)\s+(.+)",value,re.I)
    if leading and music_command_subject(leading[1]):
        return True
    match=_MUSIC_COMMAND_PREFIX.fullmatch(value.rstrip('.!?'))
    if not match:
        return False
    verb,subject=match['verb'].casefold(),match['subject'].casefold()
    markers=(r'\b(?:nicht|nichts|kein(?:e|en|em|er|es)?)\b' if verb.startswith(('spiel','starte')) else
             r'\b(?:pas|jamais)\b' if verb.startswith(('joue','mets')) else
             r'\b(?:no|nunca|jamás)\b' if verb in {'reproduce','pon'} else
             r"\b(?:niet|nooit|geen|not|never|don't)\b")
    return bool(re.search(markers,subject))


def _native_media_request(text: str):
    subject = music_command_subject(text)
    if not subject:
        return None
    subject = re.sub(r"^l['’](?=album\b)", '', subject, flags=re.I)
    value = re.sub(r'^(?:the|het|de|een|mijn|my|eine[nmrs]?|das|der|die|den|une?|le|la|les|el|una?|mi)\s+', '', subject, flags=re.I)
    match = re.fullmatch(r'(album|álbum|playlist|afspeellijst|song|track|nummer|lied|chanson|titre|canci[oó]n)\s+(.+)', value, re.I)
    if not match:
        match = re.fullmatch(r'(.+?)\s+(playlist|afspeellijst)', value, re.I)
        if match:
            title = clean_music_query(match[1])
            return _parsed_request('playlist', title, playlist=title)
        return None
    noun, title = match[1].casefold(), clean_music_query(match[2])
    kind = 'playlist' if noun in {'playlist', 'afspeellijst'} else 'album' if noun in {'album','álbum'} else 'track'
    if kind == 'playlist':
        return _parsed_request(kind, title, playlist=title)
    split = re.split(r'\s+(?:van|by|von|de)\s+', title, maxsplit=1, flags=re.I)
    title, artist = split[0], split[1] if len(split) == 2 else ''
    return _parsed_request(kind, _query_with_artist(title, artist), title=title, artist=artist)


_ARTIST_QUERY_PATTERNS = (
    r"^\s*(?:speel|start|zet|draai)\s+(?:eens\s+|even\s+|maar\s+|graag\s+)?(?:artiest|band|artist)\s+(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:artist|band)\s+(.+?)\s*$",
    r"^\s*(?:artiest|band|artist)\s+(.+?)\s*$",
    r"^\s*ik\s+heb\s+(?:wel\s+)?(?:zin|trek)\s+in\s+(.+?)\s*$",
    r"^\s*ik\s+wil\s+(?:wel\s+|graag\s+)?(?:iets|something)\s+van\s+(.+?)\s+(?:horen|luisteren|starten|opzetten|spelen)\s*$",
    r"^\s*i\s+(?:want|would\s+like)\s+(?:something|some)\s+by\s+(.+?)\s*$",
    r"^\s*ik\s+wil\s+(?:wel\s+|graag\s+)?(.+?)\s+(?:horen|luisteren|starten|opzetten|spelen)\s*$",
    r"^\s*(.+?)\s+wil\s+ik\s+(?:wel\s+|graag\s+)?(?:horen|luisteren|starten|opzetten|spelen)\s*$",
    r"^\s*(?:zet|speel|start|draai)\s+(?:eens\s+|even\s+|maar\s+|graag\s+)?(?:af\s+|op\s+|aan\s+)?(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(.+?)\s*$",
    r"^\s*i\s+(?:feel\s+like|want\s+to\s+hear|want)\s+(.+?)\s*$",
)

_LIKED_QUERY_PATTERNS = (
    r"^\s*(?:speel|start|zet|draai)\s+(?:mijn\s+)?(?:standaard\s+playlist|favorieten|liked\s+songs)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:play|start)\s+(?:my\s+)?(?:default\s+playlist|liked\s+songs|favorites)\s*$",
)

_PLAYLIST_QUERY_PATTERNS = (
    r"^\s*(?:speel|start|zet|draai)\s+(?:mijn\s+)?(?:playlist|afspeellijst)\s+(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:speel|start|zet|draai)\s+(.+?)\s+(?:playlist|afspeellijst)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:my\s+)?playlist\s+(.+?)\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(.+?)\s+playlist\s*$",
)

_TRACK_WORDS = r"(?:nummer|liedje|track|song|kraker|monsterhit|hit|vette\s+track|dikke\s+knaller|knaller|beuker)"
_SLANG_ARTIST_TRACK_WORDS = r"(?:kraker|monsterhit|hit|vette\s+track|dikke\s+knaller|knaller|beuker)"

_SLANG_ARTIST_QUERY_PATTERNS = (
    rf"^\s*(?:speel|start|zet|draai)\s+(?:eens\s+|even\s+|maar\s+|graag\s+)?(?:een\s+|de\s+)?{_SLANG_ARTIST_TRACK_WORDS}\s+van\s+(.+?)\s*(?:op|af|aan)?\s*$",
    rf"^\s*(?:een\s+|de\s+)?{_SLANG_ARTIST_TRACK_WORDS}\s+van\s+(.+?)\s*$",
)

_TRACK_QUERY_PATTERNS = (
    rf"^\s*ik\s+wil\s+(?:wel\s+|graag\s+)?(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s+(?:horen|luisteren|starten|opzetten|spelen)\s*$",
    rf"^\s*(?:speel|start|zet|draai)\s+(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s+van\s+(?:artiest|band)\s+(.+?)\s*(?:op|af|aan)?\s*$",
    rf"^\s*(?:speel|start|zet|draai)\s+(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s+van\s+(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:speel|start|zet|draai)\s+(.+?)\s+van\s+(.+?)\s*(?:op|af|aan)?\s*$",
    rf"^\s*(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s+van\s+(?:artiest|band)\s+(.+?)\s*$",
    rf"^\s*(?:speel|start|zet|draai)\s+(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s*(?:op|af|aan)?\s*$",
    rf"^\s*(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s+van\s+(.+?)\s*$",
    rf"^\s*(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:the\s+)?(?:song|track)\s+(.+?)\s+by\s+(.+?)\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:the\s+)?(?:song|track)\s+(.+?)\s*$",
    r"^\s*(?:the\s+)?(?:song|track)\s+(.+?)\s+by\s+(.+?)\s*$",
    r"^\s*(?:the\s+)?(?:song|track)\s+(.+?)\s*$",
)

_ARTIST_WITH_TRACK_QUERY_PATTERNS = (
    r"^\s*(?:speel|start|zet|draai)\s+(.+?)\s*[,;:–-]\s*(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(.+?)\s*[,;:–-]\s*(.+?)\s*$",
    rf"^\s*(?:speel|start|zet|draai)\s+(?:artiest|band)\s+(.+?)\s+met\s+(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s*(?:op|af|aan)?\s*$",
    rf"^\s*(?:artiest|band)\s+(.+?)\s+met\s+(?:het\s+|de\s+|die\s+)?{_TRACK_WORDS}\s+(.+?)\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:artist|band)\s+(.+?)\s+with\s+(?:the\s+)?(?:song|track)\s+(.+?)\s*$",
    r"^\s*(?:artist|band)\s+(.+?)\s+with\s+(?:the\s+)?(?:song|track)\s+(.+?)\s*$",
)

_ARTIST_WITH_ALBUM_QUERY_PATTERNS = (
    r"^\s*(?:speel|start|zet|draai)\s+(?!(?:het|de|een|album|plaat)\b)(.+?)\s+(?:album|plaat)\s+(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:artiest|band)\s+(.+?)\s+(?:album|plaat)\s+(.+?)\s*$",
    r"^\s*(?:play|put\s+on)\s+(?!(?:the|a|an|album|record)\b)(.+?)\s+(?:album|record)\s+(.+?)\s*$",
)

_ALBUM_QUERY_PATTERNS = (
    r"^\s*(?:speel|start|zet|draai)\s+(?:het\s+)?(?:album|de\s+plaat)\s+(.+?)\s+van\s+(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:speel|start|zet|draai)\s+(?:het\s+)?(?:album|de\s+plaat)\s+(.+?)\s*(?:op|af|aan)?\s*$",
    r"^\s*(?:het\s+)?(?:album|de\s+plaat)\s+(.+?)\s+van\s+(.+?)\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:the\s+)?album\s+(.+?)\s+by\s+(.+?)\s*$",
    r"^\s*(?:play|start|put\s+on)\s+(?:the\s+)?album\s+(.+?)\s*$",
    r"^\s*(?:the\s+)?album\s+(.+?)\s+by\s+(.+?)\s*$",
    r"^\s*(?:the\s+)?album\s+(.+?)\s*$",
    r"^\s*(?:het\s+)?(?:album|de\s+plaat)\s+(.+?)\s*$",
)



def listening_request_target(text: str) -> str:
    """An explicit positive listening request, not a question about music."""
    value = str(text or "").strip().strip(".!?")
    patterns = (
        r"ik\s+wil\s+(?:graag\s+|wel\s+)?(.+?)\s+(?:horen|beluisteren|luisteren)",
        r"i\s+(?:want|would\s+like)\s+to\s+(?:hear|listen\s+to)\s+(.+)",
        r"ich\s+(?:möchte|will)\s+(.+?)\s+hören",
        r"je\s+(?:veux|voudrais)\s+écouter\s+(.+)",
        r"(?:yo\s+)?quiero\s+escuchar\s+(.+)",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, value, re.I)
        if match:
            target = re.sub(r"^(?:iets van|something by|something from|some by)\s+", "", match[1].strip(), flags=re.I)
            explicit_kind = re.match(r"^(?:(?:the|het|de|my|mijn)\s+)?(?:album|playlist|afspeellijst|track|song|nummer)\b", target, re.I)
            if not explicit_kind and re.search(r"\b(?:muziek|music|musik|musique|música|iets|something|etwas|quelque|algo)\b", target, re.I):
                return ""
            if (0 < len(target) <= 160
                    and not re.search(r"[\n\r{}<>]|https?://|spotify:", target, re.I)
                    and not re.search(r"\b(?:niet|nooit|not|never|nicht|nichts|pas|jamais|no|nunca|about|over|über|sobre)\b", target, re.I)):
                return target
    return ""

def parse_spoken_music_request(text: str) -> dict[str, str | None]:
    """Parse a spoken DJConnect music request into a Spotify search target."""
    query = clean_music_query(text)
    if not query:
        return _parsed_request("artist", "")
    for pattern in _LIKED_QUERY_PATTERNS:
        if re.match(pattern, query, flags=re.IGNORECASE):
            return _parsed_request("liked", query)
    playlist = _match_single_value(_PLAYLIST_QUERY_PATTERNS, query)
    if playlist:
        return _parsed_request("playlist", playlist, playlist=playlist)
    artist_track = _match_artist_title(_ARTIST_WITH_TRACK_QUERY_PATTERNS, query)
    if artist_track:
        artist, title = artist_track
        return _parsed_request("track", _query_with_artist(title, artist), title=title, artist=artist)
    slang_artist = _match_single_value(_SLANG_ARTIST_QUERY_PATTERNS, query)
    if slang_artist:
        return _parsed_request("artist", slang_artist, artist=slang_artist)
    artist_album = _match_artist_title(_ARTIST_WITH_ALBUM_QUERY_PATTERNS, query)
    if artist_album:
        artist, title = artist_album
        return _parsed_request("album", _query_with_artist(title, artist), title=title, artist=artist)
    album = _match_title_artist(_ALBUM_QUERY_PATTERNS, query)
    if album:
        title, artist = album
        return _parsed_request("album", _query_with_artist(title, artist), title=title, artist=artist)
    track = _match_title_artist(_TRACK_QUERY_PATTERNS, query)
    if track:
        title, artist = track
        return _parsed_request("track", _query_with_artist(title, artist), title=title, artist=artist)
    if native := _native_media_request(text):
        return native
    if (target := listening_request_target(text)):
        return parse_spoken_music_request("play " + target)
    artist = extract_artist_query(query)
    return _parsed_request("artist", artist, artist=artist)


def _parsed_request(
    media_type: str,
    query: str,
    *,
    artist: str | None = None,
    title: str | None = None,
    playlist: str | None = None,
) -> dict[str, str | None]:
    return {
        "type": media_type,
        "query": query,
        "artist": artist,
        "title": title,
        "playlist": playlist,
    }


def _query_with_artist(title: str, artist: str) -> str:
    return f"{title} {artist}".strip() if artist else title


def _match_single_value(patterns: tuple[str, ...], query: str) -> str:
    for pattern in patterns:
        match = re.match(pattern, query, flags=re.IGNORECASE)
        if match:
            candidate = clean_music_query(match.group(1))
            if candidate:
                return candidate
    return ""


def _match_title_artist(patterns: tuple[str, ...], query: str) -> tuple[str, str] | None:
    for pattern in patterns:
        match = re.match(pattern, query, flags=re.IGNORECASE)
        if not match:
            continue
        title = clean_music_query(match.group(1))
        artist = clean_music_query(match.group(2)) if len(match.groups()) > 1 else ""
        if title:
            return title, artist
    return None


def _match_artist_title(patterns: tuple[str, ...], query: str) -> tuple[str, str] | None:
    for pattern in patterns:
        match = re.match(pattern, query, flags=re.IGNORECASE)
        if not match:
            continue
        artist = clean_music_query(match.group(1))
        title = clean_music_query(match.group(2)) if len(match.groups()) > 1 else ""
        if artist and title:
            return artist, title
    return None


def extract_artist_query(text: str) -> str:
    """Extract the likely artist from a spoken music request."""
    query = clean_music_query(text)
    for pattern in _ARTIST_QUERY_PATTERNS:
        match = re.match(pattern, query, flags=re.IGNORECASE)
        if match:
            candidate = clean_music_query(match.group(1))
            if candidate:
                return candidate
    if subject := music_command_subject(query):
        return subject
    return query


def clean_music_query(text: str) -> str:
    value = " ".join(str(text or "").strip().split())
    value = re.sub(r"[.!?]+$", "", value).strip()
    return value.strip(" \"'")
