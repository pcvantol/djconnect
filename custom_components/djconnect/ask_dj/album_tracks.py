"""Contextual album listing through the existing owner, backend and history."""

from datetime import UTC, datetime, timedelta
import asyncio
import hashlib
import re

from .dialogue import current_turn, DialogueError
from .observations import language, _identified_playback

COPY = {
    "en": (
        "Here is more from {album}:",
        "Here are the tracks on {album}:",
        "This is the available part of the album track list.",
        "I cannot reliably identify the album from the available music context.",
        "I cannot read this album’s tracks right now. Please try again.",
        "Your configured music service does not support reading album tracks.",
        "There are no other tracks in this catalog result.",
    ),
    "nl": (
        "Op {album} vind je verder:",
        "Deze nummers staan op {album}:",
        "Dit is het beschikbare deel van de tracklijst.",
        "Ik kan het album niet betrouwbaar vaststellen uit de beschikbare muziekcontext.",
        "Ik kan de nummers van dit album nu niet ophalen. Probeer het opnieuw.",
        "Je ingestelde muziekdienst ondersteunt het opvragen van albumnummers niet.",
        "Dit catalogusresultaat bevat geen andere nummers.",
    ),
    "de": (
        "Auf {album} findest du außerdem:",
        "Diese Titel stehen auf {album}:",
        "Dies ist der verfügbare Teil der Titelliste.",
        "Ich kann das Album aus dem verfügbaren Musikkontext nicht zuverlässig bestimmen.",
        "Ich kann die Titel dieses Albums gerade nicht abrufen. Versuche es erneut.",
        "Dein eingestellter Musikdienst unterstützt das Abrufen von Albumtiteln nicht.",
        "Dieses Katalogergebnis enthält keine weiteren Titel.",
    ),
    "fr": (
        "Voici les autres morceaux de {album} :",
        "Voici les morceaux de {album} :",
        "Voici la partie disponible de la liste des morceaux.",
        "Je ne peux pas identifier l’album de façon fiable dans le contexte musical disponible.",
        "Je ne peux pas récupérer les morceaux de cet album pour le moment. Réessaie.",
        "Ton service musical configuré ne permet pas de consulter les morceaux des albums.",
        "Ce résultat du catalogue ne contient aucun autre morceau.",
    ),
    "es": (
        "En {album} también encontrarás:",
        "Estas canciones están en {album}:",
        "Esta es la parte disponible de la lista de canciones.",
        "No puedo identificar el álbum con fiabilidad en el contexto musical disponible.",
        "No puedo consultar las canciones de este álbum ahora. Inténtalo de nuevo.",
        "Tu servicio musical configurado no permite consultar las canciones de los álbumes.",
        "Este resultado del catálogo no contiene más canciones.",
    ),
}

PLAY_LABELS = {
    'en': ('Play album', 'Play'), 'nl': ('Speel album', 'Afspelen'),
    'de': ('Album abspielen', 'Abspielen'), 'fr': ('Lire l’album', 'Lire'),
    'es': ('Reproducir álbum', 'Reproducir'),
}


def playable_rows(hass, catalog, tracks, locale):
    """One exact edition header and its tracks, using the existing choice owner."""
    from .responses import register_image_proxy_url

    image = catalog.get('album_image_url') or ''
    image = register_image_proxy_url(hass, image) if image.startswith(('https://', 'http://')) else ''
    album_label, track_label = PLAY_LABELS[locale]
    album = {'id': catalog['album_uri'], 'uri': catalog['album_uri'],
        'context_uri': catalog['album_uri'], 'kind': 'album', 'title': catalog['album_name'],
        'artist': catalog.get('album_artist') or '', 'subtitle': catalog.get('album_artist') or '',
        'label': album_label, 'button_label': album_label, 'action_style': 'play_now',
        'image_url': image}
    rows = [album]
    for track in tracks:
        rows.append({**track, 'kind': 'track', 'id': track.get('id') or track['uri'],
            'subtitle': track.get('artist') or '', 'image_url': image,
            'label': track_label, 'button_label': track_label, 'action_style': 'play_now'})
    return rows


def album_tracks_question(text):
    value = " ".join(text.casefold().strip(" ¿¡?.!").split())
    patterns = (
        r"(?:welke|wat voor) (?:andere |overige )?(?:nummers|liedjes|tracks) (?:(?:staan|zitten)(?: er)?(?: nog meer)? (?:op|in)|bevat|heeft) (?:dit|dat|het huidige|deze) album",
        r"(?:what|which) (?:other |more )?(?:songs|tracks) (?:are|appear)(?: there)? (?:on|in) (?:this|that|the current) album",
        r"what are (?:the |all the )?(?:songs|tracks) on (?:this|that|the current) album",
        r"welche (?:anderen |weiteren )?(?:lieder|titel|tracks|songs) sind auf (?:diesem|dem aktuellen) album",
        r"quels (?:autres )?(?:morceaux|titres) (?:sont|figurent) (?:sur|dans) (?:cet|ce) album",
        r"qué (?:otras )?(?:canciones|temas) hay en (?:este|ese) álbum",
        r"(?:toon|geef|laat zien|list|show|zeige|liste|montre|muestra) "
        r"(?:(?:de|the|all|all the|die|alle|les|las|los) )?"
        r"(?:nummers|liedjes|tracks|songs|tracklist|tracklijst|titel|lieder|titres|morceaux|chansons|canciones|temas) "
        r"(?:van|op|from|on|of|auf|von|de|sur|en|del) "
        r"(?:dit|dat|deze|huidige|this|that|current|diesem|dieses|dieser|aktuellen|cet|ce|este|ese|actual) [aá]lbum",
    )
    return any(re.fullmatch(pattern, value) for pattern in patterns)


def _target(metadata):
    if not isinstance(metadata, dict):
        return None
    if not _identified_playback(metadata):
        return None
    recording = metadata.get("uri") or metadata.get("track_uri")
    if not recording:
        match = re.fullmatch(
            r"https://open\.spotify\.com/track/([A-Za-z0-9]{22})",
            str(metadata.get("source_url") or ""),
        )
        if match:
            proposed = "spotify:track:" + match[1]
            if metadata.get("item_id") == hashlib.sha256(proposed.encode()).hexdigest()[:24]:
                recording = proposed
    album = metadata.get("album_uri")
    if isinstance(metadata.get("album"), dict):
        album = album or metadata["album"].get("uri")
    if not isinstance(recording, str) or not re.fullmatch(
        r"spotify:track:[A-Za-z0-9]{22}", recording
    ):
        return None
    if album and (
        not isinstance(album, str) or not re.fullmatch(r"spotify:album:[A-Za-z0-9]{22}", album)
    ):
        return None
    return {"track_uri": recording, **({"album_uri": album} if album else {})}


async def album_tracks_read(hass, runtime, text, selected=None, *, exclude_current=None):
    from . import run_music_command
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError

    turn = current_turn.get()
    copy = COPY[language()]
    other = exclude_current if exclude_current is not None else bool(
        re.search(
            r"\b(?:nog meer|andere|other|more|anderen|andere|autres|otras|otros|más)\b",
            text.casefold(),
        )
    )
    now = datetime.now(UTC)
    clock_started = turn.history.dialogue.clock() if turn else None
    deadline = clock_started + 60 if turn else None
    valid_until = now + timedelta(seconds=60)

    def validate_deadline():
        if turn and turn.history.dialogue.clock() >= deadline:
            raise DialogueError("playback_observation_expired", 409)

    if turn:
        turn.delivery_validators.append(validate_deadline)
        if selected is None:
            from ..session_runtime import session_runtime_manager

            manager = session_runtime_manager(hass)
            owner = turn.scope.removeprefix("profile:")
            active = manager.current_active(owner)
            if active:
                session_id, item_id = active.session_id, active.broadcast.state.playback.item_id

                def validate_current():
                    current = manager.current_active(owner)
                    if (
                        current is None
                        or current.session_id != session_id
                        or current.broadcast.state.playback.item_id != item_id
                    ):
                        raise DialogueError("session_context_changed", 409)

                turn.delivery_validators.append(validate_current)

    async def guard():
        if turn:
            await turn.guard()
            for validate in turn.delivery_validators:
                validate()

    def bind_expiry(metadata):
        nonlocal deadline, valid_until
        if not turn:
            return
        stamp = metadata.get("valid_until") or metadata.get("expires_at")
        if stamp:
            try:
                expiry = datetime.fromisoformat(stamp)
                if expiry.tzinfo is None:
                    raise ValueError("naive_expiry")
                valid_until = min(valid_until, expiry.astimezone(UTC))
                deadline = min(deadline, clock_started + (valid_until - now).total_seconds())
            except (ValueError, TypeError):
                raise DialogueError("playback_observation_expired", 409) from None
        validate_deadline()

    async def fresh():
        await guard()
        result = await asyncio.wait_for(run_music_command(hass, runtime, "status"), 5)
        await guard()
        metadata = (
            result.get("playback")
            if isinstance(result, dict) and result.get("success") is not False
            else {}
        )
        if not isinstance(metadata, dict):
            metadata = {}
        bind_expiry(metadata)
        return metadata

    observation = {
        "schema_version": 1,
        "state": "unknown",
        "album_uri": None,
        "current_track_omitted": False,
        "returned_count": 0,
        "as_of": now.isoformat(),
        "valid_until": (now + timedelta(seconds=60)).isoformat(),
    }
    message, items, sources = copy[3], [], []
    try:
        metadata = (selected.get("playback") or {}) if selected is not None else await fresh()
        bind_expiry(metadata)
        target = _target(metadata)
        if target:
            if (
                selected is None
                and turn
                and turn.captured_playback_item_id
                and hashlib.sha256(target["track_uri"].encode()).hexdigest()[:24]
                != turn.captured_playback_item_id
            ):
                raise DialogueError("playback_context_changed", 409)
            await guard()
            catalog = await asyncio.wait_for(
                run_music_command(hass, runtime, "album_tracks", target, play=False), 12
            )
            await guard()
            if selected is None and _target(await fresh()) != target:
                raise DialogueError("playback_context_changed", 409)
            if (
                not isinstance(catalog, dict)
                or catalog.get("success") is False
                or catalog.get("state") not in {"complete", "partial"}
                or not isinstance(catalog.get("items"), list)
            ):
                raise SpotifyBackendError("Album catalog unavailable")
            album = catalog["album_uri"]
            if target.get("album_uri") and target["album_uri"] != album:
                raise SpotifyBackendError("Album catalog changed")
            omitted = other and any(i.get("uri") == target["track_uri"] for i in catalog["items"])
            items = [
                i for i in catalog["items"][:50] if not other or i.get("uri") != target["track_uri"]
            ]
            state = catalog["state"]
            if state == "complete" and not items:
                state = "known_empty"
            observation.update(
                state=state,
                album_uri=album,
                current_track_omitted=omitted,
                returned_count=len(items),
            )
            message = copy[0 if other else 1].format(album=catalog["album_name"])
            if state == "partial":
                message += "\n" + copy[2]
            elif state == "known_empty":
                message += "\n" + copy[6]
            sources = [
                {
                    "source": "spotify_album_catalog",
                    "title": "Spotify",
                    "kind": "source",
                    "url": "https://open.spotify.com/album/" + album.rsplit(":", 1)[-1],
                }
            ]
            items = playable_rows(hass, catalog, items, language())
    except MusicBackendCapabilityError:
        observation["state"], message = "unsupported", copy[5]
    except (SpotifyBackendError, ConnectionError, OSError, TimeoutError):
        observation["state"], message = "unavailable", copy[4]
    await guard()
    if turn:
        turn.speech_deadline = min(turn.speech_deadline or deadline, deadline)
        observation["valid_until"] = valid_until.isoformat()
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "none",
        "intent": {"category": "informational", "intent": "album_tracks_information"},
        "items": items,
        "playback_actions": items,
        "sources": sources,
        "links": sources,
        "images": [],
        "text_source": "qualified_catalog_result",
        "is_generated_text": False,
        "_album_track_choices": bool(items),
        "album_track_observation": observation,
        "_private_current_context": True,
        "speech_processing_basis": "accepted_local_reply",
    }
