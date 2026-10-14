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
