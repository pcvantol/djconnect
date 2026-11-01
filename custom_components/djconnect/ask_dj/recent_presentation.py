"""Original recent-list display metadata; never media, selection or playback authority."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json

KEY = "recent_history_presentation"
KINDS = {"tracks": "track", "albums": "album", "artists": "artist", "playlists": "playlist"}
ITEM_FIELDS = {"item_id", "kind", "title", "subtitle", "played_at"}


def _text(value, maximum):
    return (isinstance(value, str) and 0 < len(value) <= maximum
            and value == value.strip()
            and not any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value))


def checked(value):
    """A closed optional display contract; unknown/action/media fields close the whole value."""
    if (not isinstance(value, dict)
            or set(value) != {"schema_version", "item_type", "caption", "omitted_count", "items"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(value["item_type"], str) or value["item_type"] not in KINDS
            or not _text(value["caption"], 512)
            or type(value["omitted_count"]) is not int or not 0 <= value["omitted_count"] <= 50
            or not isinstance(value["items"], list) or not 1 <= len(value["items"]) <= 10):
        return None
    for ordinal, item in enumerate(value["items"]):
        if (not isinstance(item, dict) or set(item) - ITEM_FIELDS
                or item.get("item_id") != "recent-" + str(ordinal)
                or item.get("kind") != KINDS[value["item_type"]]
                or not _text(item.get("title"), 512)
                or any(not _text(v, 512 if k == "subtitle" else 80)
                       for k, v in item.items() if k not in {"item_id", "kind", "title"})):
            return None
        if "played_at" in item:
            try:
                stamp = datetime.fromisoformat(item["played_at"])
                if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
                    return None
            except (ValueError, OverflowError):
                return None
    if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 16384:
        return None
    return deepcopy(value)


def build(items, item_type, caption, omitted_count):
    """Only explicit producer metadata is copied; no text parsing or expired media renewal."""
    retained = []
    for ordinal, item in enumerate(items):
        if not isinstance(item, dict):
            return None
        original = {k: v for k, v in item.items() if k in ITEM_FIELDS and v != ""}
        original["item_id"] = "recent-" + str(ordinal)
        if "played_at" in original:
            try:
                stamp = datetime.fromisoformat(original["played_at"])
                if stamp.tzinfo is None or stamp.utcoffset() is None:
                    return None
                original["played_at"] = stamp.astimezone(UTC).isoformat()
            except (TypeError, ValueError, OverflowError):
                return None
        retained.append(original)
    return checked({"schema_version": 1, "item_type": item_type, "caption": caption,
                    "omitted_count": omitted_count,
                    "items": retained})


def from_response(response):
    intent = response.get("intent")
    value = checked(response.get(KEY))
    if (value is None or response.get("success") is not True or not isinstance(intent, dict)
            or intent.get("intent") != "recently_played_history"
            or intent.get("action") != "recently_played"
            or intent.get("item_type") != value["item_type"]):
        return None
    return value
