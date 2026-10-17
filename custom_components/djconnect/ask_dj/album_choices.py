"""Qualified alternative albums use the existing frozen result/selection owner."""

import re

from .dialogue import current_turn


def other_album_request(text):
    patterns = (
        r"(?:heb je|ken je|kun je (?:me|mij) (?:een|nog een))\s+(?:nog\s+)?(?:een\s+)?ander\s+album\s+van\s+(.+?)(?:\s+aanraden)?",
        r"(?:do you have|can you (?:suggest|recommend)|have you got)\s+(?:another|a different)\s+album\s+(?:by|from)\s+(.+?)",
        r"(?:hast du|kennst du|empfiehl mir)\s+(?:ein\s+)?anderes\s+album\s+von\s+(.+?)",
        r"(?:as-tu|connais-tu|recommande-moi)\s+un autre\s+album\s+de\s+(.+?)",
        r"(?:tienes|conoces|recomiéndame)\s+otro\s+álbum\s+de\s+(.+?)",
    )
    value = text.strip().lstrip("¿").rstrip(" .?!")
    for pattern in patterns:
        match = re.fullmatch(pattern, value, re.I)
        if match and 0 < len(match[1]) <= 256:
            from . import _clean_artist_item_name

            artist = _clean_artist_item_name(match[1])
            if artist:
                return {"item_type": "album", "artist": artist, "count": 1, "exclude_current": True}
    return None


async def other_album_response(hass, runtime, artist):
    from . import run_music_command, _spotify_artist_albums, _artist_album_playback_action
    from .dialogue import catalogue_result_text
    from .observations import _identified_playback

    turn = current_turn.get()

    async def guard():
        if turn:
            await turn.guard()

    await guard()
    status = await run_music_command(hass, runtime, "status")
    await guard()
    playback = (
        status.get("playback")
        if isinstance(status, dict) and status.get("success") is not False
        else {}
    )
    current_album = playback.get("album_uri") if _identified_playback(playback) else None
    if isinstance(playback.get("album"), dict):
        current_album = current_album or playback["album"].get("uri")
    catalog = await _spotify_artist_albums(hass, runtime, artist)
    await guard()
    albums = []
    if (
        isinstance(catalog, dict)
        and str(catalog.get("artist") or "").casefold() == artist.casefold()
    ):
        albums = [
            album
            for album in catalog.get("albums", [])
            if isinstance(album, dict)
            and re.fullmatch(r"spotify:album:[A-Za-z0-9]{22}", str(album.get("uri") or ""))
            and album.get("uri") != current_album
            and str(album.get("artist") or "").casefold() == artist.casefold()
        ]
    action = _artist_album_playback_action(hass, artist, albums[0]) if albums else None
    actions = [action] if action else []
    locale = turn.style.get("language", "en") if turn else "en"
    copy = {
        "en": (
            "Here is another album by {artist}. Choose Play to hear the whole album.",
            "I cannot find another playable album by {artist} right now.",
        ),
        "nl": (
            "Hier is een ander album van {artist}. Met Afspelen hoor je het hele album.",
            "Ik vind nu geen ander afspeelbaar album van {artist}.",
        ),
        "de": (
            "Hier ist ein anderes Album von {artist}. Mit Abspielen hörst du das ganze Album.",
            "Ich finde gerade kein anderes abspielbares Album von {artist}.",
        ),
        "fr": (
            "Voici un autre album de {artist}. Choisis Lire pour écouter l’album entier.",
            "Je ne trouve pas d’autre album lisible de {artist} pour le moment.",
        ),
        "es": (
            "Aquí tienes otro álbum de {artist}. Elige Reproducir para escuchar el álbum completo.",
            "Ahora no encuentro otro álbum reproducible de {artist}.",
        ),
    }
    caption = copy[locale][0 if actions else 1].format(artist=artist)
    message = catalogue_result_text(actions, locale, caption=caption) if actions else caption
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "items": actions,
        "playback_actions": actions,
        "images": [],
        "text_source": "qualified_catalog_result",
        "is_generated_text": False,
        "_catalogue_history_caption": caption,
        "sources": [{"source": "spotify_artist_albums", "title": "Spotify", "kind": "source"}],
    }
