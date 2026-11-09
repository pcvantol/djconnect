"""Explicit OAuth recovery for an orphaned shared Profile connection.

No credential is reused: the existing HA options flow obtains a fresh grant.
The original paired entry can become the connection owner only while the same
Profile/account has no remaining provider entry, including disabled entries.
"""

from __future__ import annotations

import re

from .const import DOMAIN, MUSIC_BACKEND_SPOTIFY_DIRECT
from .domain.storage import STORE_KEY, ProfilePlatformStorage
from .profile_backend import PROFILE_BACKEND_ENTRY_ID, _profile_for_entry


def binding(hass, entry):
    """Return public identity fences, or no recovery admission."""
    manager = hass.data.get(DOMAIN, {}).get(STORE_KEY)
    if not isinstance(manager, ProfilePlatformStorage):
        return None
    conf = {**entry.data, **entry.options}
    original = conf.get(PROFILE_BACKEND_ENTRY_ID)
    if (
        hass.config_entries.async_get_entry(entry.entry_id) is not entry
        or not original
        or hass.config_entries.async_get_entry(original) is not None
        or entry.disabled_by is not None
        or not conf.get("device_id")
    ):
        return None
    household = manager.household
    device = household.devices.get(conf["device_id"])
    if (
        device is None
        or device.client_type != conf.get("client_type")
        or re.fullmatch(r"[a-f0-9]{32}", device.binding_generation or "") is None
    ):
        return None
    profile = household.profiles.get(device.linked_profile_id)
    if profile is None or str(profile.state) != "active":
        return None
    prefs = profile.preferences
    backend = household.music_backends.get(prefs.default_backend_id)
    account = household.music_accounts.get(prefs.default_music_account_id)
    if (
        backend is None
        or str(backend.state) != "active"
        or backend.backend_id != MUSIC_BACKEND_SPOTIFY_DIRECT
        or account is None
        or str(account.state) != "active"
        or account.backend_id != backend.backend_id
        or profile.profile_id not in account.linked_profile_ids
        or not re.fullmatch(r"[a-fA-F0-9]{32}", account.provider_account_id or "")
    ):
        return None
    # An existing/disabled/unloaded owner must be restored through its own flow.
    # Never elect a second owner merely because an existing one is unavailable.
    for other in hass.config_entries.async_entries(DOMAIN):
        other_conf = {**other.data, **other.options}
        if (
            other.entry_id != entry.entry_id
            and _profile_for_entry(household, other) == profile.profile_id
            and not other_conf.get(PROFILE_BACKEND_ENTRY_ID)
            and other_conf.get("music_backend") == MUSIC_BACKEND_SPOTIFY_DIRECT
        ):
            return None
    return {
        "entry_id": entry.entry_id,
        "original_provider_entry_id": original,
        "device_id": conf["device_id"],
        "binding_generation": device.binding_generation,
        "client_type": conf["client_type"],
        "profile_id": profile.profile_id,
        "account_id": account.account_id,
        "backend_id": backend.backend_id,
        "client_id": account.provider_account_id,
    }


def for_config(hass, conf):
    """Find the exact existing entry represented by an options form."""
    entries = getattr(getattr(hass, "config_entries", None), "async_entries", lambda _: [])(DOMAIN)
    matches = [entry for entry in entries if entry.data.get("device_id") == conf.get("device_id")]
    return binding(hass, matches[0]) if len(matches) == 1 else None


def repaired_config(hass, entry, expected, client_id):
    """Recheck after OAuth awaits; return one HA-owned entry update, no secrets."""
    if not expected or binding(hass, entry) != expected or client_id != expected["client_id"]:
        raise ValueError("profile_connection_unavailable")
    data, options = dict(entry.data), dict(entry.options)
    for container in (data, options):
        container.pop(PROFILE_BACKEND_ENTRY_ID, None)
    data.update(
        profile_id=expected["profile_id"],
        music_account_id=expected["account_id"],
        music_backend_id=expected["backend_id"],
        music_backend=expected["backend_id"],
    )
    # Remove only stale overrides of the same repaired identity, never devices
    # or another Profile. The entry manager remains the sole persistence writer.
    for key in ("profile_id", "music_account_id", "music_backend_id", "music_backend"):
        options.pop(key, None)
    for key in ("spotify_client_id", "spotify_refresh_token", "spotify_market", "spotify_scopes", "spotify_scope_evidence"):
        options.pop(key, None)
    return data, options


def reauthorization_binding(hass, entry):
    """Resolve a linked device's current Profile connection, without credentials."""
    from .profile_backend import profile_backend_entry_id
    from .client_retirement import is_retired_entry

    manager = hass.data.get(DOMAIN, {}).get(STORE_KEY)
    if not isinstance(manager, ProfilePlatformStorage):
        return None
    entries = hass.config_entries
    if (entries.async_get_entry(entry.entry_id) is not entry
            or entry.disabled_by is not None or is_retired_entry(entry)):
        return None
    conf = {**entry.data, **entry.options}
    household = manager.household
    device = household.devices.get(conf.get("device_id"))
    if (device is None or device.client_type != conf.get("client_type")
            or re.fullmatch(r"[a-f0-9]{32}", device.binding_generation or "") is None):
        return None
    profile_id = device.linked_profile_id
    try:
        owner_id = profile_backend_entry_id(hass, profile_id)
    except ValueError:
        return None
    owner = entries.async_get_entry(owner_id)
    if owner is None or owner.disabled_by is not None:
        return None
    source = {**owner.data, **owner.options}
    profile = household.profiles[profile_id]
    backend = household.music_backends.get(profile.preferences.default_backend_id)
    account = household.music_accounts.get(profile.preferences.default_music_account_id)
    if (backend is None or str(backend.state) != "active"
            or backend.backend_id != MUSIC_BACKEND_SPOTIFY_DIRECT
            or account is None or source.get("spotify_client_id") != account.provider_account_id
            or not re.fullmatch(r"[a-fA-F0-9]{32}", account.provider_account_id or "")):
        return None
    original = conf.get(PROFILE_BACKEND_ENTRY_ID)
    if original and original != owner_id and entries.async_get_entry(original) is not None:
        return None  # Never reinterpret another surviving owner reference.
    if not original and entry is not owner:
        return None  # A credential-bearing entry is not a linked-device alias.
    owner_device = household.devices.get(source.get("device_id"))
    return {
        "requester_entry_id": entry.entry_id,
        "device_id": conf["device_id"], "client_type": device.client_type,
        "binding_generation": device.binding_generation,
        "original_provider_entry_id": original,
        "profile_id": profile_id, "account_id": account.account_id,
        "backend_id": backend.backend_id, "client_id": account.provider_account_id,
        "owner_entry_id": owner_id,
        "owner_binding_generation": getattr(owner_device, "binding_generation", None),
    }


def reauthorization_entries(hass, expected, client_id):
    """Revalidate the original public binding before committing a fresh grant."""
    entry = hass.config_entries.async_get_entry(expected["requester_entry_id"])
    if (entry is None or client_id != expected["client_id"]
            or reauthorization_binding(hass, entry) != expected):
        raise ValueError("profile_connection_unavailable")
    return entry, hass.config_entries.async_get_entry(expected["owner_entry_id"])


def reconnect_reference(hass, expected, client_id):
    """Reconcile only the explicitly selected linked device; never copy secrets."""
    entry, owner = reauthorization_entries(hass, expected, client_id)
    if entry is owner:
        return dict(entry.options)
    options = dict(entry.options)
    options.update(profile_backend_entry_id=owner.entry_id,
                   profile_id=expected["profile_id"],
                   music_account_id=expected["account_id"],
                   music_backend_id=expected["backend_id"],
                   music_backend=expected["backend_id"])
    return options
