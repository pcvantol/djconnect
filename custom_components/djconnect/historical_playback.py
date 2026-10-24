"""Retained-recording identity and closed queue-preservation playback contract."""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime
import json
import re
import time

SOURCE_FIELDS = ("backend_id", "music_account_id", "provider_entry_id", "provider_account_id")
CAPABILITY = "historical_exact_track_playback"
COMMAND = "play_history_item"
offers_enabled = ContextVar("djconnect_historical_playback_offers", default=False)
offer_locale = ContextVar("djconnect_historical_playback_locale", default="en")
LABELS = {
    "en": "Play this recording",
    "nl": "Speel deze opname",
    "de": "Diese Aufnahme abspielen",
    "fr": "Lire cet enregistrement",
    "es": "Reproducir esta grabación",
}
_TRACK = re.compile(r"spotify:track:[A-Za-z0-9]{22}\Z")
_ALBUM = re.compile(r"spotify:album:[A-Za-z0-9]{22}\Z")


def checked_reference(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "session_id", "entry_id"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or any(
            not isinstance(value[k], str)
            or not 0 < len(value[k]) <= 128
            or any(ord(c) < 33 for c in value[k])
            for k in ("session_id", "entry_id")
        )
    ):
        raise ValueError("invalid_historical_playback_reference")
    return dict(value)


def recording(row):
    """Only an already qualified row supplies a target; never text/current state."""
    try:
        body = json.loads(row["body"])
        if not isinstance(body, dict):
            return None
        if row["kind"] == "playback_observed":
            if (
                body.get("provider") != "Spotify"
                or body.get("coverage") != "observed_playing_not_full_listen"
            ):
                return None
            match = re.fullmatch(
                r"https://open\.spotify\.com/track/([A-Za-z0-9]{22})",
                str(body.get("source_url", "")),
            )
            uri = "spotify:track:" + match[1] if match else ""
            source, album = body.get("source_context"), body.get("album_uri", "")
        else:
            return None
        if (
            not isinstance(uri, str)
            or not _TRACK.fullmatch(uri)
            or not isinstance(source, dict)
            or set(source) != set(SOURCE_FIELDS)
            or any(
                not isinstance(source[k], str) or not 0 < len(source[k]) <= 256
                for k in SOURCE_FIELDS
            )
            or not isinstance(album, str)
            or (album and not _ALBUM.fullmatch(album))
        ):
            return None
        title, artist = body.get("title"), body.get("artist")
        if row["kind"] == "playback_observed" and (
            not isinstance(title, str) or not title or not isinstance(artist, str) or not artist
        ):
            return None
        return {
            "uri": uri,
            "title": title if isinstance(title, str) else "",
            "artist": artist if isinstance(artist, str) else "",
            "album": body.get("album") if isinstance(body.get("album"), str) else "",
            "album_uri": album,
            "source_context": dict(source),
        }
    except (KeyError, ValueError, TypeError):
        return None


UNAVAILABLE = "historical_queue_preservation_unavailable"
UNAVAILABLE_MESSAGES = {
    "en": "Playing from history is unavailable because keeping your queue unchanged cannot be guaranteed.",
    "nl": "Afspelen vanuit historie is niet beschikbaar omdat behoud van je wachtrij niet kan worden gegarandeerd.",
    "de": "Die Wiedergabe aus dem Verlauf ist nicht verfügbar, da der Erhalt deiner Warteschlange nicht garantiert werden kann.",
    "fr": "La lecture depuis l’historique est indisponible, car la conservation de votre file d’attente ne peut être garantie.",
    "es": "La reproducción desde el historial no está disponible porque no se puede garantizar que se conserve tu cola.",
}


def unavailable_message(locale):
    language = locale.lower().split("-", 1)[0] if isinstance(locale, str) else "en"
    return UNAVAILABLE_MESSAGES.get(language, UNAVAILABLE_MESSAGES["en"])


def offer(row, entry, *, locale=None):
    # V1 proved exact recording identity, never preservation of every remaining
    # queue occurrence/order. No qualified provider operation exists. Neither a
    # caller version nor the legacy ContextVar can grant this capability.
    return entry


async def validate_saved_output_replay(query, owner, saved, payload):
    """Close ambiguous V1 historical output receipts after their RAM offer is lost.

    Legacy receipts did not persist the historical admission marker. Reopen
    explicit retained playback dependencies; never manufacture positive provider
    provenance from their absence. Ordinary output receipts and implicit current
    playback evidence retain their existing duplicate semantics.
    """
    from .ask_dj.dialogue import DialogueError

    command = (payload.get("_command_action") or (None,))[0]
    choice = payload.get("choice_action")
    if command not in {"ask_dj_play_recommendation_on_output", "ask_dj_play_request_on_output"} and not (
        isinstance(choice, dict) and choice.get("operation") == "play"
    ):
        return
    turn = saved["assistant_message"].get("session_turn", {})
    explicit = list(turn.get("dependency_entries", []))
    selected = turn.get("context", {}).get("selected_entry")
    if isinstance(selected, dict):
        explicit.append(selected)
    implicit = turn.get("implicit_playback_entry")
    for ref in explicit:
        if not isinstance(ref, dict) or not ref.get("session_id") or not ref.get("entry_id"):
            continue
        target = {k: ref[k] for k in ("session_id", "entry_id")}
        if isinstance(implicit, dict) and all(implicit.get(k) == target[k] for k in target) and ref != selected:
            continue
        await query.async_open_source_entry(owner, target["session_id"], target["entry_id"])
        row = await query._repository.async_entry_record(owner, target["session_id"], target["entry_id"])
        if row is not None and row["kind"] == "playback_observed":
            raise DialogueError(UNAVAILABLE, 409)


async def execute(hass, runtime, payload, value):
    """Validate the original readable item, then deny before any effect admission."""
    from .ask_dj.dialogue import current_turn, DialogueError
    from .session_conversation import query_service
    from .forecast_imagery import artist_authority

    turn = current_turn.get()
    if turn is None or not turn.scope.startswith("profile:"):
        raise DialogueError("conversation_authority_required", 403)
    try:
        reference = checked_reference(value)
    except ValueError as exc:
        raise DialogueError(str(exc), 400) from None
    selected = turn.selected_read_context
    if not isinstance(selected, dict) or any(
        selected.get(k) != reference[k] for k in ("session_id", "entry_id")
    ):
        raise DialogueError("historical_playback_unavailable", 410)
    owner = turn.scope.removeprefix("profile:")
    await turn.guard()
    query = query_service(hass, turn.history)
    opened = await query.async_open_source_entry(
        owner, reference["session_id"], reference["entry_id"]
    )
    row = await query._repository.async_entry_record(
        owner, reference["session_id"], reference["entry_id"]
    )
    await turn.guard()
    track = recording(row) if row else None
    if track is None:
        raise DialogueError("historical_playback_unavailable", 410)
    source = deepcopy(track.pop("source_context"))
    authority = artist_authority(hass, runtime, owner_profile_id=owner, expected_source=source)
    deadline = datetime.fromisoformat(opened["entry"]["retained_until"]).timestamp()

    def validate_original():
        if not authority() or time.time() >= deadline:
            raise DialogueError("historical_playback_withdrawn", 410)

    validate_original()
    # Ordinary play replaces provider context and is not an atomic queue insert.
    # Preserve the original read/owner/source fences, but never issue a play grant,
    # request output inventory, transfer output, or delegate to ordinary playback.
    raise DialogueError(UNAVAILABLE, 409)
