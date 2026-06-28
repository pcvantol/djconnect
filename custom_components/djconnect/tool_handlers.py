"""DJConnect AI/conversation tool handlers."""
from __future__ import annotations

import sys
from typing import Any

from homeassistant.core import HomeAssistant

from .use_cases import run_music_command

_DEFAULT_RUN_MUSIC_COMMAND = run_music_command


async def async_call_ai_tool(
    hass: HomeAssistant,
    runtime: Any,
    tool_name: str,
    parameters: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Call an explicitly exposed DJConnect AI tool."""
    params = dict(parameters or {})
    if tool_name == "djconnect_track_insight":
        from .track_insight import async_track_insight_tool

        return await async_track_insight_tool(hass, runtime, **params)
    if tool_name == "djconnect_now_playing":
        return await _now_playing(hass, runtime)
    if tool_name == "djconnect_music_dna_summary":
        return await _music_dna_summary(runtime, params, user_id=user_id)
    if tool_name == "djconnect_recently_played":
        return await _recently_played(hass, runtime, params, user_id=user_id)
    if tool_name == "djconnect_search_music":
        return await _search_music(hass, runtime, params)
    if tool_name == "djconnect_list_outputs":
        return await _list_outputs(hass, runtime)
    if tool_name == "djconnect_build_recommendations":
        return await _build_recommendations(hass, runtime, params, user_id=user_id)
    if tool_name == "djconnect_prepare_playback_action":
        return await _prepare_playback_action(runtime, params, user_id=user_id)
    if tool_name == "djconnect_execute_confirmed_action":
        return await _execute_confirmed_action(hass, runtime, params, user_id=user_id)
    raise ValueError(f"Unsupported DJConnect AI tool: {tool_name}")


async def _now_playing(hass: HomeAssistant, runtime: Any) -> dict[str, Any]:
    result = await _run_music_command(hass, runtime, "status")
    playback = result.get("playback") if isinstance(result, dict) else {}
    return {
        "success": True,
        "type": "now_playing",
        "playback": playback if isinstance(playback, dict) else {},
        "sources": [{"source": "djconnect_backend", "kind": "source"}],
    }


async def _music_dna_summary(runtime: Any, params: dict[str, Any], *, user_id: str | None) -> dict[str, Any]:
    memory = getattr(runtime, "memory", None)
    context_getter = getattr(memory, "async_context_for_runtime", None)
    if not callable(context_getter):
        return {"success": False, "error": "music_dna_unavailable", "message": "Music DNA is unavailable."}
    context = await context_getter(runtime, params, user_id=user_id)
    from .music_dna import prompt_context_text

    text = prompt_context_text(context) or "Music DNA is nog leeg."
    return {
        "success": True,
        "type": "music_dna_summary",
        "text": text,
        "music_dna_key": context.get("music_dna_key"),
        "music_dna": context.get("memory") or {},
        "sources": [{"source": "djconnect_music_dna", "kind": "source", "title": "Music DNA"}],
    }


async def _recently_played(
    hass: HomeAssistant,
    runtime: Any,
    params: dict[str, Any],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    item_type = str(params.get("item_type") or "tracks").strip().lower()
    limit = max(1, min(int(params.get("limit") or 50), 50))
    result = await _run_music_command(
        hass,
        runtime,
        "recently_played",
        {"limit": limit},
    )
    tracks = result.get("tracks") if isinstance(result, dict) else []
    return {
        "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
        "type": "recently_played",
        "item_type": item_type,
        "tracks": tracks if isinstance(tracks, list) else [],
        "raw": result if isinstance(result, dict) else {},
        "sources": [{"source": "spotify_recently_played", "kind": "source"}],
    }


async def _search_music(hass: HomeAssistant, runtime: Any, params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query") or "").strip()
    media_type = str(params.get("media_type") or "track").strip().lower()
    if not query:
        return {"success": False, "error": "missing_query", "message": "query is required."}
    command = {
        "album": "search_albums",
        "artist": "artist_profile",
        "playlist": "search_playlists",
        "track": "search_tracks",
    }.get(media_type, "search_tracks")
    value: Any = {"query": query, "limit": int(params.get("limit") or 5)}
    if command == "artist_profile":
        value = query
    result = await _run_music_command(hass, runtime, command, value, play=False)
    return {
        "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
        "type": "music_search",
        "media_type": media_type,
        "query": query,
        "result": result,
        "sources": [{"source": "djconnect_backend_search", "kind": "source"}],
        "playback_actions": [],
    }


async def _list_outputs(hass: HomeAssistant, runtime: Any) -> dict[str, Any]:
    result = await _run_music_command(hass, runtime, "devices")
    outputs = []
    if isinstance(result, dict):
        value = result.get("devices") or result.get("outputs") or result.get("available_outputs") or []
        outputs = value if isinstance(value, list) else []
    return {
        "success": True,
        "type": "outputs",
        "outputs": outputs,
        "items": outputs,
        "sources": [{"source": "djconnect_backend_outputs", "kind": "source"}],
    }


async def _build_recommendations(
    hass: HomeAssistant,
    runtime: Any,
    params: dict[str, Any],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    memory = getattr(runtime, "memory", None)
    context_getter = getattr(memory, "async_context_for_runtime", None)
    music_dna = {}
    if callable(context_getter):
        context = await context_getter(runtime, params, user_id=user_id)
        music_dna = context.get("memory") if isinstance(context, dict) else {}
    try:
        profile_result = await _run_music_command(hass, runtime, "listening_profile")
    except Exception:  # noqa: BLE001
        profile_result = {}
    profile = profile_result.get("profile") if isinstance(profile_result, dict) else {}
    return {
        "success": True,
        "type": "recommendation_candidates",
        "music_dna": music_dna if isinstance(music_dna, dict) else {},
        "listening_profile": profile if isinstance(profile, dict) else {},
        "spotify_profile": profile if isinstance(profile, dict) else {},
        "sources": [
            {"source": "djconnect_music_dna", "kind": "source", "title": "Music DNA"},
            {"source": "spotify_top_tracks_short_term", "kind": "source", "title": "Spotify top tracks"},
        ],
        "playback_actions": [],
    }


async def _prepare_playback_action(
    runtime: Any,
    params: dict[str, Any],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    memory = getattr(runtime, "memory", None)
    storer = getattr(memory, "async_store_pending_followup", None)
    if not callable(storer):
        return {"success": False, "error": "music_dna_unavailable", "message": "Music DNA is unavailable."}
    action = _playback_action_from_params(params)
    pending = await storer(
        runtime,
        {
            "type": "ai_tool_confirmation",
            "question": f"Wil je {action.get('title') or 'deze muziek'} afspelen?",
            "proposed_intent": "ai_tool_playback_confirmation",
            "proposed_action": "djconnect_execute_prepared_playback",
            "proposed_payload": action,
        },
        params,
        user_id=user_id,
    )
    return {
        "success": True,
        "type": "prepared_playback_action",
        "pending_action": pending,
        "confirmation_actions": [
            {"kind": "confirmation", "response_value": "yes", "label": "Ja"},
            {"kind": "confirmation", "response_value": "no", "label": "Nee"},
        ],
        "playback_actions": [],
    }


async def _execute_confirmed_action(
    hass: HomeAssistant,
    runtime: Any,
    params: dict[str, Any],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    response = str(params.get("response") or "").strip().lower()
    if response not in {"yes", "ja"}:
        return {"success": True, "type": "confirmed_action", "action": "declined", "message": "Niet uitgevoerd."}
    memory = getattr(runtime, "memory", None)
    consumer = getattr(memory, "async_consume_pending_followup", None)
    if not callable(consumer):
        return {"success": False, "error": "music_dna_unavailable", "message": "Music DNA is unavailable."}
    pending = await consumer(runtime, params, user_id=user_id)
    action = pending.get("proposed_payload") if isinstance(pending, dict) else {}
    if not isinstance(action, dict) or pending.get("proposed_action") != "djconnect_execute_prepared_playback":
        return {"success": False, "error": "no_pending_action", "message": "No matching confirmed action is pending."}
    return await _execute_playback_action(hass, runtime, action)


async def _execute_playback_action(hass: HomeAssistant, runtime: Any, action: dict[str, Any]) -> dict[str, Any]:
    uris = [str(uri).strip() for uri in action.get("uris") or [] if str(uri or "").strip()]
    context_uri = str(action.get("context_uri") or "").strip()
    uri = str(action.get("uri") or "").strip()
    if uris:
        result = await _run_music_command(hass, runtime, "play_uris", {"uris": uris}, play=True)
    elif context_uri:
        result = await _run_music_command(
            hass,
            runtime,
            "play_context_at",
            {"context_uri": context_uri, "offset_uri": action.get("offset_uri") or uri},
            play=True,
        )
    elif uri:
        result = await _run_music_command(hass, runtime, "play_uris", {"uris": [uri]}, play=True)
    else:
        return {"success": False, "error": "missing_playback_target", "message": "No playable URI was confirmed."}
    return {
        "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
        "type": "confirmed_action",
        "action": "executed",
        "result": result,
    }


def _playback_action_from_params(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "title": str(params.get("title") or "").strip(),
            "subtitle": str(params.get("subtitle") or "").strip(),
            "uri": str(params.get("uri") or "").strip(),
            "context_uri": str(params.get("context_uri") or "").strip(),
            "offset_uri": str(params.get("offset_uri") or "").strip(),
            "kind": str(params.get("kind") or "track").strip(),
            "uris": [str(uri).strip() for uri in params.get("uris") or [] if str(uri or "").strip()],
            "reason": str(params.get("reason") or "").strip(),
            "music_dna_key": str(params.get("music_dna_key") or "").strip(),
        }.items()
        if value not in ("", [], None)
    }


async def _run_music_command(
    hass: HomeAssistant,
    runtime: Any,
    command: str,
    value: Any = None,
    *,
    play: bool | None = None,
) -> dict[str, Any]:
    ask_dj_module = sys.modules.get("custom_components.djconnect.ask_dj")
    ask_dj_runner = getattr(ask_dj_module, "run_music_command", None)
    if callable(ask_dj_runner) and ask_dj_runner is not _DEFAULT_RUN_MUSIC_COMMAND:
        return await ask_dj_runner(hass, runtime, command, value, play=play)
    return await run_music_command(hass, runtime, command, value, play=play)
