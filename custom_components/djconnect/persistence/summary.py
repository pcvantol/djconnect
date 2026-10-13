"""Private compact accepted-event aggregates; owned by existing Session repositories."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json

VERSION = "djconnect-session-history-summary/1"
MAX_ACCEPTED_EVENTS = 8192
MOODS = ("chill", "groove", "energy", "party")
COLUMNS = (
    "tracks",
    "moments",
    "tracks_coverage",
    "moments_coverage",
    "mood_coverage",
    "mood_durations",
    "mood_current",
    "mood_since",
    "source_binding",
)


def binding(context):
    context = context or {}
    return {
        **{
            k: str(context.get(k) or "")[:128]
            for k in ("backend_id", "music_account_id", "provider_entry_id")
        },
        "account_fingerprint": hashlib.sha256(
            str(context.get("provider_account_id") or "").encode()
        ).hexdigest(),
    }


def initialize_tx(tx, session_id, mood, stamp, context=None):
    tx.execute(
        "INSERT INTO djconnect_session_summaries (session_id,tracks,moments,tracks_coverage,moments_coverage,mood_coverage,mood_durations,mood_current,mood_since,source_binding) VALUES (?,0,0,'complete','complete',?,?,?,?,?)",
        (
            session_id,
            "complete" if mood in MOODS else "unknown",
            json.dumps(dict.fromkeys(MOODS, 0)),
            mood if mood in MOODS else "",
            stamp,
            json.dumps(binding(context)),
        ),
    )


def record_event_tx(tx, session_id, kind, reference_id, entry_id=""):
    """Return new/duplicate/full; retain every accepted identity until Session erasure."""
    if (
        kind not in {"playback_observed", "dj_moment"}
        or not isinstance(reference_id, str)
        or not reference_id
        or len(reference_id) > 256
    ):
        raise ValueError("invalid_summary_event_identity")
    old = tx.fetchone(
        "SELECT entry_id FROM djconnect_session_acceptances WHERE session_id=? AND kind=? AND reference_id=?",
        (session_id, kind, reference_id),
    )
    if old is not None:
        return "duplicate", str(old[0])
    count = tx.fetchone(
        "SELECT COUNT(*) FROM djconnect_session_acceptances WHERE session_id=?", (session_id,)
    )[0]
    if count >= MAX_ACCEPTED_EVENTS:
        if kind == "playback_observed":
            coverage = tx.fetchone(
                "SELECT tracks_coverage FROM djconnect_session_summaries WHERE session_id=?",
                (session_id,),
            )
            if coverage and coverage[0] == "complete":
                tx.execute(
                    "UPDATE djconnect_session_summaries SET tracks_coverage='partial' WHERE session_id=?",
                    (session_id,),
                )
                tx.execute(
                    "UPDATE djconnect_persistent_sessions SET history_revision=history_revision+1 WHERE session_id=?",
                    (session_id,),
                )
            return "full", ""
        raise ValueError("session_summary_capacity")
    tx.execute(
        "INSERT INTO djconnect_session_acceptances (session_id,kind,reference_id,entry_id) VALUES (?,?,?,?)",
        (session_id, kind, reference_id, entry_id),
    )
    column = "tracks" if kind == "playback_observed" else "moments"
    coverage = column + "_coverage"
    tx.execute(
        f"UPDATE djconnect_session_summaries SET {column}={column}+1 WHERE session_id=? AND {coverage}!='withdrawn'",
        (session_id,),
    )
    return "new", entry_id


def mood_tx(tx, session_id, mood, stamp, *, terminal=False, interrupted=False):
    row = tx.fetchone(
        "SELECT mood_durations,mood_current,mood_since,mood_coverage FROM djconnect_session_summaries WHERE session_id=?",
        (session_id,),
    )
    if row is None:
        return
    durations, current, since, coverage = row
    durations = json.loads(durations)
    if interrupted:
        coverage = "unknown"
    elif current in MOODS and since:
        delta = int(
            (datetime.fromisoformat(stamp) - datetime.fromisoformat(since)).total_seconds()
            * 1_000_000
        )
        if delta < 0:
            coverage = "unknown"
        else:
            durations[current] += delta
    if mood not in MOODS and not terminal:
        coverage = "unknown"
    tx.execute(
        "UPDATE djconnect_session_summaries SET mood_durations=?,mood_current=?,mood_since=?,mood_coverage=? WHERE session_id=?",
        (
            json.dumps(durations),
            "" if terminal else mood,
            "" if terminal else stamp,
            coverage,
            session_id,
        ),
    )


def withdraw_tx(tx, session_id):
    """Conservative permanent removal of source-dependent derived totals, not dedup keys."""
    tx.execute(
        "UPDATE djconnect_session_summaries SET tracks=0,moments=0,tracks_coverage='withdrawn',moments_coverage='withdrawn' WHERE session_id=?",
        (session_id,),
    )


def project(row, session, as_of):
    """No writes: at most one open confirmed interval, fixed four-counter work."""
    state = "final" if session["lifecycle_status"] in {"ENDED", "INTERRUPTED"} else "provisional"
    revision = session["revision"]
    if row is None:
        data = {
            "tracks": None,
            "moments": None,
            "tracks_coverage": "unknown",
            "moments_coverage": "unknown",
            "mood_coverage": "unknown",
            "mood_durations": "{}",
            "mood_current": "",
            "mood_since": "",
        }
    else:
        data = dict(zip(COLUMNS, row))
    durations = json.loads(data["mood_durations"])
    coverage = data["mood_coverage"]
    if state == "provisional" and data["mood_current"] in MOODS and data["mood_since"]:
        delta = int(
            (
                datetime.fromisoformat(as_of) - datetime.fromisoformat(data["mood_since"])
            ).total_seconds()
            * 1_000_000
        )
        if delta < 0:
            coverage = "unknown"
        else:
            current = data["mood_current"]
            durations[current] = durations.get(current, 0) + delta
    total = sum(durations.values())
    value = None
    if coverage == "complete" and total > 0:
        value = next((m for m, duration in durations.items() if duration * 2 > total), "mixed")
    elif total == 0:
        coverage = "unknown"

    def metric(value, basis, coverage):
        return {
            "value": value if coverage not in {"unknown", "withdrawn"} else None,
            "basis": basis,
            "coverage": coverage,
            "state": state,
            "revision": revision,
            "as_of": as_of,
        }

    return {
        "schema_version": VERSION,
        "session_revision": revision,
        "state": state,
        "as_of": as_of,
        "tracks_observed": {
            **metric(data["tracks"], "accepted_playback_observed_entries", data["tracks_coverage"]),
            "observation_scope": "stage_1_media_identity_changes_not_occurrences",
        },
        "moments_published": metric(
            data["moments"], "semantic_publication_commit", data["moments_coverage"]
        ),
        "mood": metric(value, "confirmed_symbolic_mood_elapsed_intervals", coverage),
    }


def attach_tx(tx, records):
    """One bounded IN query per page, no timeline reads or per-row queries."""
    if not records:
        return records
    ids = [r["session_id"] for r in records]
    rows = tx.fetchall(
        "SELECT session_id,"
        + ",".join(COLUMNS)
        + " FROM djconnect_session_summaries WHERE session_id IN ("
        + ",".join("?" for _ in ids)
        + ")",
        tuple(ids),
    )
    values = {r[0]: r[1:] for r in rows}
    as_of = datetime.now(UTC).isoformat()
    for record in records:
        row = values.get(record["session_id"])
        record["summary"] = project(row, record, as_of)
        record["summary_binding"] = json.loads(row[-1]) if row else {}
    return records
