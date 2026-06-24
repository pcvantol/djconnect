"""Persistent cross-device Ask DJ history."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import uuid
from typing import Any

from .const import CONF_CLIENT_TYPE, CONF_DEVICE_ID, CONF_DEVICE_NAME

STORE_KEY = "djconnect_ask_dj_history"
STORE_VERSION = 1
MAX_MESSAGES_PER_USER = 1000
MAX_TEXT_LENGTH = 4000
MAX_ITEMS = 20
RETENTION_MESSAGE_COOLDOWN = timedelta(hours=1)
RETENTION_MESSAGE_TEXT = (
    "Ask DJ heeft de limiet van 1000 berichten bereikt. Oudste berichten worden verwijderd."
)


class AskDJHistoryManager:
    """Store user-scoped Ask DJ chat history for cross-device sync."""

    def __init__(self, hass: Any | None = None, store: Any | None = None) -> None:
        self.hass = hass
        self._store = store if store is not None else self._create_store(hass)
        self._loaded = False
        self._data: dict[str, Any] = {"version": STORE_VERSION, "global_clear_revision": 0, "users": {}}

    @property
    def data(self) -> dict[str, Any]:
        """Return the in-memory history cache."""
        return self._data

    async def async_load(self) -> dict[str, Any]:
        """Load persistent Ask DJ history from Home Assistant Store."""
        if self._loaded:
            return self._data
        loaded = await self._store.async_load() if self._store is not None else None
        self._data = _normalize_store_data(loaded)
        self._loaded = True
        return self._data

    async def async_save(self) -> None:
        """Persist compact Ask DJ history."""
        await self.async_load()
        if self._store is not None:
            await self._store.async_save(_compact_store_data(self._data))

    async def async_history(
        self,
        user_id: str | None,
        *,
        since_revision: int | None = None,
        limit: int = MAX_MESSAGES_PER_USER,
    ) -> dict[str, Any]:
        """Return bounded history for one HA user."""
        await self.async_load()
        user_key = _user_key(user_id)
        state = self._user_state(user_key)
        messages = sorted(
            list(state.get("messages") or []),
            key=lambda item: str(item.get("created_at") or ""),
        )
        if since_revision is not None and since_revision >= int(state.get("history_revision") or 0):
            messages = []
        else:
            messages = messages[-_limit(limit):]
        return {
            "success": True,
            "user_id": user_key,
            "history_revision": int(state.get("history_revision") or 0),
            "clear_revision": self._effective_clear_revision(state),
            **_history_limit_metadata(state),
            "messages": deepcopy(messages),
            "server_time": _now(),
        }

    async def async_clear(self, user_id: str | None) -> dict[str, Any]:
        """Clear history for one HA user and advance sync revisions."""
        await self.async_load()
        user_key = _user_key(user_id)
        state = self._user_state(user_key)
        state["history_revision"] = int(state.get("history_revision") or 0) + 1
        state["clear_revision"] = int(state.get("clear_revision") or 0) + 1
        state["messages"] = []
        _clear_trim_metadata(state)
        state["updated_at"] = _now()
        await self.async_save()
        return {
            "success": True,
            "user_id": user_key,
            "history_revision": state["history_revision"],
            "clear_revision": self._effective_clear_revision(state),
            **_history_limit_metadata(state),
            "messages": [],
            "server_time": _now(),
        }

    async def async_clear_all(self) -> dict[str, Any]:
        """Clear history for all app clients and advance a global clear revision."""
        await self.async_load()
        global_clear_revision = int(self._data.get("global_clear_revision") or 0) + 1
        self._data["global_clear_revision"] = global_clear_revision
        users = self._data.setdefault("users", {})
        if not users:
            users[_user_key(None)] = {"history_revision": 0, "clear_revision": 0, "messages": []}
        max_history_revision = global_clear_revision
        for state in users.values():
            if not isinstance(state, dict):
                continue
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
            state["clear_revision"] = max(int(state.get("clear_revision") or 0), global_clear_revision)
            state["messages"] = []
            _clear_trim_metadata(state)
            state["updated_at"] = _now()
            max_history_revision = max(max_history_revision, int(state["history_revision"]))
        await self.async_save()
        return {
            "success": True,
            "user_id": "all",
            "history_revision": max_history_revision,
            "clear_revision": global_clear_revision,
            "history_limit": MAX_MESSAGES_PER_USER,
            "history_trimmed_before": None,
            "history_trimmed_count": 0,
            "messages": [],
            "server_time": _now(),
        }

    async def async_append_exchange(
        self,
        user_id: str | None,
        request_payload: dict[str, Any],
        assistant_response: dict[str, Any],
    ) -> dict[str, Any]:
        """Append user and assistant messages, deduping client retries."""
        await self.async_load()
        user_key = _user_key(user_id)
        state = self._user_state(user_key)
        client_message_id = _clean_text(request_payload.get("client_message_id"))
        existing = self._find_exchange(state, client_message_id)
        if existing is not None:
            return {
                "success": True,
                "user_id": user_key,
                **existing,
                "history_revision": int(state.get("history_revision") or 0),
                "clear_revision": self._effective_clear_revision(state),
                **_history_limit_metadata(state),
                "server_time": _now(),
                "deduplicated": True,
            }

        user_message = _message_from_request(request_payload)
        assistant_message = _message_from_response(request_payload, assistant_response)
        exchange_id = _exchange_id(request_payload, user_message)
        user_message["exchange_id"] = exchange_id
        user_message["exchange_order"] = 0
        assistant_message["exchange_id"] = exchange_id
        assistant_message["exchange_order"] = 1
        state.setdefault("messages", []).extend([user_message, assistant_message])
        state["history_revision"] = int(state.get("history_revision") or 0) + 1
        trimmed = _apply_history_limit(state)
        if trimmed:
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
        state["updated_at"] = _now()
        await self.async_save()
        return {
            "success": True,
            "user_id": user_key,
            "user_message": deepcopy(user_message),
            "assistant_message": deepcopy(assistant_message),
            "messages": [deepcopy(user_message), deepcopy(assistant_message)],
            "history_revision": state["history_revision"],
            "clear_revision": self._effective_clear_revision(state),
            **_history_limit_metadata(state),
            "server_time": _now(),
        }

    async def async_append_assistant_message(
        self,
        user_id: str | None,
        request_payload: dict[str, Any],
        assistant_response: dict[str, Any],
    ) -> dict[str, Any]:
        """Append an assistant-only message, for ambient server-side Ask DJ events."""
        await self.async_load()
        user_keys = self._target_user_keys(user_id)
        assistant_message = _message_from_response(request_payload, assistant_response)
        client_message_id = _clean_text(request_payload.get("client_message_id"))
        if client_message_id:
            existing = self._find_assistant_message(user_keys, client_message_id)
            if existing is not None:
                first_state = self._user_state(user_keys[0])
                return {
                    "success": True,
                    "user_id": user_keys[0],
                    "assistant_message": deepcopy(existing),
                    "history_revision": int(first_state.get("history_revision") or 0),
                    "clear_revision": self._effective_clear_revision(first_state),
                    **_history_limit_metadata(first_state),
                    "server_time": _now(),
                    "deduplicated": True,
                }
        for user_key in user_keys:
            state = self._user_state(user_key)
            state.setdefault("messages", []).append(deepcopy(assistant_message))
            state["history_revision"] = int(state.get("history_revision") or 0) + 1
            trimmed = _apply_history_limit(state)
            if trimmed:
                state["history_revision"] = int(state.get("history_revision") or 0) + 1
            state["updated_at"] = _now()
        await self.async_save()
        first_state = self._user_state(user_keys[0])
        return {
            "success": True,
            "user_id": user_keys[0],
            "assistant_message": deepcopy(assistant_message),
            "history_revision": int(first_state.get("history_revision") or 0),
            "clear_revision": self._effective_clear_revision(first_state),
            **_history_limit_metadata(first_state),
            "server_time": _now(),
        }

    async def async_has_client_message_id(
        self,
        user_id: str | None,
        client_message_id: str,
    ) -> bool:
        """Return whether a message id already exists for the target history."""
        await self.async_load()
        message_id = _clean_text(client_message_id)
        if not message_id:
            return False
        return self._find_assistant_message(self._target_user_keys(user_id), message_id) is not None

    def recent_messages_for_prompt(
        self,
        user_id: str | None,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Return recent messages already loaded in memory for prompt context."""
        user_key = _user_key(user_id)
        state = (self._data.get("users") or {}).get(user_key) or {}
        messages = sorted(
            list(state.get("messages") or []),
            key=lambda item: str(item.get("created_at") or ""),
        )
        return deepcopy(messages[-_limit(limit):])

    def _user_state(self, user_id: str) -> dict[str, Any]:
        users = self._data.setdefault("users", {})
        if user_id not in users or not isinstance(users[user_id], dict):
            users[user_id] = {
                "history_revision": 0,
                "clear_revision": 0,
                "messages": [],
                "history_trimmed_before": None,
                "history_trimmed_count": 0,
            }
        state = users[user_id]
        state.setdefault("history_revision", 0)
        state.setdefault("clear_revision", 0)
        state.setdefault("messages", [])
        state.setdefault("history_trimmed_before", None)
        state.setdefault("history_trimmed_count", 0)
        return state

    def _effective_clear_revision(self, state: dict[str, Any]) -> int:
        return max(
            int(state.get("clear_revision") or 0),
            int(self._data.get("global_clear_revision") or 0),
        )

    def _target_user_keys(self, user_id: str | None) -> list[str]:
        if _clean_text(user_id):
            return [_user_key(user_id)]
        users = self._data.get("users") or {}
        keys = [str(key) for key in users.keys() if _clean_text(key)]
        return keys or [_user_key(None)]

    def _find_exchange(
        self,
        state: dict[str, Any],
        client_message_id: str,
    ) -> dict[str, Any] | None:
        if not client_message_id:
            return None
        messages = list(state.get("messages") or [])
        for index, message in enumerate(messages):
            if (
                message.get("role") == "user"
                and message.get("client_message_id") == client_message_id
            ):
                assistant = None
                for candidate in messages[index + 1 :]:
                    if candidate.get("role") == "assistant":
                        assistant = candidate
                        break
                return {
                    "user_message": deepcopy(message),
                    "assistant_message": deepcopy(assistant or {}),
                    "messages": [deepcopy(message), deepcopy(assistant or {})],
                }
        return None

    def _find_assistant_message(
        self,
        user_keys: list[str],
        client_message_id: str,
    ) -> dict[str, Any] | None:
        if not client_message_id:
            return None
        for user_key in user_keys:
            state = self._user_state(user_key)
            for message in state.get("messages") or []:
                if (
                    isinstance(message, dict)
                    and message.get("role") == "assistant"
                    and message.get("client_message_id") == client_message_id
                ):
                    return deepcopy(message)
        return None

    def _create_store(self, hass: Any | None) -> Any | None:
        if hass is None:
            return None
        try:
            from homeassistant.helpers.storage import Store
        except Exception:  # noqa: BLE001
            return None
        return Store(hass, STORE_VERSION, STORE_KEY)


def _message_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    return _compact_message(
        {
            "id": _server_message_id(),
            "client_message_id": _clean_text(payload.get("client_message_id")),
            "role": "user",
            "text": _clean_text(payload.get("text") or payload.get("message")),
            "created_at": now,
            "client_id": _client_id(payload),
            "client_type": _clean_text(payload.get(CONF_CLIENT_TYPE)),
            "status": "delivered",
            "images": [],
            "links": [],
            "sources": [],
            "audio_url": None,
            "playback_actions": [],
        }
    )


def _message_from_response(
    request_payload: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    text = _clean_text(
        response.get("dj_text")
        or response.get("text")
        or response.get("message")
    )
    return _compact_message(
        {
            "id": _server_message_id(),
            "client_message_id": _clean_text(request_payload.get("client_message_id")),
            "role": "assistant",
            "message_kind": _message_kind(response),
            "origin": _clean_text(response.get("origin")),
            "text": text,
            "created_at": _now(),
            "client_id": _client_id(request_payload),
            "client_type": _clean_text(request_payload.get(CONF_CLIENT_TYPE)),
            "status": "delivered" if response.get("success", True) else "error",
            "images": _compact_items(response.get("images")),
            "links": _compact_items(response.get("links")),
            "sources": _compact_items(response.get("sources")),
            "audio_url": _clean_text(response.get("audio_url")) or None,
            "playback_actions": _compact_items(response.get("playback_actions")),
            "intent": deepcopy(response.get("intent")) if response.get("intent") else None,
            "action": _clean_text(response.get("action")),
        }
    )


def _exchange_id(request_payload: dict[str, Any], user_message: dict[str, Any]) -> str:
    return (
        _clean_text(request_payload.get("client_message_id"))
        or _clean_text(user_message.get("id"))
        or _server_message_id()
    )


def _message_kind(response: dict[str, Any]) -> str:
    value = _clean_text(response.get("message_kind") or response.get("kind"))
    if value in {"system", "assistant", "error"}:
        return value
    intent = response.get("intent") if isinstance(response.get("intent"), dict) else {}
    if intent.get("intent") == "ambient_music_fact":
        return "system"
    return "assistant"


def _compact_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in message.items()
        if value not in ("", [], {}, None)
        or key in {"audio_url", "images", "links", "sources", "playback_actions"}
    }


def _compact_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value[:MAX_ITEMS]:
        if isinstance(item, dict):
            clean = {
                str(key): _clean_value(entry)
                for key, entry in item.items()
                if _clean_value(entry) not in ("", [], {}, None)
            }
            if clean:
                items.append(clean)
    return items


def _compact_store_data(data: dict[str, Any]) -> dict[str, Any]:
    users: dict[str, Any] = {}
    for user_id, state in (data.get("users") or {}).items():
        if not isinstance(state, dict):
            continue
        messages = [
            _compact_message(message)
            for message in state.get("messages", [])[-MAX_MESSAGES_PER_USER:]
            if isinstance(message, dict)
        ]
        users[_user_key(user_id)] = {
            "history_revision": int(state.get("history_revision") or 0),
            "clear_revision": int(state.get("clear_revision") or 0),
            "messages": messages,
            "updated_at": _clean_text(state.get("updated_at")),
            "history_trimmed_before": _clean_text(state.get("history_trimmed_before")) or None,
            "history_trimmed_count": int(state.get("history_trimmed_count") or 0),
        }
    return {
        "version": STORE_VERSION,
        "global_clear_revision": int(data.get("global_clear_revision") or 0),
        "users": users,
    }


def _normalize_store_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"version": STORE_VERSION, "global_clear_revision": 0, "users": {}}
    normalized = {
        "version": STORE_VERSION,
        "global_clear_revision": int(data.get("global_clear_revision") or 0),
        "users": {},
    }
    for user_id, state in (data.get("users") or {}).items():
        if not isinstance(state, dict):
            continue
        normalized["users"][_user_key(user_id)] = {
            "history_revision": int(state.get("history_revision") or 0),
            "clear_revision": int(state.get("clear_revision") or 0),
            "messages": [
                _compact_message(message)
                for message in state.get("messages", [])[-MAX_MESSAGES_PER_USER:]
                if isinstance(message, dict)
            ],
            "updated_at": _clean_text(state.get("updated_at")),
            "history_trimmed_before": _clean_text(state.get("history_trimmed_before")) or None,
            "history_trimmed_count": int(state.get("history_trimmed_count") or 0),
        }
    return normalized


def _client_id(payload: dict[str, Any]) -> str:
    return _clean_text(
        payload.get("client_id")
        or payload.get(CONF_DEVICE_ID)
        or payload.get(CONF_DEVICE_NAME)
    )


def _clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_clean_value(item) for item in value[:MAX_ITEMS]]
    if isinstance(value, dict):
        return {
            str(key): _clean_value(item)
            for key, item in value.items()
            if _clean_value(item) not in ("", [], {}, None)
        }
    return _clean_text(value)


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > MAX_TEXT_LENGTH:
        return text[:MAX_TEXT_LENGTH]
    return text


def _limit(value: int) -> int:
    try:
        return max(1, min(MAX_MESSAGES_PER_USER, int(value)))
    except (TypeError, ValueError):
        return MAX_MESSAGES_PER_USER


def _history_limit_metadata(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "history_limit": MAX_MESSAGES_PER_USER,
        "history_trimmed_before": _clean_text(state.get("history_trimmed_before")) or None,
        "history_trimmed_count": int(state.get("history_trimmed_count") or 0),
    }


def _clear_trim_metadata(state: dict[str, Any]) -> None:
    state["history_trimmed_before"] = None
    state["history_trimmed_count"] = 0


def _apply_history_limit(state: dict[str, Any]) -> bool:
    messages = [message for message in state.get("messages", []) if isinstance(message, dict)]
    if len(messages) <= MAX_MESSAGES_PER_USER:
        state["messages"] = messages
        state.setdefault("history_trimmed_before", None)
        state.setdefault("history_trimmed_count", 0)
        return False

    add_notice = _should_add_retention_message(messages)
    remove_count = len(messages) - MAX_MESSAGES_PER_USER + (1 if add_notice else 0)
    removed = messages[:remove_count]
    kept = messages[remove_count:]
    cutoff = _trim_cutoff_timestamp(kept, removed)
    if add_notice:
        kept.append(_retention_system_message())
    state["messages"] = kept[-MAX_MESSAGES_PER_USER:]
    state["history_trimmed_before"] = cutoff
    previous_count = int(state.get("history_trimmed_count") or 0)
    state["history_trimmed_count"] = previous_count + len(removed)
    return True


def _should_add_retention_message(messages: list[dict[str, Any]]) -> bool:
    latest = None
    for message in reversed(messages):
        if (
            message.get("role") == "assistant"
            and message.get("message_kind") == "system"
            and message.get("origin") == "history_retention"
        ):
            latest = _parse_time(message.get("created_at"))
            break
    if latest is None:
        return True
    return datetime.now(timezone.utc) - latest >= RETENTION_MESSAGE_COOLDOWN


def _retention_system_message() -> dict[str, Any]:
    return _compact_message(
        {
            "id": _server_message_id(),
            "role": "assistant",
            "message_kind": "system",
            "origin": "history_retention",
            "text": RETENTION_MESSAGE_TEXT,
            "created_at": _now(),
            "status": "delivered",
            "images": [],
            "links": [],
            "sources": [],
            "audio_url": None,
            "playback_actions": [],
            "intent": {
                "category": "system",
                "intent": "history_limit_reached",
            },
            "action": "none",
        }
    )


def _trim_cutoff_timestamp(kept: list[dict[str, Any]], removed: list[dict[str, Any]]) -> str:
    for message in kept:
        timestamp = _clean_text(message.get("created_at"))
        if timestamp:
            return timestamp
    for message in reversed(removed):
        timestamp = _clean_text(message.get("created_at"))
        if timestamp:
            return timestamp
    return _now()


def _parse_time(value: Any) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _server_message_id() -> str:
    return f"server-{uuid.uuid4()}"


def _user_key(user_id: Any) -> str:
    cleaned = _clean_text(user_id)
    return cleaned or "anonymous"
