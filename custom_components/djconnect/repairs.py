from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import issue_registry as ir

from .const import (
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_CONVERSATION_AGENT,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_TOKEN,
    CONF_HA_EXTERNAL_URL,
    CONF_MUSIC_BACKEND,
    CONF_SETUP_METHOD,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_MARKET,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_SCOPES,
    DEFAULT_SPOTIFY_MARKET,
    DEFAULT_SPOTIFY_SCOPES,
    DOMAIN,
    MUSIC_BACKEND_MUSIC_ASSISTANT,
    SETUP_METHOD_CONVERSATION_AGENT,
)
from .spotify_oauth import (
    build_authorize_url,
    build_redirect_uri,
    create_code_verifier,
    missing_spotify_scopes,
)

FIXABLE_SPOTIFY_ISSUES = {
    "missing_spotify_refresh_token",
    "missing_spotify_oauth_scopes",
    "spotify_refresh_token_revoked",
}
SPOTIFY_REPAIR_EXTERNAL_TEXT = {
    "missing_spotify_oauth_scopes": {
        "title": "DJConnect autoriseren bij Spotify",
        "description": (
            "DJConnect heeft opnieuw Spotify toestemming nodig om je playlists "
            "te kunnen lezen. Open Spotify, geef akkoord en keer daarna terug "
            "naar Home Assistant."
        ),
    },
    "missing_spotify_refresh_token": {
        "title": "DJConnect autoriseren bij Spotify",
        "description": (
            "DJConnect heeft Spotify toestemming nodig om muziek namens jou te "
            "bedienen. Open Spotify, geef akkoord en keer daarna terug naar "
            "Home Assistant."
        ),
    },
    "spotify_refresh_token_revoked": {
        "title": "DJConnect opnieuw autoriseren bij Spotify",
        "description": (
            "De Spotify toestemming voor DJConnect is verlopen of ingetrokken. "
            "Open Spotify, geef opnieuw akkoord en keer daarna terug naar "
            "Home Assistant."
        ),
    },
}


async def async_create_fixable_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    missing_device_token_issue_id = f"{entry.entry_id}_missing_device_token"
    if not _entry_requires_device_token(entry):
        try:
            ir.async_delete_issue(hass, DOMAIN, missing_device_token_issue_id)
        except Exception:  # noqa: BLE001
            pass
    elif not _entry_value(entry, CONF_DEVICE_TOKEN):
        ir.async_create_issue(
            hass,
            DOMAIN,
            missing_device_token_issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_device_token",
        )
    if not _entry_requires_spotify_oauth(entry):
        _delete_spotify_prerequisite_issues(hass, entry.entry_id)
        return
    missing_client_issue_id = f"{entry.entry_id}_missing_spotify_client_id"
    if not _entry_value(entry, CONF_SPOTIFY_CLIENT_ID):
        ir.async_create_issue(
            hass,
            DOMAIN,
            missing_client_issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_spotify_client_id",
        )
    else:
        _delete_issue_best_effort(hass, missing_client_issue_id)
    if not _entry_value(entry, CONF_SPOTIFY_REFRESH_TOKEN):
        ir.async_create_issue(
            hass,
            DOMAIN,
            "missing_spotify_refresh_token",
            data={"entry_id": entry.entry_id},
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_spotify_refresh_token",
        )
    else:
        _delete_issue_best_effort(hass, "missing_spotify_refresh_token")
        _delete_issue_best_effort(hass, f"{entry.entry_id}_missing_spotify_refresh_token")
    if missing_spotify_scopes(_entry_value(entry, CONF_SPOTIFY_SCOPES)):
        ir.async_create_issue(
            hass,
            DOMAIN,
            "missing_spotify_oauth_scopes",
            data={"entry_id": entry.entry_id},
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_spotify_oauth_scopes",
        )
    else:
        _delete_issue_best_effort(hass, "missing_spotify_oauth_scopes")
        _delete_issue_best_effort(hass, f"{entry.entry_id}_missing_spotify_oauth_scopes")


def _delete_spotify_prerequisite_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Clear stale Spotify setup issues for entries without their own OAuth state."""
    for issue_id in (
        f"{entry_id}_missing_spotify_client_id",
        "missing_spotify_refresh_token",
        f"{entry_id}_missing_spotify_refresh_token",
        "missing_spotify_oauth_scopes",
        f"{entry_id}_missing_spotify_oauth_scopes",
    ):
        _delete_issue_best_effort(hass, issue_id)


def _delete_issue_best_effort(hass: HomeAssistant, issue_id: str) -> None:
    try:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    except Exception:  # noqa: BLE001
        pass


def _entry_value(entry: ConfigEntry, key: str) -> Any:
    """Return config entry data/options value for repair prerequisites."""
    data = getattr(entry, "data", {}) or {}
    options = getattr(entry, "options", {}) or {}
    return data.get(key) or options.get(key)


def _entry_requires_device_token(entry: ConfigEntry) -> bool:
    """Return false for entry types that intentionally have no DJConnect client token."""
    client_type = str(_entry_value(entry, CONF_CLIENT_TYPE) or "").strip()
    setup_method = str(_entry_value(entry, CONF_SETUP_METHOD) or "").strip()
    return not (
        client_type == CLIENT_TYPE_CONVERSATION_AGENT
        or setup_method == SETUP_METHOD_CONVERSATION_AGENT
    )


def _entry_requires_spotify_oauth(entry: ConfigEntry) -> bool:
    """Return true only for entries that own Spotify OAuth configuration."""
    if str(_entry_value(entry, CONF_MUSIC_BACKEND) or "").strip() == MUSIC_BACKEND_MUSIC_ASSISTANT:
        return False
    client_type = str(_entry_value(entry, CONF_CLIENT_TYPE) or "").strip()
    if client_type == CLIENT_TYPE_CONVERSATION_AGENT:
        return False
    configured_values = (
        _entry_value(entry, CONF_SPOTIFY_CLIENT_ID),
        _entry_value(entry, CONF_SPOTIFY_REFRESH_TOKEN),
        _entry_value(entry, CONF_SPOTIFY_SCOPES),
    )
    if any(str(value or "").strip() for value in configured_values):
        return True
    return client_type in ("", CLIENT_TYPE_ESP32)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a Repairs fix flow for Spotify reauthorization."""
    issue_key = _issue_key(issue_id)
    if issue_key in FIXABLE_SPOTIFY_ISSUES:
        return SpotifyOAuthRepairFlow(hass, issue_id, data or {})
    return SpotifyOAuthRepairFlow(hass, issue_id, data or {})


class SpotifyOAuthRepairFlow(RepairsFlow):
    """Repair flow that guides users through Spotify OAuth reauthorization."""

    def __init__(
        self,
        hass: HomeAssistant,
        issue_id: str,
        data: dict[str, Any],
    ) -> None:
        self.hass = hass
        self.issue_id = issue_id
        self.data = data
        self._state = ""
        self._authorize_url = ""
        self._original_refresh_token = ""
        self._issue_key = _issue_key(issue_id)

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Show a visible repair introduction before opening Spotify."""
        entry = _entry_from_issue(self.hass, self.issue_id, self.data)
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        text = SPOTIFY_REPAIR_EXTERNAL_TEXT.get(
            self._issue_key,
            SPOTIFY_REPAIR_EXTERNAL_TEXT["spotify_refresh_token_revoked"],
        )
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "repair_title": text["title"],
                    "repair_description": text["description"],
                    "title": text["title"],
                    "description": text["description"],
                },
            )
        return await self.async_step_authorize()

    async def async_step_authorize(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Open Spotify and move back to a translated completion step."""
        entry = _entry_from_issue(self.hass, self.issue_id, self.data)
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        if user_input and user_input.get("state"):
            return await self.async_step_oauth_done(user_input)
        if not self._authorize_url:
            self._original_refresh_token = str(
                entry.data.get(CONF_SPOTIFY_REFRESH_TOKEN) or ""
            )
            self._authorize_url = await _prepare_spotify_repair_oauth(
                self.hass,
                entry,
                flow_id=str(getattr(self, "flow_id", "") or ""),
            )
            external_step = getattr(self, "async_external_step", None)
            if callable(external_step):
                text = SPOTIFY_REPAIR_EXTERNAL_TEXT.get(
                    self._issue_key,
                    SPOTIFY_REPAIR_EXTERNAL_TEXT["spotify_refresh_token_revoked"],
                )
                result = external_step(
                    step_id="authorize",
                    url=self._authorize_url,
                    description_placeholders={
                        "authorize_url": self._authorize_url,
                        "repair_title": text["title"],
                        "repair_description": text["description"],
                        "title": text["title"],
                        "description": text["description"],
                    },
                )
                result["title"] = text["title"]
                result["description"] = text["description"]
                return result
            return self.async_show_form(
                step_id="authorize",
                data_schema=vol.Schema({}),
                description_placeholders={"authorize_url": self._authorize_url},
            )
        return await self.async_step_oauth_done(user_input)

    async def async_step_oauth_done(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Finish the repair only after Spotify OAuth stored a new token."""
        entry = _entry_from_issue(self.hass, self.issue_id, self.data)
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        current_refresh_token = str(entry.data.get(CONF_SPOTIFY_REFRESH_TOKEN) or "")
        token_changed = (
            bool(current_refresh_token)
            and current_refresh_token != self._original_refresh_token
        )
        token_was_missing = bool(current_refresh_token) and not self._original_refresh_token
        if token_changed or token_was_missing:
            _delete_spotify_reauth_issues(self.hass, entry.entry_id)
            return self.async_create_entry(title="", data={})
        errors = {"base": "oauth_not_completed"} if user_input is not None else {}
        return self.async_show_form(
            step_id="oauth_done",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"authorize_url": self._authorize_url},
        )


def _issue_key(issue_id: str) -> str:
    for suffix in FIXABLE_SPOTIFY_ISSUES:
        if issue_id.endswith(f"_{suffix}") or issue_id == suffix:
            return suffix
    return issue_id


def _entry_from_issue(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any],
) -> ConfigEntry | None:
    entry_id = str(data.get("entry_id") or data.get("config_entry_id") or "")
    if not entry_id:
        for suffix in FIXABLE_SPOTIFY_ISSUES:
            marker = f"_{suffix}"
            if issue_id.endswith(marker):
                entry_id = issue_id[: -len(marker)]
                break
    getter = getattr(getattr(hass, "config_entries", None), "async_get_entry", None)
    if callable(getter) and entry_id:
        entry = getter(entry_id)
        if entry is not None:
            return entry
    entries_getter = getattr(getattr(hass, "config_entries", None), "async_entries", None)
    if not callable(entries_getter):
        return None
    try:
        entries = list(entries_getter(DOMAIN))
    except TypeError:
        entries = [
            entry
            for entry in entries_getter()
            if getattr(entry, "domain", DOMAIN) == DOMAIN
        ]
    if entry_id:
        return next((entry for entry in entries if getattr(entry, "entry_id", "") == entry_id), None)
    return entries[0] if len(entries) == 1 else None


async def _prepare_spotify_repair_oauth(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    flow_id: str = "",
) -> str:
    client_id = str(_entry_value(entry, CONF_SPOTIFY_CLIENT_ID) or "").strip()
    if not client_id:
        raise RuntimeError("Spotify Client ID is not configured")
    external_url = str(entry.data.get(CONF_HA_EXTERNAL_URL) or "").strip().rstrip("/")
    if not external_url:
        external_url = str(getattr(getattr(hass, "config", None), "external_url", "") or "").strip().rstrip("/")
    redirect_uri = build_redirect_uri(external_url)
    state = secrets.token_urlsafe(24)
    code_verifier = create_code_verifier()
    scopes = DEFAULT_SPOTIFY_SCOPES
    pending = hass.data.setdefault(DOMAIN, {}).setdefault("spotify_oauth_pending", {})
    pending[state] = {
        "entry_id": entry.entry_id,
        "flow_id": flow_id,
        "client_id": client_id,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "market": entry.data.get(CONF_SPOTIFY_MARKET, DEFAULT_SPOTIFY_MARKET),
        "scopes": scopes,
        "repair_issue_id": f"{DOMAIN}:{entry.entry_id}",
    }
    return build_authorize_url(client_id, redirect_uri, scopes, state, code_verifier)


def _delete_spotify_reauth_issues(hass: HomeAssistant, entry_id: str) -> None:
    for suffix in FIXABLE_SPOTIFY_ISSUES:
        for issue_id in (suffix, f"{entry_id}_{suffix}"):
            try:
                ir.async_delete_issue(hass, DOMAIN, issue_id)
            except Exception:  # noqa: BLE001
                pass
    domain_data = hass.data.setdefault(DOMAIN, {}) if hasattr(hass, "data") else {}
    throttle = domain_data.get("spotify_reauth_issue_throttle")
    if isinstance(throttle, dict):
        throttle.pop(entry_id or "global", None)
