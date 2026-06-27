"""DJConnect AI/conversation tool schemas and metadata."""
from __future__ import annotations

from typing import Any

READ_ONLY_TOOL_NAMES = {
    "djconnect_track_insight",
    "djconnect_now_playing",
    "djconnect_music_dna_summary",
    "djconnect_recently_played",
    "djconnect_search_music",
    "djconnect_list_outputs",
    "djconnect_build_recommendations",
}


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    *,
    required: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
        "read_only": name in READ_ONLY_TOOL_NAMES,
    }


AI_TOOLS: tuple[dict[str, Any], ...] = (
    _tool(
        "djconnect_track_insight",
        "Analyze the current or provided track with Track Insight.",
        {
            "title": {"type": "string"},
            "artist": {"type": "string"},
            "album": {"type": "string"},
            "entity_id": {"type": "string"},
            "player_id": {"type": "string"},
            "music_backend": {"type": "string"},
            "locale": {"type": "string"},
            "force_refresh": {"type": "boolean"},
            "include_visual_profile": {"type": "boolean"},
            "include_raw_response": {"type": "boolean"},
        },
    ),
    _tool("djconnect_now_playing", "Read the current DJConnect backend playback state.", {}),
    _tool(
        "djconnect_music_dna_summary",
        "Read a compact Music DNA summary for the current user/client context.",
        {"music_dna_key": {"type": "string"}},
    ),
    _tool(
        "djconnect_recently_played",
        "Read recent listening-history items without changing playback.",
        {
            "item_type": {"type": "string", "enum": ["tracks", "albums", "artists", "playlists"]},
            "period": {"type": "string"},
            "limit": {"type": "integer"},
            "music_dna_key": {"type": "string"},
        },
    ),
    _tool(
        "djconnect_search_music",
        "Search music metadata without starting playback.",
        {
            "query": {"type": "string"},
            "media_type": {"type": "string", "enum": ["track", "album", "artist", "playlist"]},
            "limit": {"type": "integer"},
        },
        required=("query",),
    ),
    _tool("djconnect_list_outputs", "List available backend outputs/speakers.", {}),
    _tool(
        "djconnect_build_recommendations",
        "Build read-only personalized recommendations with optional Play Now actions.",
        {
            "text": {"type": "string"},
            "music_dna_key": {"type": "string"},
            "limit": {"type": "integer"},
        },
    ),
    _tool(
        "djconnect_prepare_playback_action",
        "Prepare a server-side confirmation action; does not mutate playback.",
        {
            "title": {"type": "string"},
            "subtitle": {"type": "string"},
            "uri": {"type": "string"},
            "context_uri": {"type": "string"},
            "offset_uri": {"type": "string"},
            "kind": {"type": "string", "enum": ["track", "album", "artist", "playlist", "track_mix"]},
            "uris": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"},
            "music_dna_key": {"type": "string"},
        },
        required=("title",),
    ),
    _tool(
        "djconnect_execute_confirmed_action",
        "Execute the latest server-side confirmed DJConnect action.",
        {"response": {"type": "string", "enum": ["yes", "no"]}, "music_dna_key": {"type": "string"}},
        required=("response",),
    ),
)
