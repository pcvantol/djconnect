"""Resolve model-proposed performer names through existing catalog read tools."""

from datetime import UTC, datetime
import asyncio
import hashlib
import re

from .dialogue import current_turn, catalogue_result_text, DialogueError


async def artist_tracks_read(hass, runtime, plan, selected):
    from . import run_music_command, _track_recommendation_actions
    from .observations import _identified_playback, selected_artist_names
    from .album_tracks import _target
    from ..session_conversation import SessionConversationError
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError

    turn = current_turn.get()
    artist = plan.artist
    artist_id = ""
    locale = turn.style.get("language", "en")
    observed = None
    identified = None
    started = turn.history.dialogue.clock()
    now = datetime.now(UTC)
    deadline = started + 60

    def validate_expiry():
        if turn.history.dialogue.clock() >= deadline:
            raise DialogueError("playback_observation_expired", 409)

    def bind_expiry(metadata):
        nonlocal deadline
        stamp = (metadata or {}).get("valid_until") or (metadata or {}).get("expires_at")
        if stamp:
            try:
                expiry = datetime.fromisoformat(stamp)
                if expiry.tzinfo is None:
                    raise ValueError("naive_expiry")
                deadline = min(deadline, started + (expiry.astimezone(UTC) - now).total_seconds())
            except (TypeError, ValueError):
                raise DialogueError("playback_observation_expired", 409) from None
        validate_expiry()
        turn.speech_deadline = min(turn.speech_deadline or deadline, deadline)
        turn.replacement_result_deadline = min(turn.replacement_result_deadline or deadline, deadline)

    if plan.reference != "named":
        # Bind once before any context/provider wait. Later reads may shorten,
        # but never renew, the original observation or its frozen offer.
        turn.effect_validators.append(validate_expiry)
        turn.delivery_validators.append(validate_expiry)

    async def read(command, value=None):
        await turn.guard()
        result = await asyncio.wait_for(run_music_command(hass, runtime, command, value),
                                        5 if command == "status" else 12)
        await turn.guard()
        return result if isinstance(result, dict) and result.get("success") is not False else {}

    try:
        if plan.reference != "named":
            observed = selected.get("playback") if selected is not None else (await read("status")).get("playback")
            bind_expiry(observed)
            identified = _identified_playback(observed)
            artist = identified[1] if identified else ""
            if not artist and selected is not None:
                subjects = selected_artist_names(selected)
                artist = subjects[0] if len(subjects) == 1 else ""
            if (selected is None and identified and turn.captured_playback_item_id
                    and hashlib.sha256(identified[0].encode()).hexdigest()[:24] != turn.captured_playback_item_id):
                raise DialogueError("playback_context_changed", 409)
        if not artist:
            catalog = {}
        else:
            if turn.lookup_calls + 2 > 2:
                raise DialogueError("conversation_lookup_budget", 503)
            turn.lookup_calls += 2
            profile = (await read("artist_profile", {"artist": artist})).get("artist", {})
            artist_id = str(profile.get("id") or "")
            canonical = str(profile.get("name") or "")
            if (not re.fullmatch(r"[A-Za-z0-9]{22}", artist_id) or not canonical
                    or profile.get("uri") != "spotify:artist:" + artist_id):
                catalog = {}
            else:
                artist = canonical
                catalog = await read("search_tracks", {"query": 'artist:"' + artist + '"', "limit": 10})
        tracks = catalog.get("tracks", [])
        tracks = [t for t in tracks if isinstance(t, dict)
                  and re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", str(t.get("uri") or ""))
                  and isinstance(t.get("artist_ids"), list) and artist_id in t["artist_ids"]]
        if plan.reference == "current" and identified:
            confirmed = (await read("status")).get("playback")
            bind_expiry(confirmed)
            if _identified_playback(confirmed) != identified:
                raise DialogueError("playback_context_changed", 409)
        omitted = _target(observed or {}) if plan.reference != "named" else None
        if plan.exclude_current and tracks and plan.reference == "named":
            # This optional filter grants no dependency on current playback.
            # A status outage must not discard an independently resolved artist.
            try:
                omitted = _target((await read("status")).get("playback") or {})
            except (SpotifyBackendError, MusicBackendCapabilityError, OSError, TimeoutError):
                omitted = None
        if plan.exclude_current and omitted:
            tracks = [t for t in tracks if t["uri"] != omitted["track_uri"]]
        actions = _track_recommendation_actions(hass, tracks, limit=8, runtime=runtime)
    except (DialogueError, SessionConversationError):
        raise
    except (SpotifyBackendError, MusicBackendCapabilityError, OSError, TimeoutError):
        actions = []
    await turn.guard()
    copy = {
        "en": ("Here are some Spotify recordings by {artist} to explore.", "I cannot verify playable recordings by {artist} right now.", "Play"),
        "nl": ("Hier zijn Spotify-nummers van {artist} om verder te ontdekken.", "Ik kan nu geen afspeelbare nummers van {artist} controleren.", "Afspelen"),
        "de": ("Hier sind Spotify-Aufnahmen von {artist} zum Weiterentdecken.", "Ich kann gerade keine abspielbaren Aufnahmen von {artist} bestätigen.", "Abspielen"),
        "fr": ("Voici des morceaux de {artist} sur Spotify à découvrir.", "Je ne peux pas vérifier de morceaux lisibles de {artist} pour le moment.", "Lire"),
        "es": ("Aquí tienes canciones de {artist} en Spotify para seguir descubriendo.", "Ahora no puedo verificar canciones reproducibles de {artist}.", "Reproducir"),
    }
    caption = copy[locale][0 if actions else 1].format(artist=artist or {
        "en": "this artist", "nl": "deze artiest", "de": "diesem Künstler",
        "fr": "cet artiste", "es": "este artista"}[locale])
    for action in actions:
        action.update(label=copy[locale][2], button_label=copy[locale][2], reason=caption)
    text = catalogue_result_text(actions, locale, caption=caption) if actions else caption
    return {"success": True, "text": text, "dj_text": text, "action": "none", "images": [],
            "items": actions, "playback_actions": actions, "text_source": "qualified_catalog_result",
            "is_generated_text": False, "_private_current_context": True,
            "knowledge_basis": "qualified_provider_result_fields",
            "intent": {"category": "informational", "intent": "artist_tracks_information"},
            "sources": [{"source": "spotify_track_search", "title": "Spotify", "kind": "source"}] if actions else []}
