"""Attach confirmed Session references to the existing Ask DJ authority and history."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from uuid import NAMESPACE_URL, uuid5

from .historical_projection_query import HistoricalProjectionQueryService
from .persistence import persistence_service
from .persistence.history import HistoricalProjectionRepository
from .session_runtime import session_runtime_manager


class SessionConversationError(ValueError):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code = code
        self.status = status


def history_question(text: str) -> str | None:
    """Bounded literal intent interpretation; no model, provider lookup or model SQL."""
    patterns = (
        r"(?:wanneer|heb ik).*?(?:naar|van)\s+(.+?)\s+(?:geluisterd|gehoord)(?:[?!.]|$)",
        r"(?:when|have i).*?(?:listen(?:ed)? to|hear(?:d)?)\s+(.+?)(?:[?!.]|$)",
        r"(?:wann).*?(?:von|zu)\s+(.+?)\s+(?:gehört|zugehört)(?:[?!.]|$)",
        r"(?:quand).*?(?:écouté|entendu)\s+(.+?)(?:[?!.]|$)",
        r"(?:cuándo).*?(?:escuchado|escuché)\s+(?:a\s+)?(.+?)(?:[?!.]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip(" \"'“”«»")[:200]
    return None


def _locale(payload: dict) -> str:
    family = str(payload.get("language") or payload.get("locale") or "en").split("-", 1)[0].lower()
    return family if family in {"en", "nl", "de", "fr", "es"} else "en"


def historical_answer(payload: dict, result: dict) -> dict:
    locale = _locale(payload)
    found = {
        "en": "Found in your saved sessions (observed playback; full listening is not proven):",
        "nl": "Gevonden in je bewaarde sessies (waargenomen playback; volledig beluisteren is niet bewezen):",
        "de": "In deinen gespeicherten Sessions gefunden (beobachtete Wiedergabe; vollständiges Anhören ist nicht belegt):",
        "fr": "Trouvé dans vos sessions conservées (lecture observée ; écoute complète non démontrée) :",
        "es": "Encontrado en tus sesiones guardadas (reproducción observada; no se demuestra una escucha completa):",
    }
    missing = {
        "en": "Not found in your saved sessions. This history does not cover all your listening.",
        "nl": "Niet gevonden in je bewaarde sessies. Deze geschiedenis dekt niet al je luistermomenten.",
        "de": "Nicht in deinen gespeicherten Sessions gefunden. Dieser Verlauf umfasst nicht alles, was du gehört hast.",
        "fr": "Non trouvé dans vos sessions conservées. Cet historique ne couvre pas toutes vos écoutes.",
        "es": "No encontrado en tus sesiones guardadas. Este historial no abarca todas tus escuchas.",
    }
    matches = result["matches"]
    lines = [found[locale]] if matches else [missing[locale]]
    lines.extend(f"{m['occurred_at']} · {m['text']}" for m in matches)
    return {
        "success": True,
        "text": "\n".join(lines),
        "dj_text": "\n".join(lines),
        "intent": {"intent": "saved_session_playback_history"},
        "historical_matches": matches,
        "navigation_actions": [m["open_action"] for m in matches],
        "playback_actions": [],
        "sources": [{"source": "djconnect_observed_session_history"}],
        "history_coverage": result["coverage"],
        "full_listens_proven": False,
        "repeat_counts_supported": False,
    }


def query_service(hass, history_manager=None) -> HistoricalProjectionQueryService:
    domain = hass.data.setdefault("djconnect", {})
    query = domain.get("session_history_query")
    if query is None:
        query = HistoricalProjectionQueryService(
            HistoricalProjectionRepository(persistence_service(hass)), history_manager
        )
        domain["session_history_query"] = query
    elif history_manager is not None:
        query._conversation_history = history_manager
    return query


async def async_session_exchange(
    hass,
    runtime,
    payload,
    *,
    profile_id,
    history_manager,
    delegate,
    validate_owner,
    persist_history=True,
):
    """One scoped invocation of existing Ask DJ, with retained-reference projection."""
    client_id = payload.get("client_message_id")
    if not isinstance(client_id, str) or not client_id.strip() or len(client_id) > 128:
        raise SessionConversationError("client_message_id_required", 400)
    context = payload.get("conversation_context") or {}
    if not isinstance(context, dict) or set(context) - {"session_id", "selected_entry"}:
        raise SessionConversationError("invalid_conversation_context", 400)
    session_id = context.get("session_id") or ""
    if not isinstance(session_id, str) or len(session_id) > 128:
        raise SessionConversationError("invalid_conversation_context", 400)
    history_scope = "profile:" + profile_id
    query = query_service(hass, history_manager)
    manager = session_runtime_manager(hass)
    locks = hass.data.setdefault("djconnect", {}).setdefault("session_conversation_locks", {})
    lock = locks.setdefault(profile_id, asyncio.Lock())
    text = str(payload.get("text") or payload.get("message") or "").strip()
    if not text or len(text) > 4000:
        raise SessionConversationError("invalid_conversation_text", 400)
    digest = hashlib.sha256(
        json.dumps({"context": context, "text": text}, sort_keys=True).encode()
    ).hexdigest()
    async with lock:
        selected = None
        target = context.get("selected_entry")
        if target is not None:
            if not isinstance(target, dict) or set(target) != {"session_id", "entry_id"}:
                raise SessionConversationError("invalid_conversation_context", 400)
            selected = await query.async_open_entry(
                profile_id, target["session_id"], target["entry_id"]
            )
        active = await manager.async_get_active(profile_id)
        if session_id and (active is None or active.session_id != session_id):
            raise SessionConversationError("session_context_changed")
        captured_playback = active.broadcast.state.playback.item_id if active else ""
        saved = (
            await history_manager.async_saved_exchange(history_scope, client_id)
            if persist_history
            else None
        )
        if saved:
            turn = saved["user_message"].get("session_turn", {})
            if turn.get("request_digest") != digest:
                raise SessionConversationError("client_message_conflict")
            result = {
                **saved["assistant_message"],
                "success": True,
                "dj_text": saved["assistant_message"]["text"],
                "deduplicated": True,
            }
        else:
            turn = {
                "turn_id": "turn-" + uuid5(NAMESPACE_URL, history_scope + ":" + client_id).hex,
                "request_digest": digest,
                "profile_id": profile_id,
                "context": context,
                "captured_playback_item_id": captured_playback,
                "input_type": "voice" if payload.get("input_type") == "voice" else "text",
            }
            artist = history_question(text)
            playback_result = (
                await query.async_find_playback(profile_id, artist=artist)
                if artist is not None
                else None
            )
            result = await delegate(
                payload, history_scope, selected["entry"] if selected else None, playback_result
            )
            if not result.get("success"):
                return result
            await validate_owner()
            current = await manager.async_get_active(profile_id)
            if session_id and (
                current is None
                or current.session_id != session_id
                or (
                    target is None and current.broadcast.state.playback.item_id != captured_playback
                )
            ):
                raise SessionConversationError("session_context_changed")
            if target is not None:
                await query.async_open_entry(profile_id, target["session_id"], target["entry_id"])
            if not persist_history:
                return {
                    **result,
                    "history_persisted": False,
                    "conversation": {
                        "schema_version": 1,
                        "turn_id": turn["turn_id"],
                        "context": context,
                        "entry_ids": [],
                        "history_scope": "private_ephemeral",
                        "input_type": turn["input_type"],
                    },
                }
            saved = await history_manager.async_append_exchange(
                history_scope, payload, result, session_turn=turn
            )
        ids = []
        if session_id:
            ids = await query._repository.async_append_entries(
                profile_id,
                session_id,
                [
                    {
                        "kind": kind,
                        "reference_id": turn["turn_id"] + ":" + role,
                        "body": {
                            "turn_id": turn["turn_id"],
                            "message_id": saved[role]["id"],
                            "history_scope": history_scope,
                        },
                        "occurred_at": saved[role]["created_at"],
                    }
                    for kind, role in [
                        ("conversation_user", "user_message"),
                        ("conversation_dj", "assistant_message"),
                    ]
                ],
            )
        return {
            **result,
            **saved,
            "conversation": {
                "schema_version": 1,
                "turn_id": turn["turn_id"],
                "context": context,
                "entry_ids": ids,
                "history_scope": "profile",
                "input_type": turn["input_type"],
            },
        }
