"""Best-effort Apple push notification support for DJConnect clients."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import time
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import (
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
)

STORE_KEY = "djconnect_push_registrations"
STORE_VERSION = 1
SUPPORTED_CLIENT_TYPES = {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}
SUPPORTED_ENVIRONMENTS = {"sandbox", "production"}
INVALID_TOKEN_REASONS = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}
EVENT_ASK_DJ_RESPONSE = "ask_dj_response"
EVENT_ASK_DJ_CONFIRM = "ask_dj_confirm"
EVENT_PLAYBACK_CHANGE = "playback_change"
_LOGGER = logging.getLogger(__name__)


class PushRegistrationManager:
    """Persist APNs registrations by HA user, DJConnect device and token hash."""

    def __init__(self, hass: Any | None = None, store: Any | None = None) -> None:
        self.hass = hass
        self._store = store if store is not None else self._create_store(hass)
        self._loaded = False
        self._data: dict[str, Any] = {"version": STORE_VERSION, "registrations": {}}

    @property
    def data(self) -> dict[str, Any]:
        """Return the in-memory push registration cache."""
        return self._data

    async def async_load(self) -> dict[str, Any]:
        if self._loaded:
            return self._data
        loaded = await self._store.async_load() if self._store is not None else None
        self._data = _normalize_store_data(loaded)
        self._loaded = True
        return self._data

    async def async_save(self) -> None:
        await self.async_load()
        if self._store is not None:
            await self._store.async_save(self._data)

    async def async_register(
        self,
        *,
        user_id: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Create or update one APNs token registration."""
        await self.async_load()
        device_id = _clean_text(payload.get("device_id"), 160)
        client_type = _clean_text(payload.get("client_type"), 32).lower()
        push_token = _clean_text(payload.get("push_token"), 4096)
        if not device_id or client_type not in SUPPORTED_CLIENT_TYPES or not push_token:
            return {"success": False, "error": "invalid_push_registration"}
        environment = _normalize_environment(payload.get("push_environment"))
        now = _now()
        key = _registration_key(user_id, device_id, client_type, push_token)
        categories = _clean_categories(payload.get("notification_categories"))
        registration = {
            "user_id": _user_key(user_id),
            "device_id": device_id,
            "client_type": client_type,
            "push_token": push_token,
            "push_token_hash": _token_hash(push_token),
            "push_environment": environment,
            "app_bundle_id": _clean_text(payload.get("app_bundle_id"), 200),
            "app_version": _clean_text(payload.get("app_version"), 64),
            "locale": _clean_text(payload.get("locale"), 32),
            "categories": categories,
            "created_at": now,
            "updated_at": now,
            "last_success_at": None,
            "last_error_code": None,
            "disabled": False,
            "invalid": False,
        }
        existing = self._data["registrations"].get(key)
        if isinstance(existing, dict):
            registration["created_at"] = existing.get("created_at") or now
            registration["last_success_at"] = existing.get("last_success_at")
        self._data["registrations"][key] = registration
        await self.async_save()
        _LOGGER.debug(
            "DJConnect push registered user=%s device_id=%s client_type=%s token=%s env=%s",
            _user_key(user_id),
            device_id,
            client_type,
            redact_push_token(push_token),
            environment,
        )
        return {
            "success": True,
            "push_supported": True,
            "push_registered": True,
            "push_environment": environment,
        }

    async def async_unregister(
        self,
        *,
        user_id: str | None,
        payload: dict[str, Any],
        disable: bool = True,
    ) -> dict[str, Any]:
        """Disable or remove one APNs token registration."""
        await self.async_load()
        device_id = _clean_text(payload.get("device_id"), 160)
        client_type = _clean_text(payload.get("client_type"), 32).lower()
        push_token = _clean_text(payload.get("push_token"), 4096)
        if not device_id or client_type not in SUPPORTED_CLIENT_TYPES or not push_token:
            return {"success": False, "error": "invalid_push_registration"}
        key = _registration_key(user_id, device_id, client_type, push_token)
        registration = self._data["registrations"].get(key)
        if isinstance(registration, dict) and disable:
            registration["disabled"] = True
            registration["updated_at"] = _now()
        else:
            self._data["registrations"].pop(key, None)
        await self.async_save()
        return {
            "success": True,
            "push_supported": True,
            "push_registered": False,
        }

    async def async_registrations_for_user(
        self,
        user_id: str | None,
        *,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return active registrations for one HA user."""
        await self.async_load()
        user_key = _user_key(user_id)
        registrations: list[dict[str, Any]] = []
        for item in self._data.get("registrations", {}).values():
            if not isinstance(item, dict):
                continue
            if item.get("user_id") != user_key:
                continue
            if item.get("disabled") or item.get("invalid"):
                continue
            if item.get("client_type") not in SUPPORTED_CLIENT_TYPES:
                continue
            categories = set(item.get("categories") or [])
            if event_type and categories and event_type not in categories:
                continue
            registrations.append(dict(item))
        return registrations

    async def async_status(
        self,
        *,
        user_id: str | None,
        device_id: str | None,
        client_type: str | None,
    ) -> dict[str, Any]:
        """Return redacted push status for a client."""
        await self.async_load()
        user_key = _user_key(user_id)
        client_type = str(client_type or "").strip().lower()
        matches = [
            item
            for item in self._data.get("registrations", {}).values()
            if isinstance(item, dict)
            and item.get("user_id") == user_key
            and item.get("device_id") == device_id
            and item.get("client_type") == client_type
            and not item.get("disabled")
            and not item.get("invalid")
        ]
        last = matches[-1] if matches else None
        return {
            "push_supported": client_type in SUPPORTED_CLIENT_TYPES,
            "push_registered": bool(matches),
            "push_environment": (last or {}).get("push_environment"),
            "last_push_error": _clean_text((last or {}).get("last_error_code"), 120) or None,
        }

    async def async_mark_success(self, registration: dict[str, Any]) -> None:
        await self._update_registration(registration, last_success_at=_now(), last_error_code=None)

    async def async_mark_error(
        self,
        registration: dict[str, Any],
        error_code: str,
        *,
        invalid: bool = False,
    ) -> None:
        await self._update_registration(
            registration,
            last_error_code=_clean_text(error_code, 120),
            invalid=bool(invalid),
            disabled=bool(invalid),
        )

    async def _update_registration(self, registration: dict[str, Any], **updates: Any) -> None:
        await self.async_load()
        key = _registration_key(
            registration.get("user_id"),
            registration.get("device_id"),
            registration.get("client_type"),
            registration.get("push_token"),
        )
        item = self._data.get("registrations", {}).get(key)
        if not isinstance(item, dict):
            return
        item.update(updates)
        item["updated_at"] = _now()
        await self.async_save()

    @staticmethod
    def _create_store(hass: Any) -> Store:
        return Store(hass, STORE_VERSION, STORE_KEY)


class APNsClient:
    """Small APNs HTTP/2 client using provider token authentication."""

    def __init__(self, hass: Any, manager: PushRegistrationManager) -> None:
        self.hass = hass
        self.manager = manager
        self._jwt: str | None = None
        self._jwt_created_at = 0.0

    def enabled(self) -> bool:
        return bool(self._team_id() and self._key_id() and self._private_key())

    async def send_event(
        self,
        *,
        user_id: str | None,
        event_type: str,
        history_revision: int | None = None,
        client_message_id: str | None = None,
        source_device_id: str | None = None,
    ) -> dict[str, Any]:
        """Send one safe DJConnect event to active APNs registrations."""
        if not self.enabled():
            return {"success": True, "push_supported": False, "sent": 0, "disabled": True}
        registrations = await self.manager.async_registrations_for_user(
            user_id,
            event_type=event_type,
        )
        sent = 0
        errors = 0
        payload = build_apns_payload(
            event_type=event_type,
            history_revision=history_revision,
            client_message_id=client_message_id,
            device_id=source_device_id,
        )
        for registration in registrations[:20]:
            ok = await self._send_to_registration(registration, payload)
            sent += 1 if ok else 0
            errors += 0 if ok else 1
        return {"success": True, "push_supported": True, "sent": sent, "errors": errors}

    async def _send_to_registration(self, registration: dict[str, Any], payload: dict[str, Any]) -> bool:
        token = str(registration.get("push_token") or "").strip()
        topic = self._topic(str(registration.get("client_type") or ""))
        if not token or not topic:
            await self.manager.async_mark_error(registration, "missing_topic_or_token", invalid=False)
            return False
        environment = _normalize_environment(
            registration.get("push_environment") or self._environment()
        )
        url = f"{_apns_base_url(environment)}/3/device/{token}"
        headers = {
            "authorization": f"bearer {self._provider_jwt()}",
            "apns-topic": topic,
            "apns-push-type": "alert",
            "apns-priority": "10",
        }
        try:
            session = async_get_clientsession(self.hass)
            async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                if 200 <= int(response.status) < 300:
                    await self.manager.async_mark_success(registration)
                    return True
                reason = await _apns_error_reason(response)
                invalid = int(response.status) in {400, 410} and reason in INVALID_TOKEN_REASONS
                await self.manager.async_mark_error(registration, reason or str(response.status), invalid=invalid)
                return False
        except Exception as exc:  # noqa: BLE001
            await self.manager.async_mark_error(registration, exc.__class__.__name__)
            return False

    def _provider_jwt(self) -> str:
        now = time.time()
        if self._jwt and now - self._jwt_created_at < 45 * 60:
            return self._jwt
        self._jwt = _sign_apns_jwt(
            team_id=self._team_id(),
            key_id=self._key_id(),
            private_key=self._private_key(),
        )
        self._jwt_created_at = now
        return self._jwt

    def _team_id(self) -> str:
        return _env("APNS_TEAM_ID")

    def _key_id(self) -> str:
        return _env("APNS_KEY_ID")

    def _private_key(self) -> str:
        value = _env("APNS_PRIVATE_KEY")
        if value:
            return value.replace("\\n", "\n")
        path = _env("APNS_PRIVATE_KEY_PATH")
        if not path:
            return ""
        try:
            return Path(path).read_text(encoding="utf-8")
        except OSError:
            return ""

    def _environment(self) -> str:
        return _normalize_environment(_env("APNS_ENVIRONMENT") or "sandbox")

    def _topic(self, client_type: str) -> str:
        if client_type == CLIENT_TYPE_MACOS:
            return _env("APNS_TOPIC_MACOS") or _env("APNS_TOPIC_IOS")
        if client_type == CLIENT_TYPE_WATCHOS:
            return _env("APNS_TOPIC_WATCHOS") or _env("APNS_TOPIC_IOS")
        return _env("APNS_TOPIC_IOS")


def build_apns_payload(
    *,
    event_type: str,
    history_revision: int | None = None,
    client_message_id: str | None = None,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Build a small privacy-safe APNs payload."""
    confirm = event_type == EVENT_ASK_DJ_CONFIRM
    payload: dict[str, Any] = {
        "aps": {
            "alert": {
                "title": "Ask DJ",
                "body": "Ask DJ wacht op je keuze." if confirm else "Ask DJ heeft geantwoord.",
            },
            "sound": "default",
            "thread-id": "djconnect.askdj",
            "category": "DJCONNECT_ASK_DJ_CONFIRM" if confirm else "DJCONNECT_ASK_DJ_RESPONSE",
        },
        "event_type": EVENT_ASK_DJ_CONFIRM if confirm else EVENT_ASK_DJ_RESPONSE,
        "open_target": "ask_dj",
    }
    if device_id:
        payload["device_id"] = _clean_text(device_id, 160)
    if client_message_id:
        payload["client_message_id"] = _clean_text(client_message_id, 120)
    if history_revision is not None:
        try:
            payload["history_revision"] = int(history_revision)
        except (TypeError, ValueError):
            pass
    return payload


async def async_send_event(
    hass: Any,
    *,
    user_id: str | None,
    event_type: str,
    history_revision: int | None = None,
    client_message_id: str | None = None,
    source_device_id: str | None = None,
) -> dict[str, Any]:
    """Send a DJConnect push event without breaking the caller."""
    manager = push_manager(hass)
    client = apns_client(hass, manager)
    try:
        return await client.send_event(
            user_id=user_id,
            event_type=event_type,
            history_revision=history_revision,
            client_message_id=client_message_id,
            source_device_id=source_device_id,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect push event failed best-effort: %s", exc.__class__.__name__)
        return {"success": True, "push_supported": client.enabled(), "sent": 0, "errors": 1}


def push_manager(hass: Any) -> PushRegistrationManager:
    data = hass.data.setdefault("djconnect", {})
    manager = data.get("push_manager")
    if manager is None:
        manager = PushRegistrationManager(hass)
        data["push_manager"] = manager
    return manager


def apns_client(hass: Any, manager: PushRegistrationManager | None = None) -> APNsClient:
    data = hass.data.setdefault("djconnect", {})
    client = data.get("apns_client")
    if client is None:
        client = APNsClient(hass, manager or push_manager(hass))
        data["apns_client"] = client
    return client


def redact_push_token(value: Any) -> str:
    token = str(value or "")
    if len(token) <= 10:
        return "<redacted>"
    return f"{token[:4]}...{token[-4:]}"


def _normalize_store_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"version": STORE_VERSION, "registrations": {}}
    registrations = data.get("registrations")
    return {
        "version": STORE_VERSION,
        "registrations": registrations if isinstance(registrations, dict) else {},
    }


def _registration_key(user_id: Any, device_id: Any, client_type: Any, push_token: Any) -> str:
    return "|".join(
        (
            _user_key(user_id),
            _clean_text(device_id, 160),
            _clean_text(client_type, 32).lower(),
            _token_hash(push_token),
        )
    )


def _token_hash(token: Any) -> str:
    return hashlib.sha256(str(token or "").encode()).hexdigest()


def _user_key(user_id: str | None) -> str:
    return str(user_id or "anonymous")


def _clean_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _clean_categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = {EVENT_ASK_DJ_RESPONSE, EVENT_ASK_DJ_CONFIRM, EVENT_PLAYBACK_CHANGE}
    return sorted({_clean_text(item, 64) for item in value if _clean_text(item, 64) in allowed})


def _normalize_environment(value: Any) -> str:
    environment = str(value or "sandbox").strip().lower()
    return environment if environment in SUPPORTED_ENVIRONMENTS else "sandbox"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _apns_base_url(environment: str) -> str:
    return "https://api.push.apple.com" if environment == "production" else "https://api.sandbox.push.apple.com"


async def _apns_error_reason(response: Any) -> str:
    try:
        data = await response.json()
        if isinstance(data, dict):
            return _clean_text(data.get("reason"), 120) or str(getattr(response, "status", "error"))
    except Exception:  # noqa: BLE001
        pass
    return str(getattr(response, "status", "error"))


def _sign_apns_jwt(*, team_id: str, key_id: str, private_key: str) -> str:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, utils
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("apns_crypto_unavailable") from exc
    header = {"alg": "ES256", "kid": key_id}
    claims = {"iss": team_id, "iat": int(time.time())}
    signing_input = ".".join(
        (
            _b64url(json.dumps(header, separators=(",", ":")).encode()),
            _b64url(json.dumps(claims, separators=(",", ":")).encode()),
        )
    )
    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise RuntimeError("apns_private_key_invalid")
    signature = key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    decoded = utils.decode_dss_signature(signature)
    raw_signature = decoded[0].to_bytes(32, "big") + decoded[1].to_bytes(32, "big")
    return f"{signing_input}.{_b64url(raw_signature)}"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _env(name: str) -> str:
    return str(os.environ.get(name) or "").strip()
