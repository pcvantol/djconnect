"""Config flow for DJConnect."""

from __future__ import annotations

import asyncio
import inspect
import logging
import secrets
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from custom_components.djconnect import register_http_views

from .const import (
    CONF_ALLOW_OTA_ON_BATTERY,
    CONF_API_BASE_URL,
    CONF_ASSIST_PIPELINE_ID,
    CONF_BLE_ADDRESS,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_LANGUAGE,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TOKEN,
    CONF_DJCONNECT_INSTALL_TOKEN,
    CONF_DJ_RESPONSE_ENABLED,
    CONF_DJ_RESPONSE_PROMPT,
    CONF_DJ_RESPONSE_TTL_SECONDS,
    CONF_FIRMWARE_CHANNEL,
    CONF_HA_EXTERNAL_URL,
    CONF_HA_INSTALL_ID,
    CONF_LOCAL_URL,
    CONF_MAX_AUDIO_BYTES,
    CONF_MUSIC_ASSISTANT_PLAYER,
    CONF_MUSIC_BACKEND,
    CONF_MUSIC_BACKEND_REVISION,
    CONF_MIN_BATTERY_FOR_OTA,
    CONF_PAIR_CODE,
    CONF_PAIRING_URI,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_MARKET,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_SCOPES,
    CONF_SETUP_METHOD,
    CONF_VOICE_PROFILE,
    CONF_WIFI_PASSWORD,
    CONF_WIFI_SSID,
    DEFAULT_ASSIST_PIPELINE_ID,
    DEFAULT_API_BASE_URL,
    CLIENT_TYPE_CONVERSATION_AGENT,
    DEFAULT_CLIENT_TYPE,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DEVICE_LANGUAGE,
    DEFAULT_DJ_RESPONSE_ENABLED,
    DEFAULT_DJ_RESPONSE_PROMPT,
    DEFAULT_DJ_RESPONSE_TTL_SECONDS,
    DEFAULT_FIRMWARE_CHANNEL,
    DEFAULT_MAX_AUDIO_BYTES,
    DEFAULT_MUSIC_BACKEND,
    DEFAULT_MIN_BATTERY_FOR_OTA,
    DEFAULT_SETUP_METHOD,
    DEFAULT_SPOTIFY_MARKET,
    DEFAULT_SPOTIFY_SCOPES,
    DEFAULT_VOICE_PROFILE,
    FIRMWARE_CHANNELS,
    MUSIC_BACKEND_NAMES,
    MUSIC_BACKEND_MUSIC_ASSISTANT,
    MUSIC_BACKEND_SPOTIFY_DIRECT,
    CLIENT_TYPE_NAMES,
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_WATCHOS,
    CLIENT_TYPE_WINDOWS,
    DOMAIN,
    SETUP_METHOD_BLE_WIFI,
    SETUP_METHOD_CONVERSATION_AGENT,
    SETUP_METHOD_PAIR_APP,
    SETUP_METHOD_PAIR_LOCAL_DEVICE,
    API_PAIR,
)
from .central_api import TOKEN_PREFIX, async_rotate_install_token
from .ble import async_discover_devices, async_provision_wifi
from .client_identity import (
    client_type_uses_local_device_api,
    default_pair_client_type,
    pair_client_type_options,
)
from .discovery import DiscoveredClient, async_discover_djconnect_clients
from .discovery_selection import (
    discovered_client_defaults,
    discovered_client_key,
    discovered_client_options,
    selected_discovered_client,
)
from .pairing_defaults import (
    clean as _clean,
    default_local_url as _default_local_url,
    device_name_for_client_type,
    valid_pair_code as _valid_pair_code,
)
from .ha_urls import async_ha_local_url
from .spotify_oauth import build_authorize_url, build_redirect_uri, create_code_verifier
from .voice_profiles import normalize_voice_profile, voice_profile_options

_LOGGER = logging.getLogger(__name__)

DEVICE_LANGUAGE_NAMES = {"en": "English", "nl": "Nederlands"}
OPTIONS_ACTION_FIELD = "options_action"
OPTIONS_ACTION_SAVE = "save_options"
OPTIONS_ACTION_RETRY_PAIRING = "retry_device_pairing"
OPTIONS_ACTION_REPAIR = "repair_device_pairing"
OPTIONS_ACTION_SPOTIFY_REAUTH = "spotify_reauthorize"
OPTIONS_ACTION_CHANGE_MUSIC_BACKEND = "change_music_backend"
OPTIONS_ACTION_CENTRAL_API = "central_api"
OPTIONS_ACTION_ROTATE_INSTALL_TOKEN = "rotate_install_token"
BLE_ACTION_FIELD = "ble_action"
BLE_ACTION_PROVISION = "provision_wifi"
BLE_ACTION_RETRY_SCAN = "retry_ble_scan"
BLE_ACTION_CONTINUE_PAIRING = "continue_to_pairing"
DISCOVERY_CLIENT_FIELD = "discovered_client"
DISCOVERY_PAIRING_INFO_ERROR = "pairing_info_unavailable"
APP_PAIR_CODE_DISPLAY_FIELD = "app_pair_code"
APP_HA_LOCAL_URL_DISPLAY_FIELD = "app_ha_local_url"
APP_IPHONE_PAIRING_URI_FIELD = "app_iphone_pairing_uri"
APP_WATCH_PAIRING_URI_FIELD = "app_watch_pairing_uri"
APP_PAIR_CODE_DIGITS = 6
APP_PAIRING_PENDING_KEY = "config_flow_app_pairing_pending"
BLE_DISCOVERY_TIMEOUT = 5
BLE_PROVISION_TIMEOUT = 25
SETUP_METHOD_NAMES_EN = {
    SETUP_METHOD_CONVERSATION_AGENT: (
        "DJConnect DJ Assist-agent\n"
        "For Home Assistant Assist satellites"
    ),
    SETUP_METHOD_PAIR_LOCAL_DEVICE: (
        "Pair DJConnect device ESP32 or Raspberry Pi"
    ),
    SETUP_METHOD_PAIR_APP: (
        "Pair DJConnect app\n"
        "iPhone/iPad, Apple Watch, macOS or Windows"
    ),
    SETUP_METHOD_BLE_WIFI: "Configure ESP32 device WiFi (over Bluetooth)",
}
SETUP_METHOD_NAMES_NL = {
    SETUP_METHOD_CONVERSATION_AGENT: (
        "DJConnect DJ Assist-agent\n"
        "Voor Home Assistant Assist-satellites"
    ),
    SETUP_METHOD_PAIR_LOCAL_DEVICE: (
        "DJConnect apparaat koppelen ESP32 of Raspberry Pi"
    ),
    SETUP_METHOD_PAIR_APP: (
        "DJConnect app koppelen\n"
        "iPhone/iPad, Apple Watch, macOS of Windows"
    ),
    SETUP_METHOD_BLE_WIFI: "ESP32 apparaat WiFi configureren (via Bluetooth)",
}
BLE_ACTION_NAMES_EN = {
    BLE_ACTION_PROVISION: "Write WiFi over Bluetooth",
    BLE_ACTION_RETRY_SCAN: "Rescan Bluetooth devices",
    BLE_ACTION_CONTINUE_PAIRING: "Continue to pairing",
}
BLE_ACTION_NAMES_NL = {
    BLE_ACTION_PROVISION: "WiFi via Bluetooth schrijven",
    BLE_ACTION_RETRY_SCAN: "Bluetooth apparaten opnieuw scannen",
    BLE_ACTION_CONTINUE_PAIRING: "Doorgaan naar koppelen",
}
OPTIONS_ACTION_NAMES_EN = {
    OPTIONS_ACTION_SAVE: "Save settings",
    OPTIONS_ACTION_SPOTIFY_REAUTH: "Reauthorize Spotify",
    OPTIONS_ACTION_CHANGE_MUSIC_BACKEND: "Change music backend",
    OPTIONS_ACTION_RETRY_PAIRING: "Retry pairing with current code",
    OPTIONS_ACTION_REPAIR: "Re-pair with new pairing code",
}
OPTIONS_ACTION_NAMES_NL = {
    OPTIONS_ACTION_SAVE: "Instellingen opslaan",
    OPTIONS_ACTION_SPOTIFY_REAUTH: "Spotify opnieuw autoriseren",
    OPTIONS_ACTION_CHANGE_MUSIC_BACKEND: "Muziekbackend wijzigen",
    OPTIONS_ACTION_RETRY_PAIRING: "Koppelen opnieuw proberen met huidige code",
    OPTIONS_ACTION_REPAIR: "Opnieuw koppelen met nieuwe koppelcode",
}
CLIENT_TYPE_NAME_SUFFIXES = {
    CLIENT_TYPE_ESP32: "ESP32",
    "ios": "iOS",
    "macos": "macOS",
    "watchos": "Watch",
    "raspberry_pi": "Raspberry Pi",
    "windows": "Windows",
    CLIENT_TYPE_CONVERSATION_AGENT: "Assist",
}

VOICE_FORM_FIELDS = {
    CONF_ASSIST_PIPELINE_ID,
    CONF_FIRMWARE_CHANNEL,
    CONF_VOICE_PROFILE,
}


def _bool(value: Any, default: bool = False) -> bool:
    return default if value is None else bool(value)


def _int(value: Any, default: int) -> int:
    try:
        return int(_clean(value, default))
    except (TypeError, ValueError):
        return default


def _defaultable_value(
    source: dict[str, Any],
    key: str,
    default: Any,
    *,
    preserve_empty: bool,
) -> Any:
    """Return an option value while preserving explicit empty `Default` choices."""
    if preserve_empty and key in source and source.get(key) in (None, ""):
        return ""
    return _clean(source.get(key), default)


def _ha_device_language(hass: Any) -> str:
    """Return supported device UI language from the current HA language."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    return "nl" if language.startswith("nl") else DEFAULT_DEVICE_LANGUAGE


def _setup_method_names(hass: Any) -> dict[str, str]:
    """Return setup method labels in the current Home Assistant language."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    return SETUP_METHOD_NAMES_NL if language.startswith("nl") else SETUP_METHOD_NAMES_EN


def _ble_action_names(hass: Any) -> dict[str, str]:
    """Return mutually exclusive BLE setup actions in the current HA language."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    return BLE_ACTION_NAMES_NL if language.startswith("nl") else BLE_ACTION_NAMES_EN


def _options_action_names(hass: Any) -> dict[str, str]:
    """Return options flow actions in the current HA language."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    return OPTIONS_ACTION_NAMES_NL if language.startswith("nl") else OPTIONS_ACTION_NAMES_EN


def _ha_language(hass: Any) -> str:
    """Return the current Home Assistant UI language."""
    return str(getattr(getattr(hass, "config", None), "language", "") or "")


def _options_actions_for_status(hass: Any, defaults: dict[str, Any]) -> dict[str, str]:
    """Return visible options actions for the current pairing state."""
    actions = dict(_options_action_names(hass))
    if defaults.get(CONF_MUSIC_BACKEND) == MUSIC_BACKEND_MUSIC_ASSISTANT:
        actions.pop(OPTIONS_ACTION_SPOTIFY_REAUTH, None)
    pairing_status = str(defaults.get("ha_pairing_status") or "").strip().lower()
    if pairing_status not in {"pending", "stale", "invalid", "unpaired"}:
        actions.pop(OPTIONS_ACTION_RETRY_PAIRING, None)
    return actions


def _conversation_agent_options_actions(hass: Any, defaults: dict[str, Any]) -> dict[str, str]:
    """Return actions relevant for DJConnect as an Assist conversation agent."""
    names = _options_action_names(hass)
    actions = {
        OPTIONS_ACTION_SAVE: names[OPTIONS_ACTION_SAVE],
        OPTIONS_ACTION_CHANGE_MUSIC_BACKEND: names[OPTIONS_ACTION_CHANGE_MUSIC_BACKEND],
    }
    if defaults.get(CONF_MUSIC_BACKEND, DEFAULT_MUSIC_BACKEND) != MUSIC_BACKEND_MUSIC_ASSISTANT:
        actions[OPTIONS_ACTION_SPOTIFY_REAUTH] = names[OPTIONS_ACTION_SPOTIFY_REAUTH]
    return actions


def _default_options_action(options_actions: dict[str, str]) -> str:
    """Return the first visible options action."""
    return next(iter(options_actions), OPTIONS_ACTION_CHANGE_MUSIC_BACKEND)


def _generate_pair_code() -> str:
    """Return a short numeric pairing code generated by Home Assistant."""
    return f"{secrets.randbelow(10 ** APP_PAIR_CODE_DIGITS):0{APP_PAIR_CODE_DIGITS}d}"


def _build_pairing_uri(ha_url: str, pair_code: str, client_type: str) -> str:
    """Return the app QR/deep-link payload for inbound-only clients."""
    query = urlencode(
        {
            "ha_url": str(ha_url or "").rstrip("/"),
            "pair_code": pair_code,
            "client_type": client_type,
            "pair_path": API_PAIR,
        }
    )
    return f"djconnect://pair?{query}"


def _qr_svg_data_uri(value: str) -> str:
    """Return an inline SVG QR code data URI for a pairing payload."""
    payload = str(value or "").strip()
    if not payload:
        return ""
    try:
        import segno  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return ""
    try:
        out = BytesIO()
        segno.make(payload, error="m").save(
            out,
            kind="svg",
            scale=4,
            border=2,
            xmldecl=False,
            svgns=True,
        )
        svg = out.getvalue().decode("utf-8")
        if "<svg" in svg and "<rect" not in svg:
            insert_at = svg.find(">")
            if insert_at != -1:
                svg = (
                    svg[: insert_at + 1]
                    + '<rect width="100%" height="100%" fill="white"/>'
                    + svg[insert_at + 1 :]
                )
        return f"data:image/svg+xml;utf8,{quote(svg)}"
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not generate app pairing QR code: %s", exc)
        return ""


def _central_api_install_id(current: dict[str, Any]) -> str:
    value = str(current.get(CONF_HA_INSTALL_ID) or "").strip()
    return value or f"ha_{secrets.token_urlsafe(24)}"


def _valid_install_token(value: Any) -> bool:
    token = str(value or "").strip()
    return token.startswith(TOKEN_PREFIX) and len(token) > len(TOKEN_PREFIX)


def _password_selector() -> Any:
    text_selector = getattr(selector, "TextSelector", None)
    text_config = getattr(selector, "TextSelectorConfig", None)
    text_type = getattr(selector, "TextSelectorType", None)
    if text_selector and text_config and text_type:
        try:
            return text_selector(text_config(type=text_type.PASSWORD))
        except Exception:  # noqa: BLE001
            pass
    return str


def _manual_discovery_label(hass: Any) -> str:
    """Return the manual-entry label in the current Home Assistant language."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    if language.startswith("nl"):
        return "Handmatig invoeren"
    if language.startswith("de"):
        return "Manuell eingeben"
    if language.startswith("fr"):
        return "Saisie manuelle"
    if language.startswith("es"):
        return "Entrada manual"
    return "Manual entry"


def _device_name_for_client_type(client_type: Any, base_name: Any = DEFAULT_DEVICE_NAME) -> str:
    """Return the suggested HA device name with a client-type suffix."""
    return device_name_for_client_type(
        client_type,
        base_name,
        suffixes=CLIENT_TYPE_NAME_SUFFIXES,
    )


def _spotify_oauth_title(hass: Any, *, reauth: bool = False) -> str:
    """Return a localized title for Home Assistant external OAuth steps."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    if language.startswith("nl"):
        return "Spotify opnieuw autoriseren" if reauth else "DJConnect autoriseren bij Spotify"
    if language.startswith("de"):
        return "Spotify erneut autorisieren" if reauth else "DJConnect bei Spotify autorisieren"
    if language.startswith("fr"):
        return "Réautoriser Spotify" if reauth else "Autoriser DJConnect avec Spotify"
    if language.startswith("es"):
        return "Reautorizar Spotify" if reauth else "Autorizar DJConnect con Spotify"
    return "Reauthorize Spotify" if reauth else "Authorize DJConnect with Spotify"


def _spotify_oauth_description(hass: Any, *, reauth: bool = False) -> str:
    """Return localized body text for Home Assistant external OAuth popups."""
    language = str(getattr(getattr(hass, "config", None), "language", "") or "").lower()
    if language.startswith("nl"):
        if reauth:
            return (
                "Home Assistant opent Spotify om DJConnect opnieuw toestemming te geven. "
                "Na akkoord keer je terug naar Home Assistant."
            )
        return (
            "Home Assistant opent Spotify in je browser. "
            "Na akkoord ga je terug naar Home Assistant om de setup af te maken."
        )
    if language.startswith("de"):
        if reauth:
            return (
                "Home Assistant öffnet Spotify, damit DJConnect erneut autorisiert werden kann. "
                "Nach der Zustimmung kehrst du zu Home Assistant zurück."
            )
        return (
            "Home Assistant öffnet Spotify in deinem Browser. "
            "Kehre nach der Zustimmung hierher zurück, um die Einrichtung fortzusetzen."
        )
    if language.startswith("fr"):
        if reauth:
            return (
                "Home Assistant ouvre Spotify afin de réautoriser DJConnect. "
                "Après validation, reviens dans Home Assistant."
            )
        return (
            "Home Assistant ouvre Spotify dans ton navigateur. "
            "Après validation, reviens ici pour continuer la configuration."
        )
    if language.startswith("es"):
        if reauth:
            return (
                "Home Assistant abre Spotify para autorizar DJConnect de nuevo. "
                "Después de aprobarlo, vuelve a Home Assistant."
            )
        return (
            "Home Assistant abre Spotify en tu navegador. "
            "Después de aprobar el acceso, vuelve aquí para continuar la configuración."
        )
    if reauth:
        return (
            "Home Assistant opens Spotify so DJConnect can be authorized again. "
            "After approval you return to Home Assistant."
        )
    return (
        "Home Assistant opens Spotify in your browser. "
        "After approving access, return here to continue setup."
    )


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _options_with_current(options: dict[str, str], current: Any = "") -> dict[str, str]:
    """Keep stored free-text values selectable after switching to dropdowns."""
    value = _clean(current, "")
    merged = dict(options)
    if value and value not in merged:
        merged[value] = str(value)
    return merged


def _state_attributes(hass: Any, entity_id: str) -> dict[str, Any]:
    states = getattr(hass, "states", None)
    if not entity_id or not states or not hasattr(states, "get"):
        return {}
    state = states.get(entity_id)
    return getattr(state, "attributes", {}) or {}


def _entity_options(
    hass: Any,
    domain: str,
    current: Any = "",
    *,
    include_empty: bool = True,
) -> dict[str, str]:
    """Return HA entity IDs as dropdown options."""
    options: dict[str, str] = {"": "Default"} if include_empty else {}
    states = getattr(hass, "states", None)
    if states and hasattr(states, "async_entity_ids"):
        try:
            for entity_id in sorted(states.async_entity_ids(domain)):
                state = states.get(entity_id) if hasattr(states, "get") else None
                name = getattr(state, "name", None) or entity_id
                options[entity_id] = f"{name} ({entity_id})"
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Could not list %s entities for DJConnect config flow",
                domain,
                exc_info=True,
            )
    return _options_with_current(options, current)


def _ble_wifi_schema(devices: dict[str, str], hass: Any = None) -> dict[Any, Any]:
    """Build BLE WiFi provisioning fields with discovered devices when present."""
    device_validator = vol.In({"": "Select device", **devices}) if devices else str
    default_device = next(iter(devices), "") if len(devices) == 1 else ""
    return {
        vol.Required(BLE_ACTION_FIELD, default=BLE_ACTION_PROVISION): vol.In(
            _ble_action_names(hass)
        ),
        vol.Optional(CONF_BLE_ADDRESS, default=default_device): device_validator,
        vol.Optional(CONF_WIFI_SSID, default=""): str,
        vol.Optional(CONF_WIFI_PASSWORD, default=""): str,
    }


async def _discover_ble_devices_safe(hass: Any) -> dict[str, str]:
    """Discover setup devices without letting Bluetooth stall the config flow."""
    try:
        return await asyncio.wait_for(
            async_discover_devices(hass),
            timeout=BLE_DISCOVERY_TIMEOUT,
        )
    except TimeoutError:
        _LOGGER.warning("DJConnect BLE discovery timed out; allowing manual address entry")
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("DJConnect BLE discovery failed: %s", exc)
    return {}


async def _provision_ble_wifi_safe(
    hass: Any,
    address: str,
    ssid: str,
    password: str,
) -> dict[str, Any]:
    """Write WiFi credentials with a hard timeout so setup can continue."""
    try:
        return await asyncio.wait_for(
            async_provision_wifi(hass, address, ssid, password),
            timeout=BLE_PROVISION_TIMEOUT,
        )
    except TimeoutError as exc:
        raise RuntimeError(
            "Bluetooth WiFi provisioning timed out. Put the device back in setup "
            "mode or use normal WiFi pairing."
        ) from exc


def _spotify_schema() -> dict[Any, Any]:
    """Build Spotify OAuth fields."""
    return _spotify_schema_with_defaults()


def _backend_schema(default_backend: str = DEFAULT_MUSIC_BACKEND) -> dict[Any, Any]:
    """Build the hard backend choice schema."""
    return {
        vol.Required(CONF_MUSIC_BACKEND, default=default_backend): vol.In(
            MUSIC_BACKEND_NAMES
        )
    }


def _music_assistant_schema(
    players: dict[str, str],
    default_player: str = "",
) -> dict[Any, Any]:
    """Build Music Assistant target player fields."""
    return {
        vol.Required(
            CONF_MUSIC_ASSISTANT_PLAYER,
            default=default_player or next(iter(players), ""),
        ): vol.In(players)
    }


def _music_assistant_available(hass: Any) -> bool:
    """Return whether Music Assistant appears configured in Home Assistant."""
    data = getattr(hass, "data", {}) if hass is not None else {}
    if isinstance(data, dict) and any(key in data for key in ("music_assistant", "mass")):
        return True
    return bool(_music_assistant_players(hass))


def _music_assistant_players(hass: Any) -> dict[str, str]:
    """Return usable Music Assistant media_player entities."""
    players: dict[str, str] = {}
    states = getattr(hass, "states", None)
    entity_ids = []
    if states and hasattr(states, "async_entity_ids"):
        try:
            entity_ids = list(states.async_entity_ids("media_player"))
        except Exception:  # noqa: BLE001
            entity_ids = []
    for entity_id in sorted(entity_ids):
        state = states.get(entity_id) if hasattr(states, "get") else None
        attrs = getattr(state, "attributes", {}) or {}
        integration = str(
            attrs.get("integration")
            or attrs.get("platform")
            or attrs.get("source")
            or attrs.get("mass_player_type")
            or ""
        ).lower()
        if (
            "music_assistant" in integration
            or "mass" in integration
            or attrs.get("mass_player_type")
            or attrs.get("music_assistant_player")
        ):
            players[entity_id] = attrs.get("friendly_name") or entity_id
    data = getattr(hass, "data", {}) if hass is not None else {}
    if isinstance(data, dict):
        for key in ("music_assistant_players", "mass_players"):
            value = data.get(key)
            if isinstance(value, dict):
                for entity_id, label in value.items():
                    players[str(entity_id)] = str(label or entity_id)
    return players


def _validate_music_assistant_player(hass: Any, entity_id: Any) -> str | None:
    """Return a field error when the selected Music Assistant player is invalid."""
    player = str(entity_id or "").strip()
    if not player:
        return "music_assistant_player_missing"
    if "." not in player:
        return "music_assistant_player_invalid"
    domain, _, object_id = player.partition(".")
    if domain != "media_player" or not object_id:
        return "music_assistant_player_invalid"
    states = getattr(hass, "states", None)
    state = states.get(player) if states and hasattr(states, "get") else None
    if state is None:
        return "music_assistant_player_not_found"
    attrs = getattr(state, "attributes", {}) or {}
    integration = str(
        attrs.get("integration")
        or attrs.get("platform")
        or attrs.get("source")
        or attrs.get("mass_player_type")
        or ""
    ).lower()
    if not (
        "music_assistant" in integration
        or "mass" in integration
        or attrs.get("mass_player_type")
        or attrs.get("music_assistant_player")
    ):
        return "music_assistant_player_not_music_assistant"
    return None


def _spotify_schema_with_defaults(
    *,
    external_url: str = "",
    client_id: str = "",
) -> dict[Any, Any]:
    """Build Spotify OAuth fields."""
    schema: dict[Any, Any] = {
        vol.Required(CONF_SPOTIFY_CLIENT_ID, default=client_id): str,
        vol.Required(CONF_HA_EXTERNAL_URL, default=external_url): str,
    }
    return schema


async def _async_default_external_url(hass: Any) -> str:
    """Return HA's configured external URL when available."""
    url = await _async_network_external_url(hass)
    if not url:
        url = await _async_cloud_external_url(hass)
    if not url:
        url = await _async_configured_external_url(hass)
    return url.strip().rstrip("/")


async def _async_network_external_url(hass: Any) -> str:
    """Return HA Network external URL, preferring Nabu Casa Cloud when available."""
    try:
        from homeassistant.helpers import network

        get_url = getattr(network, "async_get_url", None) or getattr(network, "get_url", None)
        if get_url is None:
            return ""
        kwargs = {
            "prefer_external": True,
            "prefer_cloud": True,
            "allow_internal": False,
            "allow_external": True,
            "allow_cloud": True,
            "require_ssl": True,
        }
        try:
            url = await _async_maybe_await(get_url(hass, **kwargs))
        except TypeError:
            kwargs.pop("prefer_cloud", None)
            url = await _async_maybe_await(get_url(hass, **kwargs))
        return str(url or "")
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not read Home Assistant Network external URL", exc_info=True)
    return ""


async def _async_cloud_external_url(hass: Any) -> str:
    """Return the Home Assistant Cloud remote UI URL when exposed by HA."""
    try:
        from homeassistant.components import cloud

        remote_url = getattr(cloud, "async_remote_ui_url", None)
        if remote_url is not None:
            return str(await _async_maybe_await(remote_url(hass)) or "")
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not read Home Assistant Cloud URL", exc_info=True)
    cloud_data = getattr(hass, "data", {}).get("cloud") if hasattr(hass, "data") else None
    for attr in ("remote_ui_url", "remote_url", "url"):
        value = getattr(cloud_data, attr, "")
        if callable(value):
            try:
                value = value()
            except Exception:  # noqa: BLE001
                value = ""
        if value:
            return str(value)
    return ""


async def _async_maybe_await(value: Any) -> Any:
    """Await HA helper results only when the helper is asynchronous."""
    if inspect.isawaitable(value):
        return await value
    return value


async def _async_configured_external_url(hass: Any) -> str:
    """Return external URL from HA config objects across supported versions."""
    config = getattr(hass, "config", None)
    candidates = [
        getattr(config, "external_url", ""),
        getattr(getattr(config, "api", None), "external_url", ""),
    ]
    for getter_name in ("get_external_url", "async_get_external_url"):
        getter = getattr(config, getter_name, None)
        if callable(getter):
            try:
                value = getter()
                candidates.append(await _async_maybe_await(value))
            except Exception:  # noqa: BLE001
                _LOGGER.debug("DJConnect could not read %s", getter_name, exc_info=True)
    data = getattr(hass, "data", {}) if hass is not None else {}
    if isinstance(data, dict):
        for key in ("external_url", "ha_external_url"):
            candidates.append(data.get(key, ""))
    for value in candidates:
        if value:
            return str(value)
    return ""


def _voice_name(voice: Any) -> tuple[str, str] | None:
    """Normalize HA TTS voice objects into value/label pairs."""
    if isinstance(voice, str):
        return (voice, voice) if voice else None
    if isinstance(voice, dict):
        voice_id = voice.get("voice_id") or voice.get("id") or voice.get("name")
        voice_name = voice.get("name") or voice_id
    else:
        voice_id = (
            getattr(voice, "voice_id", None)
            or getattr(voice, "id", None)
            or getattr(voice, "name", None)
        )
        voice_name = getattr(voice, "name", None) or voice_id
    return (str(voice_id), str(voice_name)) if voice_id else None


def _get_assist_pipelines(hass: Any) -> list[Any]:
    """Return Assist pipelines when HA exposes them."""
    try:
        from homeassistant.components.assist_pipeline.pipeline import async_get_pipelines

        pipelines = async_get_pipelines(hass)
        if isinstance(pipelines, dict):
            return list(pipelines.values())
        if isinstance(pipelines, (list, tuple, set)):
            return list(pipelines)
        listed = getattr(pipelines, "async_get_pipelines", None)
        if callable(listed):
            values = listed()
            if isinstance(values, dict):
                return list(values.values())
            return list(values or [])
        stored = getattr(pipelines, "pipelines", None)
        if isinstance(stored, dict):
            return list(stored.values())
        if isinstance(stored, (list, tuple, set)):
            return list(stored)
        preferred = getattr(pipelines, "async_get_preferred_pipeline", None)
        if callable(preferred):
            pipeline = preferred()
            return [pipeline] if pipeline is not None else []
        return list(pipelines)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not list Assist pipelines", exc_info=True)
        return []


def _get_assist_pipeline(hass: Any, pipeline_id: str) -> Any | None:
    if not pipeline_id:
        return None
    return next(
        (
            pipeline
            for pipeline in _get_assist_pipelines(hass)
            if getattr(pipeline, "id", None) == pipeline_id
        ),
        None,
    )


async def _assist_pipeline_options(hass: Any, current: Any = "") -> dict[str, str]:
    """Return Assist pipeline IDs as dropdown options."""
    options = {"": "Default"}
    for pipeline in _get_assist_pipelines(hass):
        pipeline_id = getattr(pipeline, "id", "")
        if pipeline_id:
            options[pipeline_id] = getattr(pipeline, "name", "") or pipeline_id
    return _options_with_current(options, current)


def _assist_pipeline_has_stt_tts(pipeline: Any) -> bool:
    """Return true when an Assist pipeline can handle both voice directions."""
    stt_engine = str(getattr(pipeline, "stt_engine", "") or "").strip()
    tts_engine = str(getattr(pipeline, "tts_engine", "") or "").strip()
    return bool(stt_engine and tts_engine)


def _has_valid_assist_pipeline(hass: Any) -> bool:
    """Return whether HA has at least one Assist pipeline with STT and TTS."""
    return any(
        _assist_pipeline_has_stt_tts(pipeline)
        for pipeline in _get_assist_pipelines(hass)
    )


def _base_voice_schema(
    hass: Any,
    defaults: dict[str, Any],
    *,
    assist_options: dict[str, str],
    options_actions: dict[str, str] | None = None,
    readonly_local_url: str | None = None,
) -> dict[Any, Any]:
    """Build the non-advanced voice settings schema."""
    schema: dict[Any, Any] = {}
    if options_actions is not None:
        schema[
            vol.Required(
                OPTIONS_ACTION_FIELD,
                default=_default_options_action(options_actions),
            )
        ] = vol.In(options_actions)
    if readonly_local_url is not None:
        label = readonly_local_url or "Not configured"
        schema[vol.Optional(CONF_LOCAL_URL, default=readonly_local_url)] = vol.In(
            {readonly_local_url: label}
        )
    schema.update({
        vol.Optional(
            CONF_VOICE_PROFILE,
            default=normalize_voice_profile(defaults.get(CONF_VOICE_PROFILE)),
        ): vol.In(voice_profile_options(_ha_language(hass))),
        vol.Optional(
            CONF_ASSIST_PIPELINE_ID,
            default=defaults.get(CONF_ASSIST_PIPELINE_ID, ""),
        ): vol.In(assist_options),
    })
    if defaults.get(CONF_CLIENT_TYPE, DEFAULT_CLIENT_TYPE) == CLIENT_TYPE_ESP32:
        schema[
            vol.Optional(
                CONF_FIRMWARE_CHANNEL,
                default=defaults.get(CONF_FIRMWARE_CHANNEL, DEFAULT_FIRMWARE_CHANNEL),
            )
        ] = _firmware_channel_selector()
    return schema


def _firmware_channel_selector() -> Any:
    """Return a labeled firmware channel selector when HA exposes selector helpers."""
    select_selector = getattr(selector, "SelectSelector", None)
    select_config = getattr(selector, "SelectSelectorConfig", None)
    select_option = getattr(selector, "SelectOptionDict", None)
    if select_selector and select_config and select_option:
        return select_selector(
            select_config(
                options=[
                    select_option(value="stable", label="Stable"),
                    select_option(value="beta", label="Beta"),
                ]
            )
        )
    return vol.In(FIRMWARE_CHANNELS)


def _conversation_agent_options_schema(
    hass: Any,
    defaults: dict[str, Any],
) -> vol.Schema:
    """Build the compact options schema used from Assist conversation agent settings."""
    actions = _conversation_agent_options_actions(hass, defaults)
    schema: dict[Any, Any] = {
        vol.Optional(
            CONF_VOICE_PROFILE,
            default=normalize_voice_profile(defaults.get(CONF_VOICE_PROFILE)),
        ): vol.In(voice_profile_options(_ha_language(hass))),
        vol.Required(
            OPTIONS_ACTION_FIELD,
            default=_default_options_action(actions),
        ): vol.In(actions),
    }
    return vol.Schema(schema)


def _music_backend_switch_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the explicit backend switch schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MUSIC_BACKEND,
                default=defaults.get(CONF_MUSIC_BACKEND, DEFAULT_MUSIC_BACKEND),
            ): vol.In(MUSIC_BACKEND_NAMES),
        }
    )


def _conversation_agent_voice_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the compact setup schema used for Assist conversation agent entries."""
    return vol.Schema({})


def _central_api_schema(current: dict[str, Any]) -> vol.Schema:
    """Build the central DJConnect API token options schema."""
    install_id = _central_api_install_id(current)
    token = str(current.get(CONF_DJCONNECT_INSTALL_TOKEN) or "").strip()
    schema: dict[Any, Any] = {
        vol.Optional(
            CONF_API_BASE_URL,
            default=str(current.get(CONF_API_BASE_URL) or DEFAULT_API_BASE_URL),
        ): str,
        vol.Optional(CONF_HA_INSTALL_ID, default=install_id): vol.In({install_id: install_id}),
        vol.Optional(CONF_DJCONNECT_INSTALL_TOKEN, default=token): _password_selector(),
        vol.Optional(OPTIONS_ACTION_FIELD, default=OPTIONS_ACTION_SAVE): vol.In(
            {
                OPTIONS_ACTION_SAVE: "Save token",
                OPTIONS_ACTION_ROTATE_INSTALL_TOKEN: "Rotate token",
            }
        ),
    }
    return vol.Schema(schema)


def _central_api_errors(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate central DJConnect API settings."""
    errors: dict[str, str] = {}
    base_url = str(user_input.get(CONF_API_BASE_URL) or "").strip()
    if not _is_https_url(base_url):
        errors[CONF_API_BASE_URL] = "central_api_url_invalid"
    token = str(user_input.get(CONF_DJCONNECT_INSTALL_TOKEN) or "").strip()
    if not _valid_install_token(token):
        errors[CONF_DJCONNECT_INSTALL_TOKEN] = "install_token_invalid"
    return errors


async def _voice_schema(
    hass: Any,
    defaults: dict[str, Any],
    *,
    include_options_action: bool = False,
    include_readonly_local_url: bool = False,
) -> vol.Schema:
    """Build a voice/options schema with dropdowns where HA can provide choices."""
    schema = _base_voice_schema(
        hass,
        defaults,
        assist_options=await _assist_pipeline_options(
            hass,
            defaults.get(CONF_ASSIST_PIPELINE_ID, ""),
        ),
        options_actions=(
            _options_actions_for_status(hass, defaults)
            if include_options_action
            else None
        ),
        readonly_local_url=(
            str(defaults.get(CONF_LOCAL_URL) or "")
            if include_readonly_local_url
            else None
        ),
    )
    return vol.Schema(schema)


def _voice_defaults(
    data: dict[str, Any] | None = None,
    *,
    preserve_empty: bool = False,
) -> dict[str, Any]:
    """Return voice/options config with safe defaults."""
    source = data or {}
    return {
        CONF_ASSIST_PIPELINE_ID: _defaultable_value(
            source,
            CONF_ASSIST_PIPELINE_ID,
            DEFAULT_ASSIST_PIPELINE_ID,
            preserve_empty=preserve_empty,
        ),
        CONF_DJ_RESPONSE_ENABLED: _bool(
            source.get(CONF_DJ_RESPONSE_ENABLED),
            DEFAULT_DJ_RESPONSE_ENABLED,
        ),
        CONF_DJ_RESPONSE_TTL_SECONDS: _int(
            source.get(CONF_DJ_RESPONSE_TTL_SECONDS),
            DEFAULT_DJ_RESPONSE_TTL_SECONDS,
        ),
        CONF_DJ_RESPONSE_PROMPT: DEFAULT_DJ_RESPONSE_PROMPT,
        CONF_VOICE_PROFILE: normalize_voice_profile(
            source.get(CONF_VOICE_PROFILE) or DEFAULT_VOICE_PROFILE
        ),
        CONF_MAX_AUDIO_BYTES: _int(
            source.get(CONF_MAX_AUDIO_BYTES),
            DEFAULT_MAX_AUDIO_BYTES,
        ),
        CONF_ALLOW_OTA_ON_BATTERY: _bool(source.get(CONF_ALLOW_OTA_ON_BATTERY), True),
        CONF_MIN_BATTERY_FOR_OTA: _int(
            source.get(CONF_MIN_BATTERY_FOR_OTA),
            DEFAULT_MIN_BATTERY_FOR_OTA,
        ),
        CONF_FIRMWARE_CHANNEL: _firmware_channel_default(
            source.get(CONF_FIRMWARE_CHANNEL),
        ),
    }


def _voice_form_values(source: dict[str, Any]) -> dict[str, Any]:
    """Return only voice fields intentionally exposed in config/options forms."""
    return {key: source[key] for key in VOICE_FORM_FIELDS if key in source}


def _voice_defaults_for_client(
    source: dict[str, Any] | None = None,
    *,
    client_type: Any = DEFAULT_CLIENT_TYPE,
    preserve_empty: bool = False,
) -> dict[str, Any]:
    """Return voice defaults, omitting ESP32-only settings for app clients."""
    defaults = _voice_defaults(source, preserve_empty=preserve_empty)
    if client_type != CLIENT_TYPE_ESP32:
        defaults.pop(CONF_FIRMWARE_CHANNEL, None)
    return defaults


def _firmware_channel_default(value: Any) -> str:
    channel = str(value or DEFAULT_FIRMWARE_CHANNEL).strip().lower()
    return "beta" if channel == "beta" else DEFAULT_FIRMWARE_CHANNEL


def _voice_errors(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate required voice/options fields."""
    profile = user_input.get(CONF_VOICE_PROFILE)
    if profile is not None and normalize_voice_profile(profile) != profile:
        return {CONF_VOICE_PROFILE: "invalid_voice_profile"}
    return {}


def _spotify_direct_ready(current: dict[str, Any]) -> bool:
    """Return whether Spotify Direct has enough stored OAuth config to become active."""
    return bool(
        str(current.get(CONF_SPOTIFY_CLIENT_ID) or "").strip()
        and str(current.get(CONF_SPOTIFY_REFRESH_TOKEN) or "").strip()
    )


def _current_backend_revision(current: dict[str, Any]) -> int:
    try:
        return max(0, int(current.get(CONF_MUSIC_BACKEND_REVISION) or 0))
    except (TypeError, ValueError):
        return 0


def _next_backend_revision(current: dict[str, Any]) -> int:
    return _current_backend_revision(current) + 1


def _mark_backend_specific_pending_state_stale(runtime: Any, revision: int) -> None:
    """Mark backend-specific pending playback state stale after a backend switch."""
    status = getattr(runtime, "device_status", None)
    if isinstance(status, dict):
        status["music_backend_actions_stale"] = True
        status["music_backend_actions_stale_after_revision"] = revision
    memory = getattr(runtime, "memory", None)
    store = getattr(memory, "_data", None)
    memories = store.get("memories") if isinstance(store, dict) else None
    if isinstance(memories, dict):
        for item in memories.values():
            if not isinstance(item, dict):
                continue
            pending = item.get("pending_followup")
            if isinstance(pending, dict) and not pending.get("handled"):
                pending["handled"] = True
                pending["stale"] = True
                pending["stale_reason"] = "music_backend_changed"


async def _async_pair_before_create(hass: Any, data: dict[str, Any]) -> None:
    """Pair the ESP before HA creates a successful config entry."""
    from custom_components.djconnect import DJConnectRuntime

    entry = SimpleNamespace(
        entry_id="config-flow-pairing",
        data=data,
        options={},
    )
    runtime = DJConnectRuntime(entry=entry)
    runtime.device_token = data.get(CONF_DEVICE_TOKEN)
    runtime.pairing_code = data.get(CONF_PAIR_CODE)
    runtime.pairing_device_id = data.get(CONF_DEVICE_ID)
    if data.get(CONF_DEVICE_ID):
        runtime.device_status["device_id"] = data[CONF_DEVICE_ID]
    if data.get(CONF_LOCAL_URL):
        runtime.device_status["local_url"] = data[CONF_LOCAL_URL]

    await runtime.pair_device(hass)

    data[CONF_DEVICE_TOKEN] = runtime.device_token
    real_device_id = runtime.device_status.get("device_id") or runtime.pairing_device_id
    if real_device_id:
        data[CONF_DEVICE_ID] = real_device_id
    local_url = runtime.device_status.get("local_url")
    if local_url:
        data[CONF_LOCAL_URL] = local_url


class DJConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the DJConnect config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._pairing: dict[str, Any] = {}
        self._backend: dict[str, Any] = {CONF_MUSIC_BACKEND: DEFAULT_MUSIC_BACKEND}
        self._spotify: dict[str, Any] = {}
        self._oauth: dict[str, str] = {}
        self._discovery_checked = False
        self._discovered_clients: list[DiscoveredClient] = []
        self._discovered_defaults: dict[str, Any] = {}
        self._discovered_device_name_authoritative = False
        self._selected_discovered_key = ""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose setup path."""
        errors: dict[str, str] = {}
        if not _has_valid_assist_pipeline(getattr(self, "hass", None)):
            errors["base"] = "assist_pipeline_required"
        if errors:
            if user_input is not None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                CONF_SETUP_METHOD,
                                default=user_input.get(
                                    CONF_SETUP_METHOD,
                                    DEFAULT_SETUP_METHOD,
                                ),
                            ): vol.In(_setup_method_names(getattr(self, "hass", None))),
                        }
                    ),
                    errors=errors,
                    last_step=False,
                )
        if user_input is not None:
            method = user_input.get(CONF_SETUP_METHOD, DEFAULT_SETUP_METHOD)
            if method == SETUP_METHOD_BLE_WIFI:
                self._pairing_setup_method = SETUP_METHOD_PAIR_LOCAL_DEVICE
                return await self.async_step_ble_wifi()
            if method == SETUP_METHOD_CONVERSATION_AGENT:
                await self.async_set_unique_id("djconnect-conversation-agent")
                self._abort_if_unique_id_configured()
                self._pairing = {
                    CONF_SETUP_METHOD: SETUP_METHOD_CONVERSATION_AGENT,
                    CONF_DEVICE_ID: "djconnect-conversation-agent",
                    CONF_DEVICE_NAME: "DJConnect DJ",
                    CONF_CLIENT_TYPE: CLIENT_TYPE_CONVERSATION_AGENT,
                }
                self._conversation_agent_only = True
                return await self.async_step_backend()
            if method in {SETUP_METHOD_PAIR_LOCAL_DEVICE, SETUP_METHOD_PAIR_APP}:
                self._pairing_setup_method = method
            else:
                self._pairing_setup_method = SETUP_METHOD_PAIR_APP
            if self._pairing_setup_method == SETUP_METHOD_PAIR_LOCAL_DEVICE:
                return await self.async_step_pair_local_device()
            return await self.async_step_pair_app()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SETUP_METHOD,
                        default=DEFAULT_SETUP_METHOD,
                    ): vol.In(_setup_method_names(getattr(self, "hass", None))),
                }
            ),
            errors=errors,
            last_step=False,
        )

    async def async_step_ble_wifi(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Provision WiFi credentials to a DJConnect setup device over BLE."""
        errors: dict[str, str] = {}
        devices = await _discover_ble_devices_safe(self.hass)

        if user_input is not None:
            action = user_input.get(BLE_ACTION_FIELD, BLE_ACTION_PROVISION)
            if action == BLE_ACTION_CONTINUE_PAIRING:
                self._pairing_setup_method = SETUP_METHOD_PAIR_LOCAL_DEVICE
                return await self.async_step_pair()
            if action == BLE_ACTION_RETRY_SCAN:
                return await self.async_step_ble_wifi()
            address = str(user_input.get(CONF_BLE_ADDRESS, "")).strip()
            ssid = str(user_input.get(CONF_WIFI_SSID, "")).strip()
            password = str(user_input.get(CONF_WIFI_PASSWORD, ""))
            if not address:
                errors[CONF_BLE_ADDRESS] = "ble_device_required"
            elif not ssid:
                errors[CONF_WIFI_SSID] = "wifi_ssid_required"
            else:
                try:
                    status = await _provision_ble_wifi_safe(
                        self.hass,
                        address,
                        ssid,
                        password,
                    )
                    _LOGGER.debug(
                        "DJConnect BLE WiFi provisioning completed: %s",
                        status.get("state"),
                    )
                    return await self.async_step_pair_local_device()
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("DJConnect BLE WiFi provisioning failed: %s", exc)
                    errors["base"] = "ble_wifi_failed"

        return self.async_show_form(
            step_id="ble_wifi",
            data_schema=vol.Schema(_ble_wifi_schema(devices, getattr(self, "hass", None))),
            errors=errors,
            last_step=False,
        )

    async def async_step_pair(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Pair the DJConnect device using the displayed pair code."""
        errors: dict[str, str] = {}
        step_id = self._pair_details_step_id()
        is_app_pairing = (
            getattr(self, "_pairing_setup_method", "") == SETUP_METHOD_PAIR_APP
        )
        if not _has_valid_assist_pipeline(getattr(self, "hass", None)):
            return self.async_show_form(
                step_id=step_id,
                data_schema=vol.Schema(self._user_schema()),
                errors={"base": "assist_pipeline_required"},
                last_step=False,
            )

        if user_input is None:
            if is_app_pairing:
                await self._ensure_app_pairing_defaults()
            else:
                await self._ensure_mdns_discovery()
        else:
            discovered_key = str(user_input.get(DISCOVERY_CLIENT_FIELD) or "").strip()
            if not is_app_pairing and DISCOVERY_CLIENT_FIELD in user_input:
                if discovered_key and discovered_key != self._selected_discovered_key:
                    self._apply_discovered_client_key(discovered_key)
                    return await self.async_step_pair()
                if not discovered_key and self._selected_discovered_key:
                    self._selected_discovered_key = ""
                    self._discovered_defaults = {}
                    self._discovered_device_name_authoritative = False
                    return await self.async_step_pair()
            if is_app_pairing:
                await self._ensure_app_pairing_defaults()
            pair_code = str(
                (
                    self._discovered_defaults.get(CONF_PAIR_CODE)
                    if is_app_pairing
                    else user_input.get(CONF_PAIR_CODE, "")
                )
                or ""
            ).strip()
            self._last_pair_code = pair_code
            if not pair_code:
                errors[CONF_PAIR_CODE] = "missing_pair_code"
            elif not _valid_pair_code(pair_code):
                errors[CONF_PAIR_CODE] = "invalid_pair_code"
            else:
                defaults = getattr(self, "_discovered_defaults", {})
                client_type = _clean(
                    getattr(self, "_selected_pair_client_type", "")
                    or user_input.get(CONF_CLIENT_TYPE),
                    defaults.get(CONF_CLIENT_TYPE, self._default_pair_client_type()),
                )
                local_url = _clean(
                    user_input.get(CONF_LOCAL_URL),
                    _clean(defaults.get(CONF_LOCAL_URL), _default_local_url(pair_code)),
                )
                selected_client = self._selected_discovered_client()
                if (
                    selected_client is not None
                    and selected_client.pairing_info_failed
                    and str(local_url or "").strip() == selected_client.local_url
                ):
                    errors["base"] = DISCOVERY_PAIRING_INFO_ERROR
                    return self.async_show_form(
                        step_id=step_id,
                        data_schema=vol.Schema(self._user_schema()),
                        errors=errors,
                        last_step=False,
                    )
                device_id = str(defaults.get(CONF_DEVICE_ID) or "").strip()
                pending_app_pairing = (
                    self._pending_app_pairing(pair_code) if is_app_pairing else {}
                )
                if is_app_pairing and not pending_app_pairing:
                    errors["base"] = "app_pairing_not_received"
                    return self.async_show_form(
                        step_id=step_id,
                        data_schema=vol.Schema(self._user_schema()),
                        errors=errors,
                        description_placeholders=self._pair_description_placeholders(),
                        last_step=False,
                    )
                if pending_app_pairing:
                    device_id = str(pending_app_pairing.get(CONF_DEVICE_ID) or "").strip()
                    client_type = _clean(
                        pending_app_pairing.get(CONF_CLIENT_TYPE),
                        client_type,
                    )
                if not device_id or client_type == CLIENT_TYPE_ESP32:
                    device_id = f"djconnect-{pair_code}"
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                self._pairing = {
                    CONF_PAIR_CODE: pair_code,
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: _clean(
                        pending_app_pairing.get(CONF_DEVICE_NAME)
                        if pending_app_pairing
                        else user_input.get(CONF_DEVICE_NAME),
                        defaults.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME),
                    ),
                    CONF_CLIENT_TYPE: client_type,
                    CONF_DEVICE_TOKEN: str(
                        pending_app_pairing.get(CONF_DEVICE_TOKEN) or ""
                    )
                    or secrets.token_urlsafe(32),
                }
                if is_app_pairing:
                    pairing_uri = _build_pairing_uri(
                        str(defaults.get("ha_local_url") or ""),
                        pair_code,
                        str(client_type),
                    )
                    if pairing_uri:
                        self._pairing[CONF_PAIRING_URI] = pairing_uri
                if self._client_type_uses_local_device_api(client_type):
                    self._pairing[CONF_LOCAL_URL] = local_url
                if client_type == CLIENT_TYPE_ESP32:
                    self._pairing[CONF_DEVICE_LANGUAGE] = _ha_device_language(
                        getattr(self, "hass", None)
                    )
                if is_app_pairing:
                    self._clear_pending_app_pairing(pair_code)
                return await self.async_step_backend()

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(self._user_schema()),
            errors=errors,
            description_placeholders=self._pair_description_placeholders(),
            last_step=False,
        )

    def _pair_step_id(self) -> str:
        """Return the translated pair-step variant for the selected setup path."""
        setup_method = getattr(self, "_pairing_setup_method", "")
        if setup_method == SETUP_METHOD_PAIR_LOCAL_DEVICE:
            return "pair_local_device_type"
        if setup_method == SETUP_METHOD_PAIR_APP:
            return "pair_app_type"
        return "pair_type"

    def _pair_details_step_id(self) -> str:
        """Return the translated pair-details step for the selected setup path."""
        setup_method = getattr(self, "_pairing_setup_method", "")
        if setup_method == SETUP_METHOD_PAIR_LOCAL_DEVICE:
            return "pair_local_device_details"
        if setup_method == SETUP_METHOD_PAIR_APP:
            client_type = _clean(
                getattr(self, "_selected_pair_client_type", ""),
                self._default_pair_client_type(),
            )
            if client_type == CLIENT_TYPE_IOS:
                return "pair_app_ios_details"
            if client_type == CLIENT_TYPE_WATCHOS:
                return "pair_app_watch_details"
            if client_type == CLIENT_TYPE_MACOS:
                return "pair_app_macos_details"
            if client_type == CLIENT_TYPE_WINDOWS:
                return "pair_app_windows_details"
            return "pair_app_details"
        return "pair"

    async def async_step_pair_local_device(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose the local-device client type before pairing details."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_LOCAL_DEVICE
        return await self._async_step_pair_type(user_input)

    async def async_step_pair_local_device_type(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the translated local-device client type step."""
        return await self.async_step_pair_local_device(user_input)

    async def async_step_pair_local_device_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle local-device pairing details after client type selection."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_LOCAL_DEVICE
        return await self.async_step_pair(user_input)

    async def async_step_pair_app(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose the app client type before pairing details."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP
        return await self._async_step_pair_type(user_input)

    async def async_step_pair_app_type(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the translated app client type step."""
        return await self.async_step_pair_app(user_input)

    async def async_step_pair_app_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle app-client pairing details after client type selection."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP
        return await self.async_step_pair(user_input)

    async def async_step_pair_app_ios_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle iOS app pairing details after client type selection."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP
        self._selected_pair_client_type = CLIENT_TYPE_IOS
        return await self.async_step_pair(user_input)

    async def async_step_pair_app_watch_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Apple Watch app pairing details after client type selection."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP
        self._selected_pair_client_type = CLIENT_TYPE_WATCHOS
        return await self.async_step_pair(user_input)

    async def async_step_pair_app_macos_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle macOS app pairing details after client type selection."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP
        self._selected_pair_client_type = CLIENT_TYPE_MACOS
        return await self.async_step_pair(user_input)

    async def async_step_pair_app_windows_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle Windows app pairing details after client type selection."""
        self._pairing_setup_method = SETUP_METHOD_PAIR_APP
        self._selected_pair_client_type = CLIENT_TYPE_WINDOWS
        return await self.async_step_pair(user_input)

    async def _async_step_pair_type(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the client type choice before showing pairing details."""
        if user_input is not None:
            client_type = _clean(
                user_input.get(CONF_CLIENT_TYPE),
                self._default_pair_client_type(),
            )
            if client_type not in self._pair_client_type_options():
                client_type = self._default_pair_client_type()
            self._selected_pair_client_type = client_type
            defaults = dict(getattr(self, "_discovered_defaults", {}) or {})
            defaults[CONF_CLIENT_TYPE] = client_type
            defaults[CONF_DEVICE_NAME] = _device_name_for_client_type(
                client_type,
                DEFAULT_DEVICE_NAME,
            )
            self._discovered_defaults = defaults
            self._discovered_device_name_authoritative = False
            return await self.async_step_pair(user_input=None)

        return self.async_show_form(
            step_id=self._pair_step_id(),
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CLIENT_TYPE,
                        default=_clean(
                            getattr(self, "_selected_pair_client_type", ""),
                            self._default_pair_client_type(),
                        ),
                    ): vol.In(self._pair_client_type_names()),
                }
            ),
            errors={},
            last_step=False,
        )

    async def _ensure_app_pairing_defaults(self) -> None:
        """Prepare HA-generated pairing values for inbound-only app clients."""
        if getattr(self, "_discovered_defaults", {}).get(CONF_PAIR_CODE):
            defaults = dict(getattr(self, "_discovered_defaults", {}) or {})
            client_type = _clean(
                getattr(self, "_selected_pair_client_type", ""),
                defaults.get(CONF_CLIENT_TYPE, self._default_pair_client_type()),
            )
            ha_local_url = str(defaults.get("ha_local_url") or "")
            pair_code = str(defaults.get(CONF_PAIR_CODE) or "")
            defaults.update(
                {
                    CONF_CLIENT_TYPE: client_type,
                    CONF_DEVICE_NAME: _device_name_for_client_type(
                        client_type,
                        DEFAULT_DEVICE_NAME,
                    ),
                    CONF_PAIRING_URI: _build_pairing_uri(
                        ha_local_url,
                        pair_code,
                        client_type,
                    ),
                    "iphone_pairing_uri": _build_pairing_uri(
                        ha_local_url,
                        pair_code,
                        CLIENT_TYPE_IOS,
                    ),
                    "watch_pairing_uri": _build_pairing_uri(
                        ha_local_url,
                        pair_code,
                        CLIENT_TYPE_WATCHOS,
                    ),
                }
            )
            self._discovered_defaults = defaults
            self._register_pending_app_pairing_context()
            return
        client_type = _clean(
            getattr(self, "_selected_pair_client_type", ""),
            self._default_pair_client_type(),
        )
        pair_code = _generate_pair_code()
        try:
            ha_local_url = await async_ha_local_url(getattr(self, "hass", None), {})
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect could not determine app pairing HA URL: %s", exc)
            ha_local_url = "http://homeassistant.local:8123"
        self._last_pair_code = pair_code
        self._discovered_defaults = {
            CONF_PAIR_CODE: pair_code,
            CONF_CLIENT_TYPE: client_type,
            CONF_DEVICE_NAME: _device_name_for_client_type(
                client_type,
                DEFAULT_DEVICE_NAME,
            ),
            "ha_local_url": ha_local_url,
            CONF_PAIRING_URI: _build_pairing_uri(ha_local_url, pair_code, client_type),
            "iphone_pairing_uri": _build_pairing_uri(
                ha_local_url,
                pair_code,
                CLIENT_TYPE_IOS,
            ),
            "watch_pairing_uri": _build_pairing_uri(
                ha_local_url,
                pair_code,
                CLIENT_TYPE_WATCHOS,
            ),
        }
        self._register_pending_app_pairing_context()

    def _register_pending_app_pairing_context(self) -> None:
        """Expose the open app-pairing config-flow step to the HTTP pair route."""
        defaults = getattr(self, "_discovered_defaults", {}) or {}
        pair_code = str(defaults.get(CONF_PAIR_CODE) or "").strip()
        if not pair_code:
            return
        try:
            register_http_views(self.hass)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect could not register app pairing HTTP views: %s", exc)
        hass_data = getattr(self.hass, "data", None)
        if not isinstance(hass_data, dict):
            return
        domain_data = hass_data.setdefault(DOMAIN, {})
        pending = domain_data.setdefault(APP_PAIRING_PENDING_KEY, {})
        context = pending.setdefault(pair_code, {})
        client_type = _clean(
            defaults.get(CONF_CLIENT_TYPE),
            self._default_pair_client_type(),
        )
        received = context.get("pairing_received")
        if (
            isinstance(received, dict)
            and received
            and str(received.get(CONF_CLIENT_TYPE) or "").strip() != client_type
        ):
            received = {}
        context.update(
            {
                "flow_id": getattr(self, "flow_id", ""),
                CONF_PAIR_CODE: pair_code,
                CONF_CLIENT_TYPE: client_type,
                CONF_DEVICE_TOKEN: str(context.get(CONF_DEVICE_TOKEN) or "")
                or secrets.token_urlsafe(32),
                CONF_ASSIST_PIPELINE_ID: str(
                    defaults.get(CONF_ASSIST_PIPELINE_ID) or DEFAULT_ASSIST_PIPELINE_ID
                ),
                CONF_HA_EXTERNAL_URL: str(defaults.get(CONF_HA_EXTERNAL_URL) or ""),
                "ha_local_url": str(defaults.get("ha_local_url") or ""),
                "pairing_received": received or {},
            }
        )

    def _pending_app_pairing(self, pair_code: str) -> dict[str, Any]:
        """Return an app pairing payload received through the HTTP pair route."""
        hass_data = getattr(getattr(self, "hass", None), "data", None)
        if not isinstance(hass_data, dict):
            return {}
        pending = hass_data.setdefault(DOMAIN, {}).setdefault(APP_PAIRING_PENDING_KEY, {})
        if not isinstance(pending, dict):
            return {}
        context = pending.get(pair_code)
        if not isinstance(context, dict):
            return {}
        flow_id = str(context.get("flow_id") or "").strip()
        if not flow_id or flow_id != str(getattr(self, "flow_id", "") or "").strip():
            return {}
        received = context.get("pairing_received")
        if isinstance(received, dict) and received.get(CONF_DEVICE_ID):
            return {**context, **received}
        return {}

    def _clear_pending_app_pairing(self, pair_code: str) -> None:
        """Remove a consumed app-pairing context."""
        hass_data = getattr(getattr(self, "hass", None), "data", None)
        if not isinstance(hass_data, dict):
            return
        pending = hass_data.setdefault(DOMAIN, {}).setdefault(APP_PAIRING_PENDING_KEY, {})
        if isinstance(pending, dict):
            pending.pop(str(pair_code or "").strip(), None)

    def _pair_description_placeholders(self) -> dict[str, str]:
        """Return app pairing values shown in the HA config-flow description."""
        defaults = getattr(self, "_discovered_defaults", {})
        iphone_pairing_uri = str(defaults.get("iphone_pairing_uri") or "")
        watch_pairing_uri = str(defaults.get("watch_pairing_uri") or "")
        return {
            "pair_code": str(defaults.get(CONF_PAIR_CODE) or ""),
            "ha_local_url": str(defaults.get("ha_local_url") or ""),
            "pairing_uri": str(defaults.get(CONF_PAIRING_URI) or ""),
            "iphone_pairing_uri": iphone_pairing_uri,
            "watch_pairing_uri": watch_pairing_uri,
            "iphone_qr_image": _qr_svg_data_uri(iphone_pairing_uri),
            "watch_qr_image": _qr_svg_data_uri(watch_pairing_uri),
        }

    async def _ensure_mdns_discovery(self) -> None:
        """Discover visible DJConnect clients once per pair flow."""
        if getattr(self, "_discovery_checked", False):
            return
        self._discovery_checked = True
        try:
            self._discovered_clients = await async_discover_djconnect_clients(self.hass)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect config-flow mDNS discovery failed: %s", exc)
            self._discovered_clients = []
        if self._discovered_clients:
            allowed = set(self._pair_client_type_options())
            self._discovered_clients = [
                client
                for client in self._discovered_clients
                if client.client_type in allowed
            ]
        if self._discovered_clients:
            client = next(
                (
                    discovered
                    for discovered in self._discovered_clients
                    if discovered.client_type != CLIENT_TYPE_ESP32
                ),
                self._discovered_clients[0],
            )
            self._selected_discovered_key = self._discovered_client_key(client)
            self._apply_discovered_client(client)

    def _apply_discovered_client_key(self, key: str) -> None:
        """Apply a selected mDNS client as form defaults."""
        for client in getattr(self, "_discovered_clients", []):
            if self._discovered_client_key(client) == key:
                self._selected_discovered_key = key
                self._apply_discovered_client(client)
                return

    def _selected_discovered_client(self) -> DiscoveredClient | None:
        """Return the selected mDNS client, if the user picked one."""
        return selected_discovered_client(
            getattr(self, "_discovered_clients", []),
            getattr(self, "_selected_discovered_key", ""),
        )

    def _apply_discovered_client(self, client: DiscoveredClient) -> None:
        """Use a discovered client as authoritative defaults for pairing."""
        self._discovered_defaults = discovered_client_defaults(client)
        self._discovered_device_name_authoritative = True
        if client.pair_code:
            self._last_pair_code = client.pair_code

    def _discovered_client_options(self) -> dict[str, str]:
        """Return mDNS discovery choices for the pairing form."""
        selected_type = _clean(getattr(self, "_selected_pair_client_type", ""), "")
        allowed = {selected_type} if selected_type else set(self._pair_client_type_options())
        return discovered_client_options(
            [
                client
                for client in getattr(self, "_discovered_clients", [])
                if client.client_type in allowed
            ]
        )

    @staticmethod
    def _discovered_client_key(client: DiscoveredClient) -> str:
        return discovered_client_key(client)

    def _user_schema(self) -> dict[Any, Any]:
        """Build pairing schema."""
        defaults = getattr(self, "_discovered_defaults", {})
        pair_code = str(
            defaults.get(CONF_PAIR_CODE)
            or getattr(self, "_last_pair_code", "")
            or ""
        )
        client_type = _clean(defaults.get(CONF_CLIENT_TYPE), self._default_pair_client_type())
        client_type = _clean(
            getattr(self, "_selected_pair_client_type", "") or client_type,
            self._default_pair_client_type(),
        )
        default_device_name = _clean(defaults.get(CONF_DEVICE_NAME), DEFAULT_DEVICE_NAME)
        if getattr(self, "_discovered_device_name_authoritative", False):
            device_name = default_device_name
        elif not defaults.get(CONF_CLIENT_TYPE):
            device_name = default_device_name
        else:
            device_name = _device_name_for_client_type(client_type, default_device_name)
        local_url = _clean(defaults.get(CONF_LOCAL_URL), _default_local_url(pair_code))
        schema: dict[Any, Any] = {}
        discovery_options = self._discovered_client_options()
        if discovery_options:
            schema[
                vol.Optional(
                    DISCOVERY_CLIENT_FIELD,
                    default=getattr(self, "_selected_discovered_key", ""),
                )
            ] = vol.In(
                {
                    "": _manual_discovery_label(getattr(self, "hass", None)),
                    **discovery_options,
                }
            )
        if getattr(self, "_pairing_setup_method", "") == SETUP_METHOD_PAIR_APP:
            if client_type in {
                CLIENT_TYPE_IOS,
                CLIENT_TYPE_WATCHOS,
                CLIENT_TYPE_MACOS,
                CLIENT_TYPE_WINDOWS,
            }:
                schema[vol.Optional(APP_PAIR_CODE_DISPLAY_FIELD, default=pair_code)] = str
                schema[
                    vol.Optional(
                        APP_HA_LOCAL_URL_DISPLAY_FIELD,
                        default=str(defaults.get("ha_local_url") or ""),
                    )
                ] = str
        else:
            schema[vol.Optional(CONF_PAIR_CODE, default=pair_code)] = str
        schema[vol.Optional(CONF_DEVICE_NAME, default=device_name)] = str
        if self._client_type_uses_local_device_api(client_type):
            schema[vol.Optional(CONF_LOCAL_URL, default=local_url)] = str
        return schema

    def _default_pair_client_type(self) -> str:
        return default_pair_client_type(getattr(self, "_pairing_setup_method", ""))

    def _pair_client_type_options(self) -> list[str]:
        return pair_client_type_options(getattr(self, "_pairing_setup_method", ""))

    def _pair_client_type_names(self) -> dict[str, str]:
        return {
            client_type: CLIENT_TYPE_NAMES[client_type]
            for client_type in self._pair_client_type_options()
        }

    @staticmethod
    def _client_type_uses_local_device_api(client_type: Any) -> bool:
        return client_type_uses_local_device_api(client_type)

    async def async_step_backend(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose Spotify Direct or Music Assistant."""
        if user_input is not None:
            backend = str(
                user_input.get(CONF_MUSIC_BACKEND) or DEFAULT_MUSIC_BACKEND
            ).strip()
            if backend == MUSIC_BACKEND_MUSIC_ASSISTANT:
                if not _music_assistant_available(self.hass):
                    return self.async_show_form(
                        step_id="backend",
                        data_schema=vol.Schema(_backend_schema()),
                        errors={"base": "music_assistant_unavailable"},
                        last_step=False,
                    )
                if not _music_assistant_players(self.hass):
                    return self.async_show_form(
                        step_id="backend",
                        data_schema=vol.Schema(_backend_schema()),
                        errors={"base": "music_assistant_no_players"},
                        last_step=False,
                    )
                self._backend = {CONF_MUSIC_BACKEND: backend}
                return await self.async_step_music_assistant()
            self._backend = {CONF_MUSIC_BACKEND: MUSIC_BACKEND_SPOTIFY_DIRECT}
            return await self.async_step_spotify()

        return self.async_show_form(
            step_id="backend",
            data_schema=vol.Schema(_backend_schema()),
            errors={},
            last_step=False,
        )

    async def async_step_music_assistant(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure Music Assistant target player."""
        errors: dict[str, str] = {}
        players = _music_assistant_players(self.hass)
        if not _music_assistant_available(self.hass):
            errors["base"] = "music_assistant_unavailable"
        elif not players:
            errors["base"] = "music_assistant_no_players"
        if user_input is not None and not errors:
            player = str(user_input.get(CONF_MUSIC_ASSISTANT_PLAYER) or "").strip()
            player_error = _validate_music_assistant_player(self.hass, player)
            if player_error:
                errors[CONF_MUSIC_ASSISTANT_PLAYER] = player_error
            elif player not in players:
                errors[CONF_MUSIC_ASSISTANT_PLAYER] = "music_assistant_player_not_found"
            else:
                self._backend = {
                    CONF_MUSIC_BACKEND: MUSIC_BACKEND_MUSIC_ASSISTANT,
                    CONF_MUSIC_ASSISTANT_PLAYER: player,
                }
                self._spotify = {}
                if getattr(self, "_conversation_agent_only", False):
                    return self._create_conversation_agent_entry()
                return await self.async_step_voice()

        return self.async_show_form(
            step_id="music_assistant",
            data_schema=vol.Schema(
                _music_assistant_schema(players) if players else {}
            ),
            errors=errors,
            last_step=False,
        )

    async def async_step_spotify(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect Spotify Client ID and HTTPS HA external URL."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = str(user_input.get(CONF_SPOTIFY_CLIENT_ID) or "").strip()
            external_url = str(user_input.get(CONF_HA_EXTERNAL_URL, "")).strip().rstrip("/")
            if not client_id:
                errors[CONF_SPOTIFY_CLIENT_ID] = "spotify_client_id_required"
            elif not external_url:
                errors[CONF_HA_EXTERNAL_URL] = "external_url_required"
            elif not external_url.startswith("https://"):
                errors[CONF_HA_EXTERNAL_URL] = "external_url_https_required"
            elif not _is_https_url(external_url):
                errors[CONF_HA_EXTERNAL_URL] = "external_url_invalid"
            else:
                try:
                    self._prepare_spotify_oauth(client_id, external_url, user_input)
                    register_http_views(self.hass)
                    return await self.async_step_spotify_oauth()
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Could not start Spotify OAuth")
                    errors["base"] = "oauth_setup_failed"

        default_external_url = await _async_default_external_url(self.hass)
        shown_external_url = str(
            (user_input or {}).get(CONF_HA_EXTERNAL_URL)
            or default_external_url
            or ""
        ).strip().rstrip("/")
        return self.async_show_form(
            step_id="spotify",
            data_schema=vol.Schema(
                _spotify_schema_with_defaults(
                    external_url=shown_external_url,
                    client_id=str((user_input or {}).get(CONF_SPOTIFY_CLIENT_ID) or ""),
                )
            ),
            errors=errors,
            description_placeholders={
                "callback_path": "/api/djconnect/spotify/callback",
                "developer_url": "https://developer.spotify.com/dashboard",
                "redirect_uri": build_redirect_uri(shown_external_url) if shown_external_url else "",
            },
            last_step=False,
        )

    def _prepare_spotify_oauth(
        self,
        client_id: str,
        external_url: str,
        user_input: dict[str, Any],
    ) -> None:
        """Store pending Spotify OAuth context before opening the external step."""
        redirect_uri = build_redirect_uri(external_url)
        self._spotify = {
            CONF_SPOTIFY_CLIENT_ID: client_id,
            CONF_HA_EXTERNAL_URL: external_url,
            CONF_SPOTIFY_MARKET: _clean(
                user_input.get(CONF_SPOTIFY_MARKET),
                DEFAULT_SPOTIFY_MARKET,
            ),
            CONF_SPOTIFY_SCOPES: DEFAULT_SPOTIFY_SCOPES,
        }
        self._oauth = {
            "state": secrets.token_urlsafe(24),
            "code_verifier": create_code_verifier(),
            "redirect_uri": redirect_uri,
        }
        self._oauth["authorize_url"] = build_authorize_url(
            client_id,
            redirect_uri,
            DEFAULT_SPOTIFY_SCOPES,
            self._oauth["state"],
            self._oauth["code_verifier"],
        )
        pending = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            "config_flow_oauth_pending",
            {},
        )
        pending[self._oauth["state"]] = {
            "flow_id": self.flow_id,
            "client_id": client_id,
            "code_verifier": self._oauth["code_verifier"],
            "redirect_uri": redirect_uri,
            "market": self._spotify[CONF_SPOTIFY_MARKET],
            "scopes": DEFAULT_SPOTIFY_SCOPES,
        }

    async def async_step_spotify_oauth(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Open Spotify OAuth as an external step and finish from the callback."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._handle_spotify_oauth_result(user_input)
            if not errors:
                if getattr(self, "_conversation_agent_only", False):
                    return self.async_external_step_done(
                        next_step_id="finish_conversation_agent"
                    )
                return self.async_external_step_done(next_step_id="voice")

        if errors:
            return self.async_show_form(
                step_id="spotify_oauth",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

        if not self._oauth.get("authorize_url"):
            return self.async_show_form(
                step_id="spotify_oauth",
                data_schema=vol.Schema({}),
                errors={"base": "oauth_setup_failed"},
                last_step=False,
            )

        result = self.async_external_step(
            step_id="spotify_oauth",
            url=self._oauth["authorize_url"],
            description_placeholders={
                "redirect_uri": self._oauth.get("redirect_uri", ""),
            },
        )
        result["title"] = _spotify_oauth_title(self.hass)
        result["description"] = _spotify_oauth_description(self.hass)
        return result

    def _handle_spotify_oauth_result(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Read the callback result stored by the HTTP OAuth callback."""
        state = str(user_input.get("state", "")).strip()
        if not state:
            return {"base": "oauth_failed"}
        try:
            result = (
                self.hass.data.get(DOMAIN, {})
                .get("config_flow_oauth_results", {})
                .pop(state, None)
            )
            if not result:
                return {"base": "oauth_not_completed"}
            self._spotify[CONF_SPOTIFY_REFRESH_TOKEN] = result[
                CONF_SPOTIFY_REFRESH_TOKEN
            ]
            self._spotify[CONF_SPOTIFY_MARKET] = result.get(
                CONF_SPOTIFY_MARKET,
                DEFAULT_SPOTIFY_MARKET,
            )
            self._spotify[CONF_SPOTIFY_SCOPES] = result.get(
                CONF_SPOTIFY_SCOPES,
                DEFAULT_SPOTIFY_SCOPES,
            )
            return {}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Spotify OAuth failed")
        return {"base": "oauth_failed"}

    async def async_step_finish_conversation_agent(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Finish conversation-agent-only setup without showing voice settings."""
        return self._create_conversation_agent_entry()

    def _create_conversation_agent_entry(self) -> FlowResult:
        """Create the compact conversation-agent-only config entry."""
        data: dict[str, Any] = {}
        data.update(self._pairing)
        data.update(self._backend)
        data.update(self._spotify)
        data.update(
            _voice_defaults_for_client(
                {},
                client_type=CLIENT_TYPE_CONVERSATION_AGENT,
            )
        )
        return self.async_create_entry(
            title=data.get(CONF_DEVICE_NAME, "DJConnect DJ"),
            data=data,
        )

    async def async_step_voice(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect optional voice settings. Empty fields are allowed."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _voice_errors(user_input)
            if not errors:
                data: dict[str, Any] = {}
                data.update(self._pairing)
                data.update(self._backend)
                data.update(self._spotify)
                client_type = data.get(CONF_CLIENT_TYPE, DEFAULT_CLIENT_TYPE)
                data.update(
                    _voice_defaults_for_client(
                        _voice_form_values(user_input),
                        client_type=client_type,
                    )
                )
                if getattr(self, "_conversation_agent_only", False):
                    return self._create_conversation_agent_entry()
                if not self._client_type_uses_local_device_api(client_type):
                    return self.async_create_entry(
                        title=data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME),
                        data=data,
                    )
                try:
                    await _async_pair_before_create(self.hass, data)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("DJConnect initial device pairing failed: %s", exc)
                    errors["base"] = "repair_pairing_failed"
                    return self.async_show_form(
                        step_id="voice",
                        data_schema=await _voice_schema(
                            self.hass,
                            {
                                **self._pairing,
                                **_voice_defaults_for_client(
                                    _voice_form_values(user_input),
                                    client_type=self._pairing.get(
                                        CONF_CLIENT_TYPE,
                                        DEFAULT_CLIENT_TYPE,
                                    ),
                                ),
                            },
                        ),
                        errors=errors,
                    )
                return self.async_create_entry(
                    title=data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME),
                    data=data,
                )

        return self.async_show_form(
            step_id="voice",
            data_schema=(
                _conversation_agent_voice_schema(_voice_defaults({}))
                if getattr(self, "_conversation_agent_only", False)
                else await _voice_schema(
                    self.hass,
                    {
                        **self._pairing,
                        **_voice_defaults_for_client(
                            {},
                            client_type=self._pairing.get(
                                CONF_CLIENT_TYPE,
                                DEFAULT_CLIENT_TYPE,
                            ),
                        ),
                    },
                )
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "DJConnectOptionsFlow":
        """Create options flow."""
        return DJConnectOptionsFlow(config_entry)


class DJConnectOptionsFlow(config_entries.OptionsFlow):
    """Handle DJConnect options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._oauth: dict[str, str] = {}
        self._pending_backend_switch: dict[str, Any] | None = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage DJConnect options."""
        current = {**self._config_entry.data, **self._config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            action = user_input.get(OPTIONS_ACTION_FIELD)
            if action == OPTIONS_ACTION_SPOTIFY_REAUTH:
                return await self.async_step_spotify_reauth()
            if action == OPTIONS_ACTION_CHANGE_MUSIC_BACKEND:
                return await self.async_step_music_backend()
            if action == OPTIONS_ACTION_CENTRAL_API:
                return await self.async_step_central_api()
            if action == OPTIONS_ACTION_RETRY_PAIRING:
                return await self._async_retry_pairing()
            if action == OPTIONS_ACTION_REPAIR:
                return await self.async_step_repair_pairing()
            errors = _voice_errors(user_input)
            if not errors:
                merged = dict(current)
                merged.update(
                    {
                        key: value
                        for key, value in user_input.items()
                        if key in VOICE_FORM_FIELDS
                    }
                )
                return self.async_create_entry(
                    title="",
                    data=_voice_defaults_for_client(
                        merged,
                        client_type=merged.get(CONF_CLIENT_TYPE, DEFAULT_CLIENT_TYPE),
                        preserve_empty=True,
                    ),
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_conversation_agent_options_schema(self.hass, current),
            errors=errors,
            last_step=False,
        )

    async def async_step_music_backend(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Explicitly switch the selected music backend."""
        current = {**self._config_entry.data, **self._config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            selected_backend = str(
                user_input.get(CONF_MUSIC_BACKEND)
                or current.get(CONF_MUSIC_BACKEND)
                or DEFAULT_MUSIC_BACKEND
            ).strip()
            if selected_backend == MUSIC_BACKEND_MUSIC_ASSISTANT:
                if not _music_assistant_available(self.hass):
                    errors["base"] = "music_assistant_not_configured"
                elif not _music_assistant_players(self.hass):
                    errors["base"] = "music_assistant_no_players"
                else:
                    self._pending_backend_switch = {
                        CONF_MUSIC_BACKEND: selected_backend,
                    }
                    return await self.async_step_music_assistant_player()
            elif selected_backend == MUSIC_BACKEND_SPOTIFY_DIRECT:
                merged = self._backend_switch_options(
                    {
                        CONF_MUSIC_BACKEND: selected_backend,
                    }
                )
                if not _spotify_direct_ready({**self._config_entry.data, **merged}):
                    self._pending_backend_switch = {
                        CONF_MUSIC_BACKEND: selected_backend,
                    }
                    return await self.async_step_spotify_reauth()
                return self._finish_backend_switch(merged)
            else:
                errors[CONF_MUSIC_BACKEND] = "backend_switch_failed"

        return self.async_show_form(
            step_id="music_backend",
            data_schema=_music_backend_switch_schema(current),
            errors=errors,
        )

    async def async_step_music_assistant_player(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose the Music Assistant target player during a backend switch."""
        current = {**self._config_entry.data, **self._config_entry.options}
        players = _music_assistant_players(self.hass)
        errors: dict[str, str] = {}
        if user_input is not None:
            selected_player = str(
                user_input.get(CONF_MUSIC_ASSISTANT_PLAYER) or ""
            ).strip()
            if not _music_assistant_available(self.hass):
                errors["base"] = "music_assistant_not_configured"
            elif not players:
                errors["base"] = "music_assistant_no_players"
            else:
                player_error = _validate_music_assistant_player(self.hass, selected_player)
                if player_error:
                    errors[CONF_MUSIC_ASSISTANT_PLAYER] = player_error
                elif selected_player not in players:
                    errors[CONF_MUSIC_ASSISTANT_PLAYER] = "music_assistant_player_not_found"
            if not errors:
                selected_player = str(
                    user_input.get(CONF_MUSIC_ASSISTANT_PLAYER) or ""
                ).strip()
                merged = self._backend_switch_options(
                    {
                        CONF_MUSIC_BACKEND: MUSIC_BACKEND_MUSIC_ASSISTANT,
                        CONF_MUSIC_ASSISTANT_PLAYER: selected_player,
                    }
                )
                return self._finish_backend_switch(merged)

        if not _music_assistant_available(self.hass):
            return self.async_show_form(
                step_id="music_backend",
                data_schema=_music_backend_switch_schema(current),
                errors={"base": "music_assistant_not_configured"},
            )
        if not players:
            return self.async_show_form(
                step_id="music_backend",
                data_schema=_music_backend_switch_schema(current),
                errors={"base": "music_assistant_no_players"},
            )
        return self.async_show_form(
            step_id="music_assistant_player",
            data_schema=vol.Schema(
                _music_assistant_schema(
                    players,
                    str(
                        current.get(CONF_MUSIC_ASSISTANT_PLAYER)
                        or next(iter(players), "")
                    ),
                )
            ),
            errors=errors,
        )

    def _backend_switch_options(self, updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(self._config_entry.options)
        old_backend = (
            merged.get(CONF_MUSIC_BACKEND)
            or self._config_entry.data.get(CONF_MUSIC_BACKEND)
            or DEFAULT_MUSIC_BACKEND
        )
        merged.update(updates)
        if merged.get(CONF_MUSIC_BACKEND) != old_backend:
            merged[CONF_MUSIC_BACKEND_REVISION] = _next_backend_revision(
                {**self._config_entry.data, **self._config_entry.options}
            )
        else:
            merged.setdefault(
                CONF_MUSIC_BACKEND_REVISION,
                _current_backend_revision(
                    {**self._config_entry.data, **self._config_entry.options}
                ),
            )
        return merged

    def _finish_backend_switch(self, options: dict[str, Any]) -> FlowResult:
        runtime = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if runtime is not None:
            current_revision = _current_backend_revision(
                {**self._config_entry.data, **self._config_entry.options}
            )
            if _current_backend_revision(options) > current_revision:
                _mark_backend_specific_pending_state_stale(
                    runtime,
                    _current_backend_revision(options),
                )
            runtime.update(last_error=None)
        return self.async_create_entry(title="", data=options)

    async def async_step_central_api(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure the per-install DJConnect central API token."""
        current = {**self._config_entry.data, **self._config_entry.options}
        current.setdefault(CONF_API_BASE_URL, DEFAULT_API_BASE_URL)
        current.setdefault(CONF_HA_INSTALL_ID, _central_api_install_id(current))
        errors: dict[str, str] = {}
        if user_input is not None:
            action = user_input.get(OPTIONS_ACTION_FIELD, OPTIONS_ACTION_SAVE)
            merged = dict(self._config_entry.options)
            merged[CONF_API_BASE_URL] = str(
                user_input.get(CONF_API_BASE_URL) or DEFAULT_API_BASE_URL
            ).strip()
            merged[CONF_HA_INSTALL_ID] = str(
                user_input.get(CONF_HA_INSTALL_ID) or current[CONF_HA_INSTALL_ID]
            ).strip()
            merged[CONF_DJCONNECT_INSTALL_TOKEN] = str(
                user_input.get(CONF_DJCONNECT_INSTALL_TOKEN) or ""
            ).strip()
            errors = _central_api_errors(merged)
            if not errors and action == OPTIONS_ACTION_ROTATE_INSTALL_TOKEN:
                runtime = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
                if runtime is None:
                    errors["base"] = "central_api_rotate_failed"
                else:
                    temp_entry = SimpleNamespace(
                        data={**self._config_entry.data, **merged},
                        options=merged,
                        entry_id=self._config_entry.entry_id,
                    )
                    original_entry = runtime.entry
                    runtime.entry = temp_entry
                    try:
                        result = await async_rotate_install_token(self.hass, runtime)
                    finally:
                        runtime.entry = original_entry
                    if result.get("success"):
                        rotated = dict(merged)
                        rotated[CONF_DJCONNECT_INSTALL_TOKEN] = result[CONF_DJCONNECT_INSTALL_TOKEN]
                        return self.async_create_entry(title="", data=rotated)
                    errors["base"] = "central_api_rotate_failed"
            if not errors:
                return self.async_create_entry(title="", data=merged)
            current.update(merged)

        return self.async_show_form(
            step_id="central_api",
            data_schema=_central_api_schema(current),
            errors=errors,
        )

    async def async_step_spotify_reauth(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Reauthorize Spotify from the options flow."""
        if user_input is not None:
            return self.async_external_step_done(next_step_id="spotify_reauth_done")
        current = {**self._config_entry.data, **self._config_entry.options}
        client_id = str(current.get(CONF_SPOTIFY_CLIENT_ID) or "").strip()
        external_url = str(
            current.get(CONF_HA_EXTERNAL_URL)
            or await _async_default_external_url(self.hass)
            or ""
        ).strip().rstrip("/")
        if not client_id or not external_url:
            return self.async_show_form(
                step_id="init",
                data_schema=await _voice_schema(
                    self.hass,
                    {
                        **current,
                        **_voice_defaults_for_client(
                            current,
                            client_type=current.get(
                                CONF_CLIENT_TYPE,
                                DEFAULT_CLIENT_TYPE,
                            ),
                        ),
                    },
                    include_options_action=True,
                ),
                errors={"base": "oauth_setup_failed"},
            )
        redirect_uri = build_redirect_uri(external_url)
        state = secrets.token_urlsafe(24)
        code_verifier = create_code_verifier()
        self._oauth = {
            "state": state,
            "redirect_uri": redirect_uri,
            "authorize_url": build_authorize_url(
                client_id,
                redirect_uri,
                DEFAULT_SPOTIFY_SCOPES,
                state,
                code_verifier,
            ),
        }
        pending = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            "spotify_oauth_pending",
            {},
        )
        pending[state] = {
            "flow_id": self.flow_id,
            "entry_id": self._config_entry.entry_id,
            "client_id": client_id,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "market": current.get(CONF_SPOTIFY_MARKET, DEFAULT_SPOTIFY_MARKET),
            "scopes": DEFAULT_SPOTIFY_SCOPES,
        }
        result = self.async_external_step(
            step_id="spotify_reauth",
            url=self._oauth["authorize_url"],
            description_placeholders={
                "redirect_uri": redirect_uri,
                "title": _spotify_oauth_title(self.hass, reauth=True),
                "description": _spotify_oauth_description(self.hass, reauth=True),
            },
        )
        result["title"] = _spotify_oauth_title(self.hass, reauth=True)
        result["description"] = _spotify_oauth_description(self.hass, reauth=True)
        return result

    async def async_step_spotify_reauth_done(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show a translated completion step after Spotify OAuth reauthorization."""
        if user_input is not None:
            if self._pending_backend_switch:
                merged = self._backend_switch_options(self._pending_backend_switch)
                self._pending_backend_switch = None
                return self._finish_backend_switch(merged)
            return self.async_create_entry(
                title="",
                data=dict(self._config_entry.options),
            )
        return self.async_show_form(
            step_id="spotify_reauth_done",
            data_schema=vol.Schema({}),
        )

    async def async_step_repair_pairing(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect a fresh pairing code before fully re-pairing the ESP."""
        errors: dict[str, str] = {}
        if user_input is not None:
            pair_code = str(user_input.get(CONF_PAIR_CODE, "")).strip()
            local_url = _clean(user_input.get(CONF_LOCAL_URL), None)
            if not pair_code:
                errors[CONF_PAIR_CODE] = "missing_pair_code"
            elif not _valid_pair_code(pair_code):
                errors[CONF_PAIR_CODE] = "invalid_pair_code"
            else:
                return await self._async_retry_pairing(
                    pair_code=pair_code,
                    local_url=local_url,
                )

        return self.async_show_form(
            step_id="repair_pairing",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PAIR_CODE): str,
                    vol.Optional(CONF_LOCAL_URL): str,
                }
            ),
            errors=errors,
        )

    async def _async_retry_pairing(
        self,
        pair_code: str | None = None,
        local_url: str | None = None,
    ) -> FlowResult:
        """Generate a fresh device token and retry pairing with the ESP."""
        errors: dict[str, str] = {}
        try:
            runtime = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
            if runtime is None:
                errors["base"] = "repair_pairing_failed"
            else:
                token = secrets.token_urlsafe(32)
                data = dict(self._config_entry.data)
                if pair_code is not None:
                    device_id = f"djconnect-{pair_code}"
                    data[CONF_PAIR_CODE] = pair_code
                    data[CONF_DEVICE_ID] = device_id
                    stored_local_url = _clean(
                        data.get(CONF_LOCAL_URL)
                        or runtime.device_status.get("local_url"),
                        "",
                    )
                    cleaned_local_url = _clean(
                        local_url,
                        stored_local_url or _default_local_url(pair_code),
                    )
                    data[CONF_LOCAL_URL] = cleaned_local_url
                    runtime.pairing_code = pair_code
                    runtime.pairing_device_id = device_id
                    runtime.device_status["device_id"] = device_id
                    if cleaned_local_url:
                        runtime.device_status["local_url"] = cleaned_local_url
                    runtime.device_status.pop("paired", None)
                runtime.device_token = token
                runtime.device_status["ha_pairing_status"] = "pending"
                runtime.update(last_error=None)
                data[CONF_DEVICE_TOKEN] = token
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=data,
                )
                await runtime.pair_device(self.hass)
                runtime.device_status["ha_pairing_status"] = "pending"
                runtime.update(last_error=None)
                return self.async_create_entry(
                    title="",
                    data=dict(self._config_entry.options),
                )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("DJConnect re-pair failed: %s", exc)
            errors["base"] = "repair_pairing_failed"

        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=await _voice_schema(
                self.hass,
                {
                    **current,
                    **_voice_defaults_for_client(
                        current,
                        client_type=current.get(CONF_CLIENT_TYPE, DEFAULT_CLIENT_TYPE),
                    ),
                },
                include_options_action=True,
            ),
            errors=errors,
        )
