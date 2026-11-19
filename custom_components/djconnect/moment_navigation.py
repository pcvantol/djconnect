"""Closed lightweight Moment navigation DTO; no provider, auth or analysis imports."""

from __future__ import annotations

CAPABILITY = "moment_track_insight_navigation_v1"
TTL_SECONDS = 600
LABELS = {
    "en": "View Track Insight",
    "nl": "Bekijk Track Insight",
    "de": "Track Insight ansehen",
    "fr": "Voir Track Insight",
    "es": "Ver Track Insight",
}


def navigation(action) -> dict | None:
    if action.action_type != "open_track_insight" or action.required_capability != CAPABILITY:
        return None
    payload = dict(action.payload)
    if (
        set(payload) != {"schema_version", "session_id", "moment_id", "action_id"}
        or payload["schema_version"] != "1"
    ):
        return None
    if payload["action_id"] != "insight-" + payload["moment_id"]:
        return None
    return {
        "schema_version": 1,
        "kind": "navigation",
        "target": "track_insight",
        "action_id": payload["action_id"],
        "label": action.label,
        "required_capability": CAPABILITY,
        "reference": {
            "schema_version": 1,
            **{k: payload[k] for k in ("session_id", "moment_id", "action_id")},
        },
    }
