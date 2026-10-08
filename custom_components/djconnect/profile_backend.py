"""Reuse an existing Profile's HA-owned provider connection without copying secrets."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_DEVICE_ID,
    CONF_MUSIC_ASSISTANT_PLAYER,
    CONF_MUSIC_BACKEND,
    CONF_MUSIC_BACKEND_REVISION,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_MARKET,
    CONF_SPOTIFY_SCOPES,
    CONF_HA_EXTERNAL_URL,
    DOMAIN,
    MUSIC_BACKEND_LATER_MANUAL,
    MUSIC_BACKEND_MUSIC_ASSISTANT,
    MUSIC_BACKEND_SPOTIFY_DIRECT,
)
from .domain.storage import ProfilePlatformStorage, ProfileStorageValidationError, STORE_KEY

PROFILE_BACKEND_ENTRY_ID = "profile_backend_entry_id"


_PROVIDER_CONFIG_KEYS = (
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_MARKET,
    CONF_SPOTIFY_SCOPES,
    CONF_HA_EXTERNAL_URL,
    CONF_MUSIC_ASSISTANT_PLAYER,
    CONF_MUSIC_BACKEND_REVISION,
)
_PROVIDER_STATE_KEYS = frozenset(
    {
        "spotify_access_token",
        "spotify_access_token_expires_at",
        "spotify_token_refresh_lock",
        "latest_spotify_refresh_token",
    }
)


class ProfileBackendView:
    """Stateless adapter view: caller context, existing provider auth/cache owner."""

    def __init__(self, hass: Any, caller: Any, provider: Any) -> None:
        object.__setattr__(self, "caller", caller)
        object.__setattr__(self, "_hass", hass)
        object.__setattr__(self, "_expected_provider", provider)

    @property
    def provider(self) -> Any:
        current = profile_backend_runtime(self._hass, self.caller, provider_only=True)
        if current is not self._expected_provider:
            raise ProfileStorageValidationError("profile_connection_unavailable")
        return current

    @property
    def entry(self) -> Any:
        # Existing token-rotation persistence writes the provider's original entry.
        return self.provider.entry

    @property
    def config(self) -> dict[str, Any]:
        provider = self.provider
        conf = dict(self.caller.config)
        source = provider.config
        for key in _PROVIDER_CONFIG_KEYS:
            if key in source:
                conf[key] = source[key]
        if getattr(self.provider, "latest_spotify_refresh_token", None):
            conf[CONF_SPOTIFY_REFRESH_TOKEN] = self.provider.latest_spotify_refresh_token
        return conf

    def __getattr__(self, name: str) -> Any:
        owner = (
            self.provider
            if name in _PROVIDER_STATE_KEYS
            or name
            in {
                "update_spotify_refresh_token",
                "get_current_spotify_credentials",
                "spotify_payload",
            }
            else self.caller
        )
        return getattr(owner, name)

    def __setattr__(self, name: str, value: Any) -> None:
        owner = self.provider if name in _PROVIDER_STATE_KEYS else self.caller
        setattr(owner, name, value)


def _profile_for_entry(household: Any, entry: Any) -> str:
    device_id = str(entry.data.get(CONF_DEVICE_ID) or "")
    device = household.devices.get(device_id)
    if device_id:
        return device.linked_profile_id if device else ""
    return str(entry.data.get("profile_id") or "")


def profile_backend_entry_id(hass: Any, profile_id: str) -> str:
    """Find one existing connection for the selected exact Profile/account binding."""
    manager = getattr(hass, "data", {}).get(DOMAIN, {}).get(STORE_KEY)
    if not isinstance(manager, ProfilePlatformStorage):
        raise ProfileStorageValidationError("profile_connection_unavailable")
    household = manager.household
    profile = household.profiles.get(profile_id)
    if profile is None or str(profile.state) != "active":
        raise ProfileStorageValidationError("profile_unavailable")
    prefs = profile.preferences
    if not prefs.default_backend_id or prefs.default_backend_id == MUSIC_BACKEND_LATER_MANUAL:
        return ""
    backend = household.music_backends.get(prefs.default_backend_id)
    account = household.music_accounts.get(prefs.default_music_account_id)
    if (
        backend is None
        or account is None
        or str(account.state) != "active"
        or account.backend_id != backend.backend_id
        or profile_id not in account.linked_profile_ids
    ):
        raise ProfileStorageValidationError("profile_connection_unavailable")
    entries = getattr(getattr(hass, "config_entries", None), "async_entries", lambda _: [])(DOMAIN)
    candidates = []
    for entry in entries:
        state = getattr(entry, "state", None)
        if (
            getattr(entry, "disabled_by", None) is not None
            or (state is not None and getattr(state, "value", state) != "loaded")
            or _profile_for_entry(household, entry) != profile_id
        ):
            continue
        conf = {**entry.data, **entry.options}
        if (
            conf.get(PROFILE_BACKEND_ENTRY_ID)
            or conf.get(CONF_MUSIC_BACKEND) != prefs.default_backend_id
        ):
            continue
        entry_account = str(conf.get("music_account_id") or "")
        if entry_account:
            if entry_account != account.account_id:
                continue
        else:
            # Original Assist entries omitted this field. Only their closed,
            # canonical single-account chain can establish the missing binding.
            linked = [
                a
                for a in household.music_accounts.values()
                if a.backend_id == backend.backend_id
                and profile_id in a.linked_profile_ids
                and str(a.state) == "active"
            ]
            if (
                len(linked) != 1
                or account.account_id != f"account-{backend.backend_id}-{profile_id}"
            ):
                continue
            if backend.backend_id == MUSIC_BACKEND_SPOTIFY_DIRECT and (
                not account.provider_account_id
                or account.provider_account_id != conf.get(CONF_SPOTIFY_CLIENT_ID)
            ):
                continue
        if prefs.default_backend_id == MUSIC_BACKEND_SPOTIFY_DIRECT and not conf.get(
            CONF_SPOTIFY_REFRESH_TOKEN
        ):
            continue
        if prefs.default_backend_id == MUSIC_BACKEND_MUSIC_ASSISTANT and not conf.get(
            CONF_MUSIC_ASSISTANT_PLAYER
        ):
            continue
        candidates.append(entry.entry_id)
    # Multiple provider owners are ambiguous even when their display names match.
    if len(candidates) != 1:
        raise ProfileStorageValidationError("profile_connection_unavailable")
    return candidates[0]


def profile_backend_runtime(hass: Any, runtime: Any, *, provider_only: bool = False) -> Any:
    """Resolve an onboarding-created reference against current trusted HA state."""
    if isinstance(runtime, ProfileBackendView):
        # A retained adapter may not renew its authority by rebinding a stale view.
        _ = runtime.provider
        runtime = runtime.caller
    entry = getattr(runtime, "entry", None)
    conf = {**getattr(entry, "data", {}), **getattr(entry, "options", {})}
    owner_id = str(conf.get(PROFILE_BACKEND_ENTRY_ID) or "")
    if not owner_id:
        return runtime
    data = getattr(hass, "data", {}).get(DOMAIN, {})
    manager = data.get(STORE_KEY)
    profile_id = str(
        getattr(runtime, "profile_context_profile_id", "") or conf.get("profile_id") or ""
    )
    if (
        not isinstance(manager, ProfilePlatformStorage)
        or entry is None
        or _profile_for_entry(manager.household, entry) != profile_id
    ):
        raise ProfileStorageValidationError("profile_connection_unavailable")
    profile = manager.household.profiles.get(profile_id)
    if (
        profile is None
        or str(conf.get("music_account_id") or "") != profile.preferences.default_music_account_id
    ):
        raise ProfileStorageValidationError("profile_connection_unavailable")
    if profile_backend_entry_id(hass, profile_id) != owner_id:
        raise ProfileStorageValidationError("profile_connection_unavailable")
    owner = data.get(owner_id)
    if owner is None or getattr(getattr(owner, "entry", None), "entry_id", None) != owner_id:
        raise ProfileStorageValidationError("profile_connection_unavailable")
    return owner if provider_only else ProfileBackendView(hass, runtime, owner)
