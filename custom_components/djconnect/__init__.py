from __future__ import annotations

import asyncio
from datetime import date, timedelta
import json
import logging
import re
import secrets
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import voluptuous as vol
from aiohttp import ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

try:
    from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
except ImportError:  # pragma: no cover - test stubs without HA event helpers
    async_track_time_change = None
    async_track_time_interval = None

from .const import (
    API_COMMAND,
    API_ASK_DJ,
    API_ASK_DJ_HISTORY,
    API_ASK_DJ_HISTORY_CLEAR,
    API_ASK_DJ_MESSAGE,
    API_EVENT,
    API_PAIR,
    API_PUSH_REGISTER,
    API_PUSH_UNREGISTER,
    API_SPOTIFY_CALLBACK,
    API_STATUS,
    API_SESSION_START,
    API_SESSION_END,
    API_SESSION_ACTIVE,
    API_SESSION_BROADCAST,
    API_TRACK_INSIGHT,
    API_TTS,
    API_VIBECAST,
    API_VOICE,
    CONF_API_BASE_URL,
    CLIENT_TYPE_CONVERSATION_AGENT,
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CLIENT_TYPE_RASPBERRY_PI,
    CLIENT_TYPE_WINDOWS,
    CLIENT_TYPES,
    CONF_ASSIST_PIPELINE_ID,
    CONF_CLIENT_TYPE,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF,
    CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT,
    CONF_DEVICE_ID,
    CONF_DEVICE_LANGUAGE,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TOKEN,
    CONF_DJCONNECT_INSTALL_TOKEN,
    CONF_HA_EXTERNAL_URL,
    CONF_HA_INSTALL_ID,
    CONF_LAST_PUSH_STATUS,
    CONF_LOCAL_URL,
    CONF_MUSIC_BACKEND,
    CONF_MUSIC_ASSISTANT_PLAYER,
    CONF_PAIR_CODE,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_MARKET,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_SCOPES,
    DEFAULT_API_BASE_URL,
    DEFAULT_DEVICE_LANGUAGE,
    DEFAULT_CLIENT_TYPE,
    DEFAULT_SPOTIFY_MARKET,
    DEFAULT_SPOTIFY_SCOPES,
    DOMAIN,
    PLATFORMS,
    VERSION,
)
from .central_api import async_ensure_install_token, ensure_ha_install_id
from .http import (
    DJConnectCommandView,
    DJConnectTransportCapabilitiesView,
    DJConnectAskDjHistoryClearView,
    DJConnectAskDjHistoryExportView,
    DJConnectAskDjHistoryView,
    DJConnectAskDjIdleSuggestionView,
    DJConnectAskDjMessageView,
    DJConnectAskDjView,
    DJConnectEventView,
    DJConnectImageProxyView,
    DJConnectMusicDiscoveryFeedbackView,
    DJConnectMusicDiscoveryPlayView,
    DJConnectMusicDiscoveryRefreshView,
    DJConnectMusicDiscoveryView,
    DJConnectMusicDnaClearView,
    DJConnectMusicDnaExportView,
    DJConnectMusicDnaImportView,
    DJConnectMusicDnaProfileView,
    DJConnectMusicDnaSettingsView,
    DJConnectPairView,
    DJConnectPushBootstrapView,
    DJConnectPushRegisterView,
    DJConnectPushUnregisterView,
    DJConnectSpotifyCallbackView,
    DJConnectStatusView,
    DJConnectSessionStartView,
    DJConnectSessionEndView,
    DJConnectActiveSessionView,
    DJConnectSessionBroadcastSnapshotView,
    DJConnectSessionBroadcastTokenView,
    DJConnectSessionBroadcastWebSocketView,
    DJConnectTrackInsightView,
    DJConnectTtsView,
    DJConnectVibeCastView,
    DJConnectVoiceDebugView,
    DJConnectVoiceView,
)
from .assist_stt import detect_stt_support
from .dj_response import async_send_dj_response, async_send_dj_response_best_effort
from .ha_urls import async_ha_url_payload
from .ask_dj import async_handle_ask_dj
from .ask_dj_history import AskDJHistoryManager
from .music_dna import MusicDNAManager
from .push import (
    EVENT_ASK_DJ_CONFIRM as EVENT_ASK_DJ_CONFIRM,
    EVENT_MUSIC_DISCOVERY_READY,
    EVENT_TEST_PUSH,
    SUPPORTED_CLIENT_TYPES as APNS_SUPPORTED_CLIENT_TYPES,
    async_register as async_register_push,
    async_send_event as async_send_push_event,
    async_unregister as async_unregister_push,
    relay_configured,
    should_send_push,
)
from .persistence import (
    PersistentSessionRepository,
    PersistentSessionStartupReconciler,
    HistoricalProjectionRepository,
    async_initialize_persistence,
    async_shutdown_persistence,
    persistence_service,
)
from .repairs import async_create_fixable_issues
from .spotify_oauth import (
    build_authorize_url,
    build_redirect_uri,
    create_code_verifier,
    ensure_spotify_scopes,
)
from .track_insight import TRACK_INSIGHT_EVENT
from .use_cases import music_backend_metadata, run_music_command, run_text_command
from .websocket_api import async_register as async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

DEFAULT_TEST_COMMAND = "Welk nummer draait er nu?"
DEFAULT_TEST_TTS_TEXT = (
    "Daar gaan we. DJConnect is gekoppeld, de stem werkt, "
    "en ik sta klaar voor je volgende plaat."
)
MDNS_SERVICE_TYPE = "_djconnect._tcp.local."
STATUS_SECRET_KEYS = {
    "device_token",
    "spotify_refresh_token",
    "refresh_token",
    CONF_CENTRAL_API_BOOTSTRAP_PROOF,
    "bootstrap_proof",
}
DEBUG_REDACT_KEY_PARTS = (
    "token",
    "password",
    "secret",
    "proof",
    "authorization",
    "prompt",
    "response",
    "history",
    "memory",
    "raw_audio",
)
REAL_DJCONNECT_DEVICE_ID_PATTERN = re.compile(
    r"djconnect-(?:lilygo-t-embed-s3|esp32-s3-box-3|lilygo)-[0-9A-Fa-f]{12}"
    r"|djconnect-(?:ios|macos|watchos|raspberry-pi|windows)-[A-Za-z0-9]{12}"
)
CONF_LAST_DEVICE_STATUS = "last_device_status"
APP_PAIRING_PENDING_KEY = "config_flow_app_pairing_pending"
MUSIC_DISCOVERY_DAILY_PUSH_HOUR = 8


def _is_empty_status_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _redact_debug_payload(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(secret in normalized for secret in DEBUG_REDACT_KEY_PARTS):
                result[key] = "<redacted>"
            else:
                result[key] = _redact_debug_payload(item)
        return result
    if isinstance(value, list):
        return [_redact_debug_payload(item) for item in value]
    return value


def _merge_cached_device_status(
    device_status: dict[str, Any],
    update: dict[str, Any],
    *,
    source: str,
    allow_empty_keys: set[str] | None = None,
) -> None:
    """Merge device status without erasing known values from sparse payloads."""
    allow_empty_keys = allow_empty_keys or set()
    if not update:
        _LOGGER.debug("Ignoring empty %s payload for device sensor update", source)
        return
    _LOGGER.debug("Merging %s payload without resetting missing fields", source)
    for key, value in update.items():
        if key in STATUS_SECRET_KEYS:
            continue
        if key == "ha_pairing_status" and value in (None, "", "unknown"):
            continue
        if _is_empty_status_value(value) and key in device_status and key not in allow_empty_keys:
            continue
        device_status[key] = value


def _runtime_last_command_value(runtime: Any) -> str | None:
    for key in ("last_dj_text", "last_text", "last_stt_text"):
        value = getattr(runtime, key, None)
        if value not in (None, ""):
            return str(value)
    return None


def _runtime_last_track_value(runtime: Any) -> str | None:
    playback = getattr(runtime, "last_playback", None) or {}
    if isinstance(playback, dict):
        for key in ("track_name", "title", "name", "track"):
            value = playback.get(key)
            if value not in (None, ""):
                return str(value)
        response = playback.get("device_response") or {}
        if isinstance(response, dict):
            current = response.get("playback") or response
            if isinstance(current, dict):
                for key in ("track_name", "title", "name", "track"):
                    value = current.get(key)
                    if value not in (None, ""):
                        return str(value)
    resolved = getattr(runtime, "last_resolved_media", None) or {}
    if isinstance(resolved, dict):
        for key in ("track_name", "title", "name", "artist", "artist_name"):
            value = resolved.get(key)
            if value not in (None, ""):
                return str(value)
    return None


def _cache_runtime_last_values(runtime: Any) -> None:
    """Mirror non-empty runtime command/playback values into cached device status."""
    status = getattr(runtime, "device_status", None)
    if not isinstance(status, dict):
        return
    last_command = _runtime_last_command_value(runtime)
    if last_command:
        status["last_command"] = last_command
    last_dj_text = getattr(runtime, "last_dj_text", None)
    if last_dj_text not in (None, ""):
        status["last_dj_text"] = str(last_dj_text)
    last_corrected_text = getattr(runtime, "last_corrected_text", None)
    if last_corrected_text not in (None, ""):
        status["last_corrected_text"] = str(last_corrected_text)
    last_track = _runtime_last_track_value(runtime)
    if last_track:
        status["last_track"] = last_track


def _runtime_update_signature(runtime: Any) -> str:
    """Return a stable signature for state visible through DJConnect entities."""
    payload = {
        "last_text": getattr(runtime, "last_text", None),
        "last_intent": getattr(runtime, "last_intent", None),
        "last_dj_text": getattr(runtime, "last_dj_text", None),
        "last_dj_spoken": getattr(runtime, "last_dj_spoken", None),
        "last_dj_displayed": getattr(runtime, "last_dj_displayed", None),
        "last_dj_response_at": getattr(runtime, "last_dj_response_at", None),
        "last_error": getattr(runtime, "last_error", None),
        "last_playback": _stable_entity_payload(getattr(runtime, "last_playback", None)),
        "last_stt_text": getattr(runtime, "last_stt_text", None),
        "last_corrected_text": getattr(runtime, "last_corrected_text", None),
        "last_spotify_search": getattr(runtime, "last_spotify_search", None),
        "last_resolved_media": getattr(runtime, "last_resolved_media", None),
        "device_status": _stable_entity_payload(getattr(runtime, "device_status", None)),
        "ota_in_progress": getattr(runtime, "ota_in_progress", None),
        "ota_last_error": getattr(runtime, "ota_last_error", None),
    }
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _stable_entity_payload(value: Any) -> Any:
    """Return entity-visible runtime data without volatile playback progress."""
    if isinstance(value, dict):
        return {
            key: _stable_entity_payload(item)
            for key, item in value.items()
            if key
            not in {
                "progress_ms",
                "position_ms",
                "timestamp",
                "server_time",
                "fetched_at",
                "refreshed_at",
            }
        }
    if isinstance(value, list):
        return [_stable_entity_payload(item) for item in value]
    return value


@dataclass
class DJConnectRuntime:
    entry: ConfigEntry
    last_text: str | None = None
    last_intent: dict[str, Any] | None = None
    last_dj_text: str | None = None
    last_dj_spoken: bool | None = None
    last_dj_displayed: bool | None = None
    last_dj_response_at: float | None = None
    last_error: str | None = None
    last_playback: dict[str, Any] | None = None
    last_stt_text: str | None = None
    last_corrected_text: str | None = None
    last_spotify_search: dict[str, Any] | None = None
    last_resolved_media: dict[str, Any] | None = None
    device_status: dict[str, Any] = field(default_factory=dict)
    device_token: str | None = None
    pairing_code: str | None = None
    pairing_device_id: str | None = None
    ota_in_progress: bool = False
    ota_last_error: str | None = None
    latest_spotify_refresh_token: str | None = None
    memory: Any | None = None
    listeners: list = field(default_factory=list)
    _last_update_signature: str | None = None

    @property
    def config(self) -> dict[str, Any]:
        data = dict(self.entry.data)
        data.update(dict(self.entry.options))
        return data

    def update(self, **kwargs: Any) -> None:
        should_notify = not kwargs
        for key, value in kwargs.items():
            if getattr(self, key, None) != value:
                should_notify = True
            setattr(self, key, value)
        _cache_runtime_last_values(self)
        signature = _runtime_update_signature(self)
        if signature == self._last_update_signature:
            should_notify = False
        self._last_update_signature = signature
        if not should_notify:
            return
        for listener in list(self.listeners):
            listener()

    def ensure_device_token(self) -> str:
        if not self.device_token:
            self.device_token = secrets.token_urlsafe(32)
        return self.device_token

    async def async_device_local_url(self, hass: HomeAssistant) -> str | None:
        """Return the best known device base URL."""
        local_url = (
            self.device_status.get("local_url")
            or self.device_status.get("ota_url")
            or self.config.get(CONF_LOCAL_URL)
        )
        if local_url:
            local_url = str(local_url)
            if not _is_pair_code_mdns_url(local_url):
                ip_fallback_url = _status_ip_fallback_url(self.device_status, local_url)
                if ip_fallback_url and _is_mdns_url(local_url):
                    self.device_status["local_url"] = ip_fallback_url
                    return ip_fallback_url
                return local_url
            _LOGGER.debug("DJConnect ignoring pair-code based mDNS URL: %s", local_url)
        discovered_url = await async_discover_device_url(hass, self)
        if discovered_url:
            self.device_status["local_url"] = discovered_url
            return discovered_url
        ip_fallback_url = _status_ip_fallback_url(self.device_status, local_url)
        if ip_fallback_url:
            self.device_status["local_url"] = ip_fallback_url
            return ip_fallback_url
        device_id = self.device_status.get("device_id") or self.pairing_device_id
        device_id = device_id or self.config.get(CONF_DEVICE_ID)
        return _device_id_mdns_fallback_url(device_id)

    def device_headers(self, *, include_device_id: bool = True) -> dict[str, str]:
        """Build headers for authenticated ESP requests."""
        headers = {"Content-Type": "application/json"}
        if self.device_token:
            headers["Authorization"] = f"Bearer {self.device_token}"
        if include_device_id and self.device_status.get("device_id"):
            headers["X-DJConnect-Device-ID"] = self.device_status["device_id"]
        return headers

    def authorize_device_request(
        self,
        headers: Any,
        body_device_id: str | None = None,
        client_type: str | None = None,
    ) -> bool:
        auth = str(headers.get("Authorization", "") or "").strip()
        token = auth.removeprefix("Bearer ").strip()
        header_device = str(headers.get("X-DJConnect-Device-ID") or "").strip()
        body_device = str(body_device_id or "").strip()
        token_match = bool(self.device_token and token == self.device_token)
        expected_present = bool(self.device_token)
        device_id = header_device or body_device or None
        _LOGGER.debug(
            "DJConnect device auth: device_id=%s auth=%s token_match=%s "
            "expected_token_present=%s entry_id=%s",
            device_id,
            "present" if auth else "missing",
            token_match,
            expected_present,
            getattr(self.entry, "entry_id", None),
        )
        if not token_match:
            self._log_device_auth_failure(
                "missing_bearer_token" if not token else "bearer_token_mismatch_for_entry",
                header_device,
                body_device,
                client_type,
                bool(token),
            )
            return False
        if device_id and client_type and not _device_id_matches_client_type(
            device_id,
            client_type,
        ):
            self._log_device_auth_failure(
                "device_id_client_type_mismatch",
                header_device,
                body_device,
                client_type,
                bool(token),
            )
            return False
        known_device = self.device_status.get("device_id") or self.pairing_device_id
        if known_device and header_device and not _device_id_matches(known_device, header_device):
            self._log_device_auth_failure(
                "header_device_id_mismatch",
                header_device,
                body_device,
                client_type,
                bool(token),
            )
            return False
        if known_device and body_device and not _device_id_matches(known_device, body_device):
            self._log_device_auth_failure(
                "body_device_id_mismatch",
                header_device,
                body_device,
                client_type,
                bool(token),
            )
            return False
        self._learn_device_id(header_device or body_device)
        return True

    def _log_device_auth_failure(
        self,
        reason: str,
        header_device_id: str,
        body_device_id: str,
        client_type: str | None,
        token_present: bool,
    ) -> None:
        known_device = self.device_status.get("device_id") or self.pairing_device_id
        received_device = header_device_id or body_device_id or ""
        _LOGGER.warning(
            "DJConnect client request rejected: reason=%s received_device_id=%s "
            "known_device_id=%s client_type=%s bearer_token_present=%s entry_id=%s",
            reason,
            received_device or "missing",
            known_device or "missing",
            str(client_type or "").strip() or "missing",
            token_present,
            getattr(self.entry, "entry_id", None),
        )

    def _learn_device_id(self, device_id: str | None) -> None:
        """Adopt the ESP's real device ID after setup-code based pairing."""
        if not device_id or not _is_real_djconnect_device_id(device_id):
            return
        known_device = self.device_status.get("device_id") or self.pairing_device_id
        if known_device == device_id:
            return
        if known_device and not (
            _is_setup_code_device_id(str(known_device))
            or _is_real_djconnect_device_id(str(known_device))
        ):
            return
        self.pairing_device_id = device_id
        self.device_status["device_id"] = device_id
        _LOGGER.debug(
            "DJConnect learned real device_id=%s for entry_id=%s",
            device_id,
            getattr(self.entry, "entry_id", None),
        )

    def get_current_spotify_credentials(self) -> dict[str, Any]:
        """Return canonical latest Spotify credentials for HA backend use."""
        conf = self.config
        client_id = str(conf.get(CONF_SPOTIFY_CLIENT_ID) or "").strip()
        refresh_token = str(
            self.latest_spotify_refresh_token
            or conf.get(CONF_SPOTIFY_REFRESH_TOKEN)
            or ""
        ).strip()
        if not client_id or not refresh_token:
            return {}
        scopes = str(conf.get(CONF_SPOTIFY_SCOPES, DEFAULT_SPOTIFY_SCOPES)).split()
        market = conf.get(CONF_SPOTIFY_MARKET, DEFAULT_SPOTIFY_MARKET)
        return {
            "client_id": client_id,
            "refresh_token": refresh_token,
            "spotify_client_id": client_id,
            "spotify_refresh_token": refresh_token,
            "spotify_market": market,
            "spotify_scopes": scopes,
            "market": market,
            "scopes": scopes,
        }

    def spotify_payload(self) -> dict[str, Any]:
        """Return Spotify credentials for HA backend compatibility helpers."""
        return self.get_current_spotify_credentials()

    def update_spotify_refresh_token(self, refresh_token: str | None) -> bool:
        """Update the in-memory latest Spotify refresh token if Spotify rotated it."""
        token = str(refresh_token or "").strip()
        if not token:
            return False
        current = str(
            self.latest_spotify_refresh_token
            or self.config.get(CONF_SPOTIFY_REFRESH_TOKEN)
            or ""
        )
        if token == current:
            return False
        self.latest_spotify_refresh_token = token
        return True

    def device_language(self) -> str:
        """Return the ESP UI language provisioned during pairing."""
        language = str(self.config.get(CONF_DEVICE_LANGUAGE) or DEFAULT_DEVICE_LANGUAGE)
        return "nl" if language.lower().startswith("nl") else "en"

    def client_type(self) -> str:
        """Return the paired DJConnect client type."""
        client_type = str(
            self.device_status.get(CONF_CLIENT_TYPE)
            or self.config.get(CONF_CLIENT_TYPE)
            or DEFAULT_CLIENT_TYPE
        ).strip()
        return client_type or DEFAULT_CLIENT_TYPE

    async def async_device_get(self, hass: HomeAssistant, path: str) -> dict[str, Any]:
        """Call an authenticated local ESP GET endpoint."""
        local_url = await self.async_device_local_url(hass)
        if not local_url:
            raise RuntimeError("DJConnect device local_url is unknown")
        session = async_get_clientsession(hass)
        async with session.get(
            local_url.rstrip("/") + path,
            headers=self.device_headers(),
            timeout=ClientTimeout(total=10),
        ) as resp:
            text = await resp.text()
            if resp.status in (401, 403, 404):
                self.update(last_error=f"DJConnect pairing is stale: HTTP {resp.status}")
            if resp.status < 200 or resp.status >= 300:
                raise RuntimeError(f"ESP GET {path} failed HTTP {resp.status}: {text}")
            try:
                return json.loads(text) if text else {"success": True}
            except json.JSONDecodeError:
                return {"success": True, "response": text}

    async def async_device_post(
        self,
        hass: HomeAssistant,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: int = 15,
    ) -> dict[str, Any]:
        """Call an authenticated local ESP POST endpoint."""
        local_url = await self.async_device_local_url(hass)
        if not local_url:
            raise RuntimeError("DJConnect device local_url is unknown")
        session = async_get_clientsession(hass)
        async with session.post(
            local_url.rstrip("/") + path,
            json=payload or {},
            headers=self.device_headers(),
            timeout=ClientTimeout(total=timeout),
        ) as resp:
            text = await resp.text()
            if resp.status in (401, 403, 404):
                self.update(last_error=f"DJConnect pairing is stale: HTTP {resp.status}")
            if resp.status < 200 or resp.status >= 300:
                raise RuntimeError(f"ESP POST {path} failed HTTP {resp.status}: {text}")
            try:
                return json.loads(text) if text else {"success": True}
            except json.JSONDecodeError:
                return {"success": True, "response": text}

    async def async_device_command(
        self,
        hass: HomeAssistant,
        command: str,
        **values: Any,
    ) -> dict[str, Any]:
        """Send a command to the ESP local command API."""
        payload = {"command": command}
        payload.update({key: value for key, value in values.items() if value is not None})
        result = await self.async_device_post(hass, "/api/device/command", payload)
        if isinstance(result, dict):
            status = result.get("status") or result.get("device_status")
            if isinstance(status, dict):
                _merge_cached_device_status(
                    self.device_status,
                    status,
                    source="ESP command status",
                )
            _merge_cached_device_status(
                self.device_status,
                {
                    key: result[key]
                    for key in ("spotify_status", "ha_pairing_status", "sound_output")
                    if key in result
                },
                source="ESP command response",
            )
        self.update(last_error=None)
        return result

    async def async_refresh_device_info(self, hass: HomeAssistant) -> dict[str, Any]:
        """Refresh local ESP device info through the local API."""
        data = await self.async_device_get(hass, "/api/device/info")
        status = data.get("status") if isinstance(data, dict) else None
        if isinstance(status, dict):
            _merge_cached_device_status(
                self.device_status,
                status,
                source="ESP device info status",
            )
        if isinstance(data, dict):
            _merge_cached_device_status(
                self.device_status,
                {
                    key: value
                    for key, value in data.items()
                    if key not in STATUS_SECRET_KEYS
                },
                source="ESP device info",
            )
        self.update(last_error=None)
        return data

    async def start_ota(self, hass: HomeAssistant, release: Any) -> None:
        local_url = await self.async_device_local_url(hass)
        if not local_url:
            raise RuntimeError(
                "DJConnect device local_url is unknown; send a /status update first"
            )
        payload = {
            "version": release.version,
            "url": release.firmware_url,
            "sha256": release.sha256,
            "device": release.device,
            "asset": release.firmware_asset,
        }
        self.ota_in_progress = True
        self.ota_last_error = None
        self.update()
        session = async_get_clientsession(hass)
        errors: list[str] = []
        try:
            for candidate_url in _device_url_candidates(local_url, self.device_status):
                url = candidate_url.rstrip("/") + "/api/device/ota"
                try:
                    async with session.post(
                        url,
                        json=payload,
                        headers=self.device_headers(),
                        timeout=ClientTimeout(total=30),
                    ) as resp:
                        text = await resp.text()
                        if resp.status < 200 or resp.status >= 300:
                            raise RuntimeError(
                                f"ESP OTA request failed HTTP {resp.status}: {text}"
                            )
                        if candidate_url != local_url:
                            self.device_status["local_url"] = candidate_url
                        _LOGGER.info("DJConnect OTA accepted by device: %s", text)
                        return
                except RuntimeError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{candidate_url}: {exc}")
                    _LOGGER.warning(
                        "DJConnect OTA request to %s failed, trying fallback if available: %s",
                        candidate_url,
                        exc,
                    )
            raise RuntimeError("DJConnect OTA request failed: " + "; ".join(errors))
        except Exception as exc:  # noqa: BLE001
            self.ota_in_progress = False
            self.ota_last_error = str(exc)
            self.update()
            raise

    async def pair_device(self, hass: HomeAssistant) -> dict[str, Any]:
        conf = self.config
        local_url = await self.async_device_local_url(hass)
        if not local_url:
            raise RuntimeError("DJConnect device local_url is unknown")
        session = async_get_clientsession(hass)
        pairing_info: dict[str, Any] = {}
        try:
            pairing_info_url = local_url.rstrip("/") + "/api/device/pairing-info"
            _LOGGER.debug("DJConnect pairing-info request url=%s", pairing_info_url)
            async with session.get(
                pairing_info_url,
                timeout=ClientTimeout(total=10),
            ) as resp:
                text = await resp.text()
                _LOGGER.debug(
                    "DJConnect pairing-info response status=%s body=%s",
                    resp.status,
                    text,
                )
                if resp.status < 200 or resp.status >= 300:
                    raise RuntimeError(
                        f"ESP pairing info failed HTTP {resp.status}: {text}"
                    )
                pairing_info = json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError("ESP pairing info returned invalid JSON") from exc

        expected_pair_code = str(conf.get(CONF_PAIR_CODE) or "").strip()
        reported_pair_code = str(pairing_info.get("pair_code") or "").strip()
        if expected_pair_code and reported_pair_code and expected_pair_code != reported_pair_code:
            _LOGGER.debug(
                "DJConnect pairing-info code mismatch expected_pair_code=%s "
                "reported_pair_code=%s reported_device_id=%s reported_client_type=%s",
                expected_pair_code,
                reported_pair_code,
                pairing_info.get("device_id") or "missing",
                pairing_info.get(CONF_CLIENT_TYPE) or pairing_info.get("client_type") or "missing",
            )
            raise RuntimeError("ESP pairing code does not match this setup")
        reported_device_id = str(pairing_info.get("device_id") or "").strip()
        if reported_device_id:
            self._learn_device_id(reported_device_id)
        reported_client_type = str(
            pairing_info.get(CONF_CLIENT_TYPE) or pairing_info.get("client_type") or ""
        ).strip()
        if reported_client_type in CLIENT_TYPES:
            self.device_status[CONF_CLIENT_TYPE] = reported_client_type
        reported_local_url = str(pairing_info.get("local_url") or "").strip()
        if reported_local_url:
            self.device_status["local_url"] = reported_local_url
        token = self.ensure_device_token()
        url = local_url.rstrip("/") + "/api/device/pair"
        payload_client_type = (
            reported_client_type if reported_client_type in CLIENT_TYPES else self.client_type()
        )
        payload = {
            "pair_code": conf.get(CONF_PAIR_CODE),
            "device_id": reported_device_id or conf.get(CONF_DEVICE_ID),
            "device_name": conf.get(CONF_DEVICE_NAME, "DJConnect"),
            "client_type": payload_client_type,
            "device_token": token,
            "assist_pipeline_id": conf.get(CONF_ASSIST_PIPELINE_ID, ""),
        }
        if payload_client_type == CLIENT_TYPE_ESP32:
            payload["device_language"] = self.device_language()
            payload["language"] = self.device_language()
        payload.update(await async_ha_url_payload(hass, conf))
        if not payload.get("ha_local_url"):
            raise RuntimeError("Home Assistant local URL is required for pairing")
        _LOGGER.debug(
            "DJConnect device pair request url=%s payload=%s",
            url,
            _redact_debug_payload(payload),
        )
        async with session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=ClientTimeout(total=30),
        ) as resp:
            text = await resp.text()
            _LOGGER.debug(
                "DJConnect device pair response status=%s body=%s",
                resp.status,
                text,
            )
            if resp.status < 200 or resp.status >= 300:
                raise RuntimeError(f"ESP pairing failed HTTP {resp.status}: {text}")
            return json.loads(text) if text else {"success": True}

async def async_discover_device_url(
    hass: HomeAssistant,
    runtime: DJConnectRuntime,
) -> str | None:
    """Resolve the DJConnect device URL from the `_djconnect._tcp` mDNS service."""
    try:
        from homeassistant.components import zeroconf

        zc = await zeroconf.async_get_async_instance(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect mDNS discovery unavailable", exc_info=True)
        return None

    for service_name in _mdns_service_name_candidates(runtime):
        info = await _async_get_mdns_service_info(zc, service_name)
        url = _url_from_service_info(info, runtime)
        if url:
            _LOGGER.debug("DJConnect discovered device URL via mDNS: %s", url)
            return url
    url = await _async_discover_single_mdns_service_url(zc)
    if url:
        _LOGGER.debug("DJConnect discovered single visible device URL via mDNS: %s", url)
        return url
    return None


async def _async_get_mdns_service_info(async_zc: Any, service_name: str) -> Any:
    """Read one mDNS service record using HA's AsyncZeroconf wrapper."""
    getter = getattr(async_zc, "async_get_service_info", None)
    if getter is None:
        return None
    try:
        return await getter(MDNS_SERVICE_TYPE, service_name)
    except Exception:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect mDNS lookup failed for %s",
            service_name,
            exc_info=True,
        )
        return None


async def _async_discover_single_mdns_service_url(async_zc: Any) -> str | None:
    """Browse `_djconnect._tcp` and return the only visible DJConnect device URL."""
    try:
        from zeroconf import ServiceStateChange
        from zeroconf.asyncio import AsyncServiceBrowser
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect mDNS browse fallback unavailable", exc_info=True)
        return None

    service_names: set[str] = set()

    def _on_service_state_change(
        zeroconf: Any,
        service_type: str,
        name: str,
        state_change: Any,
    ) -> None:
        if state_change == ServiceStateChange.Added:
            service_names.add(name)

    browser = None
    try:
        zc = getattr(async_zc, "zeroconf", async_zc)
        browser = AsyncServiceBrowser(
            zc,
            MDNS_SERVICE_TYPE,
            handlers=[_on_service_state_change],
        )
        await asyncio.sleep(2)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect mDNS browse fallback failed", exc_info=True)
        return None
    finally:
        if browser is not None:
            cancel = getattr(browser, "async_cancel", None)
            if cancel is not None:
                result = cancel()
                if hasattr(result, "__await__"):
                    await result

    infos = [
        await _async_get_mdns_service_info(async_zc, service_name)
        for service_name in sorted(service_names)
    ]
    urls = [url for info in infos if (url := _url_from_service_info_unmatched(info))]
    unique_urls = list(dict.fromkeys(urls))
    if len(unique_urls) == 1:
        return unique_urls[0]
    if len(unique_urls) > 1:
        _LOGGER.warning(
            "DJConnect found multiple mDNS devices; set the manual device URL in options"
        )
    return None


def _mdns_service_name_candidates(runtime: DJConnectRuntime) -> list[str]:
    """Build likely `_djconnect._tcp` instance names for the paired device."""
    device_id = _runtime_device_id(runtime)
    if not device_id:
        return []
    names = [
        f"{device_id}.{MDNS_SERVICE_TYPE}",
        f"{device_id.upper()}.{MDNS_SERVICE_TYPE}",
    ]
    if device_id.startswith("djconnect-"):
        suffix = device_id.removeprefix("djconnect-")
        names.extend(
            [
                f"DJConnect {suffix}.{MDNS_SERVICE_TYPE}",
                f"DJConnect {suffix.upper()}.{MDNS_SERVICE_TYPE}",
            ]
        )
    return list(dict.fromkeys(names))


def _runtime_device_id(runtime: DJConnectRuntime) -> str:
    """Return the known DJConnect device identifier, when available."""
    return str(
        runtime.device_status.get("device_id")
        or runtime.pairing_device_id
        or runtime.config.get(CONF_DEVICE_ID)
        or ""
    ).strip()


def _device_id_mdns_fallback_url(device_id: Any) -> str | None:
    """Return a fallback URL only for real ESP DJConnect device IDs."""
    normalized = str(device_id or "").strip()
    if _is_real_esp_djconnect_device_id(normalized):
        return f"http://{normalized}.local"
    return None


def _device_url_candidates(primary_url: str, status: dict[str, Any]) -> list[str]:
    """Return primary URL plus IP fallbacks from cached ESP status."""
    urls = [_normalize_device_base_url(primary_url)]
    for candidate in _device_ip_fallback_urls(status):
        normalized = _normalize_device_base_url(candidate)
        if normalized and normalized not in urls:
            urls.append(normalized)
    return [url for url in urls if url]


def _device_ip_fallback_urls(status: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("ip", "local_ip", "wifi_ip", "host"):
        url = _device_url_from_ip_like(status.get(key))
        if url:
            urls.append(url)
    wifi = status.get("wifi")
    if isinstance(wifi, dict):
        for key in ("ip", "local_ip", "wifi_ip", "host"):
            url = _device_url_from_ip_like(wifi.get(key))
            if url:
                urls.append(url)
    for key in ("local_url", "ota_url"):
        url = _device_url_from_ip_like(status.get(key))
        if url:
            urls.append(url)
    return urls


def _device_url_from_ip_like(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        parts = urlsplit(text)
        host = parts.hostname or ""
        return text if _is_ipv4_address(host) else None
    host = text.split(":", 1)[0]
    return f"http://{text}" if _is_ipv4_address(host) else None


def _normalize_device_base_url(value: Any) -> str:
    text = str(value or "").strip().rstrip("/")
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = "http://" + text
    parts = urlsplit(text)
    return urlunsplit((parts.scheme or "http", parts.netloc, "", "", ""))


def _is_ipv4_address(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 and str(int(part)) == part for part in parts)
    except ValueError:
        return False


def _status_ip_fallback_url(status: dict[str, Any], previous_url: Any = "") -> str | None:
    """Return an IP-based device URL from cached ESP status."""
    if not isinstance(status, dict):
        return None
    ip = _first_status_ip(status)
    if not ip:
        return None
    port = _url_port(previous_url) or _first_status_port(status)
    return f"http://{ip}{f':{port}' if port else ''}"


def _first_status_ip(status: dict[str, Any]) -> str:
    for source in (
        status,
        status.get("wifi") if isinstance(status.get("wifi"), dict) else {},
        status.get("network") if isinstance(status.get("network"), dict) else {},
    ):
        for key in ("ip", "ip_address", "wifi_ip", "local_ip"):
            value = str(source.get(key) or "").strip()
            if _is_ipv4_address(value):
                return value
    return ""


def _first_status_port(status: dict[str, Any]) -> str:
    for source in (
        status,
        status.get("api") if isinstance(status.get("api"), dict) else {},
        status.get("network") if isinstance(status.get("network"), dict) else {},
    ):
        for key in ("port", "api_port", "local_port"):
            value = source.get(key)
            try:
                port = int(value)
            except (TypeError, ValueError):
                continue
            if 0 < port <= 65535:
                return str(port)
    return ""


def _url_port(url: Any) -> str:
    match = re.match(r"^https?://[^/:]+:(\d+)(?:/|$)", str(url or "").strip())
    return match.group(1) if match else ""


def _is_real_djconnect_device_id(device_id: str) -> bool:
    return bool(REAL_DJCONNECT_DEVICE_ID_PATTERN.fullmatch(str(device_id or "").strip()))


def _is_real_esp_djconnect_device_id(device_id: str) -> bool:
    return bool(
        re.fullmatch(
            r"djconnect-(?:lilygo-t-embed-s3|esp32-s3-box-3|lilygo)-[0-9A-Fa-f]{12}",
            str(device_id or "").strip(),
        )
    )


def _is_setup_code_device_id(device_id: str) -> bool:
    return bool(re.fullmatch(r"djconnect-\d{6}", str(device_id or "").strip()))


def _device_id_matches_client_type(device_id: str, client_type: str) -> bool:
    normalized = str(device_id or "").strip()
    normalized_client = str(client_type or "").strip()
    if normalized_client == CLIENT_TYPE_IOS:
        return bool(re.fullmatch(r"djconnect-ios-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_MACOS:
        return bool(re.fullmatch(r"djconnect-macos-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_WATCHOS:
        return bool(re.fullmatch(r"djconnect-watchos-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_RASPBERRY_PI:
        return bool(re.fullmatch(r"djconnect-raspberry-pi-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_WINDOWS:
        return bool(re.fullmatch(r"djconnect-windows-[A-Za-z0-9]{12}", normalized))
    if normalized_client == CLIENT_TYPE_ESP32:
        return bool(
            re.fullmatch(
                r"djconnect-(?:lilygo-t-embed-s3|esp32-s3-box-3|lilygo)-[0-9A-Fa-f]{12}",
                normalized,
            )
            or _is_setup_code_device_id(normalized)
        )
    return False


def _device_id_matches(known_device: str, request_device: str) -> bool:
    """Allow the ESP real ID to replace a temporary setup-code ID."""
    known = str(known_device or "").strip()
    requested = str(request_device or "").strip()
    if not known or not requested or known == requested:
        return True
    if _is_setup_code_device_id(known) and _is_real_djconnect_device_id(requested):
        return True
    return _is_real_djconnect_device_id(known) and _is_real_djconnect_device_id(requested)


def _is_pair_code_mdns_url(value: str) -> bool:
    """Detect obsolete fallback URLs created from short setup pair codes."""
    return bool(re.fullmatch(r"https?://djconnect-\d{6}\.local(?::\d+)?/?", value.strip()))


def _is_mdns_url(value: str) -> bool:
    """Detect a local mDNS hostname URL."""
    return bool(re.match(r"^https?://[^/]+\.local(?::\d+)?(?:/.*)?$", str(value or "").strip()))


def _url_from_service_info(info: Any, runtime: DJConnectRuntime) -> str | None:
    if info is None:
        return None
    name = str(getattr(info, "name", "") or "").lower()
    device_id = _runtime_device_id(runtime)
    if device_id and not _mdns_name_matches_device(name, device_id):
        return None
    host = (
        getattr(info, "server", None)
        or getattr(info, "host", None)
        or getattr(info, "hostname", None)
    )
    port = int(getattr(info, "port", 80) or 80)
    if not host:
        return None
    host = str(host).rstrip(".")
    return f"http://{host}:{port}" if port != 80 else f"http://{host}"


def _url_from_service_info_unmatched(info: Any) -> str | None:
    """Build a URL from an mDNS service record without device-id filtering."""
    if info is None:
        return None
    host = (
        getattr(info, "server", None)
        or getattr(info, "host", None)
        or getattr(info, "hostname", None)
    )
    port = int(getattr(info, "port", 80) or 80)
    if not host:
        return None
    host = str(host).rstrip(".")
    return f"http://{host}:{port}" if port != 80 else f"http://{host}"


def _mdns_name_matches_device(name: str, device_id: str) -> bool:
    """Match full device IDs and friendly `DJConnect xxxx` mDNS names."""
    normalized_name = name.lower()
    normalized_id = device_id.lower()
    if normalized_id in normalized_name:
        return True
    if normalized_id.startswith("djconnect-"):
        suffix = normalized_id.removeprefix("djconnect-")
        return f"djconnect {suffix}" in normalized_name
    return False


def _service_text(call: ServiceCall, default: str, *aliases: str) -> str:
    """Return normalized service text while keeping developer actions forgiving."""
    for key in ("text", *aliases):
        value = call.data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return str(default).strip()


def _developer_service_schema(fields: dict[Any, Any]):
    """Build a service schema while keeping lightweight test stubs compatible."""
    allow_extra = getattr(vol, "ALLOW_EXTRA", None)
    if allow_extra is None:
        return vol.Schema(fields)
    return vol.Schema(fields, extra=allow_extra)


DEVELOPER_SERVICE_SCHEMAS = {
    "test_parse": _developer_service_schema(
        {
            vol.Optional("command_text"): str,
            vol.Optional("text"): str,
        }
    ),
    "test_tts": _developer_service_schema(
        {
            vol.Optional("dj_response_text"): str,
            vol.Optional("text"): str,
        }
    ),
    "test_command": _developer_service_schema(
        {
            vol.Optional("command_text"): str,
            vol.Optional("text"): str,
            vol.Optional("play", default=True): bool,
        }
    ),
    "test_ptt_text": _developer_service_schema(
        {
            vol.Optional("command_text"): str,
            vol.Optional("text"): str,
        }
    ),
    "test_apns_push": _developer_service_schema(
        {
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("event_type", default=EVENT_TEST_PUSH): str,
            vol.Optional("user_id"): str,
            vol.Optional("send", default=False): bool,
            vol.Optional("explicit_user_request", default=True): bool,
        }
    ),
    "push_register": _developer_service_schema(
        {
            vol.Required("push_token"): str,
            vol.Required("push_environment"): str,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("user_id"): str,
            vol.Optional("app_bundle_id"): str,
            vol.Optional("app_version"): str,
            vol.Optional("app_build"): str,
            vol.Optional("locale"): str,
            vol.Optional("language"): str,
            vol.Optional("notification_categories"): object,
            vol.Optional("bootstrap_proof"): str,
            vol.Optional(CONF_CENTRAL_API_BOOTSTRAP_PROOF): str,
            vol.Optional(CONF_CENTRAL_API_BOOTSTRAP_PROOF_EXPIRES_AT): str,
        }
    ),
    "push_unregister": _developer_service_schema(
        {
            vol.Required("push_token"): str,
            vol.Required("push_environment"): str,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("user_id"): str,
            vol.Optional("app_bundle_id"): str,
            vol.Optional("app_version"): str,
            vol.Optional("app_build"): str,
            vol.Optional("locale"): str,
            vol.Optional("language"): str,
            vol.Optional("notification_categories"): object,
        }
    ),
    "music_backend_status": _developer_service_schema({}),
    "start_spotify_oauth": _developer_service_schema(
        {
            vol.Optional("client_id"): str,
            vol.Optional("ha_base_url"): str,
            vol.Optional("market"): str,
            vol.Optional("scopes"): str,
        }
    ),
    "device_command": _developer_service_schema(
        {
            vol.Required("command"): str,
            vol.Optional("payload"): dict,
        }
    ),
    "queue": _developer_service_schema(
        {
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "playlists": _developer_service_schema(
        {
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("limit"): int,
            vol.Optional("market"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "playback_status": _developer_service_schema(
        {
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "playback_devices": _developer_service_schema(
        {
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "playback_command": _developer_service_schema(
        {
            vol.Required("command"): str,
            vol.Optional("value"): object,
            vol.Optional("play", default=False): bool,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "refresh_device_info": _developer_service_schema({}),
    "reboot_device": _developer_service_schema({}),
    "forget_device": _developer_service_schema({}),
    "ask_dj": _developer_service_schema(
        {
            vol.Required("text"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("client_message_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("dj_style"): str,
            vol.Optional("mood"): int,
            vol.Optional("audio_response"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "ask_dj_message": _developer_service_schema(
        {
            vol.Required("text"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("client_message_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("dj_style"): str,
            vol.Optional("mood"): int,
            vol.Optional("audio_response"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "ask_dj_idle_suggestion": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "ask_dj_history": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("since_revision"): int,
        }
    ),
    "track_insight": _developer_service_schema(
        {
            vol.Optional("entity_id"): str,
            vol.Optional("player_id"): str,
            vol.Optional("title"): str,
            vol.Optional("artist"): str,
            vol.Optional("album"): str,
            vol.Optional("genres"): object,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("music_backend"): str,
            vol.Optional("force_refresh", default=False): bool,
            vol.Optional("include_visual_profile", default=True): bool,
            vol.Optional("include_raw_response", default=False): bool,
            vol.Optional("locale"): str,
            vol.Optional("language"): str,
            vol.Optional("mood"): int,
            vol.Optional("timezone"): str,
        }
    ),
    "vibecast_feed": _developer_service_schema(
        {
            vol.Optional("client_type"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("locale"): str,
            vol.Optional("language"): str,
            vol.Optional("render_capabilities"): str,
            vol.Optional("app_version"): str,
            vol.Optional("app_build"): str,
        }
    ),
    "music_discovery_feed": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("force_refresh", default=False): bool,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "refresh_music_discovery": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "play_music_discovery_item": _developer_service_schema(
        {
            vol.Required("discovery_item_id"): str,
            vol.Optional("section_id"): str,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "music_dna_profile": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "set_music_dna_enabled": _developer_service_schema(
        {
            vol.Required("enabled"): bool,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "clear_music_dna": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "music_dna_export": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("app_version"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "music_dna_import": _developer_service_schema(
        {
            vol.Required("profile"): object,
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("app_version"): str,
            vol.Optional("locale"): str,
            vol.Optional("timezone"): str,
        }
    ),
    "clear_ask_dj_history": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
        }
    ),
    "ask_dj_history_state": _developer_service_schema(
        {
            vol.Optional("music_dna_key"): str,
            vol.Optional("profile_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("client_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("device_name"): str,
            vol.Optional("history_revision"): int,
            vol.Optional("clear_revision"): int,
            vol.Optional("generation"): int,
        }
    ),
    "profile_export": _developer_service_schema(
        {
            vol.Optional("profile_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("include_personal_data", default=True): bool,
        }
    ),
    "household_export": _developer_service_schema(
        {
            vol.Optional("profile_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
        }
    ),
    "integration_export": _developer_service_schema(
        {
            vol.Optional("profile_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
        }
    ),
    "profile_import": _developer_service_schema(
        {
            vol.Required("export"): object,
            vol.Optional("overwrite", default=False): bool,
            vol.Optional("reassign_id", default=False): bool,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
        }
    ),
    "household_import": _developer_service_schema(
        {
            vol.Required("export"): object,
            vol.Optional("overwrite", default=False): bool,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
        }
    ),
    "clear_profile_state": _developer_service_schema(
        {
            vol.Optional("profile_id"): str,
            vol.Optional("device_id"): str,
            vol.Optional("client_type"): str,
            vol.Optional("ask_dj", default=False): bool,
            vol.Optional("music_dna", default=False): bool,
            vol.Optional("recommendations", default=False): bool,
            vol.Optional("mood", default=False): bool,
            vol.Optional("all", default=False): bool,
        }
    ),
}


async def async_speak_dj_test(
    hass: HomeAssistant,
    runtime: DJConnectRuntime,
    text: str,
) -> dict[str, Any]:
    """Send a DJ test response to the DJConnect device display/speaker."""
    _LOGGER.debug("DJConnect test_tts sending DJ response to device")
    result = await async_send_dj_response(hass, runtime, text)
    return {"text": text, **result}


def _push_status_snapshot(runtime: Any) -> list[dict[str, Any]]:
    statuses = getattr(runtime, "push_status", None)
    if not isinstance(statuses, dict):
        return []
    result: list[dict[str, Any]] = []
    for key, value in statuses.items():
        if not isinstance(value, dict):
            continue
        device_id, client_type = _split_push_status_key(key)
        result.append(
            {
                "device_id": device_id,
                "client_type": client_type,
                "push_registered": bool(value.get("push_registered")),
                "push_environment": value.get("push_environment"),
                "last_push_error": value.get("last_push_error"),
            }
        )
    return result


def _split_push_status_key(key: Any) -> tuple[str, str]:
    raw = str(key or "")
    if "|" in raw:
        device_id, client_type = raw.rsplit("|", 1)
        return device_id, client_type
    return raw, ""


def _runtime_push_device_id(runtime: Any, requested: Any = None) -> str | None:
    if requested:
        return str(requested).strip()
    status = getattr(runtime, "device_status", {}) or {}
    config = getattr(runtime, "config", {}) or {}
    value = status.get(CONF_DEVICE_ID) or config.get(CONF_DEVICE_ID)
    return str(value).strip() if value else None


def _runtime_push_client_type(runtime: Any, requested: Any = None) -> str:
    if requested:
        return str(requested).strip().lower()
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        value = getter()
        if value:
            return str(value).strip().lower()
    status = getattr(runtime, "device_status", {}) or {}
    config = getattr(runtime, "config", {}) or {}
    return (
        str(status.get(CONF_CLIENT_TYPE) or config.get(CONF_CLIENT_TYPE) or "")
        .strip()
        .lower()
    )


def _push_debug_payload(
    runtime: Any,
    *,
    device_id: str | None,
    client_type: str,
    event_type: str,
    user_id: str | None,
    explicit_user_request: bool,
    send: bool,
    decision: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = getattr(runtime, "config", {}) or {}
    status = getattr(runtime, "device_status", {}) or {}
    payload: dict[str, Any] = {
        "success": bool((result or decision).get("success", decision.get("send", False))),
        "send_requested": send,
        "event_type": event_type,
        "device_id": device_id,
        "client_type": client_type,
        "user_id_provided": bool(user_id),
        "explicit_user_request": explicit_user_request,
        "central_api_configured": relay_configured(runtime),
        "ha_install_id_present": bool(
            config.get(CONF_HA_INSTALL_ID) or status.get(CONF_HA_INSTALL_ID)
        ),
        "install_token_present": bool(config.get(CONF_DJCONNECT_INSTALL_TOKEN)),
        "bootstrap_proof_present": bool(
            config.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF)
            or status.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF)
        ),
        "decision": decision,
        "push_statuses": _push_status_snapshot(runtime),
    }
    if result is not None:
        payload["result"] = result
        payload["sent"] = int(result.get("sent") or 0)
        payload["error"] = (
            result.get("error")
            or result.get("last_push_error")
            or result.get("suppressed")
            or ("disabled" if result.get("disabled") else None)
        )
    else:
        payload["sent"] = 0
        payload["error"] = None if decision.get("send") else decision.get("reason")
    return payload


def register_http_views(hass: HomeAssistant) -> None:
    hass.data.setdefault(DOMAIN, {})
    if not hass.data[DOMAIN].get("http_registered"):
        for view in [
            DJConnectVoiceView(hass),
            DJConnectAskDjView(hass),
            DJConnectAskDjMessageView(hass),
            DJConnectAskDjIdleSuggestionView(hass),
            DJConnectAskDjHistoryView(hass),
            DJConnectAskDjHistoryExportView(hass),
            DJConnectAskDjHistoryClearView(hass),
            DJConnectCommandView(hass),
            DJConnectPushBootstrapView(hass),
            DJConnectPushRegisterView(hass),
            DJConnectPushUnregisterView(hass),
            DJConnectPairView(hass),
            DJConnectStatusView(hass),
            DJConnectTransportCapabilitiesView(hass),
            DJConnectSessionStartView(hass),
            DJConnectSessionEndView(hass),
            DJConnectActiveSessionView(hass),
            DJConnectSessionBroadcastSnapshotView(hass),
            DJConnectSessionBroadcastTokenView(hass),
            DJConnectSessionBroadcastWebSocketView(hass),
            DJConnectTrackInsightView(hass),
            DJConnectVibeCastView(hass),
            DJConnectMusicDiscoveryView(hass),
            DJConnectMusicDiscoveryRefreshView(hass),
            DJConnectMusicDiscoveryPlayView(hass),
            DJConnectMusicDiscoveryFeedbackView(hass),
            DJConnectMusicDnaProfileView(hass),
            DJConnectMusicDnaSettingsView(hass),
            DJConnectMusicDnaClearView(hass),
            DJConnectMusicDnaExportView(hass),
            DJConnectMusicDnaImportView(hass),
            DJConnectEventView(hass),
            DJConnectTtsView(hass),
            DJConnectImageProxyView(hass),
            DJConnectVoiceDebugView(hass),
            DJConnectSpotifyCallbackView(hass),
        ]:
            hass.http.register_view(view)
        hass.data[DOMAIN]["http_registered"] = True

        _LOGGER.info(
            "DJConnect HTTP endpoints registered: %s",
            ", ".join(
                (
                    API_VOICE,
                    API_ASK_DJ,
                    API_ASK_DJ_MESSAGE,
                    API_ASK_DJ_HISTORY,
                    API_ASK_DJ_HISTORY_CLEAR,
                    API_COMMAND,
                    API_PUSH_REGISTER,
                    API_PUSH_UNREGISTER,
                    API_PAIR,
                    API_STATUS,
                    API_SESSION_START,
                    API_SESSION_END,
                    API_SESSION_ACTIVE,
                    API_SESSION_BROADCAST,
                    API_TRACK_INSIGHT,
                    API_VIBECAST,
                    API_EVENT,
                    API_TTS,
                    API_SPOTIFY_CALLBACK,
                )
            ),
        )
    async_register_websocket_api(hass)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    register_http_views(hass)
    return True


def _platforms_for_runtime(runtime: DJConnectRuntime) -> list[str]:
    """Return HA platforms that make sense for this DJConnect entry."""
    if runtime.client_type() == CLIENT_TYPE_CONVERSATION_AGENT:
        return ["conversation", "sensor"]
    return list(PLATFORMS)


def _restore_runtime(hass: HomeAssistant, entry: ConfigEntry) -> DJConnectRuntime:
    runtime = DJConnectRuntime(entry=entry)
    memory_manager = hass.data[DOMAIN].get("memory_manager")
    if memory_manager is None:
        memory_manager = MusicDNAManager(hass)
        hass.data[DOMAIN]["memory_manager"] = memory_manager
    runtime.memory = memory_manager
    history_manager = hass.data[DOMAIN].get("ask_dj_history_manager")
    if history_manager is None:
        history_manager = AskDJHistoryManager(hass)
        hass.data[DOMAIN]["ask_dj_history_manager"] = history_manager
    runtime.ask_dj_history = history_manager
    cached_status = entry.data.get(CONF_LAST_DEVICE_STATUS)
    if isinstance(cached_status, dict):
        _merge_cached_device_status(
            runtime.device_status,
            cached_status,
            source="persisted device status",
        )
    cached_push_status = entry.data.get(CONF_LAST_PUSH_STATUS)
    if isinstance(cached_push_status, dict):
        runtime.push_status = {
            str(key): {
                "push_registered": bool(value.get("push_registered")),
                "push_environment": value.get("push_environment"),
                "last_push_error": value.get("last_push_error"),
            }
            for key, value in cached_push_status.items()
            if isinstance(value, dict)
        }
    if entry.data.get(CONF_SPOTIFY_REFRESH_TOKEN):
        runtime.latest_spotify_refresh_token = entry.data[CONF_SPOTIFY_REFRESH_TOKEN]
    if entry.data.get(CONF_DEVICE_TOKEN):
        runtime.device_token = entry.data[CONF_DEVICE_TOKEN]
        _LOGGER.debug(
            "DJConnect restored existing device token for entry %s",
            entry.entry_id,
        )
    if entry.data.get(CONF_DEVICE_ID):
        runtime.pairing_device_id = str(entry.data[CONF_DEVICE_ID])
        runtime.device_status["device_id"] = str(entry.data[CONF_DEVICE_ID])
    if entry.data.get(CONF_PAIR_CODE):
        runtime.pairing_code = str(entry.data[CONF_PAIR_CODE])
    local_url = str(entry.data.get(CONF_LOCAL_URL) or "").strip()
    if local_url and not _is_pair_code_mdns_url(local_url):
        runtime.device_status["local_url"] = local_url
    hass.data[DOMAIN][entry.entry_id] = runtime
    hass.data[DOMAIN]["runtime"] = runtime
    hass.data[DOMAIN].setdefault("entry_reload_signatures", {})[
        entry.entry_id
    ] = _entry_reload_signature(entry)
    _LOGGER.debug("DJConnect runtime restored for entry %s", entry.entry_id)
    return runtime


def _setup_device_coordinator(hass: HomeAssistant, runtime: DJConnectRuntime) -> None:
    """Create a coordinator for explicit local device-info refreshes."""
    try:
        from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect DataUpdateCoordinator unavailable", exc_info=True)
        return

    async def _async_update_data() -> dict[str, Any]:
        if not runtime.device_token:
            return {}
        return await runtime.async_refresh_device_info(hass)

    hass.data[DOMAIN][f"{runtime.entry.entry_id}_coordinator"] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="DJConnect local device API",
        update_method=_async_update_data,
    )


async def _try_initial_device_provisioning(
    hass: HomeAssistant,
    runtime: DJConnectRuntime,
) -> None:
    """Pair opportunistically without blocking HA startup when ESP is offline."""
    try:
        if not _should_startup_pair_device(runtime):
            _LOGGER.debug(
                "DJConnect startup direct pairing skipped; token is already stored"
            )
        else:
            await runtime.pair_device(hass)
        runtime.update(last_error=None)
    except Exception as exc:  # noqa: BLE001
        if _is_deferred_provisioning_error(exc):
            _LOGGER.info(
                "DJConnect device pairing deferred until device is reachable: %s",
                _format_exception(exc),
            )
            return
        message = _format_exception(exc)
        runtime.update(last_error=f"DJConnect device pairing failed: {message}")
        _LOGGER.warning("DJConnect device pairing deferred/failed: %s", message)


def _should_startup_pair_device(runtime: DJConnectRuntime) -> bool:
    """Return true only when startup has no stored ESP token yet."""
    if getattr(runtime, "device_token", None):
        return False
    status = getattr(runtime, "device_status", {}) or {}
    return status.get("ha_pairing_status") not in {"paired", "pending"}


def _is_deferred_provisioning_error(exc: Exception) -> bool:
    """Return true for expected startup-only ESP reachability failures."""
    message = str(exc)
    return any(
        marker in message
        for marker in (
            "local_url is unknown",
            "Cannot connect to host",
            "MDNS lookup failed",
            "Timeout while contacting DNS servers",
        )
    )


def _format_exception(exc: Exception) -> str:
    """Return useful text even when Home Assistant exceptions stringify empty."""
    text = str(exc).strip()
    if text:
        return text
    return f"{type(exc).__name__}: {exc!r}"


def _register_developer_services(
    hass: HomeAssistant,
    entry: ConfigEntry,
    runtime: DJConnectRuntime,
) -> None:
    """Register Home Assistant developer actions for parser, TTS and provisioning."""

    async def handle_test_parse(call: ServiceCall) -> dict[str, Any] | None:
        text = _service_text(call, DEFAULT_TEST_COMMAND, "command_text")
        _LOGGER.debug("DJConnect developer action test_parse: %s", text)
        result = await run_text_command(hass, runtime, text, play=False)
        _LOGGER.debug("DJConnect test_parse: %s", result)
        return result

    async def handle_test_tts(call: ServiceCall) -> dict[str, Any]:
        text = _service_text(call, DEFAULT_TEST_TTS_TEXT, "dj_response_text")
        _LOGGER.debug("DJConnect developer action test_tts: %s", text)
        result = await async_speak_dj_test(hass, runtime, text)
        _LOGGER.debug("DJConnect test_tts sent DJ response to device: %s", text)
        return result

    async def handle_test_command(call: ServiceCall) -> dict[str, Any] | None:
        text = _service_text(call, DEFAULT_TEST_COMMAND, "command_text")
        play = bool(call.data.get("play", True))
        _LOGGER.debug(
            "DJConnect developer action test_command play=%s: %s",
            play,
            text,
        )
        result = await run_text_command(hass, runtime, text, play=play)
        result["dj_response"] = await async_send_dj_response_best_effort(
            hass,
            runtime,
            result.get("dj_text") or "",
        )
        dj_response = result.get("dj_response") or {}
        _LOGGER.debug(
            "DJConnect test_command result intent=%s playback=%s dj_text=%s audio_url=%s audio_type=%s",
            result.get("intent"),
            bool(result.get("playback")),
            bool(result.get("dj_text")),
            bool(dj_response.get("audio_url")),
            dj_response.get("audio_type"),
        )
        return result

    async def handle_test_ptt_text(call: ServiceCall) -> dict[str, Any] | None:
        text = _service_text(call, DEFAULT_TEST_COMMAND, "command_text")
        _LOGGER.debug(
            "DJConnect developer action test_ptt_text after_stt_text=%s",
            text,
        )
        result = await run_text_command(
            hass,
            runtime,
            text,
            play=True,
            correct_stt=True,
        )
        result["dj_response"] = await async_send_dj_response_best_effort(
            hass,
            runtime,
            result.get("dj_text") or "",
        )
        dj_response = result.get("dj_response") or {}
        _LOGGER.debug(
            "DJConnect test_ptt_text result intent=%s playback=%s dj_text=%s audio_url=%s audio_type=%s",
            result.get("intent"),
            bool(result.get("playback")),
            bool(result.get("dj_text")),
            bool(dj_response.get("audio_url")),
            dj_response.get("audio_type"),
        )
        return result

    async def handle_test_apns_push(call: ServiceCall) -> dict[str, Any]:
        event_type = str(call.data.get("event_type") or EVENT_TEST_PUSH).strip()
        user_id = call.data.get("user_id") or getattr(
            getattr(call, "context", None),
            "user_id",
            None,
        )
        device_id = _runtime_push_device_id(runtime, call.data.get("device_id"))
        client_type = _runtime_push_client_type(runtime, call.data.get("client_type"))
        explicit_user_request = bool(call.data.get("explicit_user_request", True))
        send = bool(call.data.get("send", False))
        decision = should_send_push(
            runtime,
            user_id=user_id,
            event_type=event_type,
            source_device_id=device_id,
            client_type=client_type,
            explicit_user_request=explicit_user_request,
            consume_rate_limit=False,
        )
        if not send:
            return _push_debug_payload(
                runtime,
                device_id=device_id,
                client_type=client_type,
                event_type=event_type,
                user_id=user_id,
                explicit_user_request=explicit_user_request,
                send=False,
                decision=decision,
            )
        result = await async_send_push_event(
            hass,
            runtime,
            user_id=user_id,
            event_type=event_type,
            source_device_id=device_id,
            client_type=client_type,
            explicit_user_request=explicit_user_request,
        )
        debug = _push_debug_payload(
            runtime,
            device_id=device_id,
            client_type=client_type,
            event_type=event_type,
            user_id=user_id,
            explicit_user_request=explicit_user_request,
            send=True,
            decision=decision,
            result=result,
        )
        _LOGGER.info(
            "DJConnect APNs test push: sent=%s error=%s supported=%s configured=%s",
            debug.get("sent"),
            debug.get("error"),
            result.get("push_supported"),
            debug.get("central_api_configured"),
        )
        return debug

    def apns_registration_payload(call: ServiceCall) -> dict[str, Any]:
        payload = dict(call.data)
        payload.setdefault(CONF_DEVICE_ID, _runtime_push_device_id(runtime, payload.get(CONF_DEVICE_ID)))
        payload.setdefault(CONF_CLIENT_TYPE, _runtime_push_client_type(runtime, payload.get(CONF_CLIENT_TYPE)))
        return payload

    def apns_registration_user_id(call: ServiceCall) -> str | None:
        return call.data.get("user_id") or getattr(getattr(call, "context", None), "user_id", None)

    async def handle_push_register(call: ServiceCall) -> dict[str, Any]:
        payload = apns_registration_payload(call)
        _LOGGER.debug(
            "DJConnect APNs push register service request client_type=%s device_id_present=%s environment=%s token_present=%s bootstrap_proof_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get(CONF_DEVICE_ID) or "").strip()),
            str(payload.get("push_environment") or "").strip()[:32],
            bool(str(payload.get("push_token") or "").strip()),
            bool(
                str(
                    payload.get(CONF_CENTRAL_API_BOOTSTRAP_PROOF)
                    or payload.get("bootstrap_proof")
                    or ""
                ).strip()
            ),
        )
        return await async_register_push(
            hass,
            runtime,
            user_id=apns_registration_user_id(call),
            payload=payload,
        )

    async def handle_push_unregister(call: ServiceCall) -> dict[str, Any]:
        payload = apns_registration_payload(call)
        _LOGGER.debug(
            "DJConnect APNs push unregister service request client_type=%s device_id_present=%s environment=%s token_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get(CONF_DEVICE_ID) or "").strip()),
            str(payload.get("push_environment") or "").strip()[:32],
            bool(str(payload.get("push_token") or "").strip()),
        )
        return await async_unregister_push(
            hass,
            runtime,
            user_id=apns_registration_user_id(call),
            payload=payload,
        )

    async def handle_music_backend_status(call: ServiceCall) -> dict[str, Any]:
        metadata = music_backend_metadata(hass, runtime)
        return {
            "success": True,
            **metadata,
            "selected": metadata.get("music_backend"),
            "target_player": metadata.get("music_target_player"),
            "config": {
                "music_backend": runtime.config.get(CONF_MUSIC_BACKEND),
                "music_assistant_player_configured": bool(
                    runtime.config.get(CONF_MUSIC_ASSISTANT_PLAYER)
                ),
                "spotify_direct_oauth_configured": bool(
                    runtime.config.get(CONF_SPOTIFY_REFRESH_TOKEN)
                ),
            },
        }

    async def handle_start_spotify_oauth(call: ServiceCall) -> dict[str, Any]:
        client_id = (
            call.data.get("client_id")
            or runtime.config.get(CONF_SPOTIFY_CLIENT_ID)
            or ""
        ).strip()
        if not client_id:
            raise RuntimeError(
                "Provide spotify_client_id or configure it in DJConnect options"
            )
        base_url = (
            call.data.get("ha_base_url")
            or runtime.config.get(CONF_HA_EXTERNAL_URL)
            or "http://homeassistant.local:8123"
        ).strip()
        scopes = ensure_spotify_scopes(
            call.data.get("scopes")
            or runtime.config.get(CONF_SPOTIFY_SCOPES)
            or DEFAULT_SPOTIFY_SCOPES
        )
        market = (
            call.data.get("market")
            or runtime.config.get(CONF_SPOTIFY_MARKET)
            or DEFAULT_SPOTIFY_MARKET
        ).strip()
        verifier = create_code_verifier()
        state = secrets.token_urlsafe(24)
        redirect_uri = build_redirect_uri(base_url)
        _LOGGER.debug(
            "DJConnect developer action start_spotify_oauth redirect_uri=%s market=%s",
            redirect_uri,
            market,
        )
        pending = hass.data.setdefault(DOMAIN, {}).setdefault(
            "spotify_oauth_pending",
            {},
        )
        pending[state] = {
            "entry_id": entry.entry_id,
            "client_id": client_id,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "market": market,
        }
        auth_url = build_authorize_url(
            client_id,
            redirect_uri,
            scopes,
            state,
            verifier,
        )
        return {"auth_url": auth_url, "redirect_uri": redirect_uri, "scopes": scopes}

    async def handle_device_command(call: ServiceCall) -> dict[str, Any]:
        command = str(call.data.get("command") or "").strip()
        if not command:
            raise RuntimeError("Provide a DJConnect device command")
        payload = dict(call.data.get("payload") or {})
        _LOGGER.debug("DJConnect developer action device_command: %s", command)
        return await runtime.async_device_command(hass, command, **payload)

    async def handle_refresh_device_info(call: ServiceCall) -> dict[str, Any]:
        _LOGGER.debug("DJConnect developer action refresh_device_info started")
        return await runtime.async_refresh_device_info(hass)

    async def handle_reboot_device(call: ServiceCall) -> dict[str, Any]:
        _LOGGER.debug("DJConnect developer action reboot_device started")
        return await runtime.async_device_post(hass, "/api/device/reboot")

    async def handle_forget_device(call: ServiceCall) -> dict[str, Any]:
        _LOGGER.debug("DJConnect developer action forget_device started")
        return await runtime.async_device_post(hass, "/api/device/forget")

    def ask_dj_service_payload(call: ServiceCall) -> dict[str, Any]:
        payload = dict(call.data)
        payload.setdefault(CONF_CLIENT_TYPE, runtime.client_type())
        payload.setdefault(
            CONF_DEVICE_ID,
            runtime.device_status.get(CONF_DEVICE_ID) or runtime.pairing_device_id,
        )
        return payload

    def ask_dj_service_headers(payload: dict[str, Any]) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-DJConnect-Client-Type": str(payload.get(CONF_CLIENT_TYPE) or runtime.client_type()),
        }
        device_id = str(payload.get(CONF_DEVICE_ID) or "").strip()
        if device_id:
            headers["X-DJConnect-Device-ID"] = device_id
        if payload.get("client_id"):
            headers["X-DJConnect-Client-ID"] = str(payload.get("client_id"))
        if payload.get("device_name"):
            headers["X-DJConnect-Device-Name"] = str(payload.get("device_name"))
        if payload.get("locale"):
            headers["X-DJConnect-Locale"] = str(payload.get("locale"))
        if payload.get("timezone"):
            headers["X-DJConnect-Timezone"] = str(payload.get("timezone"))
        if runtime.device_token:
            headers["Authorization"] = f"Bearer {runtime.device_token}"
        return headers

    def ask_dj_service_user_id(call: ServiceCall) -> str | None:
        return call.data.get("user_id") or getattr(getattr(call, "context", None), "user_id", None)

    async def handle_ask_dj(call: ServiceCall) -> dict[str, Any]:
        payload = ask_dj_service_payload(call)
        _LOGGER.debug("DJConnect Ask DJ service request received")
        return await async_handle_ask_dj(
            hass,
            runtime,
            payload,
            user_id=ask_dj_service_user_id(call),
        )

    async def handle_ask_dj_message(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_ask_dj_message_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Ask DJ message service request client_type=%s client_message_id_present=%s audio_response=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get("client_message_id") or "").strip()),
            str(payload.get("audio_response") or "").strip()[:24],
        )
        result, _status = await async_handle_ask_dj_message_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_ask_dj_idle_suggestion(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_ask_dj_idle_suggestion_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Ask DJ idle suggestion service request client_type=%s",
            payload.get(CONF_CLIENT_TYPE),
        )
        result, _status = await async_handle_ask_dj_idle_suggestion_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_ask_dj_history(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_ask_dj_history_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Ask DJ history service request client_type=%s since_revision=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get("since_revision"),
        )
        result, _status = await async_handle_ask_dj_history_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_queue(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_command_payload

        payload = ask_dj_service_payload(call)
        payload["command"] = "queue"
        _LOGGER.debug(
            "DJConnect queue service request client_type=%s device_id_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get(CONF_DEVICE_ID) or "").strip()),
        )
        result, _status = await async_handle_command_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_playlists(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_command_payload

        payload = ask_dj_service_payload(call)
        value = {
            key: payload[key]
            for key in ("limit", "market", "locale")
            if payload.get(key) not in (None, "")
        }
        payload["command"] = "playlists"
        if value:
            payload["value"] = value
        _LOGGER.debug(
            "DJConnect playlists service request client_type=%s device_id_present=%s limit=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get(CONF_DEVICE_ID) or "").strip()),
            value.get("limit"),
        )
        result, _status = await async_handle_command_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_playback_command_service(
        call: ServiceCall,
        command: str | None = None,
    ) -> dict[str, Any]:
        from .api_handlers import async_handle_command_payload

        payload = ask_dj_service_payload(call)
        command_name = str(command or payload.get("command") or "").strip()
        if not command_name:
            raise RuntimeError("Provide a playback command")
        payload["command"] = command_name
        if "value" in call.data:
            payload["value"] = call.data.get("value")
        if "play" in call.data:
            payload["play"] = bool(call.data.get("play"))
        _LOGGER.debug(
            "DJConnect playback service request command=%s client_type=%s device_id_present=%s play=%s value_present=%s",
            command_name,
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get(CONF_DEVICE_ID) or "").strip()),
            bool(payload.get("play", False)),
            "value" in payload,
        )
        result, _status = await async_handle_command_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_playback_status(call: ServiceCall) -> dict[str, Any]:
        return await handle_playback_command_service(call, "status")

    async def handle_playback_devices(call: ServiceCall) -> dict[str, Any]:
        return await handle_playback_command_service(call, "devices")

    async def handle_playback_command(call: ServiceCall) -> dict[str, Any]:
        return await handle_playback_command_service(call)

    async def handle_track_insight(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_track_insight_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Track Insight service request client_type=%s title_present=%s artist_present=%s force_refresh=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get("title") or "").strip()),
            bool(str(payload.get("artist") or "").strip()),
            bool(payload.get("force_refresh")),
        )
        result, _status = await async_handle_track_insight_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            source="service",
        )
        if result.get("success", True) and result.get("track"):
            bus = getattr(hass, "bus", None)
            fire = getattr(bus, "async_fire", None)
            if callable(fire):
                fire(TRACK_INSIGHT_EVENT, result)
        return result

    def discovery_service_payload(call: ServiceCall) -> dict[str, Any]:
        payload = dict(call.data)
        payload.setdefault(CONF_CLIENT_TYPE, runtime.client_type())
        payload.setdefault(
            CONF_DEVICE_ID,
            runtime.device_status.get(CONF_DEVICE_ID) or runtime.pairing_device_id,
        )
        return payload

    def discovery_service_headers(payload: dict[str, Any]) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-DJConnect-Client-Type": str(payload.get(CONF_CLIENT_TYPE) or runtime.client_type()),
        }
        device_id = str(payload.get(CONF_DEVICE_ID) or "").strip()
        if device_id:
            headers["X-DJConnect-Device-ID"] = device_id
        if runtime.device_token:
            headers["Authorization"] = f"Bearer {runtime.device_token}"
        return headers

    def discovery_service_user_id(call: ServiceCall) -> str | None:
        return call.data.get("user_id") or getattr(getattr(call, "context", None), "user_id", None)

    async def handle_vibecast_feed(call: ServiceCall) -> dict[str, Any]:
        from .vibecast import async_handle_vibecast_payload

        payload = discovery_service_payload(call)
        _LOGGER.debug(
            "DJConnect VibeCast feed service request client_type=%s render_capabilities_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get("render_capabilities") or "").strip()),
        )
        result, _status = await async_handle_vibecast_payload(
            hass,
            payload,
            headers=discovery_service_headers(payload),
        )
        return result

    async def handle_music_discovery_feed(call: ServiceCall) -> dict[str, Any]:
        from .music_discovery import async_handle_music_discovery_feed_payload

        payload = discovery_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music Discovery feed service request client_type=%s force_refresh=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(payload.get("force_refresh")),
        )
        result, _status = await async_handle_music_discovery_feed_payload(
            hass,
            payload,
            headers=discovery_service_headers(payload),
            user_id=discovery_service_user_id(call),
            force_refresh=bool(payload.get("force_refresh")),
        )
        return result

    async def handle_refresh_music_discovery(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_discovery_refresh_payload

        payload = discovery_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music Discovery refresh service request client_type=%s",
            payload.get(CONF_CLIENT_TYPE),
        )
        result, _status = await async_handle_music_discovery_refresh_payload(
            hass,
            payload,
            headers=discovery_service_headers(payload),
            user_id=discovery_service_user_id(call),
        )
        return result

    async def handle_play_music_discovery_item(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_discovery_play_payload

        payload = discovery_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music Discovery play service request client_type=%s item_id_present=%s section_id_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get("discovery_item_id") or payload.get("item_id") or "").strip()),
            bool(str(payload.get("section_id") or "").strip()),
        )
        result, _status = await async_handle_music_discovery_play_payload(
            hass,
            payload,
            headers=discovery_service_headers(payload),
            user_id=discovery_service_user_id(call),
        )
        return result

    async def handle_music_discovery_feedback(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_discovery_feedback_payload

        payload = discovery_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music Discovery feedback service request client_type=%s action=%s item_id_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get("feedback") or payload.get("action"),
            bool(str(payload.get("discovery_item_id") or payload.get("item_id") or "").strip()),
        )
        result, _status = await async_handle_music_discovery_feedback_payload(
            hass,
            payload,
            headers=discovery_service_headers(payload),
            user_id=discovery_service_user_id(call),
        )
        return result

    async def handle_music_dna_profile(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_dna_profile_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music DNA profile service request client_type=%s music_dna_key_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get("music_dna_key") or "").strip()),
        )
        result, _status = await async_handle_music_dna_profile_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_set_music_dna_enabled(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_dna_settings_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music DNA settings service request client_type=%s enabled=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(payload.get("enabled")),
        )
        result, _status = await async_handle_music_dna_settings_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_clear_music_dna(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_dna_clear_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music DNA clear service request client_type=%s music_dna_key_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            bool(str(payload.get("music_dna_key") or "").strip()),
        )
        result, _status = await async_handle_music_dna_clear_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_music_dna_export(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_dna_export_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music DNA export service request client_type=%s",
            payload.get(CONF_CLIENT_TYPE),
        )
        result, _status = await async_handle_music_dna_export_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_music_dna_import(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_music_dna_import_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Music DNA import service request client_type=%s profile_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            "profile" in payload,
        )
        result, _status = await async_handle_music_dna_import_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_clear_ask_dj_history(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_ask_dj_history_clear_payload

        payload = ask_dj_service_payload(call)
        _LOGGER.debug(
            "DJConnect Ask DJ history clear service request client_type=%s",
            payload.get(CONF_CLIENT_TYPE),
        )
        result, _status = await async_handle_ask_dj_history_clear_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_ask_dj_history_state(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_ask_dj_history_state_payload

        payload = ask_dj_service_payload(call)
        if "history_revision" not in payload and "generation" in payload:
            payload["history_revision"] = payload.get("generation")
        _LOGGER.debug(
            "DJConnect Ask DJ history state service request client_type=%s history_revision=%s clear_revision=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get("history_revision"),
            payload.get("clear_revision"),
        )
        result, _status = await async_handle_ask_dj_history_state_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_profile_export(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_profile_export_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_profile_export_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_household_export(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_household_export_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_household_export_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_integration_export(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_integration_export_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_integration_export_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_profile_import(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_profile_import_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_profile_import_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_household_import(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_household_import_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_household_import_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_clear_profile_state(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_profile_clear_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_profile_clear_payload(
            hass,
            payload,
            headers=ask_dj_service_headers(payload),
            user_id=ask_dj_service_user_id(call),
        )
        return result

    async def handle_start_session(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_session_start_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_session_start_payload(
            hass, payload, headers=ask_dj_service_headers(payload), user_id=ask_dj_service_user_id(call)
        )
        return result

    async def handle_end_session(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_session_end_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_session_end_payload(
            hass, payload, headers=ask_dj_service_headers(payload), user_id=ask_dj_service_user_id(call)
        )
        return result

    async def handle_active_session(call: ServiceCall) -> dict[str, Any]:
        from .api_handlers import async_handle_active_session_payload

        payload = ask_dj_service_payload(call)
        result, _status = await async_handle_active_session_payload(
            hass, payload, headers=ask_dj_service_headers(payload), user_id=ask_dj_service_user_id(call)
        )
        return result

    service_handlers = {
        "test_parse": (handle_test_parse, "optional"),
        "test_tts": (handle_test_tts, "optional"),
        "test_command": (handle_test_command, "optional"),
        "test_ptt_text": (handle_test_ptt_text, "optional"),
        "test_apns_push": (handle_test_apns_push, "optional"),
        "push_register": (handle_push_register, "optional"),
        "push_unregister": (handle_push_unregister, "optional"),
        "music_backend_status": (handle_music_backend_status, "only"),
        "start_spotify_oauth": (handle_start_spotify_oauth, "only"),
        "device_command": (handle_device_command, "optional"),
        "queue": (handle_queue, "optional"),
        "playlists": (handle_playlists, "optional"),
        "playback_status": (handle_playback_status, "optional"),
        "playback_devices": (handle_playback_devices, "optional"),
        "playback_command": (handle_playback_command, "optional"),
        "refresh_device_info": (handle_refresh_device_info, "optional"),
        "reboot_device": (handle_reboot_device, "optional"),
        "forget_device": (handle_forget_device, "optional"),
        "ask_dj": (handle_ask_dj, "optional"),
        "ask_dj_message": (handle_ask_dj_message, "optional"),
        "ask_dj_idle_suggestion": (handle_ask_dj_idle_suggestion, "optional"),
        "ask_dj_history": (handle_ask_dj_history, "optional"),
        "track_insight": (handle_track_insight, "optional"),
        "vibecast_feed": (handle_vibecast_feed, "optional"),
        "music_discovery_feed": (handle_music_discovery_feed, "optional"),
        "refresh_music_discovery": (handle_refresh_music_discovery, "optional"),
        "play_music_discovery_item": (handle_play_music_discovery_item, "optional"),
        "music_discovery_feedback": (handle_music_discovery_feedback, "optional"),
        "music_dna_profile": (handle_music_dna_profile, "optional"),
        "set_music_dna_enabled": (handle_set_music_dna_enabled, "optional"),
        "clear_music_dna": (handle_clear_music_dna, "optional"),
        "music_dna_export": (handle_music_dna_export, "optional"),
        "music_dna_import": (handle_music_dna_import, "optional"),
        "clear_ask_dj_history": (handle_clear_ask_dj_history, "optional"),
        "ask_dj_history_state": (handle_ask_dj_history_state, "optional"),
        "profile_export": (handle_profile_export, "optional"),
        "household_export": (handle_household_export, "optional"),
        "integration_export": (handle_integration_export, "optional"),
        "profile_import": (handle_profile_import, "optional"),
        "household_import": (handle_household_import, "optional"),
        "clear_profile_state": (handle_clear_profile_state, "optional"),
        "start_session": (handle_start_session, "optional"),
        "end_session": (handle_end_session, "optional"),
        "active_session": (handle_active_session, "optional"),
    }
    for service_name, (handler, response_mode) in service_handlers.items():
        hass.services.async_register(
            DOMAIN,
            service_name,
            handler,
            schema=DEVELOPER_SERVICE_SCHEMAS.get(service_name),
            supports_response=response_mode,
        )
        _LOGGER.debug(
            "DJConnect registered developer action %s with response mode %s",
            service_name,
            response_mode,
        )


def _schedule_daily_music_discovery_push(hass: HomeAssistant, entry: ConfigEntry, runtime: Any) -> None:
    """Schedule the daily Music Discovery APNs wake/sync hint."""
    if async_track_time_change is None:
        _LOGGER.debug("DJConnect daily Music Discovery push scheduler unavailable")
        return

    async def _send_daily_push(now) -> None:
        await _async_send_daily_music_discovery_push(hass, runtime, now=now)

    unsub = async_track_time_change(
        hass,
        _send_daily_push,
        hour=MUSIC_DISCOVERY_DAILY_PUSH_HOUR,
        minute=0,
        second=0,
    )
    entry.async_on_unload(unsub)


def _schedule_hourly_music_discovery_refresh(hass: HomeAssistant, entry: ConfigEntry, runtime: Any) -> None:
    """Schedule server-side Music Discovery refresh without waiting for clients."""
    if async_track_time_interval is None:
        _LOGGER.debug("DJConnect hourly Music Discovery refresh scheduler unavailable")
        return

    async def _refresh(_now) -> None:
        await _async_refresh_music_discovery_server_side(hass, runtime)

    unsub = async_track_time_interval(hass, _refresh, timedelta(hours=1))
    entry.async_on_unload(unsub)


async def _async_refresh_music_discovery_server_side(
    hass: HomeAssistant,
    runtime: Any,
) -> dict[str, Any]:
    """Refresh Music DNA/Discovery cache for eligible runtimes on the server."""
    client_type = _runtime_push_client_type(runtime)
    device_id = _runtime_push_device_id(runtime)
    if not client_type or not device_id:
        return {"success": True, "refreshed": False, "suppressed": "missing_identity"}
    device_token = str(getattr(runtime, "device_token", "") or "").strip()
    if not device_token:
        return {"success": True, "refreshed": False, "suppressed": "missing_device_token"}
    if not await _music_dna_enabled_for_daily_push(runtime, device_id, client_type):
        return {"success": True, "refreshed": False, "suppressed": "music_dna_disabled"}
    profile_refreshed = await _async_refresh_music_dna_listening_profile_server_side(
        hass,
        runtime,
        {
            CONF_DEVICE_ID: device_id,
            CONF_CLIENT_TYPE: client_type,
        },
    )
    try:
        from .music_discovery import async_handle_music_discovery_feed_payload

        result, status = await async_handle_music_discovery_feed_payload(
            hass,
            {
                CONF_DEVICE_ID: device_id,
                CONF_CLIENT_TYPE: client_type,
            },
            headers={
                "Authorization": f"Bearer {device_token}",
                "X-DJConnect-Device-ID": device_id,
                "X-DJConnect-Client-Type": client_type,
            },
            user_id=None,
            force_refresh=True,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect hourly Music Discovery refresh failed: %s", exc.__class__.__name__)
        return {"success": False, "refreshed": False, "error": "refresh_failed"}
    sections = result.get("sections") if isinstance(result, dict) else []
    item_count = sum(len(section.get("items") or []) for section in sections if isinstance(section, dict))
    refreshed = status == 200 and bool(result.get("enabled"))
    _LOGGER.debug(
        "DJConnect hourly Music Discovery refresh result refreshed=%s status=%s sections=%s items=%s client_type=%s",
        refreshed,
        status,
        len(sections) if isinstance(sections, list) else 0,
        item_count,
        client_type,
    )
    return {
        "success": bool(status == 200),
        "refreshed": refreshed,
        "music_dna_profile_refreshed": profile_refreshed,
        "status": status,
        "sections": len(sections) if isinstance(sections, list) else 0,
        "items": item_count,
    }


async def _async_refresh_music_dna_listening_profile_server_side(
    hass: HomeAssistant,
    runtime: Any,
    payload: dict[str, Any],
) -> bool:
    """Refresh compact Music DNA Spotify profile data on the server."""
    memory = getattr(runtime, "memory", None)
    freshness = getattr(memory, "async_listening_profile_is_fresh", None)
    updater = getattr(memory, "async_update_listening_profile", None)
    if not callable(freshness) or not callable(updater):
        return False
    try:
        if await freshness(runtime, payload, user_id=None, ttl_seconds=60 * 60):
            return False
        result = await run_music_command(hass, runtime, "listening_profile")
        profile = result.get("profile") if isinstance(result, dict) else {}
        if not isinstance(profile, dict) or not profile:
            return False
        await updater(runtime, profile, payload, user_id=None)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect hourly Music DNA listening profile refresh failed: %s", exc.__class__.__name__)
        return False
    _LOGGER.debug(
        "DJConnect hourly Music DNA listening profile refreshed client_type=%s device_id=%s",
        payload.get(CONF_CLIENT_TYPE),
        payload.get(CONF_DEVICE_ID),
    )
    return True


async def _async_send_daily_music_discovery_push(
    hass: HomeAssistant,
    runtime: Any,
    *,
    now: Any | None = None,
) -> dict[str, Any]:
    """Send one daily Music Discovery push when Music DNA is enabled."""
    client_type = _runtime_push_client_type(runtime)
    if client_type not in APNS_SUPPORTED_CLIENT_TYPES:
        return {"success": True, "sent": 0, "suppressed": "unsupported_client_type"}
    device_id = _runtime_push_device_id(runtime)
    if not await _music_dna_enabled_for_daily_push(runtime, device_id, client_type):
        return {"success": True, "sent": 0, "suppressed": "music_dna_disabled"}
    today = (now.date() if hasattr(now, "date") else date.today()).isoformat()
    if getattr(runtime, "music_discovery_daily_push_date", None) == today:
        return {"success": True, "sent": 0, "suppressed": "already_sent_today"}
    result = await async_send_push_event(
        hass,
        runtime,
        user_id=None,
        event_type=EVENT_MUSIC_DISCOVERY_READY,
        source_device_id=device_id,
        client_type=client_type,
    )
    if result.get("sent"):
        setattr(runtime, "music_discovery_daily_push_date", today)
    _LOGGER.debug(
        "DJConnect daily Music Discovery push result sent=%s suppressed=%s error=%s client_type=%s",
        result.get("sent"),
        result.get("suppressed"),
        result.get("error") or result.get("last_push_error"),
        client_type,
    )
    return result


async def _music_dna_enabled_for_daily_push(
    runtime: Any,
    device_id: str | None,
    client_type: str,
) -> bool:
    memory = getattr(runtime, "memory", None)
    if memory is None:
        return False
    payload = {
        key: value
        for key, value in (
            (CONF_DEVICE_ID, device_id),
            (CONF_CLIENT_TYPE, client_type),
        )
        if value
    }
    try:
        context = await memory.async_context_for_runtime(runtime, payload, user_id=None)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect daily Music Discovery push Music DNA lookup failed: %s", exc.__class__.__name__)
        return False
    memory_payload = context.get("memory") if isinstance(context, dict) else {}
    return bool(isinstance(memory_payload, dict) and memory_payload.get("enabled"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    try:
        await async_initialize_persistence(hass)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.error("DJConnect persistence bootstrap failed: %s", exc.__class__.__name__)
        return False
    await PersistentSessionStartupReconciler(
        PersistentSessionRepository(persistence_service(hass)),
        history=HistoricalProjectionRepository(persistence_service(hass)),
    ).async_reconcile()
    # Some Home Assistant startup paths load config entries without first
    # retaining the integration-level setup state. Registering here as well
    # keeps the public HA routes available for every configured runtime.
    register_http_views(hass)
    option_updates = dict(entry.options)
    runtime_for_defaults = DJConnectRuntime(entry=entry)
    if not option_updates.get(CONF_API_BASE_URL):
        option_updates[CONF_API_BASE_URL] = DEFAULT_API_BASE_URL
    if not option_updates.get(CONF_HA_INSTALL_ID) and not entry.data.get(CONF_HA_INSTALL_ID):
        option_updates[CONF_HA_INSTALL_ID] = ensure_ha_install_id(
            runtime_for_defaults,
            hass,
        )
    if option_updates != dict(entry.options):
        hass.config_entries.async_update_entry(entry, options=option_updates)
    runtime = _restore_runtime(hass, entry)
    if runtime.memory is not None:
        await runtime.memory.async_load()
    task_factory = getattr(hass, "async_create_task", None)
    if callable(task_factory):
        task_factory(async_ensure_install_token(hass, runtime))
    _setup_device_coordinator(hass, runtime)
    stt_info = detect_stt_support(hass, runtime.config)
    _LOGGER.info(
        "DJConnect STT route: ha_version=%s pipeline_id=%s pipeline_name=%s "
        "language=%s stt_engine=%s stt_available=%s audio_format=%s configured=%s",
        stt_info.get("ha_version"),
        stt_info.get("pipeline_id"),
        stt_info.get("pipeline_name"),
        stt_info.get("language"),
        stt_info.get("stt_engine"),
        bool(stt_info.get("stt_engine")),
        stt_info.get("audio_format"),
        stt_info.get("configured"),
    )
    await async_create_fixable_issues(hass, entry)
    await _try_initial_device_provisioning(hass, runtime)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _schedule_daily_music_discovery_push(hass, entry, runtime)
    _schedule_hourly_music_discovery_refresh(hass, entry, runtime)
    _register_developer_services(hass, entry, runtime)

    await hass.config_entries.async_forward_entry_setups(entry, _platforms_for_runtime(runtime))
    _LOGGER.info("DJConnect v%s loaded", VERSION)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    platforms = _platforms_for_runtime(runtime) if runtime is not None else list(PLATFORMS)
    unloaded = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unloaded:
        if runtime is not None:
            from .playback_observation import playback_observation_manager

            await playback_observation_manager(hass).async_stop_runtime(runtime)
        _clear_pending_app_pairings_for_entry(hass, entry, runtime)
        hass.data[DOMAIN].pop(entry.entry_id, None)
        runtime = hass.data[DOMAIN].get("runtime")
        if runtime and runtime.entry.entry_id == entry.entry_id:
            hass.data[DOMAIN].pop("runtime", None)
        if not _has_runtime_entries(hass):
            await _async_clear_all_server_state(hass)
            await async_shutdown_persistence(hass)
    return unloaded


def _clear_pending_app_pairings_for_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    runtime: Any | None,
) -> None:
    """Remove pending app-pairing contexts tied to an unloaded entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    pending = domain_data.get(APP_PAIRING_PENDING_KEY)
    if not isinstance(pending, dict):
        return
    data = getattr(entry, "data", {}) or {}
    status = getattr(runtime, "device_status", {}) or {}
    device_ids = {
        str(value).strip()
        for value in (
            data.get(CONF_DEVICE_ID),
            status.get(CONF_DEVICE_ID),
            getattr(runtime, "pairing_device_id", None),
        )
        if str(value or "").strip()
    }
    tokens = {
        str(value).strip()
        for value in (
            data.get(CONF_DEVICE_TOKEN),
            getattr(runtime, "device_token", None),
        )
        if str(value or "").strip()
    }
    for pair_code, context in list(pending.items()):
        if not isinstance(context, dict):
            continue
        received = context.get("pairing_received")
        received = received if isinstance(received, dict) else {}
        context_device_id = str(
            received.get(CONF_DEVICE_ID) or context.get(CONF_DEVICE_ID) or ""
        ).strip()
        context_token = str(
            received.get(CONF_DEVICE_TOKEN) or context.get(CONF_DEVICE_TOKEN) or ""
        ).strip()
        if (
            context_device_id
            and context_device_id in device_ids
            or context_token
            and context_token in tokens
        ):
            pending.pop(pair_code, None)


def _has_runtime_entries(hass: HomeAssistant) -> bool:
    """Return whether any DJConnect config-entry runtime is still loaded."""
    return any(
        key != "runtime" and hasattr(value, "authorize_device_request")
        for key, value in hass.data.get(DOMAIN, {}).items()
    )


async def _async_clear_all_server_state(hass: HomeAssistant) -> None:
    """Clear server-side Music DNA/history after the last DJConnect entry unloads."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    memory_manager = domain_data.pop("memory_manager", None)
    if memory_manager is not None and hasattr(memory_manager, "async_clear"):
        await memory_manager.async_clear()
    history_manager = domain_data.pop("ask_dj_history_manager", None)
    if history_manager is not None and hasattr(history_manager, "async_clear_all"):
        await history_manager.async_clear_all()
    _LOGGER.info("DJConnect cleared server-side Music DNA and Ask DJ history after last entry unload")


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    signatures = domain_data.setdefault("entry_reload_signatures", {})
    current_signature = _entry_reload_signature(entry)
    previous_signature = signatures.get(entry.entry_id)
    signatures[entry.entry_id] = current_signature
    if previous_signature == current_signature:
        runtime = domain_data.get(entry.entry_id)
        if runtime is not None:
            runtime.entry = entry
            cached_status = entry.data.get(CONF_LAST_DEVICE_STATUS)
            if isinstance(cached_status, dict):
                _merge_cached_device_status(
                    runtime.device_status,
                    cached_status,
                    source="persisted device status update",
                )
            if entry.data.get(CONF_SPOTIFY_REFRESH_TOKEN):
                runtime.latest_spotify_refresh_token = entry.data[
                    CONF_SPOTIFY_REFRESH_TOKEN
                ]
        _LOGGER.debug(
            "DJConnect config entry update only changed runtime cache fields; skipping reload"
        )
        return
    await hass.config_entries.async_reload(entry.entry_id)


def _entry_reload_signature(entry: ConfigEntry) -> tuple[tuple[str, Any], tuple[str, Any]]:
    """Return config values that should trigger a full integration reload."""

    def stable_items(values: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
        return tuple(
            sorted(
                (str(key), value)
                for key, value in (values or {}).items()
                if key not in {CONF_SPOTIFY_REFRESH_TOKEN, CONF_LAST_DEVICE_STATUS}
            )
        )

    return (
        stable_items(getattr(entry, "data", {}) or {}),
        stable_items(getattr(entry, "options", {}) or {}),
    )
