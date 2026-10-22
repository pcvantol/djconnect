"""Explicit retained-recording playback through the existing Ask DJ effect owner."""

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


def offer(row, entry, *, locale=None):
    if not offers_enabled.get() or recording(row) is None:
        return entry
    locale = locale if locale is not None else offer_locale.get()
    language = locale.split("-", 1)[0] if isinstance(locale, str) else "en"
    value = {"schema_version": 1, "session_id": row["session_id"], "entry_id": row["entry_id"]}
    return {
        **entry,
        "playback_actions": [
            {
                "kind": "historical_track",
                "command": COMMAND,
                "label": LABELS.get(language, LABELS["en"]),
                "required_capability": CAPABILITY,
                "value": value,
            }
        ],
    }


async def execute(hass, runtime, payload, value):
    """A manual tap admits one exact original recording, with current source fences."""
    from .ask_dj.dialogue import current_turn, DialogueError, EffectGrant
    from .session_conversation import query_service
    from .forecast_imagery import artist_authority
    from .http import _handle_ask_dj_play_recommendation

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
    turn.historical_playback_admission = {
        "validate": validate_original,
        "reference": dict(reference),
    }
    turn.effect_validators.append(validate_original)
    turn.delivery_validators.append(validate_original)
    turn.effect_grants = (
        EffectGrant(frozenset({"play"}), "explicit_historical_recording", media=(track["uri"],)),
    )
    action = {"kind": "track", **track}
    result = await _handle_ask_dj_play_recommendation(hass, runtime, action, payload)
    await turn.guard()
    if result.get("success") is not False:
        result["historical_playback_reference"] = reference
    return result
