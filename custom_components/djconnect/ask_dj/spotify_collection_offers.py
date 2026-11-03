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
