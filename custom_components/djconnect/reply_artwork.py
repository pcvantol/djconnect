"""Captured reply subject identity; original pixels and image leases never persist."""

from __future__ import annotations

from copy import deepcopy
import re

SOURCE_FIELDS = ("backend_id", "music_account_id", "provider_entry_id", "provider_account_id")
_URI = re.compile(r"spotify:(track|album|artist):[A-Za-z0-9]{22}\Z")
KEY = "reply_media_reference"


def checked(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "subject_uri", "album_uri", "source_context"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or not isinstance(value["subject_uri"], str)
        or not _URI.fullmatch(value["subject_uri"])
        or not isinstance(value["album_uri"], str)
        or (
            value["album_uri"]
            and not re.fullmatch(r"spotify:album:[A-Za-z0-9]{22}", value["album_uri"])
        )
        or not isinstance(value["source_context"], dict)
        or set(value["source_context"]) != set(SOURCE_FIELDS)
        or any(
            not isinstance(v, str) or not 0 < len(v) <= 256
            for v in value["source_context"].values()
        )
    ):
        return None
    if value["subject_uri"].startswith("spotify:track:") and not value["album_uri"]:
        return None
    if (
        value["subject_uri"].startswith("spotify:album:")
        and value["album_uri"] != value["subject_uri"]
    ):
        return None
    if value["subject_uri"].startswith("spotify:artist:") and value["album_uri"]:
        return None
    return deepcopy(value)


def public(value):
    """A stored original source binding is internal, including nested duplicate receipts."""
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k != KEY}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value


def source_admission(hass, runtime, owner):
    """Capture the existing loaded source, never pick a substitute account on read."""
    from .profile_backend import profile_backend_runtime
    from .profile_context import profile_storage
    from .forecast_imagery import artist_authority

    try:
        storage = profile_storage(hass)
        profile = storage.household.profiles[owner]
        account = storage.household.music_accounts[profile.preferences.default_music_account_id]
        backend = storage.household.music_backends[profile.preferences.default_backend_id]
        provider = profile_backend_runtime(hass, runtime, provider_only=True)
        if str(backend.provider) != "spotify_direct":
            return None, None
        source = {
            "backend_id": backend.backend_id,
            "music_account_id": account.account_id,
            "provider_entry_id": provider.entry.entry_id,
            "provider_account_id": str(account.provider_account_id),
        }
        if any(not isinstance(source[k], str) or not source[k] for k in SOURCE_FIELDS):
            return None, None
        authority = artist_authority(hass, runtime, owner_profile_id=owner, expected_source=source)
        return (source, authority) if authority() else (None, None)
    except (AttributeError, KeyError, ValueError, PermissionError):
        return None, None


def subject(source, source_context):
    """Only this provider-normalized image's explicit subject and edition qualify."""
    from .discovery_artwork import provider_asset_id

    if not isinstance(source, dict):
        return None
    url = next(
        (
            source.get(k)
            for k in ("album_image_url", "media_image_url", "image_url", "thumbnail_url")
            if source.get(k)
        ),
        None,
    )
    if not provider_asset_id(url):
        return None
    uri = next((source.get(k) for k in ("uri", "track_uri", "current_uri") if source.get(k)), None)
    if not isinstance(uri, str) or not _URI.fullmatch(uri):
        return None
    album = source.get("album_uri")
    if not album and isinstance(source.get("album"), dict):
        album = source["album"].get("uri")
    album = album or (uri if uri.startswith("spotify:album:") else "")
    return checked(
        {
            "schema_version": 1,
            "subject_uri": uri,
            "album_uri": album,
            "source_context": source_context,
        }
    )


def remember_image(source, image):
    from .ask_dj.dialogue import current_turn

    turn = current_turn.get()
    if (
        turn is None
        or getattr(turn, "reply_source_authority", None) is None
        or not turn.reply_source_authority()
    ):
        return
    value = subject(source, turn.reply_source_context)
    if value is not None:
        turn.reply_media_candidate = (value, image["url"])


def accepted(turn, result):
    candidate = turn.reply_media_candidate
    if (
        not candidate
        or getattr(turn, "reply_source_authority", None) is None
        or not turn.reply_source_authority()
        or result.get("success") is False
    ):
        return None
    urls = {i.get("url") for i in result.get("images", []) if isinstance(i, dict)}
    return checked(candidate[0]) if candidate[1] in urls else None
