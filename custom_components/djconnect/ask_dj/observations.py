"""Private read/presentation lens over existing queue, Forecast and history owners.

No Planner, cache, model input, playback mutation or independent conversation.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re

from .dialogue import current_turn, DialogueError, valid_uri

COPY = {
    "en": {"queue": "Currently reported queue:", "known_empty": "The queue read succeeded and contains no upcoming items.", "unavailable": "I could not read the queue right now; I cannot tell whether it is empty.", "unsupported": "This backend does not support reading its queue.", "partial": "This is the available part of the reported queue.", "stale": "The available queue observation has expired.", "withdrawn": "Access to this queue observation has been withdrawn.", "not_requested": "The queue has not been read.", "play": "Play Now", "reason": "Reported queue item; viewing does not play it.", "order": "This is observed queue order, not a guarantee of what will play next.", "no_session": "There is no active DJ-session preview; I can report the queue.", "no_forecast": "A current DJ-session preview is not available.", "saved": "Last saved observation", "previous": "Last recorded different track", "unknown": "I do not have a qualified previous-track observation.", "coverage": "These are recorded observations, not an exact record of every playback instance."},
    "nl": {"queue": "Actueel gemelde wachtrij:", "known_empty": "De wachtrij is succesvol gelezen en bevat geen volgende items.", "unavailable": "Ik kan de wachtrij nu niet lezen; ik weet daardoor niet of hij leeg is.", "unsupported": "Deze muziekbackend ondersteunt het lezen van de wachtrij niet.", "partial": "Dit is het beschikbare deel van de gemelde wachtrij.", "stale": "De beschikbare wachtrijwaarneming is verlopen.", "withdrawn": "De toegang tot deze wachtrijwaarneming is ingetrokken.", "not_requested": "De wachtrij is nog niet opgevraagd.", "play": "Afspelen", "reason": "Gemeld wachtrij-item; bekijken speelt niets af.", "order": "Dit is de waargenomen wachtrijvolgorde, geen garantie voor wat hierna speelt.", "no_session": "Er is geen actieve DJ-sessievooruitblik; ik kan wel de wachtrij tonen.", "no_forecast": "Een actuele vooruitblik van de DJ-sessie is niet beschikbaar.", "saved": "Laatste opgeslagen waarneming", "previous": "Laatst vastgelegde andere track", "unknown": "Ik heb geen gekwalificeerde waarneming van een vorige track.", "coverage": "Dit zijn vastgelegde waarnemingen, geen exacte registratie van iedere afspeelbeurt."},
    "de": {"queue": "Aktuell gemeldete Warteschlange:", "known_empty": "Die Warteschlange wurde erfolgreich gelesen und enthält keine kommenden Einträge.", "unavailable": "Ich kann die Warteschlange gerade nicht lesen; ob sie leer ist, weiß ich daher nicht.", "unsupported": "Dieses Musik-Backend unterstützt das Lesen der Warteschlange nicht.", "partial": "Dies ist der verfügbare Teil der gemeldeten Warteschlange.", "stale": "Die verfügbare Beobachtung der Warteschlange ist abgelaufen.", "withdrawn": "Der Zugriff auf diese Beobachtung wurde entzogen.", "not_requested": "Die Warteschlange wurde noch nicht abgefragt.", "play": "Abspielen", "reason": "Gemeldeter Warteschlangeneintrag; Anzeigen startet keine Wiedergabe.", "order": "Dies ist die beobachtete Reihenfolge, keine Garantie für die folgende Wiedergabe.", "no_session": "Es gibt keinen aktiven DJ-Sitzungsausblick; ich kann die Warteschlange anzeigen.", "no_forecast": "Ein aktueller DJ-Sitzungsausblick ist nicht verfügbar.", "saved": "Letzte gespeicherte Beobachtung", "previous": "Zuletzt erfasster anderer Titel", "unknown": "Eine qualifizierte Beobachtung eines vorherigen Titels fehlt.", "coverage": "Dies sind erfasste Beobachtungen, keine genaue Aufzeichnung jedes Abspielvorgangs."},
    "fr": {"queue": "File d’attente actuellement signalée :", "known_empty": "La file a été lue avec succès et ne contient aucun élément à venir.", "unavailable": "Je ne peux pas lire la file pour le moment ; je ne sais donc pas si elle est vide.", "unsupported": "Ce service musical ne permet pas de lire sa file d’attente.", "partial": "Voici la partie disponible de la file signalée.", "stale": "L’observation disponible de la file a expiré.", "withdrawn": "L’accès à cette observation a été retiré.", "not_requested": "La file n’a pas encore été consultée.", "play": "Lire", "reason": "Élément signalé de la file ; l’afficher ne lance aucune lecture.", "order": "Cet ordre est observé, sans garantie sur la prochaine lecture.", "no_session": "Aucun aperçu de session DJ active n’est disponible ; je peux montrer la file.", "no_forecast": "Un aperçu actuel de la session DJ n’est pas disponible.", "saved": "Dernière observation sauvegardée", "previous": "Dernier autre morceau enregistré", "unknown": "Je n’ai pas d’observation qualifiée d’un morceau précédent.", "coverage": "Ce sont des observations enregistrées, pas un relevé exact de chaque lecture."},
    "es": {"queue": "Cola comunicada actualmente:", "known_empty": "La cola se ha leído correctamente y no contiene elementos próximos.", "unavailable": "No puedo leer la cola ahora; por eso no sé si está vacía.", "unsupported": "Este servicio musical no permite leer su cola.", "partial": "Esta es la parte disponible de la cola comunicada.", "stale": "La observación disponible de la cola ha caducado.", "withdrawn": "Se ha retirado el acceso a esta observación.", "not_requested": "La cola todavía no se ha consultado.", "play": "Reproducir", "reason": "Elemento comunicado de la cola; mostrarlo no inicia la reproducción.", "order": "Este es el orden observado, no una garantía de lo que sonará después.", "no_session": "No hay un avance de sesión DJ activa; puedo mostrar la cola.", "no_forecast": "No hay un avance actual de la sesión DJ disponible.", "saved": "Última observación guardada", "previous": "Última otra canción registrada", "unknown": "No tengo una observación cualificada de una canción anterior.", "coverage": "Son observaciones registradas, no un registro exacto de cada reproducción."},
}


RECORDING_UNAVAILABLE = {
    "en": "I cannot reliably identify the recording from the authorized music context.",
    "nl": "Ik kan de opname niet betrouwbaar vaststellen uit de beschikbare muziekcontext.",
    "de": "Ich kann die Aufnahme im verfügbaren Musikkontext nicht zuverlässig bestimmen.",
    "fr": "Je ne peux pas identifier cette version de façon fiable dans le contexte musical disponible.",
    "es": "No puedo identificar con fiabilidad la grabación en el contexto musical disponible.",
}


def forecast_question(text):
    value = text.casefold().strip()
    return bool(re.search(r"\b(?:kwartier|komende vijftien|volgende 15|next (?:fifteen|15) minutes|quarter hour|nächsten (?:fünfzehn|15) minuten|viertelstunde|prochain (?:quart d'heure|quart d’heure)|prochaines (?:quinze|15) minutes|próximos (?:quince|15) minutos|próximo cuarto de hora)\b", value)
                or re.match(r"^(?:(?:toon|open|show|zeige|montre|muestra)\s+(?:(?:de|the|den|le|el)\s+)?)?(?:vooruitblik|session forecast|ausblick|aperçu|avance)(?:[?.!]|$)", value))


def previous_question(text):
    value = text.casefold().strip().lstrip("¿")
    return bool(re.match(r"^(?:wat|welk\w*|what|which|was|welch\w*|quel\w*|qu[eé]|cu[aá]l)\b", value)
                and re.search(r"\b(?:vorige?|previous|vorherige\w*|précédent\w*|anterior)\b", value)
                and re.search(r"\b(?:nummer|track|song|lied|titel|morceau|chanson|canción|tema)\b", value))


def language():
    turn = current_turn.get()
    return turn.style.get("language", "en") if turn else "en"


async def queue_read(hass, runtime):
    from . import run_music_command, _queue_playback_action
    from ..use_cases import MusicBackendCapabilityError
    from ..spotify_backend import SpotifyBackendError
    turn = current_turn.get()
    if turn:
        await turn.guard()
    now = datetime.now(UTC)
    observation = {"schema_version": 1, "state": "unavailable", "as_of": now.isoformat(),
                   "valid_until": (now + timedelta(seconds=60)).isoformat(), "coverage": "bounded_provider_snapshot"}
    if turn:
        observation["owner_profile_id"] = turn.scope.removeprefix("profile:")
    try:
        result = await run_music_command(hass, runtime, "queue")
    except MusicBackendCapabilityError:
        observation["state"] = "unsupported"
        result = {}
    except (DialogueError, PermissionError):
        raise
    except (SpotifyBackendError, ConnectionError, OSError, TimeoutError):
        result = {}
    if turn:
        await turn.guard()
    queue = result.get("queue") if isinstance(result, dict) and result.get("success") is not False else None
    actions, items = [], []
    if isinstance(queue, list):
        observation["state"] = result.get("queue_state") or ("present" if queue else "known_empty")
        stamp = result.get("queue_observed_at")
        if stamp:
            try:
                stale = (now - datetime.fromisoformat(stamp)).total_seconds() >= 60
            except (TypeError, ValueError):
                stale = True
            if stale:
                observation["state"] = "stale"
        if observation["state"] in {"present", "partial"}:
            for index, item in enumerate(queue[:12]):
                if not isinstance(item, dict):
                    continue
                action = _queue_playback_action(hass, {}, item, index + 1)
                if action and valid_uri(action.get("uri")):
                    # Repeated tracks are distinct reported queue occurrences.
                    action.update(id=f"queue:{index}:{action['uri']}", queue_position=index,
                                  label=COPY[language()]["play"], button_label=COPY[language()]["play"],
                                  reason=COPY[language()]["reason"])
                    actions.append(action)
                    items.append(action)
            if len(items) < len(queue) or not items:
                observation["state"] = "partial"
    if observation["state"] not in COPY[language()] and observation["state"] != "present":
        observation["state"] = "unavailable"
    key = "queue" if observation["state"] == "present" else observation["state"]
    text = COPY[language()][key]
    if observation["state"] in {"present", "partial"}:
        text += " " + COPY[language()]["order"]
    return {"success": True, "text": text, "dj_text": text, "action": "none", "items": items,
            "playback_actions": actions, "images": [], "links": [], "queue_observation": observation,
            "sources": [{"source": "spotify_queue", "title": "Spotify queue", "kind": "source"}]}


async def forecast_read(hass, runtime):
    from ..session_runtime import session_runtime_manager
    turn = current_turn.get()
    if turn is None:
        raise DialogueError("conversation_authority_required", 403)
    await turn.guard()
    manager = session_runtime_manager(hass)
    owner = turn.scope.removeprefix("profile:")
    active = await manager.async_get_active(owner)
    forecast = None
    if active:
        forecast = await manager.async_forecast_snapshot(owner_profile_id=owner, session_id=active.session_id)
        def validate_session():
            current = manager.current_active(owner)
            if current is None or current.session_id != active.session_id:
                raise DialogueError("session_context_changed")
        turn.effect_validators.append(validate_session)
        turn.delivery_validators.append(validate_session)
    response = await queue_read(hass, runtime)
    if active:
        fresh = await manager.async_forecast_snapshot(owner_profile_id=owner, session_id=active.session_id)
        if fresh and forecast and fresh.get("revision") != forecast.get("revision"):
            raise DialogueError("session_context_changed")
        forecast = fresh
    await turn.guard()
    text = forecast.get("summary") if forecast and forecast.get("state") in {"ready", "limited"} else None
    if not text:
        text = COPY[language()]["no_forecast" if active else "no_session"]
    response.update(text=text + " " + response["text"], dj_text=text + " " + response["text"],
                    intent={"intent": "session_forecast_information"},
                    session_forecast=forecast, text_source="qualified_private_projection", is_generated_text=False,
                    _private_current_context=True)
    return response


async def previous_read(hass, runtime):
    from ..session_runtime import session_runtime_manager
    from ..session_conversation import query_service
    from ..historical_projection_query import HistoricalProjectionAccessDenied
    turn = current_turn.get()
    if turn is None:
        raise DialogueError("conversation_authority_required", 403)
    await turn.guard()
    owner = turn.scope.removeprefix("profile:")
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(owner)
    captured_item = active.broadcast.state.playback.item_id if active else ""
    def validate_previous_context():
        current = manager.current_active(owner)
        if (active is None and current is not None) or (active and (
            current is None or current.session_id != active.session_id or current.broadcast.state.playback.item_id != captured_item)):
            raise DialogueError("session_context_changed")
    turn.effect_validators.append(validate_previous_context)
    turn.delivery_validators.append(validate_previous_context)
    query = query_service(hass, turn.history)
    entry, revision = None, None
    try:
        session_id = active.session_id if active else None
        if not session_id:
            page = await query.async_session_page(owner, limit=1)
            if page["sessions"]:
                session_id = page["sessions"][0]["session_id"]
        if session_id:
            rows = await query.async_latest_playback_observations(owner, session_id)
            revision = rows["revision"]
            current_item = active.broadcast.state.playback.item_id if active else ""
            entry = next((e for e in rows["entries"] if e["playback"].get("item_id") != current_item), None)
    except HistoricalProjectionAccessDenied:
        entry = None
    await turn.guard()
    text = COPY[language()]["unknown"]
    refs = []
    if entry:
        refs = [{"session_id": entry["session_id"], "entry_id": entry["entry_id"]}]
        turn.dependencies.extend(refs)
        text = COPY[language()]["previous" if active else "saved"] + ": " + entry["text"] + ". " + COPY[language()]["coverage"]
    return {"success": True, "text": text, "dj_text": text, "intent": {"intent": "previous_track_information"},
            "playback_actions": [], "items": [], "images": [], "links": [], "text_source": "qualified_private_projection", "is_generated_text": False,
            "previous_observation": {"schema_version": 1, "state": "observed" if entry else "unknown",
                "basis": "stage1_distinct_accepted_observations", "coverage": "partial", "revision": revision,
                "as_of": datetime.now(UTC).isoformat(), "references": refs}, "_private_current_context": True,
            "sources": [{"source": "session_playback_observed", "title": entry["playback"].get("provider", "Session history"),
                "url": entry["playback"].get("source_url", "")} ] if entry else []}


def current_artist_question(text: str) -> bool:
    """Closed identification intent at the common text/STT interpretation boundary."""
    value = " ".join(text.casefold().strip().strip("¿¡?.! ").split())
    current_artist_patterns = (
        r"wie is (?:de )?(?:artiest|zanger|band) (?:van|bij) (?:het )?(?:huidige?|nu spelende|dit|dat) (?:nummer|liedje|track)",
        r"who is (?:the )?(?:artist|singer|band) (?:of|on|for) (?:the )?(?:current|currently playing|this|that) (?:song|track)",
        r"wer ist (?:der |die )?(?:künstler|sänger|band) (?:des |vom |von dem )?(?:aktuellen|jetzigen|dieses) (?:liedes|titels|songs|lied|titel|song)",
        r"qui est l['’](?:artiste|interprète) (?:du|de ce) (?:morceau|titre|chanson)(?: actuel| actuelle)?",
        r"quién es (?:el|la) (?:artista|cantante) de (?:la|el) (?:canción|tema) actual",
    )
    if any(re.fullmatch(pattern, value) for pattern in current_artist_patterns):
        return True
    return value in {
        "welke artiest is dit", "welke band is dit", "wie is dit", "wie hoor ik nu",
        "wie zingt dit", "who is this", "which artist is this", "who is this artist",
        "who am i listening to", "who is singing this", "wer ist das",
        "welcher künstler ist das", "welche band ist das", "wen höre ich gerade",
        "qui est cet artiste", "qui est-ce", "qui chante", "quel artiste est-ce",
        "quién es este artista", "qué artista es este", "quién canta esto",
    }


async def current_artist_read(hass, runtime, selected=None, *, require_recording=False):
    """Present qualified metadata locally; never treat catalog rights as model rights."""
    import asyncio
    import hashlib
    from . import run_music_command
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError

    turn = current_turn.get()
    locale = language()
    unavailable = {
        "en": "I cannot reliably identify the artist from the authorized music context.",
        "nl": "Ik kan de artiest niet betrouwbaar vaststellen uit de beschikbare muziekcontext.",
        "de": "Ich kann den Künstler aus dem verfügbaren Musikkontext nicht zuverlässig bestimmen.",
        "fr": "Je ne peux pas identifier l’artiste de manière fiable dans le contexte musical disponible.",
        "es": "No puedo identificar con fiabilidad al artista en el contexto musical disponible.",
    }
    if require_recording:
        unavailable = RECORDING_UNAVAILABLE
    identified = {
        "en": "This is {artist}, with {title}.", "nl": "Dit is {artist}, met {title}.",
        "de": "Das ist {artist} mit {title}.", "fr": "C’est {artist}, avec {title}.",
        "es": "Es {artist}, con {title}.",
    }
    artist_only = {
        "en": "This is {artist}.", "nl": "Dit is {artist}.", "de": "Das ist {artist}.",
        "fr": "C’est {artist}.", "es": "Es {artist}.",
    }

    subject = _identified_playback

    async def fresh():
        if turn:
            await turn.guard()
        observed = turn.history.dialogue.clock() if turn else 0
        try:
            result = await asyncio.wait_for(run_music_command(hass, runtime, "status"), 5)
        except (SpotifyBackendError, MusicBackendCapabilityError, OSError, TimeoutError):
            return None
        if turn:
            await turn.guard()
        if turn:
            deadline = observed + 60
            playback = result.get("playback") if isinstance(result, dict) else None
            stamp = (playback or {}).get("valid_until") or (playback or {}).get("expires_at")
            if stamp:
                try:
                    expiry = datetime.fromisoformat(stamp)
                    if expiry.tzinfo is None:
                        return None
                    deadline = min(deadline, turn.history.dialogue.clock() + (expiry - datetime.now(UTC)).total_seconds())
                except (TypeError, ValueError):
                    return None
            turn.speech_deadline = min(turn.speech_deadline or deadline, deadline)
        return subject(result.get("playback")) if isinstance(result, dict) and result.get("success") is not False else None

    answer = None
    target = None
    sources = [{"source": "djconnect_authorized_music_context", "kind": "source"}]
    if selected is not None:
        # Query/Runtime already qualified this exact selected contribution and its rights.
        target = subject(selected.get("playback"))
        if target:
            answer = identified[locale].format(artist=target[1], title=target[2])
        elif not require_recording:
            artists = selected_artist_names(selected)
            if len(artists) == 1:
                answer = artist_only[locale].format(artist=artists[0][:512])
    else:
        target = await fresh()
        if target:
            if (turn and turn.captured_playback_item_id
                and hashlib.sha256(target[0].encode()).hexdigest()[:24] != turn.captured_playback_item_id):
                raise DialogueError("session_context_changed", 409)
            # No stale cache fallback and no acceptance of a response crossing tracks.
            confirmed = await fresh()
            if confirmed is not None and confirmed != target:
                raise DialogueError("playback_context_changed", 409)
            if confirmed == target:
                answer = identified[locale].format(artist=target[1], title=target[2])
    if answer and target and re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", target[0]):
        sources = [{"source": "spotify_playback_context", "title": "Spotify", "kind": "source",
                    "url": "https://open.spotify.com/track/" + target[0].rsplit(":", 1)[-1]}]
    elif answer and selected:
        attribution = selected.get("source_attribution") or {}
        if isinstance(attribution, dict) and attribution.get("provider") and attribution.get("url"):
            sources = [{**attribution, "source": attribution["provider"], "title": attribution["provider"], "kind": "source"}]
        elif isinstance(selected.get("playback"), dict) and selected["playback"].get("provider") == "Spotify":
            sources = [{"source": "spotify_playback_context", "title": "Spotify", "kind": "source"}]
            url = selected["playback"].get("source_url", "")
            if isinstance(url, str) and re.fullmatch(r"https://open\.spotify\.com/track/[A-Za-z0-9]{22}", url):
                sources[0]["url"] = url
    if turn:
        await turn.guard()
    return {"success": True, "text": answer or unavailable[locale], "dj_text": answer or unavailable[locale],
            "action": "none", "intent": {"category": "informational", "intent": "current_artist_information"},
            "images": [], "links": [dict(source) for source in sources if source.get("url")], "sources": sources,
            "playback_actions": [], "_private_current_context": True,
            "speech_processing_basis": "spotify_owner_local_read_v1" if answer and target else "accepted_local_reply"}


def selected_artist_names(selected):
    """Share the existing limited performer admission; composers are not performers."""
    roles = {"artist", "performer"}
    if selected.get("moment_type") == "artist" and selected.get("archive_basis") == "cc0_normalized_fields_v1":
        roles.update({"Person", "Group"})
    return list(dict.fromkeys(s["name"] for s in selected.get("dialogue_subjects", [])
                             if isinstance(s, dict) and s.get("role") in roles
                             and isinstance(s.get("name"), str) and s["name"].strip()))


def _identified_playback(playback):
    if (not isinstance(playback, dict)
        or any(playback.get(k) for k in ("cached", "stale", "withdrawn"))
        or playback.get("state") in {"idle", "unavailable", "unknown", "off"}):
        return None
    expiry = playback.get("valid_until") or playback.get("expires_at")
    if expiry:
        try:
            deadline = datetime.fromisoformat(expiry)
            if deadline.tzinfo is None or deadline.astimezone(UTC) <= datetime.now(UTC):
                return None
        except (TypeError, ValueError):
            return None
    identity = playback.get("uri") or playback.get("track_uri") or playback.get("item_id")
    artist = playback.get("artist") or playback.get("artist_name")
    title = playback.get("title") or playback.get("track_name") or playback.get("name")
    if not all(isinstance(v, str) and v.strip() for v in (identity, artist, title)):
        return None
    if len(identity) > 2048 or len(artist) > 512 or len(title) > 512:
        return None
    return (identity, artist, title)


def release_question(text):
    value=text.casefold().strip().lstrip("¿")
    subject=re.search(r"\b(?:dit|dat|die|deze|huidig|huidige|this|current|dieser|dieses|aktuell(?:e|er|es|en)?|actuel|actuelle|cette|ce|esta|este|actual)\s+(?:nummer|track|song|opname|uitgave|album|recording|release|titel|lied|aufnahme|ausgabe|morceau|chanson|enregistrement|édition|canción|tema|grabación|edición)\b",value)
    when=re.search(r"\b(?:wanneer|when|wann|quand|cuándo)\b",value)
    released=re.search(r"\b(?:uitgekomen|verschenen|uitgebracht|released|release|erschienen|veröffentlicht|sorti|sortie|publié|publiée|salió|publicado|publicada|lanzó|lanzado)\b",value)
    year=re.search(r"\b(?:jaar|year|jahr|année|año)\b",value)
    return bool(subject and (year or (when and released)))


async def release_read(hass,runtime,selected=None):
    """Read exact edition metadata locally; no catalog-to-model or archive grant."""
    from . import run_music_command
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError
    from datetime import date
    import asyncio
    import hashlib
    turn=current_turn.get()
    locale=language()
    deadline=turn.history.dialogue.clock()+60 if turn else None
    def validate_deadline():
        if turn and turn.history.dialogue.clock()>=deadline:
            raise DialogueError('playback_observation_expired',409)
    if turn:
        turn.speech_deadline=min(turn.speech_deadline or deadline,deadline)
        turn.delivery_validators.append(validate_deadline)
        if selected is None:
            from ..session_runtime import session_runtime_manager
            manager=session_runtime_manager(hass)
            owner=turn.scope.removeprefix('profile:')
            active=manager.current_active(owner)
            if active:
                session_id,item_id=active.session_id,active.broadcast.state.playback.item_id
                def validate_current():
                    current=manager.current_active(owner)
                    if (current is None or current.session_id!=session_id
                        or current.broadcast.state.playback.item_id!=item_id):
                        raise DialogueError('session_context_changed',409)
                turn.delivery_validators.append(validate_current)
    copy={
        'en':('The album edition containing {title} lists {date} as its release date.', 'I recognize {title}, but no reliable release date is available for that edition.', 'I cannot reliably identify the recording from the authorized music context.'),
        'nl':('De albumuitgave met {title} vermeldt {date} als releasedatum.', 'Ik herken {title}, maar heb geen betrouwbare releasedatum van die uitgave.', 'Ik kan de opname niet betrouwbaar vaststellen uit de beschikbare muziekcontext.'),
        'de':('Die Albumausgabe mit {title} nennt {date} als Veröffentlichungsdatum.', 'Ich erkenne {title}, aber für diese Ausgabe ist kein verlässliches Veröffentlichungsdatum verfügbar.', 'Ich kann die Aufnahme im verfügbaren Musikkontext nicht zuverlässig bestimmen.'),
        'fr':('L’édition de l’album contenant {title} indique {date} comme date de sortie.', 'Je reconnais {title}, mais je ne dispose pas de date de sortie fiable pour cette édition.', 'Je ne peux pas identifier cette version de façon fiable dans le contexte musical disponible.'),
        'es':('La edición del álbum que contiene {title} indica {date} como fecha de lanzamiento.', 'Reconozco {title}, pero no dispongo de una fecha de lanzamiento fiable para esa edición.', 'No puedo identificar con fiabilidad la grabación en el contexto musical disponible.'),
    }
    def release(metadata):
        value=metadata.get('release_date')
        precision=metadata.get('release_date_precision')
        if not isinstance(value,str) or len(value)>10:
            return None
        try:
            if precision=='day' and re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
                date.fromisoformat(value)
            elif precision=='month' and re.fullmatch(r"\d{4}-\d{2}",value):
                date.fromisoformat(value+'-01')
            elif precision=='year' and re.fullmatch(r"\d{4}",value):
                date.fromisoformat(value+'-01-01')
            else:
                return None
        except ValueError:
            return None
        return value
    def bind_expiry(playback):
        nonlocal deadline
        if turn and isinstance(playback,dict):
            stamp=playback.get('valid_until') or playback.get('expires_at')
            if stamp:
                try:
                    expiry=datetime.fromisoformat(stamp)
                    if expiry.tzinfo is None:
                        raise ValueError('naive_expiry')
                    deadline=min(deadline,turn.history.dialogue.clock()+(expiry.astimezone(UTC)-datetime.now(UTC)).total_seconds())
                except (TypeError,ValueError):
                    raise DialogueError('playback_observation_expired',409) from None
                turn.speech_deadline=min(turn.speech_deadline or deadline,deadline)
            validate_deadline()
    async def fresh():
        nonlocal deadline
        if turn:
            await turn.guard()
            now=turn.history.dialogue.clock()
            deadline=min(deadline,now+60)
            turn.speech_deadline=min(turn.speech_deadline or deadline,deadline)
        try:
            result=await asyncio.wait_for(run_music_command(hass,runtime,'status'),5)
        except (SpotifyBackendError,MusicBackendCapabilityError,OSError,TimeoutError):
            return {}
        if turn:
            await turn.guard()
        playback=result.get('playback') or {} if isinstance(result,dict) and result.get('success') is not False else {}
        bind_expiry(playback)
        return playback
    metadata=dict((selected or {}).get('playback') or {})
    bind_expiry(metadata)
    # Historical playback projects a bounded item hash and a source link, not
    # the original catalog object. Recover only the exact canonical URI whose
    # hash equals that accepted identity; names never establish identity.
    match=re.fullmatch(r'https://open\.spotify\.com/track/([A-Za-z0-9]{22})',str(metadata.get('source_url') or ''))
    if not metadata.get('uri') and metadata.get('provider')=='Spotify' and match:
        uri='spotify:track:'+match[1]
        if metadata.get('item_id')==hashlib.sha256(uri.encode()).hexdigest()[:24]:
            metadata['uri']=uri
    used_current=False
    target=_identified_playback(metadata)
    selected_identity=target[0] if target else None
    if selected is None:
        used_current=True
        metadata=await fresh()
        target=_identified_playback(metadata)
        if (target and turn and turn.captured_playback_item_id
            and hashlib.sha256(target[0].encode()).hexdigest()[:24]!=turn.captured_playback_item_id):
            raise DialogueError('playback_context_changed',409)
    elif target and release(metadata) is None:
        observed=await fresh()
        if _identified_playback(observed) and _identified_playback(observed)[0]==selected_identity:
            metadata=observed
            used_current=True
    value=release(metadata) if target else None
    if target and used_current:
        confirmed=await fresh()
        if _identified_playback(confirmed)!=target or release(confirmed)!=value:
            if selected is None:
                raise DialogueError('playback_context_changed',409)
            value=None
    # A historical/selected recording remains selected when current playback differs.
    known=target is not None
    text=(copy[locale][0].format(title=target[2],date=value) if known and value
          else copy[locale][1].format(title=target[2]) if known else copy[locale][2])
    sources=[]
    if known and re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}',target[0]):
        sources=[{'source':'spotify_playback_context','title':'Spotify','kind':'source',
                  'url':'https://open.spotify.com/track/'+target[0].rsplit(':',1)[-1]}]
    if turn:
        await turn.guard()
        validate_deadline()
    return {'success':True,'text':text,'dj_text':text,'action':'none','images':[],
            'sources':sources,'links':[dict(source) for source in sources],'playback_actions':[],
            'intent':{'category':'informational','intent':'current_release_information'},
            'release_observation':{'state':'known' if value else 'unknown','release_date':value,
                                   'precision':metadata.get('release_date_precision') if value else None,
                                   'basis':'album_edition','original_release_verified':False},
            '_private_current_context':True,'speech_processing_basis':'accepted_local_reply'}
