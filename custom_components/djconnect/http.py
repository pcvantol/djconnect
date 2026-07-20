from __future__ import annotations

import base64
import html
import logging
from pathlib import Path
import re
import secrets
from typing import Any
from urllib.parse import urlsplit

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_ASK_DJ,
    API_ASK_DJ_CLEAR,
    API_ASK_DJ_HISTORY,
    API_ASK_DJ_HISTORY_CLEAR,
    API_ASK_DJ_HISTORY_EXPORT,
    API_ASK_DJ_HISTORY_STATE,
    API_ASK_DJ_IDLE_SUGGESTION,
    API_ASK_DJ_MESSAGE,
    API_BASE,
    API_COMMAND,
    API_IMAGE_PROXY,
    API_MUSIC_DISCOVERY,
    API_MUSIC_DISCOVERY_FEEDBACK,
    API_MUSIC_DISCOVERY_PLAY,
    API_MUSIC_DISCOVERY_REFRESH,
    API_MUSIC_DNA_CLEAR,
    API_MUSIC_DNA_EXPORT,
    API_MUSIC_DNA_IMPORT,
    API_MUSIC_DNA_PROFILE,
    API_MUSIC_DNA_SETTINGS,
    API_SPOTIFY_CALLBACK,
    API_EVENT,
    API_PAIR,
    API_PUSH_BOOTSTRAP,
    API_PUSH_REGISTER,
    API_PUSH_UNREGISTER,
    API_STATUS,
    API_TTS,
    API_TRACK_INSIGHT,
    API_VIBECAST,
    API_SESSION_START,
    API_SESSION_END,
    API_SESSION_ACTIVE,
    API_SESSION_BROADCAST_TOKEN,
    API_VOICE,
    CONF_ASSIST_PIPELINE_ID,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TOKEN,
    CONF_HA_EXTERNAL_URL,
    CONF_HA_INSTALL_ID,
    CONF_LOCAL_URL,
    CONF_MAX_AUDIO_BYTES,
    CONF_MUSIC_BACKEND,
    CONF_MUSIC_BACKEND_REVISION,
    CONF_PAIR_CODE,
    DOMAIN,
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CLIENT_TYPE_WINDOWS,
    DEFAULT_MAX_AUDIO_BYTES,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_MARKET,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_SCOPES,
    CONF_TTS_LANGUAGE,
    CONF_VOICE_PROFILE,
    DEFAULT_SPOTIFY_MARKET,
    DEFAULT_SPOTIFY_SCOPES,
    VOICE_PROFILE_CLEAN_HOST,
    VOICE_PROFILE_ENERGY,
    VOICE_PROFILE_LATE_NIGHT,
    VERSION,
)
from .announcements import announcement_capabilities
from .ask_dj import async_handle_ask_dj, async_idle_suggestion, image_proxy_target  # noqa: F401
from .ask_dj_history import AskDJHistoryManager
from .assist_stt import (
    DJConnectNoSttProviderError,
    transcribe_wav_with_assist,
)
from .central_api import ensure_ha_install_id
from .dj_response import async_create_dj_audio_url, async_send_dj_response_best_effort, get_tts_audio
from .ha_urls import async_ha_url_payload
from .mood import enrich_payload_with_mood_zone, mood_play_now_suffix
from .pipeline import generate_dj_response_with_assist
from .push import (
    async_bootstrap as async_bootstrap_push,
    async_register as async_register_push,
    async_send_event as async_send_push_event,
    async_status as async_push_status,
    async_unregister as async_unregister_push,
)
from .request_auth import (
    _last_stale_auth_log,
    authorize_runtime_device_request as _authorize_runtime_device_request,
    identity_payload as _identity_payload,
    payload_client_type as _payload_client_type,
    resolve_runtime as _runtime,
    runtime_client_type as _runtime_client_type,
    validate_required_client_type as _validate_required_client_type,
)
from .spotify_backend import SpotifyBackendError
from .use_cases import (
    MusicBackendCapabilityError,
    music_backend_metadata,
    run_music_command,
    run_text_command,
)
from .voice_profiles import normalize_voice_profile, voice_profile_for_mood_or_config
from .spotify_oauth import exchange_code_for_refresh_token

_LOGGER = logging.getLogger(__name__)
__all__ = ["_last_stale_auth_log", "async_send_push_event"]
_LOGO_DATA_URI: str | None = None
VOICE_DEBUG_KEY = "last_voice_debug"
VOICE_DEBUG_URL = "/api/djconnect/v1/debug/last_voice.wav"
CONF_LAST_DEVICE_STATUS = "last_device_status"


def _read_djconnect_logo_data_uri() -> str:
    """Read and encode the DJConnect app icon."""
    logo = Path(__file__).with_name("icon.png").read_bytes()
    return f"data:image/png;base64,{base64.b64encode(logo).decode()}"


async def _async_djconnect_logo_data_uri(hass: Any) -> str:
    """Return the embedded DJConnect app icon without blocking the event loop."""
    global _LOGO_DATA_URI
    if _LOGO_DATA_URI is None:
        executor = getattr(hass, "async_add_executor_job", None)
        if callable(executor):
            _LOGO_DATA_URI = await executor(_read_djconnect_logo_data_uri)
        else:
            _LOGO_DATA_URI = _read_djconnect_logo_data_uri()
    return _LOGO_DATA_URI


async def _spotify_oauth_html_response(
    hass: Any,
    *,
    title: str,
    message: str,
    status: int = 200,
    base_url: str | None = None,
    success: bool = True,
) -> web.Response:
    """Render a friendly standalone Spotify OAuth result page."""
    language = _ui_language(hass)
    close_label = {
        "en": "Close window",
        "nl": "Sluit venster",
        "de": "Fenster schließen",
        "fr": "Fermer la fenêtre",
        "es": "Cerrar ventana",
    }.get(language, "Close window")
    footer = {
        "en": "DJConnect manages playback through Home Assistant. Spotify is a trademark of Spotify AB.",
        "nl": "DJConnect beheert playback via Home Assistant. Spotify is a trademark of Spotify AB.",
        "de": "DJConnect verwaltet die Wiedergabe über Home Assistant. Spotify is a trademark of Spotify AB.",
        "fr": "DJConnect gère la lecture via Home Assistant. Spotify is a trademark of Spotify AB.",
        "es": "DJConnect gestiona la reproducción mediante Home Assistant. Spotify is a trademark of Spotify AB.",
    }.get(language, "DJConnect manages playback through Home Assistant. Spotify is a trademark of Spotify AB.")
    accent = "#1db954" if success else "#ff8a00"
    icon = "✓" if success else "!"
    logo_data_uri = await _async_djconnect_logo_data_uri(hass)
    html_body = f"""<!doctype html>
<html lang="{html.escape(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #070b08;
      --card: rgba(18, 24, 20, .88);
      --text: #f4f7f5;
      --muted: #aeb8b2;
      --accent: {accent};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 28px;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(29, 185, 84, .24), transparent 34rem),
        radial-gradient(circle at bottom right, rgba(255, 138, 0, .16), transparent 28rem),
        var(--bg);
      color: var(--text);
    }}
    main {{
      width: min(680px, 100%);
      padding: 34px;
      border: 1px solid rgba(255,255,255,.10);
      border-radius: 28px;
      background: linear-gradient(145deg, rgba(28,36,31,.94), var(--card));
      box-shadow: 0 28px 90px rgba(0,0,0,.45);
      text-align: center;
    }}
    .logo-wrap {{
      position: relative;
      display: inline-block;
    }}
    img {{
      width: 112px;
      height: 112px;
      border-radius: 24px;
      object-fit: cover;
      box-shadow: 0 12px 38px rgba(0,0,0,.34);
    }}
    .badge {{
      position: absolute;
      right: -22px;
      bottom: -16px;
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 999px;
      background: var(--accent);
      color: #051008;
      font-size: 28px;
      font-weight: 800;
    }}
    h1 {{
      margin: 20px 0 12px;
      font-size: clamp(2rem, 6vw, 3.4rem);
      line-height: 1;
      letter-spacing: -.05em;
    }}
    p {{
      margin: 0 auto;
      max-width: 560px;
      color: var(--muted);
      font-size: 1.12rem;
      line-height: 1.65;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 12px;
      margin-top: 28px;
    }}
    a, button {{
      border: 0;
      border-radius: 999px;
      padding: 14px 20px;
      background: var(--accent);
      color: #06100a;
      font: inherit;
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
    }}
    button.secondary {{
      background: rgba(255,255,255,.10);
      color: var(--text);
    }}
    small {{
      display: block;
      margin-top: 24px;
      color: rgba(244,247,245,.55);
    }}
  </style>
</head>
<body>
  <main>
    <div class="logo-wrap">
      <img src="{logo_data_uri}" alt="DJConnect app icon">
      <div class="badge" aria-hidden="true">{icon}</div>
    </div>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(message)}</p>
    <div class="actions">
      <button onclick="window.close()">{html.escape(close_label)}</button>
    </div>
    <small>{html.escape(footer)}</small>
  </main>
</body>
</html>"""
    return web.Response(text=html_body, status=status, content_type="text/html")


def _ui_language(hass: Any) -> str:
    """Return the current supported Home Assistant UI language."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    if language.startswith(("nl", "de", "fr", "es")):
        return language[:2]
    return "en"


def _oauth_copy(hass: Any, key: str, **placeholders: Any) -> str:
    """Return localized Spotify OAuth callback page copy."""
    language = _ui_language(hass)
    copy = {
        "oauth_error_title": {
            "en": "Spotify OAuth failed",
            "nl": "Spotify OAuth niet gelukt",
            "de": "Spotify OAuth fehlgeschlagen",
            "fr": "Échec OAuth Spotify",
            "es": "OAuth de Spotify falló",
        },
        "oauth_error_message": {
            "en": "Spotify returned this error: {error}. Start Spotify authorization again from Home Assistant.",
            "nl": "Spotify gaf deze fout terug: {error}. Start de Spotify autorisatie opnieuw vanuit Home Assistant.",
            "de": "Spotify hat diesen Fehler zurückgegeben: {error}. Starte die Spotify-Autorisierung erneut in Home Assistant.",
            "fr": "Spotify a renvoyé cette erreur : {error}. Relance l’autorisation Spotify depuis Home Assistant.",
            "es": "Spotify devolvió este error: {error}. Inicia de nuevo la autorización de Spotify desde Home Assistant.",
        },
        "oauth_incomplete_title": {
            "en": "Spotify OAuth incomplete",
            "nl": "Spotify OAuth niet compleet",
            "de": "Spotify OAuth unvollständig",
            "fr": "OAuth Spotify incomplet",
            "es": "OAuth de Spotify incompleto",
        },
        "oauth_incomplete_message": {
            "en": "The callback is missing state or code. Start Spotify authorization again from Home Assistant.",
            "nl": "De callback mist een state of code. Start de Spotify autorisatie opnieuw vanuit Home Assistant.",
            "de": "Dem Callback fehlt state oder code. Starte die Spotify-Autorisierung erneut in Home Assistant.",
            "fr": "Le callback ne contient pas state ou code. Relance l’autorisation Spotify depuis Home Assistant.",
            "es": "Al callback le falta state o code. Inicia de nuevo la autorización de Spotify desde Home Assistant.",
        },
        "linked_title": {
            "en": "DJConnect is linked",
            "nl": "DJConnect is gekoppeld",
            "de": "DJConnect ist gekoppelt",
            "fr": "DJConnect est associé",
            "es": "DJConnect está emparejado",
        },
        "linked_message": {
            "en": "Spotify is linked with DJConnect. You can close this window and return to Home Assistant to finish your DJConnect setup.",
            "nl": "Spotify is gekoppeld met DJConnect. Je kunt dit venster sluiten en teruggaan naar Home Assistant om je DJConnect setup af te maken.",
            "de": "Spotify ist mit DJConnect verbunden. Du kannst dieses Fenster schließen und zu Home Assistant zurückkehren, um die Einrichtung abzuschließen.",
            "fr": "Spotify est associé à DJConnect. Tu peux fermer cette fenêtre et revenir à Home Assistant pour terminer la configuration DJConnect.",
            "es": "Spotify está conectado con DJConnect. Puedes cerrar esta ventana y volver a Home Assistant para terminar la configuración de DJConnect.",
        },
        "oauth_exception_title": {
            "en": "Spotify OAuth error",
            "nl": "Spotify OAuth fout",
            "de": "Spotify OAuth-Fehler",
            "fr": "Erreur OAuth Spotify",
            "es": "Error de OAuth de Spotify",
        },
        "oauth_exception_message": {
            "en": "Home Assistant could not complete Spotify authorization: {error}",
            "nl": "Home Assistant kon de Spotify autorisatie niet afronden: {error}",
            "de": "Home Assistant konnte die Spotify-Autorisierung nicht abschließen: {error}",
            "fr": "Home Assistant n’a pas pu terminer l’autorisation Spotify : {error}",
            "es": "Home Assistant no pudo completar la autorización de Spotify: {error}",
        },
        "expired_title": {
            "en": "Spotify OAuth expired",
            "nl": "Spotify OAuth verlopen",
            "de": "Spotify OAuth abgelaufen",
            "fr": "OAuth Spotify expiré",
            "es": "OAuth de Spotify caducó",
        },
        "expired_message": {
            "en": "This OAuth session is unknown or expired. Start Spotify reauthorization again from Home Assistant.",
            "nl": "Deze OAuth sessie is onbekend of verlopen. Start Spotify opnieuw autoriseren vanuit Home Assistant.",
            "de": "Diese OAuth-Sitzung ist unbekannt oder abgelaufen. Starte die Spotify-Neuautorisierung erneut in Home Assistant.",
            "fr": "Cette session OAuth est inconnue ou expirée. Relance la réautorisation Spotify depuis Home Assistant.",
            "es": "Esta sesión OAuth es desconocida o caducó. Inicia de nuevo la reautorización de Spotify desde Home Assistant.",
        },
        "reauth_title": {
            "en": "DJConnect is reauthorized",
            "nl": "DJConnect is opnieuw geautoriseerd",
            "de": "DJConnect ist erneut autorisiert",
            "fr": "DJConnect est réautorisé",
            "es": "DJConnect está reautorizado",
        },
        "reauth_message": {
            "en": "Spotify is linked with DJConnect again. You can close this window and return to Home Assistant.",
            "nl": "Spotify is opnieuw gekoppeld met DJConnect. Je kunt dit venster sluiten en teruggaan naar Home Assistant.",
            "de": "Spotify ist erneut mit DJConnect verbunden. Du kannst dieses Fenster schließen und zu Home Assistant zurückkehren.",
            "fr": "Spotify est de nouveau associé à DJConnect. Tu peux fermer cette fenêtre et revenir à Home Assistant.",
            "es": "Spotify está conectado de nuevo con DJConnect. Puedes cerrar esta ventana y volver a Home Assistant.",
        },
    }
    template = copy[key].get(language) or copy[key]["en"]
    return template.format(**{name: str(value) for name, value in placeholders.items()})


ERROR_MESSAGES = {
    "not_configured": "DJConnect is not configured.",
    "invalid_json": "Send valid JSON.",
    "missing_pair_data": "Send both device_id and pair_code.",
    "invalid_pair_code": "The pairing code does not match this DJConnect setup.",
    "unauthorized": "The DJConnect device token is missing or invalid.",
    "missing_audio": "Send WAV audio bytes in the request body.",
    "audio_too_large": "The uploaded audio is too large.",
    "unsupported_media_type": "Send audio/wav, audio/x-wav, application/octet-stream or JSON text.",
    "invalid_command": "Send a valid DJConnect command.",
    "invalid_client_type": "Send a valid DJConnect client_type.",
    "client_type_mismatch": "The selected DJConnect app type in Home Assistant does not match this client.",
    "backend_unavailable": "The configured playback backend is unavailable.",
    "stale_pairing": "DJConnect pairing is stale. Pair the device again.",
    "version_mismatch": "DJConnect Home Assistant integration and device firmware major.minor versions must match.",
}
APP_PAIRING_PENDING_KEY = "config_flow_app_pairing_pending"
DJ_FAILURE_TEXTS = {
    "assist": {
        "en": (
            "I heard you, but I could not turn that into a DJConnect request yet. "
            "Try asking for the artist or song again."
        ),
        "nl": (
            "Ik heb je gehoord, maar kon er nog geen DJConnect verzoek van maken. "
            "Vraag de artiest of het nummer nog een keer."
        ),
    },
    "spotify": {
        "en": (
            "Ik heb je verzoek begrepen, maar Spotify kon nu niet starten. "
            "Controleer de koppeling in Home Assistant en probeer het opnieuw."
        ),
        "nl": (
            "Ik heb je verzoek begrepen, maar Spotify kon nu niet starten. "
            "Controleer de koppeling in Home Assistant en probeer het opnieuw."
        ),
    },
    "generic": {
        "en": (
            "Er ging iets mis bij DJConnect. "
            "Vraag je muziek zo nog een keer aan."
        ),
        "nl": (
            "Er ging iets mis bij DJConnect. "
            "Vraag je muziek zo nog een keer aan."
        ),
    },
}
DJ_TEST_TEXTS = {
    "en": "DJConnect is ready for your next request.",
    "nl": "DJConnect is klaar voor je volgende verzoek.",
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


def _json_error(
    view: HomeAssistantView,
    error: str,
    status_code: int,
    message: str | None = None,
):
    return view.json(
        {
            "success": False,
            "error": error,
            "message": message or ERROR_MESSAGES.get(error, error),
        },
        status_code=status_code,
    )


def _safe_debug_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:8]}...{text[-4:]}"


def _safe_playback_state(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"playing", "paused", "stopped", "idle", "off"} else ""


def _safe_intent_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("intent") or value.get("name") or "").strip()[:64]
    return str(value or "").strip()[:64]


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


def _major_minor(version: Any) -> str | None:
    match = re.search(r"(\d+)\.(\d+)(?:\.\d+)?", str(version or ""))
    if not match:
        return None
    return f"{match.group(1)}.{match.group(2)}"


def _versions_compatible(ha_version: Any, firmware_version: Any) -> bool:
    if str(firmware_version or "").strip() == "0.0.0":
        return True

    ha_major_minor = _major_minor(ha_version)
    firmware_major_minor = _major_minor(firmware_version)
    return bool(
        ha_major_minor
        and firmware_major_minor
        and ha_major_minor == firmware_major_minor
    )


def _version_mismatch_response(view: HomeAssistantView, firmware_version: Any):
    ha_major_minor = _major_minor(VERSION)
    firmware_major_minor = _major_minor(firmware_version)
    return view.json(
        {
            "success": False,
            "error": "version_mismatch",
            "message": (
                "DJConnect Home Assistant integration and device firmware "
                "major.minor versions must match."
            ),
            "ha_version": VERSION,
            "ha_major_minor": ha_major_minor,
            "firmware": firmware_version,
            "firmware_major_minor": firmware_major_minor,
        },
        status_code=426,
    )


def _ha_version_payload() -> dict[str, str | None]:
    """Return DJConnect HA integration version metadata for clients."""
    return {
        "ha_version": VERSION,
        "ha_major_minor": _major_minor(VERSION),
    }


def _bootstrap_metadata(
    hass: Any,
    runtime: Any | None,
    *,
    pairing_session_id: Any = None,
) -> dict[str, str]:
    """Return non-secret HA metadata Apple clients need for bootstrap proofs."""
    install_id = ensure_ha_install_id(runtime, hass) if runtime is not None else _pending_ha_install_id(hass)
    metadata = {
        "ha_install_id": install_id,
        "integration_version": VERSION,
    }
    session_id = str(pairing_session_id or "").strip()
    if session_id:
        metadata["pairing_session_id"] = session_id
    return metadata


def _pending_ha_install_id(hass: Any) -> str:
    """Return a stable id for pending app pairing before a config entry exists."""
    domain_data = getattr(hass, "data", {}).setdefault(DOMAIN, {})
    current = str(domain_data.get(CONF_HA_INSTALL_ID) or "").strip()
    if current:
        return current
    current = f"ha_{secrets.token_urlsafe(24)}"
    domain_data[CONF_HA_INSTALL_ID] = current
    return current


def _runtime_firmware_version(runtime: Any) -> Any:
    status = getattr(runtime, "device_status", {}) or {}
    return (
        status.get("app_version")
        or status.get("version")
        or status.get("firmware")
        or status.get("firmware_version")
    )


def _runtime_versions_compatible(runtime: Any) -> bool:
    firmware_version = _runtime_firmware_version(runtime)
    if not firmware_version:
        return True
    return _versions_compatible(VERSION, firmware_version)


def _runtime_version_mismatch_response(view: HomeAssistantView, runtime: Any):
    return _version_mismatch_response(view, _runtime_firmware_version(runtime))


def _missing_text_response(view: HomeAssistantView):
    return view.json(
        {
            "success": False,
            "error": "missing_text",
            "message": (
                "Send recognized text using X-DJConnect-Text or upload WAV audio "
                "for Home Assistant Assist STT."
            ),
        },
        status_code=400,
    )


def _stt_error_response(
    view: HomeAssistantView,
    message: str,
    status_code: int = 500,
):
    return view.json(
        {
            "success": False,
            "error": "stt_failed",
            "message": message,
        },
        status_code=status_code,
    )


def _text_from_payload(headers: Any, data: dict[str, Any] | None) -> str:
    header_text = headers.get("X-DJConnect-Text")
    if header_text:
        return str(header_text).strip()
    if data and data.get("text"):
        return str(data["text"]).strip()
    return ""


def _is_audio_upload(content_type: str) -> bool:
    return content_type in {"audio/wav", "audio/x-wav", "application/octet-stream"}


def _audio_type_from_url(audio_url: str | None) -> str | None:
    if not audio_url:
        return None
    lowered = audio_url.lower().split("?", 1)[0]
    if lowered.endswith(".mp3"):
        return "mp3"
    if lowered.endswith(".wav"):
        return "wav"
    return None


def _store_debug_voice_wav(
    hass: Any,
    device_id: str | None,
    content_type: str,
    wav: bytes,
) -> None:
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    hass.data.setdefault(DOMAIN, {})[VOICE_DEBUG_KEY] = {
        "wav": wav,
        "device_id": device_id,
        "content_type": content_type,
        "bytes": len(wav),
    }
    _LOGGER.debug(
        "DJConnect voice debug WAV captured: url=%s device_id=%s content_type=%s bytes=%s",
        VOICE_DEBUG_URL,
        device_id,
        content_type,
        len(wav),
    )


def _is_voice_only_payload(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    voice_keys = {"recording", "state", "last_error", "error", "message", "recognized_text"}
    identity_keys = {"device_id", CONF_CLIENT_TYPE, "payload_type"}
    keys = set(data)
    return bool(keys & voice_keys) and keys <= voice_keys | identity_keys


def _is_command_payload(data: Any) -> bool:
    return isinstance(data, dict) and (
        data.get("payload_type") == "command" or bool(data.get("command"))
    )


def _set_device_state(runtime: Any, state: str) -> None:
    status = getattr(runtime, "device_status", None)
    if isinstance(status, dict):
        status["state"] = state


def _normalized_status_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten firmware status compatibility fields into HA entity keys."""
    normalized = dict(data)
    settings = data.get("settings")
    if isinstance(settings, dict):
        for key, value in settings.items():
            normalized.setdefault(key, value)
    wake_word_value = _status_value(
        settings if isinstance(settings, dict) else {},
        "wake_word_enabled",
        "wake_word",
    )
    if wake_word_value is None:
        wake_word_value = _status_value(data, "wake_word_enabled", "wake_word")
    if wake_word_value is not None:
        normalized["wake_word_enabled"] = wake_word_value
    screen = data.get("screen")
    if isinstance(screen, dict):
        if screen.get("state") is not None:
            normalized.setdefault("screen_state", screen.get("state"))
        if screen.get("brightness_level") is not None:
            normalized.setdefault("screen_brightness_level", screen.get("brightness_level"))
            normalized.setdefault("screen_brightness", screen.get("brightness_level"))
    led = data.get("led")
    if isinstance(led, dict) and led.get("state") is not None:
        normalized.setdefault("led_state", led.get("state"))
    aliases = {
        "screen_brightness_percent": "screen_brightness",
        "speaker_volume_percent": "speaker_volume",
        "screen_off_timeout_ms": "screen_timeout_ms",
    }
    for source, target in aliases.items():
        if normalized.get(source) is not None:
            normalized[target] = normalized[source]
    app_version = _status_value(
        normalized,
        "app_version",
        "version",
        "firmware",
        "firmware_version",
    )
    if app_version is not None:
        normalized["app_version"] = app_version
        normalized.setdefault("version", app_version)
        normalized.setdefault("firmware", app_version)
    normalized = enrich_payload_with_mood_zone(normalized)
    if normalized.get("mood_zone"):
        _LOGGER.debug(
            "DJConnect status mood context: mood=%s zone=%s",
            normalized.get("mood"),
            normalized.get("mood_zone"),
        )
    return normalized


def _status_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _is_ask_dj_voice_client(client_type: str | None) -> bool:
    return str(client_type or "").strip().lower() in {
        CLIENT_TYPE_IOS,
        CLIENT_TYPE_MACOS,
        CLIENT_TYPE_WATCHOS,
        CLIENT_TYPE_WINDOWS,
    }


def _voice_header_payload(headers: Any, device_id: str, client_type: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        CONF_DEVICE_ID: device_id,
        CONF_CLIENT_TYPE: client_type,
    }
    for header, key in (
        ("X-DJConnect-Profile-ID", "profile_id"),
        ("X-DJConnect-Satellite-ID", "satellite_id"),
        ("X-DJConnect-Voice-Endpoint-ID", "voice_endpoint_id"),
        ("X-DJConnect-Assist-Pipeline-ID", "assist_pipeline_id"),
        ("X-DJConnect-HA-Device-ID", "ha_device_id"),
        ("X-DJConnect-Area-ID", "area_id"),
        ("X-DJConnect-Room-ID", "room_id"),
        ("X-DJConnect-Player-ID", "player_id"),
        ("X-DJConnect-Playback-Zone-ID", "playback_zone_id"),
        ("X-DJConnect-Session-ID", "session_id"),
    ):
        value = str(headers.get(header) or "").strip()
        if value:
            payload[key] = value
    music_dna_key = str(headers.get("X-DJConnect-Music-DNA-Key") or "").strip()
    if music_dna_key:
        payload["music_dna_key"] = music_dna_key
    dj_style = str(headers.get("X-DJConnect-DJ-Style") or "").strip()
    if dj_style:
        payload["dj_style"] = dj_style
    mood = str(headers.get("X-DJConnect-Mood") or "").strip()
    if mood:
        payload["mood"] = mood
    return enrich_payload_with_mood_zone(payload)


def _ask_dj_capabilities(
    runtime: Any | None = None,
    *,
    client_type: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ask_dj_supported": True,
        "ask_dj_voice_supported": True,
        "voice_supported": True,
        "ask_dj_audio_response_supported": True,
        "push_supported": True,
    }
    if runtime is not None:
        payload["dj_announcement"] = announcement_capabilities(
            runtime,
            client_type=client_type,
        )
    return payload


async def _push_status(
    hass: Any,
    runtime: Any,
    *,
    user_id: str | None,
    device_id: str | None,
    client_type: str | None,
) -> dict[str, Any]:
    return await async_push_status(
        hass,
        runtime,
        user_id=user_id,
        device_id=device_id,
        client_type=client_type,
    )


def _request_remote_ip(request: Any) -> str | None:
    value = str(getattr(request, "remote", "") or "").strip()
    host = value.rsplit(":", 1)[0] if value.count(":") == 1 else value
    parts = host.split(".")
    if len(parts) != 4:
        return None
    try:
        if all(0 <= int(part) <= 255 and str(int(part)) == part for part in parts):
            return host
    except ValueError:
        return None
    return None


def _merge_status_update(status: dict[str, Any], update: dict[str, Any]) -> bool:
    """Merge ESP status without letting sparse heartbeats erase known values."""
    if not update:
        _LOGGER.debug("Ignoring empty ESP status payload for device sensor update")
        return False
    _LOGGER.debug("Merging ESP status payload without resetting missing fields")
    changed = False
    for key, value in update.items():
        if key == "ha_pairing_status" and value in (None, "", "unknown"):
            continue
        if _is_empty_status_value(value) and key in status:
            continue
        if status.get(key) != value:
            changed = True
        status[key] = value
    return changed


def _is_empty_status_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _request_user_id(request: Any) -> str | None:
    context = getattr(request, "context", None)
    user_id = getattr(context, "user_id", None)
    if user_id:
        return str(user_id)
    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None)
    return str(user_id) if user_id else None


def _history_manager(hass: Any, runtime: Any | None = None) -> AskDJHistoryManager:
    manager = getattr(runtime, "ask_dj_history", None) if runtime is not None else None
    if manager is not None:
        return manager
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("ask_dj_history_manager")
    if manager is None:
        manager = AskDJHistoryManager(hass)
        domain_data["ask_dj_history_manager"] = manager
    if runtime is not None:
        runtime.ask_dj_history = manager
    return manager


def _query_int(request: Any, key: str) -> int | None:
    query = getattr(request, "query", None) or {}
    try:
        value = query.get(key)
    except AttributeError:
        return None
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _update_memory_metadata(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    user_id: str | None = None,
) -> str | None:
    memory = getattr(runtime, "memory", None)
    updater = getattr(memory, "async_update_client_metadata", None)
    if not callable(updater):
        return None
    return await updater(runtime, payload or {}, user_id=user_id)


async def _run_text_command_with_memory(
    hass: Any,
    runtime: Any,
    user_text: str,
    *,
    play: bool,
    correct_stt: bool,
    memory_payload: dict[str, Any] | None,
    user_id: str | None,
) -> dict[str, Any]:
    try:
        return await run_text_command(
            hass,
            runtime,
            user_text,
            play=play,
            correct_stt=correct_stt,
            memory_payload=memory_payload,
            user_id=user_id,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return await run_text_command(
            hass,
            runtime,
            user_text,
            play=play,
            correct_stt=correct_stt,
        )


def _current_spotify_credentials(runtime: Any) -> dict[str, Any]:
    getter = getattr(runtime, "get_current_spotify_credentials", None)
    if callable(getter):
        current = getter()
        if current:
            return current
    payload = getattr(runtime, "spotify_payload", None)
    current = payload() if callable(payload) else {}
    return current or {}


def _entry_spotify_credentials(entry: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    values.update(getattr(entry, "data", {}) or {})
    values.update(getattr(entry, "options", {}) or {})
    client_id = str(values.get(CONF_SPOTIFY_CLIENT_ID) or "").strip()
    refresh_token = str(values.get(CONF_SPOTIFY_REFRESH_TOKEN) or "").strip()
    if not client_id or not refresh_token:
        return {}
    scopes = values.get(CONF_SPOTIFY_SCOPES, DEFAULT_SPOTIFY_SCOPES)
    if isinstance(scopes, str):
        scopes = scopes.split()
    return {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "spotify_client_id": client_id,
        "spotify_refresh_token": refresh_token,
        "spotify_market": values.get(CONF_SPOTIFY_MARKET, DEFAULT_SPOTIFY_MARKET),
        "spotify_scopes": scopes,
    }


def _current_spotify_credentials_for_status(hass: Any, runtime: Any) -> dict[str, Any]:
    current = _current_spotify_credentials(runtime)
    if current:
        return current
    entry = getattr(runtime, "entry", None)
    current = _entry_spotify_credentials(entry)
    if current:
        return current
    entries_getter = getattr(getattr(hass, "config_entries", None), "async_entries", None)
    if not callable(entries_getter):
        return {}
    try:
        entries = list(entries_getter(DOMAIN))
    except TypeError:
        entries = [
            candidate
            for candidate in entries_getter()
            if getattr(candidate, "domain", DOMAIN) == DOMAIN
        ]
    for candidate in entries:
        current = _entry_spotify_credentials(candidate)
        if current:
            return current
    return {}


def _safe_config_keys(values: dict[str, Any] | None) -> list[str]:
    return sorted(str(key) for key in (values or {}).keys())


def _store_rotated_spotify_refresh_token(
    hass: Any,
    entry: Any,
    runtime: Any,
    refresh_token: str | None,
) -> bool:
    token = str(refresh_token or "").strip()
    if not token or entry is None:
        return False
    changed = False
    updater = getattr(runtime, "update_spotify_refresh_token", None)
    if callable(updater):
        changed = bool(updater(token))
    current = str((getattr(entry, "data", {}) or {}).get(CONF_SPOTIFY_REFRESH_TOKEN) or "")
    if token != current:
        new_data = dict(entry.data)
        new_data[CONF_SPOTIFY_REFRESH_TOKEN] = token
        hass.config_entries.async_update_entry(entry, data=new_data)
        changed = True
    if changed:
        _LOGGER.debug("DJConnect Spotify refresh_token=rotated")
    return changed


def _delete_spotify_reauth_issues(hass: Any, entry_id: str) -> None:
    try:
        from homeassistant.helpers import issue_registry as ir

        for suffix in (
            "missing_spotify_refresh_token",
            "missing_spotify_oauth_scopes",
            "spotify_refresh_token_revoked",
        ):
            ir.async_delete_issue(hass, DOMAIN, suffix)
            ir.async_delete_issue(hass, DOMAIN, f"{entry_id}_{suffix}")
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not delete Spotify reauth repair issues", exc_info=True)


def _persist_paired_device(
    hass: Any,
    runtime: Any,
    device_id: str,
    local_url: str | None,
    device_token: str,
    client_type: str | None = None,
) -> None:
    """Persist ESP pairing details so HA restarts keep the real device identity."""
    entry = getattr(runtime, "entry", None)
    config_entries = getattr(hass, "config_entries", None)
    updater = getattr(config_entries, "async_update_entry", None)
    if entry is None or not callable(updater):
        return
    new_data = dict(getattr(entry, "data", {}) or {})
    new_data[CONF_DEVICE_ID] = device_id
    new_data[CONF_DEVICE_TOKEN] = device_token
    new_data[CONF_CLIENT_TYPE] = str(client_type or _runtime_client_type(runtime))
    new_data[CONF_LAST_DEVICE_STATUS] = _persistable_device_status(
        getattr(runtime, "device_status", {}) or {}
    )
    cleaned_url = str(local_url or "").strip()
    if cleaned_url:
        new_data[CONF_LOCAL_URL] = cleaned_url
    updater(entry, data=new_data)


def _persist_runtime_device_status(hass: Any, runtime: Any) -> None:
    """Persist the latest cached device status without rotating pairing data."""
    entry = getattr(runtime, "entry", None)
    config_entries = getattr(hass, "config_entries", None)
    updater = getattr(config_entries, "async_update_entry", None)
    if entry is None or not callable(updater):
        return
    new_data = dict(getattr(entry, "data", {}) or {})
    new_data[CONF_LAST_DEVICE_STATUS] = _persistable_device_status(
        getattr(runtime, "device_status", {}) or {}
    )
    updater(entry, data=new_data)


def _persistable_device_status(status: dict[str, Any]) -> dict[str, Any]:
    """Return a compact status cache that is safe to store in the config entry."""
    if not isinstance(status, dict):
        return {}
    result: dict[str, Any] = {}
    for key, value in status.items():
        normalized = str(key).lower()
        if any(secret in normalized for secret in ("token", "password", "secret", "proof")):
            continue
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            result[key] = value
        elif isinstance(value, list):
            result[key] = value[:10]
        elif isinstance(value, dict):
            result[key] = _persistable_nested_status(value)
    return result


def _persistable_nested_status(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        normalized = str(key).lower()
        if any(secret in normalized for secret in ("token", "password", "secret", "proof")):
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            result[key] = item
        elif isinstance(item, list):
            result[key] = item[:10]
        elif isinstance(item, dict):
            result[key] = _persistable_nested_status(item)
    return result


def _device_language(runtime: Any) -> str:
    language_getter = getattr(runtime, "device_language", None)
    if callable(language_getter):
        language = str(language_getter() or "").lower()
    else:
        language = ""
    return "nl" if language.startswith("nl") else "en"


def _esp32_language_payload(runtime: Any) -> dict[str, str]:
    """Return HA-provisioned language metadata for ESP32 clients only."""
    if _runtime_client_type(runtime) != CLIENT_TYPE_ESP32:
        return {}
    language = _device_language(runtime)
    return {"device_language": language, "language": language}


def _failure_kind(exc: Exception) -> str:
    text = str(exc).lower()
    if "kan geen apparaat vinden" in text or "cannot find a device" in text:
        return "assist"
    if "niet vinden" in text and any(
        fragment in text
        for fragment in ("noem de artiest", "media type", "antwoord alleen")
    ):
        return "assist"
    if any(word in text for word in ("assist", "conversation", "pipeline")):
        return "assist"
    if any(
        word in text
        for word in ("spotify", "playback", "media_player", "play_media", "player")
    ):
        return "spotify"
    if "apparaat" in text:
        return "spotify"
    return "generic"


def _command_failed_text(runtime: Any, exc: Exception | None = None) -> str:
    kind = _failure_kind(exc) if exc else "generic"
    return DJ_FAILURE_TEXTS[kind][_device_language(runtime)]


def _test_dj_text(runtime: Any) -> str:
    return DJ_TEST_TEXTS[_device_language(runtime)]


def _backend_unavailable_payload(
    command: str,
    runtime: Any,
    exc: Exception,
) -> dict[str, Any]:
    """Return a non-empty JSON body for backend command failures."""
    metadata = music_backend_metadata(None, runtime)
    if str(command or "").strip().lower() == "playlists":
        payload = {
            "success": False,
            "error": "playback_backend_unavailable",
            "message": _safe_backend_error_message(exc) or "Playback backend unavailable",
            "backend_available": False,
            "playlists": [],
            "items": [],
            "data": {"playlists": [], "items": []},
            "result": {"playlists": [], "items": []},
            "count": 0,
        }
        payload.update(metadata)
        return payload
    payload = {
        "success": False,
        "error": "backend_unavailable",
        "message": _safe_backend_error_message(exc) or ERROR_MESSAGES["backend_unavailable"],
        "backend_available": False,
        "playback": getattr(runtime, "last_playback", None) or {},
    }
    payload.update(metadata)
    return payload


def _unsupported_backend_capability_payload(
    hass: Any,
    runtime: Any,
    exc: Exception,
) -> dict[str, Any]:
    """Return the stable client contract for unsupported backend capabilities."""
    payload = {
        "success": False,
        "error": "unsupported_backend_capability",
        "capability": getattr(exc, "capability", "unknown"),
        "backend": getattr(exc, "backend", None)
        or music_backend_metadata(hass, runtime).get("music_backend"),
        "message": str(exc) or "The selected music backend does not support this action.",
        "backend_available": True,
    }
    payload.update(music_backend_metadata(hass, runtime))
    return payload


def _looks_like_backend_capability_error(exc: Exception) -> bool:
    """Return true for capability errors even after test/module reload boundaries."""
    return isinstance(exc, MusicBackendCapabilityError) or (
        hasattr(exc, "capability") and hasattr(exc, "backend")
    )


def _status_playback_unavailable_payload() -> dict[str, Any]:
    """Return a privacy-safe app status fallback when backend playback is unavailable."""
    return {
        "backend_available": False,
        "playback": {"has_playback": False},
        "playback_error": "playback_backend_unavailable",
    }


def _client_status_uses_backend_playback(client_type: str | None) -> bool:
    """Return true for app clients that expect a live playback snapshot in status."""
    return str(client_type or "").strip().lower() in {
        CLIENT_TYPE_IOS,
        CLIENT_TYPE_MACOS,
        CLIENT_TYPE_WATCHOS,
    }


async def _status_playback_payload(hass: Any, runtime: Any) -> dict[str, Any]:
    """Fetch the canonical command=status playback shape for app status responses."""
    try:
        result = await run_music_command(hass, runtime, "status")
    except MusicBackendCapabilityError as exc:
        _LOGGER.debug(
            "DJConnect status playback unsupported by selected backend: %s",
            getattr(exc, "capability", "unknown"),
        )
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = True
        return {
            "backend_available": True,
            "playback": {"has_playback": False},
            "playback_error": "unsupported_backend_capability",
        }
    except SpotifyBackendError as exc:
        _LOGGER.debug(
            "DJConnect status playback backend unavailable: %s",
            exc.__class__.__name__,
        )
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = False
        return _status_playback_unavailable_payload()
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("DJConnect status playback refresh failed: %s", exc.__class__.__name__)
        runtime.update(last_error=_safe_backend_error_message(exc))
        runtime.device_status["backend_available"] = False
        return _status_playback_unavailable_payload()

    playback = result.get("playback")
    if not isinstance(playback, dict) or "has_playback" not in playback:
        playback = {"has_playback": False}
    runtime.last_playback = playback
    runtime.device_status["backend_available"] = True
    runtime.update(last_error=None)
    return {
        "backend_available": True,
        "playback": playback,
    }


def _playlist_command_value(data: dict[str, Any], client_type: str) -> dict[str, Any]:
    """Build canonical playlist command options for all client payload shapes."""
    request_limit = data.get("limit")
    value = data.get("value")
    if isinstance(value, dict):
        merged = dict(value)
        merged.setdefault("client_type", client_type)
        if request_limit is not None and merged.get("limit") in (None, ""):
            merged["limit"] = request_limit
        return merged
    if value not in (None, ""):
        return {"client_type": client_type, "limit": value}
    return {"client_type": client_type, "limit": request_limit}


def _repeat_command_value(data: dict[str, Any]) -> str:
    """Accept repeat button payloads from older and newer app clients."""
    value = data.get("value")
    if isinstance(value, dict):
        for key in ("value", "repeat", "repeat_state", "repeatState", "mode", "option"):
            candidate = str(value.get(key) or "").strip().lower()
            if candidate in {"off", "track", "context"}:
                return candidate
    for key in ("value", "repeat", "repeat_state", "repeatState", "mode", "option"):
        candidate = str(data.get(key) or "").strip().lower()
        if candidate in {"off", "track", "context"}:
            return candidate
    label = str(data.get("label") or data.get("button_label") or data.get("title") or "").strip().lower()
    if "uit" in label or label == "off":
        return "off"
    if "nummer" in label or "track" in label:
        return "track"
    if "alles" in label or "context" in label or "aan" in label:
        return "context"
    return str(value or "").strip().lower()


def _shuffle_command_value(data: dict[str, Any]) -> Any:
    """Accept shuffle button payloads with nested action values."""
    value = data.get("value")
    if isinstance(value, dict):
        for key in ("value", "enabled", "shuffle", "shuffle_state", "shuffleState"):
            if key in value:
                return value.get(key)
    for key in ("value", "enabled", "shuffle", "shuffle_state", "shuffleState"):
        if key in data:
            return data.get(key)
    return value


def _volume_delta_command_value(data: dict[str, Any]) -> Any:
    """Accept volume control payloads with either value or delta keys."""
    value = data.get("value")
    if isinstance(value, dict):
        for key in ("value", "delta", "volume_delta", "volumeDelta"):
            if key in value:
                return value.get(key)
    for key in ("value", "delta", "volume_delta", "volumeDelta"):
        if key in data:
            return data.get(key)
    return value


async def _handle_volume_delta_command(hass: Any, runtime: Any, value: Any) -> dict[str, Any]:
    try:
        delta = int(value)
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "invalid_volume_delta",
            "message": "volume_delta value must be a number",
            "images": [],
            "links": [],
            "sources": [],
        }
    status = await run_music_command(hass, runtime, "status")
    playback = status.get("playback") if isinstance(status, dict) else {}
    current = _playback_volume_percent(playback, runtime)
    if current is None:
        return {
            "success": False,
            "error": "playback_unavailable",
            "message": "current volume is unavailable",
            "images": [],
            "links": [],
            "sources": [],
        }
    target = max(0, min(60, current + delta))
    result = await run_music_command(hass, runtime, "set_volume", target)
    return {
        "success": True,
        "text": "Ik heb het volume aangepast.",
        "dj_text": "Ik heb het volume aangepast.",
        "playback": result.get("playback") if isinstance(result, dict) else {},
        "images": [],
        "links": [],
        "sources": [],
        "items": [],
    }


def _playback_volume_percent(playback: Any, runtime: Any) -> int | None:
    candidates: list[Any] = []
    if isinstance(playback, dict):
        candidates.extend(
            playback.get(key)
            for key in (
                "volume",
                "volume_percent",
                "volumePercent",
                "device_volume",
                "deviceVolume",
            )
        )
        device = playback.get("device")
        if isinstance(device, dict):
            candidates.extend(
                device.get(key)
                for key in ("volume", "volume_percent", "volumePercent")
            )
    device_status = getattr(runtime, "device_status", {}) or {}
    if isinstance(device_status, dict):
        candidates.extend(
            device_status.get(key)
            for key in ("volume", "volume_percent", "spotify_volume", "speaker_volume_percent")
        )
    for value in candidates:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= number <= 100:
            return min(60, number)
    return None


async def _handle_ask_dj_play_recommendation(
    hass: Any,
    runtime: Any,
    value: Any,
    request_payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "success": False,
            "error": "missing_recommendation_uri",
            "message": "Aanbeveling ontbreekt.",
        }
    recommendation = _normalize_recommendation_value(value)
    stale = _stale_backend_action_error(runtime, recommendation)
    if stale:
        stale.update(music_backend_metadata(hass, runtime))
        return stale
    backend_meta = music_backend_metadata(hass, runtime)
    selected_backend = str(backend_meta.get("music_backend") or "").strip()
    uri = str(recommendation.get("uri") or "").strip()
    context_uri = str(recommendation.get("context_uri") or "").strip()
    offset_uri = str(recommendation.get("offset_uri") or "").strip()
    kind = str(recommendation.get("kind") or _spotify_recommendation_kind(uri or context_uri)).strip()
    uris = _recommendation_track_uris(recommendation.get("uris"))
    if selected_backend == "music_assistant":
        media_value = _music_assistant_recommendation_value(recommendation)
        if not media_value:
            return {
                "success": False,
                "error": "stale_backend_action",
                "message": "This action was created for a previous music backend. Ask DJ again for a fresh recommendation.",
                **backend_meta,
            }
        try:
            result = await run_music_command(hass, runtime, "play", media_value, play=True)
        except MusicBackendCapabilityError as exc:
            return _unsupported_backend_capability_payload(hass, runtime, exc)
        except SpotifyBackendError as exc:
            return {
                "success": False,
                "error": "backend_playback_failed",
                "message": _safe_backend_error_message(exc),
                **backend_meta,
            }
        return await _recommendation_play_success_response(
            hass,
            runtime,
            recommendation,
            request_payload,
            result,
            user_id=user_id,
        )
    if not (uri or context_uri):
        return {
            "success": False,
            "error": "missing_recommendation_uri",
            "message": "Ik weet niet welke aanbeveling ik moet afspelen.",
        }
    if kind not in {"track", "album", "artist", "playlist", "track_mix"}:
        return {
            "success": False,
            "error": "unsupported_recommendation_kind",
            "message": "Ik kan dit type aanbeveling nog niet afspelen.",
        }
    if uri and _spotify_recommendation_kind(uri) not in {"track", "album", "artist", "playlist"}:
        return {
            "success": False,
            "error": "unsupported_recommendation_kind",
            "message": "Ik kan alleen Spotify track, album, artist of playlist URIs afspelen.",
        }
    if context_uri and _spotify_recommendation_kind(context_uri) not in {"album", "artist", "playlist"}:
        return {
            "success": False,
            "error": "unsupported_recommendation_kind",
            "message": "Ik kan deze Spotify context niet afspelen.",
        }
    if offset_uri and _spotify_recommendation_kind(offset_uri) != "track":
        return {
            "success": False,
            "error": "unsupported_recommendation_kind",
            "message": "De offset van een aanbeveling moet een Spotify track zijn.",
        }
    try:
        if kind == "track_mix":
            result = await run_music_command(hass, runtime, "play_uris", uris, play=True)
        elif kind == "track" and context_uri and offset_uri:
            result = await run_music_command(
                hass,
                runtime,
                "play_context_at",
                {"context_uri": context_uri, "offset_uri": offset_uri},
                play=True,
            )
        elif kind == "track":
            result = await run_music_command(hass, runtime, "play", uri, play=True)
        else:
            target = context_uri or uri
            result = await run_music_command(hass, runtime, "play", target, play=True)
    except MusicBackendCapabilityError as exc:
        return _unsupported_backend_capability_payload(hass, runtime, exc)
    except SpotifyBackendError as exc:
        message = str(exc)
        safe_message = _safe_backend_error_message(exc)
        if _looks_like_no_active_output(message):
            return await _speaker_selection_for_recommendation(
                hass,
                runtime,
                recommendation,
                request_payload,
            )
        if "reauthorize" in message.lower() or "authorization" in message.lower():
            return {
                "success": False,
                "error": "spotify_auth_required",
                "message": safe_message,
            }
        return {
            "success": False,
            "error": "spotify_playback_failed",
            "message": safe_message,
        }
    return await _recommendation_play_success_response(
        hass,
        runtime,
        recommendation,
        request_payload,
        result,
        user_id=user_id,
    )


async def _recommendation_play_success_response(
    hass: Any,
    runtime: Any,
    recommendation: dict[str, Any],
    request_payload: dict[str, Any],
    result: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    kind = str(recommendation.get("kind") or "").strip()
    memory = getattr(runtime, "memory", None)
    if memory is not None:
        recorder = getattr(memory, "async_record_recommendation_play", None)
        if callable(recorder):
            try:
                memory_payload = dict(request_payload)
                if recommendation.get("music_dna_key") and not memory_payload.get("music_dna_key"):
                    memory_payload["music_dna_key"] = recommendation["music_dna_key"]
                await recorder(runtime, recommendation, memory_payload, user_id=user_id)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("DJConnect recommendation play memory update failed: %s", exc)
    playback = result.get("playback") if isinstance(result, dict) else {}
    media = _play_now_dj_response_media(recommendation, playback, request_payload)
    fallback_dj_text = _play_now_fallback_dj_text(
        media,
        recommendation,
        _play_now_response_conf(runtime, request_payload, recommendation),
        save_mix_prompt=kind == "track_mix",
    )
    dj_response_debug: dict[str, Any] = {}
    dj_text = await generate_dj_response_with_assist(
        hass,
        media=media,
        fallback_text=fallback_dj_text,
        conf=getattr(runtime, "config", {}) or {},
        debug=dj_response_debug,
    )
    generated_text = dj_response_debug.get("fallback_used") is False
    text_source = "generated" if generated_text else "fallback"
    audio_url = await async_create_dj_audio_url(hass, runtime, dj_text)
    dj_response = {
        "success": True,
        "delivered": False,
        "displayed": False,
        "spoken": False,
        "audio_url": bool(audio_url),
        "audio_url_value": audio_url,
        "audio_type": _audio_type_from_url(audio_url),
    }
    runtime.update(
        last_error=None,
        last_dj_text=dj_text,
        last_dj_response_debug=dj_response_debug,
        last_playback=playback or getattr(runtime, "last_playback", None),
    )
    return {
        "success": True,
        "message": dj_text,
        "text": dj_text,
        "dj_text": dj_text,
        "text_source": text_source,
        "is_generated_text": generated_text,
        "action": "spotify_start_recommendation",
        "playback": playback or {},
        "dj_response": dj_response,
        "audio_url": audio_url,
        "audio_type": _audio_type_from_url(audio_url),
        "assistant_message": {
            "role": "assistant",
            "message_kind": "assistant",
            "origin": "play_now",
            "text": dj_text,
            "text_source": text_source,
            "is_generated_text": generated_text,
            "audio_url": audio_url,
            "playback_actions": [],
            "items": [],
            "images": [],
            "links": [],
            "sources": [],
        },
        "recommendation": {
            key: recommendation.get(key)
            for key in ("uri", "uris", "context_uri", "offset_uri", "kind", "title", "subtitle", "reason")
            if recommendation.get(key)
        },
        **music_backend_metadata(hass, runtime),
    }


def _play_now_dj_response_media(
    recommendation: dict[str, Any],
    playback: Any,
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    media: dict[str, Any] = {}
    if isinstance(playback, dict):
        media.update(
            {
                key: value
                for key in (
                    "type",
                    "media_content_type",
                    "track_name",
                    "title",
                    "artist",
                    "artist_name",
                    "album_name",
                    "album",
                    "playlist",
                    "name",
                )
                if (value := playback.get(key)) not in (None, "", [], {})
            }
        )
    kind = str(recommendation.get("kind") or _spotify_recommendation_kind(recommendation.get("uri") or recommendation.get("context_uri")) or "").strip()
    title = str(recommendation.get("title") or "").strip()
    subtitle = str(recommendation.get("subtitle") or "").strip()
    if kind and not media.get("type"):
        media["type"] = kind
    if title:
        if kind == "album":
            media.setdefault("album_name", title)
            media.setdefault("album", title)
        elif kind == "playlist":
            media.setdefault("playlist", title)
            media.setdefault("name", title)
        else:
            media.setdefault("track_name", title)
            media.setdefault("title", title)
    if subtitle:
        media.setdefault("artist", subtitle)
        media.setdefault("artist_name", subtitle)
    for key in ("language", "locale", "device_language", "mood", "energy"):
        value = request_payload.get(key) or recommendation.get(key)
        if value:
            media[key] = value
    return enrich_payload_with_mood_zone(media)


def _play_now_response_conf(
    runtime: Any,
    request_payload: dict[str, Any],
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    conf = dict(getattr(runtime, "config", {}) or {})
    voice_profile = (
        request_payload.get(CONF_VOICE_PROFILE)
        or request_payload.get("voice_profile")
        or request_payload.get("dj_style")
        or recommendation.get(CONF_VOICE_PROFILE)
        or recommendation.get("voice_profile")
        or recommendation.get("dj_style")
    )
    if voice_profile:
        conf[CONF_VOICE_PROFILE] = normalize_voice_profile(voice_profile)
    mood_payload = enrich_payload_with_mood_zone({**recommendation, **request_payload})
    conf[CONF_VOICE_PROFILE] = voice_profile_for_mood_or_config(conf, mood_payload)
    for key in (CONF_TTS_LANGUAGE, "language", "locale", "device_language"):
        value = request_payload.get(key) or recommendation.get(key)
        if value:
            conf[key] = value
    return conf


def _play_now_fallback_dj_text(
    media: dict[str, Any],
    recommendation: dict[str, Any],
    conf: dict[str, Any],
    *,
    save_mix_prompt: bool = False,
) -> str:
    title = str(media.get("track_name") or media.get("title") or recommendation.get("title") or "").strip()
    artist = str(media.get("artist") or media.get("artist_name") or recommendation.get("subtitle") or "").strip()
    album = str(media.get("album_name") or media.get("album") or "").strip()
    playlist = str(media.get("playlist") or "").strip()
    subject = title or playlist or str(recommendation.get("uri") or recommendation.get("context_uri") or "je keuze").strip()
    if artist and subject:
        now_playing = f"{subject} van {artist}"
    else:
        now_playing = subject
    if album and title and album != title:
        now_playing = f"{now_playing}, van {album}"
    profile = voice_profile_for_mood_or_config(conf, media)
    if profile == VOICE_PROFILE_LATE_NIGHT:
        text = f"Mooi, ik zet {now_playing} zacht in de spotlights. Leun maar even achterover."
    elif profile == VOICE_PROFILE_ENERGY:
        text = f"Daar gaan we: {now_playing}. Volume in je hoofd omhoog, dit is de volgende!"
    elif profile == VOICE_PROFILE_CLEAN_HOST:
        text = f"Gestart: {now_playing}. Ik houd de muziek voor je in beweging."
    else:
        text = f"Daar is {now_playing}. Een fijne keuze voor de volgende ronde."
    language = media.get("language") or media.get("locale") or conf.get(CONF_TTS_LANGUAGE) or "nl"
    text = f"{text}{mood_play_now_suffix(media, language)}"
    if save_mix_prompt:
        return f"{text} Wil je dat ik deze mix opsla als Spotify playlist?"
    return text


async def _handle_ask_dj_play_recommendation_on_output(
    hass: Any,
    runtime: Any,
    value: Any,
    request_payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "success": False,
            "error": "missing_output_selection",
            "message": "Ik mis de speakerkeuze.",
        }
    output_id = str(value.get("output_id") or value.get("device_id") or value.get("value") or "").strip()
    recommendation = value.get("recommendation") if isinstance(value.get("recommendation"), dict) else {}
    if not output_id:
        return {
            "success": False,
            "error": "missing_output_selection",
            "message": "Ik weet nog niet op welke speaker ik dit moet afspelen.",
        }
    if not recommendation:
        return {
            "success": False,
            "error": "missing_recommendation_uri",
            "message": "Ik weet niet welke aanbeveling ik moet afspelen.",
        }
    try:
        await run_music_command(hass, runtime, "set_output", output_id, play=False)
    except SpotifyBackendError as exc:
        return {
            "success": False,
            "error": "output_selection_failed",
            "message": _safe_backend_error_message(exc),
        }
    return await _handle_ask_dj_play_recommendation(
        hass,
        runtime,
        recommendation,
        request_payload,
        user_id=user_id,
    )


async def _handle_ask_dj_play_request_on_output(
    hass: Any,
    runtime: Any,
    value: Any,
    request_payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "success": False,
            "error": "missing_output_selection",
            "message": "Ik mis de speakerkeuze.",
        }
    output_id = str(value.get("output_id") or value.get("device_id") or value.get("value") or "").strip()
    ask_request = value.get("request") if isinstance(value.get("request"), dict) else {}
    text = str(ask_request.get("text") or request_payload.get("text") or "").strip()
    if not output_id:
        return {
            "success": False,
            "error": "missing_output_selection",
            "message": "Ik weet nog niet op welke speaker ik dit moet afspelen.",
        }
    if not text:
        return {
            "success": False,
            "error": "missing_playback_request",
            "message": "Ik weet niet welk muziekverzoek ik moet starten.",
        }
    try:
        await run_music_command(hass, runtime, "set_output", output_id, play=False)
    except SpotifyBackendError as exc:
        return {
            "success": False,
            "error": "output_selection_failed",
            "message": _safe_backend_error_message(exc),
        }
    ask_payload = {
        key: value
        for key, value in {
            **request_payload,
            **ask_request,
            "text": text,
            "audio_response": ask_request.get("audio_response") or request_payload.get("audio_response") or "auto",
        }.items()
        if value not in ("", None)
    }
    return await async_handle_ask_dj(hass, runtime, ask_payload, user_id=user_id)


async def _speaker_selection_for_recommendation(
    hass: Any,
    runtime: Any,
    recommendation: dict[str, Any],
    request_payload: dict[str, Any],
) -> dict[str, Any]:
    devices = await _available_output_devices(hass, runtime)
    actions = _output_actions_for_recommendation(devices, recommendation)
    if actions:
        title = str(recommendation.get("title") or "deze muziek").strip()
        message = (
            f"Ik weet nog niet op welke speaker ik {title} moet afspelen. "
            "Kies een speaker, dan start ik hem meteen."
        )
        return {
            "success": True,
            "message": message,
            "text": message,
            "dj_text": message,
            "action": "select_output",
            "intent": {"category": "playback", "intent": "select_output_for_recommendation"},
            "playback_actions": actions,
            "recommendation": {
                key: recommendation.get(key)
                for key in ("uri", "uris", "context_uri", "offset_uri", "kind", "title", "subtitle", "reason")
                if recommendation.get(key)
            },
        }
    return {
        "success": False,
        "error": "no_active_output",
        "message": "Ik weet nog niet op welke speaker ik dit moet afspelen en ik vind nu geen beschikbare speakers.",
    }


async def _available_output_devices(hass: Any, runtime: Any) -> list[dict[str, Any]]:
    try:
        result = await run_music_command(hass, runtime, "devices")
        devices = result.get("devices") if isinstance(result, dict) else []
        if isinstance(devices, list) and devices:
            return [device for device in devices if isinstance(device, dict)]
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect output lookup after no-active-output failed: %s", exc)
    status = getattr(runtime, "device_status", {}) or {}
    devices = status.get("available_outputs")
    return [device for device in devices if isinstance(device, dict)] if isinstance(devices, list) else []


def _output_actions_for_recommendation(
    devices: list[dict[str, Any]],
    recommendation: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for device in devices:
        device_id = str(device.get("id") or "").strip()
        name = str(device.get("name") or "").strip()
        if not device_id or not name or device_id in seen:
            continue
        seen.add(device_id)
        device_type = str(device.get("type") or "Spotify Connect").strip()
        actions.append(
            {
                key: value
                for key, value in {
                    "id": f"play_on_output:{device_id}",
                    "title": name,
                    "subtitle": device_type,
                    "label": "Speel hier",
                    "button_label": "Speel hier",
                    "kind": "output",
                    "command": "ask_dj_play_recommendation_on_output",
                    "value": {
                        "output_id": device_id,
                        "device_id": device_id,
                        "device_name": name,
                        "recommendation": recommendation,
                    },
                    "device_id": device_id,
                    "device_name": name,
                    "reason": "Kies deze Spotify Connect speaker en start daarna de aanbeveling.",
                }.items()
                if value not in ("", None)
            }
        )
        if len(actions) >= 8:
            break
    return actions


async def _handle_ask_dj_followup_response(
    hass: Any,
    runtime: Any,
    value: Any,
    request_payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "success": False,
            "error": "missing_followup_response",
            "message": "Ik mis je antwoord op de vervolgvraag.",
        }
    response_value = str(value.get("response_value") or value.get("value") or "").strip().lower()
    if response_value not in {"yes", "ja", "no", "nee"}:
        return {
            "success": False,
            "error": "invalid_followup_response",
            "message": "Antwoord met ja of nee.",
        }
    memory = getattr(runtime, "memory", None)
    pending_getter = getattr(memory, "async_pending_followup", None)
    pending_consumer = getattr(memory, "async_consume_pending_followup", None)
    pending = await pending_getter(runtime, request_payload, user_id=user_id) if callable(pending_getter) else {}
    if pending.get("expired"):
        result = {
            "success": True,
            "text": "Die vraag is verlopen. Vraag het nog even opnieuw, dan pak ik de actuele context erbij.",
            "dj_text": "Die vraag is verlopen. Vraag het nog even opnieuw, dan pak ik de actuele context erbij.",
            "action": "none",
            "intent": {"category": "playback_confirmation", "intent": "followup_expired"},
        }
        await _append_followup_history(hass, runtime, request_payload, result, user_id=user_id)
        return result
    if not pending:
        result = {
            "success": True,
            "text": "Ik heb geen openstaande vervolgvraag meer.",
            "dj_text": "Ik heb geen openstaande vervolgvraag meer.",
            "action": "none",
            "intent": {"category": "playback_confirmation", "intent": "no_pending_followup"},
        }
        await _append_followup_history(hass, runtime, request_payload, result, user_id=user_id)
        return result
    if callable(pending_consumer):
        pending = await pending_consumer(runtime, request_payload, user_id=user_id) or pending
    if response_value in {"no", "nee"}:
        result = {
            "success": True,
            "text": "Helemaal goed, ik laat de muziek zoals hij is.",
            "dj_text": "Helemaal goed, ik laat de muziek zoals hij is.",
            "action": "none",
            "intent": {"category": "playback_confirmation", "intent": "followup_declined"},
        }
        await _append_followup_history(hass, runtime, request_payload, result, user_id=user_id)
        return result
    proposed_action = str(pending.get("proposed_action") or "").strip()
    proposed_payload = pending.get("proposed_payload") if isinstance(pending.get("proposed_payload"), dict) else {}
    if proposed_action == "ask_dj_personal_recommendations":
        followup_payload = {**request_payload}
        followup_payload["text"] = str(
            proposed_payload.get("text")
            or "verras me met persoonlijke muzieksuggesties"
        )
        result = await async_handle_ask_dj(
            hass,
            runtime,
            followup_payload,
            user_id=user_id,
        )
        await _append_followup_history(hass, runtime, request_payload, result, user_id=user_id)
        return result
    if proposed_action != "ask_dj_play_recommendation" or not proposed_payload:
        result = {
            "success": False,
            "error": "unsupported_followup_action",
            "message": "Ik kan deze vervolgvraag niet meer uitvoeren.",
        }
        await _append_followup_history(hass, runtime, request_payload, result, user_id=user_id)
        return result
    result = await _handle_ask_dj_play_recommendation(
        hass,
        runtime,
        proposed_payload,
        request_payload,
        user_id=user_id,
    )
    if result.get("success"):
        title = str(proposed_payload.get("title") or "hem").strip()
        result["text"] = result["dj_text"] = result["message"] = f"Top, ik zet {title} nu voor je aan."
        result["intent"] = {"category": "playback_confirmation", "intent": "followup_accepted"}
    await _append_followup_history(hass, runtime, request_payload, result, user_id=user_id)
    return result


async def _append_followup_history(
    hass: Any,
    runtime: Any,
    request_payload: dict[str, Any],
    result: dict[str, Any],
    *,
    user_id: str | None = None,
) -> None:
    try:
        await _history_manager(hass, runtime).async_append_assistant_message(
            user_id,
            request_payload,
            result,
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Ask DJ follow-up history append failed: %s", exc)


def _normalize_recommendation_value(value: dict[str, Any]) -> dict[str, Any]:
    nested = value.get("value") if isinstance(value.get("value"), dict) else {}
    uri = str(value.get("uri") or "").strip()
    context_uri = str(value.get("context_uri") or "").strip()
    offset_uri = str(value.get("offset_uri") or "").strip()
    kind = str(value.get("kind") or _spotify_recommendation_kind(uri or context_uri)).strip().lower()
    if kind == "track" and not offset_uri and uri.startswith("spotify:track:"):
        offset_uri = uri if context_uri else ""
    return {
        "title": str(value.get("title") or "").strip(),
        "subtitle": str(value.get("subtitle") or "").strip(),
        "uri": uri,
        "context_uri": context_uri,
        "offset_uri": offset_uri,
        "uris": _recommendation_track_uris(value.get("uris")),
        "kind": kind,
        "music_dna_key": str(value.get("music_dna_key") or "").strip(),
        "reason": str(value.get("reason") or "").strip(),
        "backend": str(value.get("backend") or nested.get("backend") or "").strip(),
        "provider": str(value.get("provider") or nested.get("provider") or "").strip(),
        "music_backend_revision": value.get("music_backend_revision")
        if value.get("music_backend_revision") is not None
        else nested.get("music_backend_revision"),
        "item_id": str(value.get("item_id") or nested.get("item_id") or "").strip(),
        "media_type": str(value.get("media_type") or nested.get("media_type") or kind or "music").strip(),
        "target_player_id": str(
            value.get("target_player_id") or nested.get("target_player_id") or ""
        ).strip(),
    }


def _stale_backend_action_error(runtime: Any, action: dict[str, Any]) -> dict[str, Any]:
    current = getattr(runtime, "config", {}) or {}
    current_backend = str(current.get(CONF_MUSIC_BACKEND) or "spotify_direct").strip()
    action_backend = str(action.get("backend") or "").strip()
    if action_backend and action_backend != current_backend:
        return _stale_backend_action_payload()
    try:
        action_revision = int(action.get("music_backend_revision"))
    except (TypeError, ValueError):
        action_revision = None
    try:
        current_revision = int(current.get(CONF_MUSIC_BACKEND_REVISION) or 0)
    except (TypeError, ValueError):
        current_revision = 0
    if action_revision is not None and action_revision < current_revision:
        return _stale_backend_action_payload()
    return {}


def _stale_backend_action_payload() -> dict[str, Any]:
    return {
        "success": False,
        "error": "stale_backend_action",
        "message": (
            "This action was created for a previous music backend. "
            "Ask DJ again for a fresh recommendation."
        ),
    }


def _music_assistant_recommendation_value(action: dict[str, Any]) -> dict[str, Any]:
    item_id = str(action.get("item_id") or action.get("uri") or "").strip()
    if not item_id:
        return {}
    return {
        "item_id": item_id,
        "media_content_id": item_id,
        "media_type": str(action.get("media_type") or action.get("kind") or "music"),
        "media_content_type": str(action.get("media_type") or action.get("kind") or "music"),
        "title": action.get("title"),
        "subtitle": action.get("subtitle"),
        "provider": action.get("provider") or "music_assistant",
        "target_player_id": action.get("target_player_id"),
    }


def _safe_backend_error_message(exc: Exception) -> str:
    text = str(exc or "").strip()
    lowered = text.lower()
    if any(part in lowered for part in ("token", "secret", "password", "authorization:")):
        return "The selected music backend could not complete playback."
    return text or "The selected music backend could not complete playback."


def _spotify_recommendation_kind(uri: str) -> str:
    if uri.startswith("spotify:track:"):
        return "track"
    if uri.startswith("spotify:album:"):
        return "album"
    if uri.startswith("spotify:artist:"):
        return "artist"
    if uri.startswith("spotify:playlist:"):
        return "playlist"
    return ""


def _recommendation_track_uris(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        raw = [str(item or "").strip() for item in value]
    else:
        raw = []
    result: list[str] = []
    seen: set[str] = set()
    for uri in raw:
        if uri.startswith("spotify:track:") and uri not in seen:
            seen.add(uri)
            result.append(uri)
    return result[:100]


def _looks_like_no_active_output(message: str) -> bool:
    normalized = str(message or "").lower()
    return "no active device" in normalized or "no spotify playback device" in normalized or "device not found" in normalized


def _with_playlist_aliases(result: dict[str, Any]) -> dict[str, Any]:
    """Expose playlist lists under stable aliases used by app and ESP clients."""
    playlists = _playlist_items_from_result(result)
    result["playlists"] = playlists
    result.setdefault("items", playlists)
    result["data"] = _playlist_container(result.get("data"), playlists)
    result["result"] = _playlist_container(result.get("result"), playlists)
    result.setdefault("count", len(playlists))
    return result


def _playlist_container(value: Any, playlists: list[Any]) -> dict[str, Any]:
    """Return a playlist container supporting data.items and data.playlists."""
    if isinstance(value, dict):
        container = dict(value)
    else:
        container = {}
    container["playlists"] = playlists
    container["items"] = playlists
    return container


def _playlist_items_from_result(result: dict[str, Any]) -> list[Any]:
    """Extract playlist items from all client-supported response shapes."""
    for key in ("playlists", "items", "data", "result"):
        value = result.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested_key in ("items", "playlists"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return nested
                if isinstance(nested, dict):
                    nested_items = nested.get("items")
                    if isinstance(nested_items, list):
                        return nested_items
    return []


async def _send_failure_dj_response(
    hass: Any,
    runtime: Any,
    exc: Exception | None = None,
) -> dict[str, Any]:
    return await async_send_dj_response_best_effort(
        hass,
        runtime,
        _command_failed_text(runtime, exc),
    )


async def _handle_pending_config_flow_app_pairing(
    view: HomeAssistantView,
    hass: Any,
    data: dict[str, Any],
) -> Any | None:
    """Pair an app against an open config-flow app-pairing step."""
    pair_code = str(data.get("pair_code") or "").strip()
    pending = hass.data.setdefault(DOMAIN, {}).setdefault(APP_PAIRING_PENDING_KEY, {})
    context = pending.get(pair_code) if isinstance(pending, dict) else None
    if not isinstance(context, dict):
        return None
    if not str(context.get("flow_id") or "").strip():
        pending.pop(pair_code, None)
        return None

    device_id = str(data.get("device_id") or "").strip()
    if not device_id or not pair_code:
        payload = {
            "success": False,
            "error": "missing_pair_data",
            "message": ERROR_MESSAGES["missing_pair_data"],
        }
        _LOGGER.debug(
            "DJConnect config-flow app pairing response status=400 payload=%s",
            _redact_debug_payload(payload),
        )
        return view.json(payload, status_code=400)

    client_type = _validate_required_client_type(data)
    if client_type is None:
        payload = {
            "success": False,
            "error": "invalid_client_type",
            "message": ERROR_MESSAGES["invalid_client_type"],
        }
        _LOGGER.debug(
            "DJConnect config-flow app pairing response status=400 payload=%s",
            _redact_debug_payload(payload),
        )
        return view.json(payload, status_code=400)

    expected_client_type = str(context.get(CONF_CLIENT_TYPE) or "").strip()
    if expected_client_type and client_type != expected_client_type:
        payload = {
            "success": False,
            "error": "client_type_mismatch",
            "message": ERROR_MESSAGES["client_type_mismatch"],
            "expected_client_type": expected_client_type,
            "received_client_type": client_type,
        }
        _LOGGER.debug(
            "DJConnect config-flow app pairing client type mismatch expected=%s received=%s",
            expected_client_type,
            client_type,
        )
        return view.json(payload, status_code=400)

    token = str(context.get(CONF_DEVICE_TOKEN) or "").strip()
    if not token:
        token = context[CONF_DEVICE_TOKEN] = secrets.token_urlsafe(32)
    context["pairing_received"] = {
        CONF_DEVICE_ID: device_id,
        CONF_DEVICE_NAME: data.get("device_name") or "DJConnect",
        CONF_CLIENT_TYPE: client_type,
        CONF_DEVICE_TOKEN: token,
        "local_url": data.get("local_url"),
        "firmware": data.get("firmware"),
    }
    conf = {
        CONF_PAIR_CODE: pair_code,
        CONF_DEVICE_TOKEN: token,
        CONF_ASSIST_PIPELINE_ID: str(
            context.get(CONF_ASSIST_PIPELINE_ID) or ""
        ),
        CONF_HA_EXTERNAL_URL: str(context.get(CONF_HA_EXTERNAL_URL) or ""),
    }
    response = {
        "success": True,
        "setup_pending": True,
        "client_type": client_type,
        "device_token": token,
        "assist_pipeline_id": conf.get(CONF_ASSIST_PIPELINE_ID, ""),
        "api_base": API_BASE,
        "voice_path": API_VOICE,
        "status_path": API_STATUS,
        "event_path": API_EVENT,
    }
    response.update(_bootstrap_metadata(hass, None, pairing_session_id=context.get("flow_id")))
    response.update(_ask_dj_capabilities())
    response.update(await async_ha_url_payload(hass, conf, client_type=client_type))
    _LOGGER.info("DJConnect app paired with pending config-flow code %s", pair_code)
    _LOGGER.debug(
        "DJConnect config-flow app pairing response status=200 payload=%s",
        _redact_debug_payload(response),
    )
    return view.json(response)


class DJConnectPairView(HomeAssistantView):
    url = API_PAIR
    name = "api:djconnect:pair"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            payload = {
                "success": False,
                "error": "invalid_json",
                "message": ERROR_MESSAGES["invalid_json"],
            }
            _LOGGER.debug(
                "DJConnect pairing response status=400 payload=%s",
                _redact_debug_payload(payload),
            )
            return self.json(payload, status_code=400)

        pending_response = await _handle_pending_config_flow_app_pairing(
            self,
            hass,
            data,
        )
        if pending_response is not None:
            return pending_response

        runtime = _runtime(hass)
        if runtime is None:
            payload = {
                "success": False,
                "error": "not_configured",
                "message": ERROR_MESSAGES["not_configured"],
            }
            _LOGGER.debug(
                "DJConnect pairing response status=503 payload=%s",
                _redact_debug_payload(payload),
            )
            return self.json(payload, status_code=503)

        device_id = data.get("device_id")
        pair_code = str(data.get("pair_code") or "")
        conf = runtime.config
        expected_pair_code = str(conf.get(CONF_PAIR_CODE) or "").strip()
        _LOGGER.debug(
            "DJConnect pairing request payload=%s expected_pair_code=%s "
            "known_device_id=%s runtime_client_type=%s",
            _redact_debug_payload(data),
            expected_pair_code or "missing",
            getattr(runtime, "device_status", {}).get("device_id")
            or getattr(runtime, "pairing_device_id", None)
            or "missing",
            _runtime_client_type(runtime),
        )
        if not device_id or not pair_code:
            payload = {
                "success": False,
                "error": "missing_pair_data",
                "message": ERROR_MESSAGES["missing_pair_data"],
            }
            _LOGGER.debug(
                "DJConnect pairing response status=400 payload=%s",
                _redact_debug_payload(payload),
            )
            return self.json(payload, status_code=400)
        client_type = _validate_required_client_type(data)
        if client_type is None:
            payload = {
                "success": False,
                "error": "invalid_client_type",
                "message": ERROR_MESSAGES["invalid_client_type"],
            }
            _LOGGER.debug(
                "DJConnect pairing response status=400 payload=%s",
                _redact_debug_payload(payload),
            )
            return self.json(payload, status_code=400)
        expected_client_type = str(_runtime_client_type(runtime) or "").strip()
        if expected_client_type and client_type != expected_client_type:
            runtime.update(last_error=ERROR_MESSAGES["client_type_mismatch"])
            payload = {
                "success": False,
                "error": "client_type_mismatch",
                "message": ERROR_MESSAGES["client_type_mismatch"],
                "expected_client_type": expected_client_type,
                "received_client_type": client_type,
            }
            _LOGGER.debug(
                "DJConnect pairing client type mismatch device_id=%s "
                "expected_client_type=%s received_client_type=%s",
                device_id,
                expected_client_type,
                client_type,
            )
            _LOGGER.debug(
                "DJConnect pairing response status=400 payload=%s",
                _redact_debug_payload(payload),
            )
            return self.json(payload, status_code=400)
        if expected_pair_code and pair_code != expected_pair_code:
            runtime.update(last_error=ERROR_MESSAGES["invalid_pair_code"])
            payload = {
                "success": False,
                "error": "invalid_pair_code",
                "message": ERROR_MESSAGES["invalid_pair_code"],
            }
            _LOGGER.debug(
                "DJConnect pairing code mismatch device_id=%s client_type=%s "
                "expected_pair_code=%s received_pair_code=%s",
                device_id,
                client_type,
                expected_pair_code,
                pair_code or "missing",
            )
            _LOGGER.debug(
                "DJConnect pairing response status=401 payload=%s",
                _redact_debug_payload(payload),
            )
            return self.json(payload, status_code=401)

        # Pairing accepts the first device/code and returns a per-device token.
        token = runtime.ensure_device_token()
        runtime.pairing_code = pair_code
        runtime.pairing_device_id = device_id
        runtime.device_status.update(
            {
                "device_id": device_id,
                "device_name": data.get("device_name") or "DJConnect",
                CONF_CLIENT_TYPE: client_type,
                "firmware": data.get("firmware"),
                "local_url": data.get("local_url"),
                "ha_pairing_status": "pending",
            }
        )
        runtime.update(last_error=None)
        _persist_paired_device(
            hass,
            runtime,
            device_id,
            data.get("local_url"),
            token,
            runtime.device_status.get(CONF_CLIENT_TYPE),
        )
        _LOGGER.info("DJConnect paired device %s", device_id)
        response = {
            "success": True,
            "client_type": _runtime_client_type(runtime),
            "device_token": token,
            "assist_pipeline_id": conf.get(CONF_ASSIST_PIPELINE_ID, ""),
            "api_base": API_BASE,
            "voice_path": API_VOICE,
            "status_path": API_STATUS,
            "event_path": API_EVENT,
        }
        response.update(_bootstrap_metadata(hass, runtime))
        response.update(_ask_dj_capabilities(runtime, client_type=client_type))
        response.update(music_backend_metadata(hass, runtime))
        response.update(_esp32_language_payload(runtime))
        response.update(await async_ha_url_payload(hass, conf, client_type=client_type))
        _LOGGER.debug(
            "DJConnect pairing response status=200 payload=%s",
            _redact_debug_payload(response),
        )
        return self.json(response)


class DJConnectStatusView(HomeAssistantView):
    url = API_STATUS
    name = "api:djconnect:status"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        _LOGGER.debug(
            "DJConnect playback status request client_type=%s device_id=%s spotify_configured=%s playback_present=%s",
            data.get(CONF_CLIENT_TYPE) or data.get("client_type"),
            _safe_debug_identifier(data.get("device_id") or request.headers.get("X-DJConnect-Device-ID")),
            data.get("spotify_configured"),
            isinstance(data.get("playback"), dict),
        )
        runtime = _runtime(
            hass,
            data.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            request.headers,
        )
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            data.get("device_id"),
            _payload_client_type(data),
        ):
            return _json_error(self, "unauthorized", 401)
        status_update = _normalized_status_payload(data)
        client_type = _validate_required_client_type(status_update)
        if client_type is None:
            runtime.update(
                last_error=(
                    "DJConnect ESP status payload is missing required "
                    "client_type=esp32"
                )
            )
            return _json_error(self, "invalid_client_type", 400)
        status_update[CONF_CLIENT_TYPE] = client_type
        music_dna_key = await _update_memory_metadata(
            runtime,
            status_update,
            user_id=_request_user_id(request),
        )
        source_ip = _request_remote_ip(request)
        if source_ip:
            status_update["local_ip"] = source_ip
        status_changed = False
        if _is_command_payload(status_update):
            _LOGGER.debug("Ignoring command payload for device sensor update")
        elif _is_voice_only_payload(status_update):
            _LOGGER.debug("Ignoring voice-only payload for device sensor update")
        else:
            status_changed = _merge_status_update(runtime.device_status, status_update)
        if not _runtime_versions_compatible(runtime):
            runtime.update(
                last_error=(
                    "DJConnect version mismatch: HA "
                    f"{VERSION}, firmware {_runtime_firmware_version(runtime)}"
                )
            )
            return _runtime_version_mismatch_response(self, runtime)
        if data.get("device_id") and runtime.device_token:
            _persist_paired_device(
                hass,
                runtime,
                data["device_id"],
                data.get("local_url") or data.get("ota_url"),
                runtime.device_token,
                runtime.device_status.get(CONF_CLIENT_TYPE),
            )
        spotify_configured = data.get("spotify_configured")
        # OTA lifecycle hints from ESP.
        ota_state = data.get("ota_state") or data.get("update_state")
        if ota_state in {"idle", "success", "failed"}:
            runtime.ota_in_progress = False
        if data.get("ota_error"):
            runtime.ota_last_error = data.get("ota_error")
        if status_changed and getattr(runtime, "last_error", None) is None:
            runtime.update()
        else:
            runtime.update(last_error=None)
        conf = runtime.config
        response = {
            "success": True,
            "client_type": _runtime_client_type(runtime),
            "assist_pipeline_id": conf.get(CONF_ASSIST_PIPELINE_ID, ""),
            "playback": getattr(runtime, "last_playback", None) or {},
        }
        response.update(_bootstrap_metadata(hass, runtime))
        response.update(_ask_dj_capabilities(runtime, client_type=client_type))
        response.update(music_backend_metadata(hass, runtime))
        response.update(
            await _push_status(
                hass,
                runtime,
                user_id=_request_user_id(request),
                device_id=status_update.get("device_id"),
                client_type=client_type,
            )
        )
        if music_dna_key:
            response["music_dna_key"] = music_dna_key
        response.update(_ha_version_payload())
        response.update(_esp32_language_payload(runtime))
        response.update(await async_ha_url_payload(hass, conf, client_type=client_type))
        if _client_status_uses_backend_playback(client_type):
            response.update(await _status_playback_payload(hass, runtime))
            backend_available = bool(response.get("backend_available"))
        else:
            if response.get("music_backend") == "music_assistant":
                backend_available = bool(response.get("music_backend_available"))
            else:
                backend_available = bool(_current_spotify_credentials_for_status(hass, runtime))
            response["backend_available"] = backend_available
            playback = response.get("playback")
            if not isinstance(playback, dict) or "has_playback" not in playback:
                response["playback"] = {"has_playback": False}
        _LOGGER.debug(
            "DJConnect status from device %s: spotify_configured=%s backend_available=%s",
            _safe_debug_identifier(data.get("device_id")),
            spotify_configured,
            backend_available,
        )
        playback = response.get("playback") if isinstance(response.get("playback"), dict) else {}
        _LOGGER.debug(
            "DJConnect playback status result client_type=%s device_id=%s backend=%s backend_available=%s music_backend_available=%s has_playback=%s playback_state=%s is_playing=%s",
            client_type,
            _safe_debug_identifier(data.get("device_id")),
            response.get("music_backend"),
            backend_available,
            response.get("music_backend_available"),
            playback.get("has_playback") if isinstance(playback, dict) else None,
            _safe_playback_state(playback.get("state") if isinstance(playback, dict) else None),
            playback.get("is_playing") if isinstance(playback, dict) else None,
        )
        runtime.device_status["backend_available"] = backend_available
        return self.json(response)


class DJConnectCommandView(HomeAssistantView):
    url = API_COMMAND
    name = "api:djconnect:command"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_command_payload

        result, status_code = await async_handle_command_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class _DJConnectSessionView(HomeAssistantView):
    """Base authenticated HTTP transport for the v4 Runtime lifecycle."""

    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def _payload(self, request) -> dict[str, Any] | None:
        try:
            return await request.json()
        except Exception:  # noqa: BLE001
            return None


class DJConnectSessionStartView(_DJConnectSessionView):
    url = API_SESSION_START
    name = "api:djconnect:session:start"

    async def post(self, request):
        data = await self._payload(request)
        if data is None:
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_session_start_payload

        result, status = await async_handle_session_start_payload(
            request.app["hass"], data, headers=request.headers, user_id=_request_user_id(request)
        )
        return self.json(result, status_code=status)


class DJConnectSessionEndView(_DJConnectSessionView):
    url = API_SESSION_END
    name = "api:djconnect:session:end"

    async def post(self, request):
        data = await self._payload(request)
        if data is None:
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_session_end_payload

        result, status = await async_handle_session_end_payload(
            request.app["hass"], data, headers=request.headers, user_id=_request_user_id(request)
        )
        return self.json(result, status_code=status)


class DJConnectActiveSessionView(_DJConnectSessionView):
    url = API_SESSION_ACTIVE
    name = "api:djconnect:session:active"

    async def get(self, request):
        from .api_handlers import async_handle_active_session_payload

        result, status = await async_handle_active_session_payload(
            request.app["hass"], dict(request.query), headers=request.headers, user_id=_request_user_id(request)
        )
        return self.json(result, status_code=status)


class DJConnectSessionBroadcastTokenView(_DJConnectSessionView):
    """Owner-only route that returns an active Runtime's ephemeral Broadcast Token."""

    url = API_SESSION_BROADCAST_TOKEN
    name = "api:djconnect:session:broadcast:token"

    async def post(self, request):
        data = await self._payload(request)
        if data is None:
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_session_broadcast_token_payload

        result, status = await async_handle_session_broadcast_token_payload(
            request.app["hass"], data, headers=request.headers, user_id=_request_user_id(request)
        )
        return self.json(result, status_code=status)


class DJConnectEventView(HomeAssistantView):
    url = API_EVENT
    name = "api:djconnect:event"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        runtime = _runtime(hass)
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            data.get("device_id"),
            _payload_client_type(data),
        ):
            return _json_error(self, "unauthorized", 401)
        client_type = _validate_required_client_type(data)
        if client_type is None:
            return _json_error(self, "invalid_client_type", 400)
        runtime.device_status[CONF_CLIENT_TYPE] = client_type
        if not _runtime_versions_compatible(runtime):
            return _runtime_version_mismatch_response(self, runtime)
        event_type = data.get("type") or data.get("event")
        runtime.device_status["last_event"] = data
        runtime.update(last_error=None)
        _LOGGER.info("DJConnect event received: %s", event_type)
        return self.json({"success": True})


class DJConnectAskDjView(HomeAssistantView):
    url = API_ASK_DJ
    name = "api:djconnect:ask_dj"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        identity = _identity_payload(data)
        runtime = _runtime(
            hass,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            request.headers,
        )
        if runtime is None:
            _LOGGER.debug(
                "DJConnect Ask DJ raw rejected status=503 error=not_configured device_id=%s",
                _safe_debug_identifier(identity.get("device_id")),
            )
            return _json_error(self, "not_configured", 503)
        client_type = _validate_required_client_type(identity)
        if client_type is None:
            _LOGGER.debug(
                "DJConnect Ask DJ raw rejected status=400 error=invalid_client_type device_id=%s",
                _safe_debug_identifier(identity.get("device_id")),
            )
            return _json_error(self, "invalid_client_type", 400)
        identity[CONF_CLIENT_TYPE] = client_type
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            identity.get("device_id"),
            client_type,
        ):
            _LOGGER.debug(
                "DJConnect Ask DJ raw rejected status=401 error=unauthorized client_type=%s device_id=%s",
                client_type,
                _safe_debug_identifier(identity.get("device_id")),
            )
            return _json_error(self, "unauthorized", 401)
        payload = dict(data)
        payload.update({key: value for key, value in identity.items() if value is not None})
        payload = enrich_payload_with_mood_zone(payload)
        text = str(payload.get("text") or payload.get("prompt") or payload.get("query") or "").strip()
        _LOGGER.debug(
            "DJConnect Ask DJ raw request client_type=%s device_id=%s user_id=%s text_length=%s audio_response=%s mood_zone=%s",
            client_type,
            _safe_debug_identifier(identity.get("device_id")),
            _safe_debug_identifier(_request_user_id(request)),
            len(text),
            str(payload.get("audio_response") or "").strip()[:24],
            str(payload.get("mood_zone") or "").strip()[:24],
        )
        result = await async_handle_ask_dj(
            hass,
            runtime,
            payload,
            user_id=_request_user_id(request),
        )
        status_code = 200 if result.get("success") else 500
        _LOGGER.debug(
            "DJConnect Ask DJ raw result status=%s success=%s intent=%s action=%s audio=%s images=%s links=%s sources=%s playback_actions=%s confirmation_actions=%s error=%s",
            status_code,
            result.get("success"),
            _safe_intent_name(result.get("intent")),
            str(result.get("action") or "").strip()[:48],
            bool(result.get("audio_url")),
            len(result.get("images") or []),
            len(result.get("links") or []),
            len(result.get("sources") or []),
            len(result.get("playback_actions") or []),
            len(result.get("confirmation_actions") or []),
            result.get("error"),
        )
        return self.json(result, status_code=status_code)


class DJConnectAskDjClearView(HomeAssistantView):
    url = API_ASK_DJ_CLEAR
    name = "api:djconnect:ask_dj_clear"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        identity = _identity_payload(data)
        runtime = _runtime(
            hass,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            request.headers,
        )
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        client_type = _validate_required_client_type(identity)
        if client_type is None:
            return _json_error(self, "invalid_client_type", 400)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            identity.get("device_id"),
            client_type,
        ):
            return _json_error(self, "unauthorized", 401)
        result = await _history_manager(hass, runtime).async_clear_all()
        return self.json(result)


class DJConnectAskDjMessageView(HomeAssistantView):
    url = API_ASK_DJ_MESSAGE
    name = "api:djconnect:ask_dj_message"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_ask_dj_message_payload

        result, status_code = await async_handle_ask_dj_message_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectTrackInsightView(HomeAssistantView):
    url = API_TRACK_INSIGHT
    name = "api:djconnect:track_insight"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_track_insight_payload

        result, status_code = await async_handle_track_insight_payload(
            hass,
            data,
            headers=request.headers,
            source="http",
        )
        return self.json(result, status_code=status_code)


class DJConnectVibeCastView(HomeAssistantView):
    url = API_VIBECAST
    name = "api:djconnect:vibecast"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        hass = request.app["hass"]
        from .vibecast import async_handle_vibecast_payload

        result, status_code = await async_handle_vibecast_payload(
            hass,
            dict(request.query),
            headers=request.headers,
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDnaProfileView(HomeAssistantView):
    url = API_MUSIC_DNA_PROFILE
    name = "api:djconnect:music_dna_profile"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_dna_profile_payload

        result, status_code = await async_handle_music_dna_profile_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDiscoveryView(HomeAssistantView):
    url = API_MUSIC_DISCOVERY
    name = "api:djconnect:music_discovery"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        hass = request.app["hass"]
        from .api_handlers import async_handle_music_discovery_feed_payload

        result, status_code = await async_handle_music_discovery_feed_payload(
            hass,
            dict(request.query),
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDiscoveryRefreshView(HomeAssistantView):
    url = API_MUSIC_DISCOVERY_REFRESH
    name = "api:djconnect:music_discovery_refresh"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_discovery_refresh_payload

        result, status_code = await async_handle_music_discovery_refresh_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDiscoveryPlayView(HomeAssistantView):
    url = API_MUSIC_DISCOVERY_PLAY
    name = "api:djconnect:music_discovery_play"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_discovery_play_payload

        result, status_code = await async_handle_music_discovery_play_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDiscoveryFeedbackView(HomeAssistantView):
    url = API_MUSIC_DISCOVERY_FEEDBACK
    name = "api:djconnect:music_discovery_feedback"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_discovery_feedback_payload

        result, status_code = await async_handle_music_discovery_feedback_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDnaSettingsView(HomeAssistantView):
    url = API_MUSIC_DNA_SETTINGS
    name = "api:djconnect:music_dna_settings"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_dna_settings_payload

        result, status_code = await async_handle_music_dna_settings_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDnaClearView(HomeAssistantView):
    url = API_MUSIC_DNA_CLEAR
    name = "api:djconnect:music_dna_clear"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_dna_clear_payload

        result, status_code = await async_handle_music_dna_clear_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDnaImportView(HomeAssistantView):
    url = API_MUSIC_DNA_IMPORT
    name = "api:djconnect:music_dna_import"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_dna_import_payload

        result, status_code = await async_handle_music_dna_import_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectMusicDnaExportView(HomeAssistantView):
    url = API_MUSIC_DNA_EXPORT
    name = "api:djconnect:music_dna_export"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_music_dna_export_payload

        result, status_code = await async_handle_music_dna_export_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectPushRegisterView(HomeAssistantView):
    url = API_PUSH_REGISTER
    name = "api:djconnect:push_register"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        payload = _push_payload_from_request(data, request.headers)
        identity = _identity_payload(payload)
        runtime = _runtime(
            hass,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            request.headers,
        )
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        client_type = _validate_required_client_type(identity)
        if client_type is None or client_type not in {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}:
            return _json_error(self, "invalid_client_type", 400)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            client_type,
        ):
            return _json_error(self, "unauthorized", 401)
        payload.update({key: value for key, value in identity.items() if value is not None})
        payload[CONF_CLIENT_TYPE] = client_type
        result = await async_register_push(
            hass,
            runtime,
            user_id=_request_user_id(request),
            payload=payload,
        )
        status = 200 if result.get("success") else 400
        return self.json(result, status_code=status)


class DJConnectPushBootstrapView(HomeAssistantView):
    url = API_PUSH_BOOTSTRAP
    name = "api:djconnect:push_bootstrap"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        payload = _push_payload_from_request(data, request.headers)
        identity = _identity_payload(payload)
        runtime = _runtime(
            hass,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            request.headers,
        )
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        client_type = _validate_required_client_type(identity)
        if client_type is None or client_type not in {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}:
            return _json_error(self, "invalid_client_type", 400)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            client_type,
        ):
            return _json_error(self, "unauthorized", 401)
        payload.update({key: value for key, value in identity.items() if value is not None})
        payload[CONF_CLIENT_TYPE] = client_type
        result = await async_bootstrap_push(
            hass,
            runtime,
            user_id=_request_user_id(request),
            payload=payload,
        )
        status = 200 if result.get("success") else 400
        return self.json(result, status_code=status)


class DJConnectPushUnregisterView(HomeAssistantView):
    url = API_PUSH_UNREGISTER
    name = "api:djconnect:push_unregister"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        payload = _push_payload_from_request(data, request.headers)
        identity = _identity_payload(payload)
        runtime = _runtime(
            hass,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            request.headers,
        )
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        client_type = _validate_required_client_type(identity)
        if client_type is None or client_type not in {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}:
            return _json_error(self, "invalid_client_type", 400)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            identity.get("device_id") or request.headers.get("X-DJConnect-Device-ID"),
            client_type,
        ):
            return _json_error(self, "unauthorized", 401)
        payload.update({key: value for key, value in identity.items() if value is not None})
        payload[CONF_CLIENT_TYPE] = client_type
        result = await async_unregister_push(
            hass,
            runtime,
            user_id=_request_user_id(request),
            payload=payload,
        )
        status = 200 if result.get("success") else 400
        return self.json(result, status_code=status)


def _push_payload_from_request(data: dict, headers) -> dict:
    """Merge push request body with DJConnect identity headers."""
    payload = dict(data or {})
    for header_name, payload_key in (
        ("X-DJConnect-Device-ID", CONF_DEVICE_ID),
        ("X-DJConnect-Client-ID", "client_id"),
        ("X-DJConnect-Client-Type", CONF_CLIENT_TYPE),
        ("X-DJConnect-Device-Name", "device_name"),
        ("X-DJConnect-App-Version", "app_version"),
        ("X-DJConnect-App-Build", "app_build"),
        ("X-DJConnect-Language", "language"),
        ("X-DJConnect-Locale", "locale"),
    ):
        value = headers.get(header_name) if hasattr(headers, "get") else None
        if value and not payload.get(payload_key):
            payload[payload_key] = str(value).split(",", 1)[0].strip()
    if headers.get("Authorization") and not payload.get("authorization"):
        payload["authorization"] = "<present>"
    return payload


class DJConnectAskDjIdleSuggestionView(HomeAssistantView):
    url = API_ASK_DJ_IDLE_SUGGESTION
    name = "api:djconnect:ask_dj_idle_suggestion"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_ask_dj_idle_suggestion_payload

        result, status_code = await async_handle_ask_dj_idle_suggestion_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectAskDjHistoryView(HomeAssistantView):
    url = API_ASK_DJ_HISTORY
    name = "api:djconnect:ask_dj_history"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        hass = request.app["hass"]
        from .api_handlers import async_handle_ask_dj_history_payload

        result, status_code = await async_handle_ask_dj_history_payload(
            hass,
            {"since_revision": _query_int(request, "since_revision")},
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectAskDjHistoryExportView(HomeAssistantView):
    url = API_ASK_DJ_HISTORY_EXPORT
    name = "api:djconnect:ask_dj_history_export"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_ask_dj_history_export_payload

        result, status_code = await async_handle_ask_dj_history_export_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectAskDjHistoryClearView(HomeAssistantView):
    url = API_ASK_DJ_HISTORY_CLEAR
    name = "api:djconnect:ask_dj_history_clear"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_ask_dj_history_clear_payload

        result, status_code = await async_handle_ask_dj_history_clear_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectAskDjHistoryStateView(HomeAssistantView):
    url = API_ASK_DJ_HISTORY_STATE
    name = "api:djconnect:ask_dj_history_state"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001
            return _json_error(self, "invalid_json", 400)
        from .api_handlers import async_handle_ask_dj_history_state_payload

        result, status_code = await async_handle_ask_dj_history_state_payload(
            hass,
            data,
            headers=request.headers,
            user_id=_request_user_id(request),
        )
        return self.json(result, status_code=status_code)


class DJConnectVoiceView(HomeAssistantView):
    url = API_VOICE
    name = "api:djconnect:voice"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
        hass = request.app["hass"]
        device_id = request.headers.get("X-DJConnect-Device-ID")
        if not device_id:
            return _json_error(self, "unauthorized", 401)
        runtime = _runtime(hass, device_id, request.headers)
        if runtime is None:
            return _json_error(self, "not_configured", 503)
        if not _authorize_runtime_device_request(
            runtime,
            request.headers,
            device_id,
            request.headers.get(CONF_CLIENT_TYPE),
        ):
            return _json_error(self, "unauthorized", 401)
        if not _runtime_versions_compatible(runtime):
            return _runtime_version_mismatch_response(self, runtime)
        if getattr(runtime, "device_token", None):
            _persist_paired_device(
                hass,
                runtime,
                device_id,
                getattr(runtime, "device_status", {}).get("local_url"),
                runtime.device_token,
                getattr(runtime, "device_status", {}).get(CONF_CLIENT_TYPE),
            )

        try:
            content_type = request.headers.get("Content-Type", "")
            content_type = content_type.split(";", 1)[0].strip().lower()
            data = None
            user_text = ""
            is_audio_request = _is_audio_upload(content_type)
            header_client_type = (
                request.headers.get(CONF_CLIENT_TYPE)
                or request.headers.get("X-DJConnect-Client-Type")
                or getattr(runtime, "device_status", {}).get(CONF_CLIENT_TYPE)
            )

            if is_audio_request:
                limit = int(runtime.config.get(CONF_MAX_AUDIO_BYTES, DEFAULT_MAX_AUDIO_BYTES))
                wav = await request.read()
                if not wav:
                    return _json_error(self, "missing_audio", 400)
                if len(wav) > limit:
                    return _json_error(self, "audio_too_large", 413)
                _store_debug_voice_wav(hass, device_id, content_type, wav)
                entry = getattr(runtime, "entry", None)
                pipeline_id = str(
                    runtime.config.get(CONF_ASSIST_PIPELINE_ID) or ""
                ).strip()
                _LOGGER.info(
                    "DJConnect WAV voice request: entry_id=%s options_keys=%s "
                    "data_keys=%s assist_pipeline_id=%s "
                    "content_type=%s body_bytes=%s",
                    getattr(entry, "entry_id", None),
                    _safe_config_keys(getattr(entry, "options", None)),
                    _safe_config_keys(getattr(entry, "data", None)),
                    pipeline_id or None,
                    content_type,
                    len(wav),
                )
                _set_device_state(runtime, "processing")
                runtime.update(last_error=None)
                try:
                    user_text = await transcribe_wav_with_assist(hass, wav, runtime.config)
                except DJConnectNoSttProviderError as exc:
                    _set_device_state(runtime, "error")
                    runtime.update(last_error=_safe_backend_error_message(exc))
                    return _stt_error_response(
                        self,
                        _safe_backend_error_message(exc),
                        422 if _is_ask_dj_voice_client(header_client_type) else 503,
                    )
                except Exception as exc:  # noqa: BLE001
                    _set_device_state(runtime, "error")
                    runtime.update(last_error=_safe_backend_error_message(exc))
                    return _stt_error_response(
                        self,
                        _safe_backend_error_message(exc),
                        422 if _is_ask_dj_voice_client(header_client_type) else 500,
                    )
            elif content_type == "application/json":
                try:
                    data = await request.json()
                except Exception:  # noqa: BLE001
                    return _json_error(self, "invalid_json", 400)
                if _is_voice_only_payload(data):
                    _LOGGER.debug("Ignoring voice-only payload for device sensor update")
            elif request.headers.get("X-DJConnect-Text"):
                pass
            elif content_type:
                await request.read()
                return _json_error(self, "unsupported_media_type", 415)
            else:
                await request.read()

            user_text = user_text or _text_from_payload(request.headers, data)
            if not user_text:
                return _missing_text_response(self)
            if is_audio_request and _is_ask_dj_voice_client(header_client_type):
                ask_payload = _voice_header_payload(
                    request.headers,
                    device_id,
                    str(header_client_type or ""),
                )
                ask_payload["text"] = user_text
                ask_payload["input_type"] = "voice"
                _set_device_state(runtime, "processing")
                runtime.update(last_text=user_text, last_error=None)
                try:
                    result = await async_handle_ask_dj(
                        hass,
                        runtime,
                        ask_payload,
                        user_id=_request_user_id(request),
                    )
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("DJConnect Ask DJ voice failed: %s", _safe_backend_error_message(exc))
                    _set_device_state(runtime, "error")
                    runtime.update(last_error=_safe_backend_error_message(exc))
                    return self.json(
                        {
                            "success": False,
                            "error": "ask_dj_unavailable",
                            "message": "Ask DJ is nu niet bereikbaar.",
                            "text": "Ask DJ is nu niet bereikbaar.",
                            "dj_text": "Ask DJ is nu niet bereikbaar.",
                            "transcript": user_text,
                            "recognized_text": user_text,
                            "images": [],
                            "links": [],
                            "sources": [],
                            "actions": [],
                        },
                        status_code=503,
                    )
                _persist_runtime_device_status(hass, runtime)
                _set_device_state(runtime, "idle")
                return self.json(
                    {
                        "success": bool(result.get("success", True)),
                        **result,
                        "transcript": user_text,
                        "recognized_text": user_text,
                        "audio_type": result.get("audio_type")
                        or _audio_type_from_url(result.get("audio_url")),
                        "actions": result.get("actions") or [],
                        "sources": result.get("sources") or [],
                    }
                )
            if isinstance(data, dict):
                memory_payload = data
            else:
                memory_payload = {
                    CONF_DEVICE_ID: device_id,
                    CONF_CLIENT_TYPE: getattr(runtime, "device_status", {}).get(
                        CONF_CLIENT_TYPE
                    ),
                }
            music_dna_key = await _update_memory_metadata(
                runtime,
                memory_payload,
                user_id=_request_user_id(request),
            )

            if not is_audio_request:
                dj_text = _test_dj_text(runtime)
                _LOGGER.debug("DJConnect DJ response text test: %s", user_text)
                _set_device_state(runtime, "responding")
                runtime.update(last_text=user_text, last_dj_text=dj_text, last_error=None)
                dj_response = await async_send_dj_response_best_effort(
                    hass,
                    runtime,
                    dj_text,
                )
                _persist_runtime_device_status(hass, runtime)
                audio_url = dj_response.get("audio_url_value")
                _set_device_state(runtime, "idle")
                return self.json(
                    {
                        "success": True,
                        "text": dj_text,
                        "dj_text": dj_text,
                        "recognized_text": user_text,
                        "dj_response": dj_response,
                        "audio_url": audio_url,
                        "audio_type": _audio_type_from_url(audio_url),
                        "music_dna_key": music_dna_key,
                    }
                )

            _LOGGER.debug("DJConnect command: %s", user_text)
            _set_device_state(runtime, "processing")
            runtime.update(last_text=user_text, last_error=None)
            try:
                result = await _run_text_command_with_memory(
                    hass,
                    runtime,
                    user_text,
                    play=True,
                    correct_stt=True,
                    memory_payload=memory_payload,
                    user_id=_request_user_id(request),
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("DJConnect command parser/playback failed: %s", _safe_backend_error_message(exc))
                _set_device_state(runtime, "responding")
                dj_text = _command_failed_text(runtime, exc)
                runtime.update(last_error=_safe_backend_error_message(exc), last_dj_text=dj_text)
                dj_response = await async_send_dj_response_best_effort(
                    hass,
                    runtime,
                    dj_text,
                )
                _persist_runtime_device_status(hass, runtime)
                audio_url = dj_response.get("audio_url_value")
                _set_device_state(runtime, "idle")
                return self.json(
                    {
                        "success": True,
                        "error": "command_failed",
                        "message": _safe_backend_error_message(exc),
                        "text": dj_text,
                        "dj_text": dj_text,
                        "recognized_text": user_text,
                        "intent": getattr(runtime, "last_intent", None),
                        "dj_response": dj_response,
                        "audio_url": audio_url,
                        "audio_type": _audio_type_from_url(audio_url),
                        "music_dna_key": music_dna_key,
                    }
                )
            _set_device_state(runtime, "responding")
            result["dj_response"] = await async_send_dj_response_best_effort(
                hass,
                runtime,
                result.get("dj_text") or "",
            )
            _persist_runtime_device_status(hass, runtime)
            audio_url = result.get("dj_response", {}).get("audio_url_value")
            _set_device_state(runtime, "idle")
            _LOGGER.debug(
                "DJConnect result intent=%s playback=%s dj_text=%s audio_url=%s audio_type=%s",
                result.get("intent"),
                bool(result.get("playback")),
                bool(result.get("dj_text")),
                bool(audio_url),
                _audio_type_from_url(audio_url),
            )
            return self.json(
                {
                    "success": True,
                    **result,
                    "text": result.get("dj_text") or result.get("text"),
                    "recognized_text": user_text,
                    "audio_url": audio_url,
                    "audio_type": _audio_type_from_url(audio_url),
                    "music_dna_key": music_dna_key,
                }
            )

        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("DJConnect request failed: %s", _safe_backend_error_message(exc))
            _set_device_state(runtime, "error")
            runtime.update(last_error=_safe_backend_error_message(exc))
            dj_response = await _send_failure_dj_response(hass, runtime, exc)
            dj_text = _command_failed_text(runtime, exc)
            runtime.update(last_error=_safe_backend_error_message(exc))
            return self.json(
                {
                    "success": False,
                    "error": "command_failed",
                    "message": _safe_backend_error_message(exc),
                    "dj_text": dj_text,
                    "dj_response": dj_response,
                },
                status_code=500,
            )


class DJConnectTtsView(HomeAssistantView):
    url = API_TTS
    name = "api:djconnect:tts"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request, token: str, extension: str = "wav"):
        status, audio = get_tts_audio(request.app["hass"], token)
        if status == 404:
            return web.Response(status=404, text="DJConnect TTS audio not found")
        if status == 410:
            return web.Response(status=410, text="DJConnect TTS audio expired")
        if audio is None or extension.lower() != audio.extension:
            return web.Response(status=404, text="DJConnect TTS audio type not found")
        return web.Response(
            body=audio.data,
            content_type=audio.content_type,
            headers={"Content-Length": str(len(audio.data))},
        )


class DJConnectImageProxyView(HomeAssistantView):
    url = API_IMAGE_PROXY
    name = "api:djconnect:image_proxy"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request, token: str):
        hass = request.app["hass"]
        target = image_proxy_target(hass, token)
        if not target:
            return web.Response(status=404, text="DJConnect image not found")
        parsed = urlsplit(str(target))
        if parsed.scheme not in {"http", "https"}:
            return web.Response(status=400, text="DJConnect image URL is invalid")
        session = async_get_clientsession(hass)
        async with session.get(str(target)) as resp:
            body = await resp.read()
            if resp.status < 200 or resp.status >= 300:
                return web.Response(status=resp.status, text="DJConnect image fetch failed")
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            return web.Response(
                body=body,
                content_type=content_type,
                headers={"Content-Length": str(len(body))},
            )


class DJConnectVoiceDebugView(HomeAssistantView):
    url = VOICE_DEBUG_URL
    name = "api:djconnect:voice_debug"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        debug = request.app["hass"].data.get(DOMAIN, {}).get(VOICE_DEBUG_KEY)
        if not debug:
            return web.Response(status=404, text="DJConnect voice debug WAV not available")
        wav = debug.get("wav")
        if not wav:
            return web.Response(status=404, text="DJConnect voice debug WAV is empty")
        filename = f"djconnect-last-voice-{debug.get('device_id') or 'device'}.wav"
        return web.Response(
            body=wav,
            content_type="audio/wav",
            headers={
                "Content-Length": str(len(wav)),
                "Content-Disposition": f'inline; filename="{filename}"',
                "X-DJConnect-Device-ID": str(debug.get("device_id") or ""),
            },
        )


class DJConnectSpotifyCallbackView(HomeAssistantView):
    url = API_SPOTIFY_CALLBACK
    name = "api:djconnect:spotify_callback"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        hass = request.app["hass"]
        state = request.query.get("state")
        code = request.query.get("code")
        error = request.query.get("error")
        if error:
            return await _spotify_oauth_html_response(
                hass,
                title=_oauth_copy(hass, "oauth_error_title"),
                message=_oauth_copy(hass, "oauth_error_message", error=error),
                status=400,
                success=False,
            )
        if not state or not code:
            return await _spotify_oauth_html_response(
                hass,
                title=_oauth_copy(hass, "oauth_incomplete_title"),
                message=_oauth_copy(hass, "oauth_incomplete_message"),
                status=400,
                success=False,
            )

        # Config-flow OAuth path: during initial setup there is no config entry yet.
        # config_flow.py stores pending context under config_flow_oauth_pending.
        config_pending = hass.data.setdefault(DOMAIN, {}).setdefault("config_flow_oauth_pending", {})
        ctx = config_pending.pop(state, None)
        if ctx:
            try:
                token = await exchange_code_for_refresh_token(
                    hass,
                    client_id=ctx["client_id"],
                    code=code,
                    code_verifier=ctx["code_verifier"],
                    redirect_uri=ctx["redirect_uri"],
                )
                runtime = _runtime(hass)
                entry = getattr(runtime, "entry", None)
                if entry is not None:
                    _store_rotated_spotify_refresh_token(
                        hass,
                        entry,
                        runtime,
                        token.get("refresh_token"),
                    )
                results = hass.data.setdefault(DOMAIN, {}).setdefault("config_flow_oauth_results", {})
                results[state] = {
                    CONF_SPOTIFY_CLIENT_ID: ctx["client_id"],
                    CONF_SPOTIFY_REFRESH_TOKEN: token["refresh_token"],
                    CONF_SPOTIFY_MARKET: ctx.get("market", DEFAULT_SPOTIFY_MARKET),
                    CONF_SPOTIFY_SCOPES: ctx.get("scopes", DEFAULT_SPOTIFY_SCOPES),
                }
                flow_id = ctx.get("flow_id")
                if flow_id:
                    await hass.config_entries.flow.async_configure(flow_id, {"state": state})
                return await _spotify_oauth_html_response(
                    hass,
                    title=_oauth_copy(hass, "linked_title"),
                    message=_oauth_copy(hass, "linked_message"),
                    base_url=ctx.get("ha_external_url") or ctx.get("redirect_uri", "").split(API_SPOTIFY_CALLBACK)[0],
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("DJConnect config-flow OAuth callback failed")
                return await _spotify_oauth_html_response(
                    hass,
                    title=_oauth_copy(hass, "oauth_exception_title"),
                    message=_oauth_copy(hass, "oauth_exception_message", error=exc),
                    status=500,
                    success=False,
                )

        pending = hass.data.setdefault(DOMAIN, {}).setdefault("spotify_oauth_pending", {})
        ctx = pending.pop(state, None)
        if not ctx:
            return await _spotify_oauth_html_response(
                hass,
                title=_oauth_copy(hass, "expired_title"),
                message=_oauth_copy(hass, "expired_message"),
                status=400,
                success=False,
            )

        try:
            token = await exchange_code_for_refresh_token(
                hass,
                client_id=ctx["client_id"],
                code=code,
                code_verifier=ctx["code_verifier"],
                redirect_uri=ctx["redirect_uri"],
            )
            entry = hass.config_entries.async_get_entry(ctx["entry_id"])
            if entry is None:
                raise RuntimeError("DJConnect config entry no longer exists")
            new_data = dict(entry.data)
            new_data[CONF_SPOTIFY_CLIENT_ID] = ctx["client_id"]
            new_data[CONF_SPOTIFY_REFRESH_TOKEN] = token["refresh_token"]
            new_data[CONF_SPOTIFY_MARKET] = ctx.get("market", DEFAULT_SPOTIFY_MARKET)
            new_data[CONF_SPOTIFY_SCOPES] = ctx.get("scopes", DEFAULT_SPOTIFY_SCOPES)
            hass.config_entries.async_update_entry(entry, data=new_data)
            runtime = _runtime(hass)
            if runtime is not None:
                runtime.update_spotify_refresh_token(token.get("refresh_token"))
                _LOGGER.debug("DJConnect Spotify refresh_token=rotated/present")
            _delete_spotify_reauth_issues(hass, entry.entry_id)
            await hass.config_entries.async_reload(entry.entry_id)
            flow_id = ctx.get("flow_id")
            if flow_id:
                try:
                    await hass.config_entries.flow.async_configure(
                        flow_id,
                        {"state": state},
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.debug(
                        "DJConnect OAuth options flow was already closed before callback completion",
                        exc_info=True,
                    )
            return await _spotify_oauth_html_response(
                hass,
                title=_oauth_copy(hass, "reauth_title"),
                message=_oauth_copy(hass, "reauth_message"),
                base_url=ctx.get("ha_external_url") or ctx.get("redirect_uri", "").split(API_SPOTIFY_CALLBACK)[0],
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("DJConnect Spotify OAuth callback failed")
            return await _spotify_oauth_html_response(
                hass,
                title=_oauth_copy(hass, "oauth_exception_title"),
                message=_oauth_copy(hass, "oauth_exception_message", error=exc),
                status=500,
                success=False,
            )
