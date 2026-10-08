"""Bounded owner projections and stateless query cursors, never a history authority."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hmac
import json
import secrets
import unicodedata


class HistoryQueryError(ValueError):
    """Stable application error for malformed/stale history queries."""


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def text_highlights(text: str, query: str) -> list[dict]:
    """NFKC/casefold matching with original UTF-16 cluster boundaries for Swift."""
    needle = normalize_text(query)
    if not needle:
        return []
    normalized = []
    spans = []
    cluster = ""
    start = 0
    offset = 0

    def emit(value, first, last):
        folded = normalize_text(value)
        normalized.extend(folded)
        spans.extend([(first, last)] * len(folded))

    for char in text:
        length = len(char.encode("utf-16-le")) // 2
        if cluster and not unicodedata.combining(char):
            emit(cluster, start, offset)
            cluster = ""
            start = offset
        if not cluster:
            start = offset
        cluster += char
        offset += length
    if cluster:
        emit(cluster, start, offset)
    value = "".join(normalized)
    at = 0
    found = []
    while len(found) < 100:
        index = value.find(needle, at)
        if index < 0:
            break
        left, right = spans[index][0], spans[index + len(needle) - 1][1]
        mark = {"start_utf16": left, "length_utf16": right - left}
        if mark not in found:
            found.append(mark)
        at = index + len(needle)
    return found


class HistoryCursorCodec:
    """Query-only, process-local signing key; no durable Broadcast/recovery token."""

    def __init__(self):
        self._key = secrets.token_bytes(32)

    def encode(self, scope: dict, after: int) -> str:
        body = json.dumps({**scope, "after": after}, sort_keys=True).encode()
        return base64.urlsafe_b64encode(body + hmac.digest(self._key, body, "sha256")).decode()

    def decode(self, token: str, scope: dict) -> int:
        try:
            if not isinstance(token, str) or len(token) > 4096:
                raise ValueError()
            data = base64.b64decode(token, altchars=b"-_", validate=True)
            body, signature = data[:-32], data[-32:]
            if not hmac.compare_digest(hmac.digest(self._key, body, "sha256"), signature):
                raise ValueError()
            value = json.loads(body)
            after = value.pop("after")
            if value != scope or not isinstance(after, int) or isinstance(after, bool) or after < 0:
                raise ValueError()
            return after
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            raise HistoryQueryError("invalid_history_cursor") from exc


def project_entry(row: dict) -> dict | None:
    """Only explicitly qualified, owner-visible, retained entry bodies escape storage."""
    now = datetime.now(UTC)
    if row["visibility"] != "owner" or row["revoked_at"]:
        return None
    try:
        if datetime.fromisoformat(row["retained_until"]) <= now:
            return None
        body = json.loads(row["body"])
    except (ValueError, TypeError):
        return None
    result = {
        k: row[k]
        for k in ("entry_id", "session_id", "order", "kind", "occurred_at", "retained_until")
    }
    if row["kind"] == "playback_observed":
        if body.get("coverage") != "observed_playing_not_full_listen":
            return None
        result["playback"] = body
        result["text"] = " · ".join(
            str(body.get(k) or "") for k in ("title", "artist", "album") if body.get(k)
        )
        result["requires_spotify_attribution"] = body.get("provider") == "Spotify"
    elif row["kind"] == "dj_moment":
        if body.get("archive_basis") not in {
            "cc0_normalized_fields_v1",
            "runtime_authored_direction_v1",
        }:
            return None
        result.update(body)
    elif row["kind"] in {"conversation_user", "conversation_dj"}:
        # Text is resolved by the existing Ask DJ history authority, never copied here.
        result["conversation_reference"] = body
    else:
        return None
    return result


def revision_scope(owner: str, session: dict, mode: str, query: str = "") -> dict:
    return {
        "profile_id": owner,
        "session_id": session["session_id"],
        "revision": session["revision"],
        "mode": mode,
        "query": query,
    }


def checked_limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 50:
        raise HistoryQueryError("invalid_history_limit")
    return value


def public_session(session: dict) -> dict:
    result = {
        k: session[k]
        for k in (
            "session_id",
            "lifecycle_status",
            "created_at",
            "started_at",
            "ended_at",
            "interrupted_at",
            "revision",
        )
    }
    result["read_only"] = session["lifecycle_status"] in {"ENDED", "INTERRUPTED"}
    result["history_coverage"] = "saved_entries_only_no_retrospective_observations"
    return result


def session_retained(session: dict) -> bool:
    from datetime import timedelta

    stamp = session["ended_at"] or session["interrupted_at"] or session["created_at"]
    try:
        return bool(
            session["history_enabled"]
            and datetime.fromisoformat(stamp) > datetime.now(UTC) - timedelta(days=90)
        )
    except (ValueError, TypeError):
        return False


def new_observation_reference() -> str:
    # Core event identity, explicitly NOT a provider Playback Instance Identity.
    from uuid import uuid4

    return "observation-" + uuid4().hex
