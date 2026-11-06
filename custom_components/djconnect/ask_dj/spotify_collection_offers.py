"""Read-only Spotify collection offers backed by provider evidence."""

import asyncio
import re


def collection_request(text):
    value = " ".join(text.casefold().strip(" ?.").split())
    if re.fullmatch(
        r"heb je (?:een paar|vijf|5) (?:leuke )?(?:spotify[- ]?)?mixes voor me"
        r"|(?:do you have|can you suggest) (?:a few|five|5) (?:good )?(?:spotify )?mixes(?: for me)?",
        value,
    ):
        return ("mix", "")
    match = re.fullmatch(
        r"(?:heb je (?:spotify[- ]?)?(?:playlists|afspeellijsten) (?:van|met)"
        r"|do you have (?:spotify )?playlists (?:with|by|featuring)) (.{1,120})",
        value,
    )
    return ("artist", match[1]) if match else None


async def collection_response(hass, runtime, kind, artist, *, turn):
    from aiohttp import ClientError
    from ..spotify_backend import SpotifyBackend, SpotifyBackendError
    from . import _playlist_search_playback_actions

    async def guard():
        if turn is not None:
            await turn.guard()

    async def read():
        await guard()
        backend = SpotifyBackend(hass, runtime)
        if kind == "mix":
            candidates = await backend.search_playlists("mix", limit=10)
            await guard()
            return [
                item for item in candidates
                if item.get("owner_id") == "spotify"
                and re.search(r"\bmix(?:es)?\b", item.get("title", ""), re.I)
                and re.fullmatch(r"spotify:playlist:[A-Za-z0-9]{22}", item.get("uri", ""))
            ]
        identity = await backend.artist_profile(artist)
        await guard()
        artist_id = identity.get("id")
        if not isinstance(artist_id, str) or not re.fullmatch(r"[A-Za-z0-9]{22}", artist_id):
            return []
        candidates = await backend.search_playlists(artist, limit=10)
        await guard()
        verified = {}
        checked = set()
        for item in candidates:
            uri = item.get("uri", "")
            if uri in checked or not re.fullmatch(r"spotify:playlist:[A-Za-z0-9]{22}", uri):
                continue
            checked.add(uri)
            try:
                found = await backend.playlist_contains_artist(uri, artist_id)
            except SpotifyBackendError as exc:
                if exc.http_status not in {403, 404}:
                    raise
                found = False
            await guard()
            if found:
                verified[uri] = item
                if len(verified) == 5:
                    break
        return list(verified.values())

    try:
        candidates = await asyncio.wait_for(read(), timeout=12)
    except (SpotifyBackendError, ClientError, TimeoutError):
        candidates = []
    await guard()
    actions = _playlist_search_playback_actions(hass, candidates, limit=5)
    language = turn.style.get("language", "en") if turn else "en"
    noun = "mixes" if kind == "mix" else "playlists"
    if language == "nl":
        message = (f"Ik vond {len(actions)} Spotify-{noun}. Kies wat je wilt horen." if actions
                   else f"Ik kon geen Spotify-{noun} voor deze vraag verifiëren.")
    else:
        message = (f"I found {len(actions)} Spotify {noun}. Pick one to play." if actions
                   else f"I couldn't verify any Spotify {noun} for this request.")
    return {"success": True, "text": message, "dj_text": message, "action": "none",
            "images": [], "items": actions, "playback_actions": actions}


async def artist_collections_read(hass, runtime, artist, *, turn):
    """One interpreted name, Core/provider-owned rows, no playback mutation."""
    from aiohttp import ClientError
    from . import run_music_command, _album_search_playback_actions, _playlist_search_playback_actions
    from .dialogue import catalogue_result_text, DialogueError
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError

    await turn.guard()
    if turn.lookup_calls + 1 > 2:
        raise DialogueError("conversation_lookup_budget", 503)
    turn.lookup_calls += 1
    try:
        result = await asyncio.wait_for(run_music_command(hass, runtime, "artist_collections", {"artist": artist}), 12)
    except (SpotifyBackendError, MusicBackendCapabilityError, ClientError, OSError, TimeoutError):
        result = {}
    await turn.guard()
    if not isinstance(result, dict) or result.get("success") is False:
        result = {}
    albums = _album_search_playback_actions(hass, result.get("albums") or [], limit=5)
    playlists = _playlist_search_playback_actions(hass, result.get("playlists") or [], limit=5)
    actions = albums + playlists
    canonical = (result.get("artist") or {}).get("name") or artist
    language = turn.style.get("language", "en")
    copy = {
        "en": ("I found {a} albums and {p} playlists with music by {artist}. Pick one to play.", "I cannot verify albums or playlists by {artist} right now.", "Play"),
        "nl": ("Ik vond {a} albums en {p} playlists met muziek van {artist}. Kies wat je wilt horen.", "Ik kan nu geen albums of playlists van {artist} controleren.", "Afspelen"),
        "de": ("Ich habe {a} Alben und {p} Playlists mit Musik von {artist} gefunden. Wähle etwas zum Abspielen.", "Ich kann gerade keine Alben oder Playlists von {artist} bestätigen.", "Abspielen"),
        "fr": ("J’ai trouvé {a} albums et {p} playlists avec de la musique de {artist}. Choisissez quoi écouter.", "Je ne peux pas vérifier d’albums ou de playlists de {artist} pour le moment.", "Lire"),
        "es": ("Encontré {a} álbumes y {p} playlists con música de {artist}. Elige qué escuchar.", "Ahora no puedo verificar álbumes o playlists de {artist}.", "Reproducir"),
    }
    caption = copy[language][0 if actions else 1].format(a=len(albums), p=len(playlists), artist=canonical)
    for action in actions:
        action.update(label=copy[language][2], button_label=copy[language][2], reason=caption)
    text = catalogue_result_text(actions, language, caption=caption) if actions else caption
    return {"success": True, "text": text, "dj_text": text, "action": "none", "images": [],
            "items": actions, "playback_actions": actions,
            "text_source": "qualified_catalog_result", "is_generated_text": False,
            "knowledge_basis": "qualified_provider_result_fields", "_private_current_context": True,
            "intent": {"category":"informational", "intent":"artist_collections_information"},
            "sources": [{"source":"spotify_artist_collections", "title":"Spotify", "kind":"source"}] if actions else []}
