"""Staged retirement of an existing provider owner; no device authority transfer."""

from __future__ import annotations

import json
import asyncio
from copy import deepcopy
from contextlib import AsyncExitStack
from typing import Any

from .client_retirement import is_retired_entry
from .const import CLIENT_TYPES, CONF_CLIENT_TYPE, CONF_MUSIC_BACKEND, DOMAIN
from .domain.storage import STORE_KEY, ProfileStorageValidationError
from .profile_backend import PROFILE_BACKEND_ENTRY_ID, _PROVIDER_CONFIG_KEYS, _profile_for_entry

HISTORY_BINDINGS = "retired_provider_history_bindings"
TRANSFER_FENCE = "retired_provider_transfer_entries"


def _config(entry: Any) -> dict[str, Any]:
    return {**entry.data, **entry.options}


def _history_bindings(config: dict[str, Any]) -> dict[str, Any]:
    bindings = config.get(HISTORY_BINDINGS)
    return bindings if isinstance(bindings, dict) else {}


async def _save_verified(hass: Any) -> None:
    """Use the entry manager's sole Store writer, then read the actual file.

    HA exposes no public flush API. Keep this compatibility boundary explicit;
    unsupported managers fail closed. Store swallows WriteError, so its returned
    save alone is deliberately insufficient. No token values enter receipts.
    """
    manager = hass.config_entries
    store = getattr(manager, "_store", None)
    if store is None or not hasattr(store, "async_save") or not hasattr(store, "path"):
        raise ProfileStorageValidationError("profile_connection_unavailable")
    payload = {"entries": [entry.as_storage_fragment for entry in manager.async_entries()]}
    from homeassistant.helpers.json import json_bytes

    expected = json.loads(
        json_bytes({"entries": [item.as_dict() for item in manager.async_entries()]})
    )

    def read():
        with open(store.path, encoding="utf-8") as stream:
            return json.load(stream)["data"]

    async def finish_write():
        await store.async_save(payload)
        saved = await hass.async_add_executor_job(read)
        if saved != expected:
            raise ProfileStorageValidationError("profile_connection_unavailable")

    # Cancelling an executor await can release Store's lock while the file write
    # continues. Keep parent ownership/fences until the sole writer and readback
    # actually finish, then propagate cancellation at a durable stage boundary.
    task = asyncio.create_task(finish_write())
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    task.result()
    if cancelled:
        raise asyncio.CancelledError


async def async_transfer_retired_provider(hass: Any, donor: Any) -> bool:
    """Transfer only one existing exact peer binding, otherwise keep quarantine.

    Prepared peers still reference the original owner. Activated donor/references
    are disk-verified before donor credentials are removed. Every incomplete
    stage retains credentials in an existing entry and can be retried after
    normal HA restart; this does not claim power-loss atomicity of HA storage.
    """
    if not is_retired_entry(donor):
        return False
    data = hass.data.get(DOMAIN, {})
    storage = data.get(STORE_KEY)
    runtime = data.get(donor.entry_id)
    if storage is None or runtime is None:
        return False
    if donor.disabled_by is not None or getattr(donor.state, "value", donor.state) != "loaded":
        return False
    from .spotify_backend import _token_refresh_lock

    async with AsyncExitStack() as locks:
        # Use HA's own entry lifecycle locks before provider refresh ownership.
        # Removal/unload must not delete an activated successor during readback.
        owner_ref = _config(donor).get(PROFILE_BACKEND_ENTRY_ID)
        related = [
            item
            for item in hass.config_entries.async_entries(DOMAIN)
            if item.entry_id in {donor.entry_id, owner_ref}
            or _config(item).get(PROFILE_BACKEND_ENTRY_ID) == donor.entry_id
        ]
        for item in sorted(related, key=lambda current: current.entry_id):
            await locks.enter_async_context(item.setup_lock)
        # Existing housekeeping can already be between eligibility and its
        # database write. Follow lifecycle -> maintenance -> refresh ordering.
        await locks.enter_async_context(
            data.setdefault("session_history_maintenance_lock", asyncio.Lock())
        )
        await locks.enter_async_context(_token_refresh_lock(runtime))
        if (
            hass.config_entries.async_get_entry(donor.entry_id) is not donor
            or data.get(donor.entry_id) is not runtime
        ):
            return False
        household = await storage.async_load()
        profile_id = _profile_for_entry(household, donor)
        profile = household.profiles.get(profile_id)
        config = _config(donor)
        if getattr(runtime, "latest_spotify_refresh_token", None):
            config["spotify_refresh_token"] = runtime.latest_spotify_refresh_token
        account = household.music_accounts.get(config.get("music_account_id"))
        backend = household.music_backends.get(config.get(CONF_MUSIC_BACKEND))
        if (
            profile is None
            or str(profile.state) != "active"
            or account is None
            or str(account.state) != "active"
            or backend is None
            or str(backend.state) != "active"
            or profile_id not in account.linked_profile_ids
            or account.backend_id != backend.backend_id
            or profile.preferences.default_backend_id != backend.backend_id
            or profile.preferences.default_music_account_id != account.account_id
        ):
            return False
        entries = hass.config_entries.async_entries(DOMAIN)
        current_ref = _config(donor).get(PROFILE_BACKEND_ENTRY_ID)
        current_related = [
            item
            for item in entries
            if item.entry_id in {donor.entry_id, current_ref}
            or _config(item).get(PROFILE_BACKEND_ENTRY_ID) == donor.entry_id
        ]
        locked = {item.entry_id: item for item in related}
        if set(locked) != {item.entry_id for item in current_related} or any(
            locked.get(item.entry_id) is not item for item in current_related
        ):
            return False
        successor_id = str(config.get(PROFILE_BACKEND_ENTRY_ID) or "")
        if str(backend.provider) not in {"spotify_direct", "music_assistant"}:
            return False
        if not successor_id and (
            str(backend.provider) == "spotify_direct"
            and not (config.get("spotify_client_id") and config.get("spotify_refresh_token"))
            or str(backend.provider) == "music_assistant"
            and not config.get("music_assistant_player")
        ):
            return False
        peers = []
        for candidate in entries:
            conf = _config(candidate)
            if (
                candidate.entry_id == donor.entry_id
                or is_retired_entry(candidate)
                or candidate.disabled_by is not None
                or getattr(candidate.state, "value", candidate.state) != "loaded"
                or str(conf.get(CONF_CLIENT_TYPE) or "") not in CLIENT_TYPES
                or data.get(candidate.entry_id) is None
                or _profile_for_entry(household, candidate) != profile_id
                or conf.get("music_account_id") != account.account_id
                or conf.get(CONF_MUSIC_BACKEND) != backend.backend_id
            ):
                continue
            if successor_id:
                binding = _history_bindings(conf).get(donor.entry_id, {})
                if not isinstance(binding, dict):
                    continue
                if (
                    candidate.entry_id == successor_id
                    and binding.get("state") == "active"
                    and binding.get("version") == 1
                    and binding.get("profile_id") == profile_id
                    and binding.get("backend_id") == backend.backend_id
                    and binding.get("music_account_id") == account.account_id
                    and binding.get("provider_account_id") == str(account.provider_account_id)
                    and not conf.get(PROFILE_BACKEND_ENTRY_ID)
                    and (
                        conf.get("spotify_client_id") and conf.get("spotify_refresh_token")
                        if str(backend.provider) == "spotify_direct"
                        else conf.get("music_assistant_player")
                    )
                ):
                    peers.append(candidate)
            elif conf.get(PROFILE_BACKEND_ENTRY_ID) == donor.entry_id:
                peers.append(candidate)
        if len(peers) != 1:
            return False
        successor = peers[0]
        revoked = data.get("spotify_reauth_issue_throttle", {})
        if donor.entry_id in revoked or successor.entry_id in revoked:
            return False
        from homeassistant.helpers import issue_registry

        issue = issue_registry.async_get(hass).async_get_issue(
            DOMAIN, "spotify_refresh_token_revoked"
        )
        if issue is not None and (issue.data or {}).get("entry_id") in {
            donor.entry_id,
            successor.entry_id,
        }:
            return False
        original = {
            item.entry_id: (deepcopy(dict(item.data)), deepcopy(dict(item.options)))
            for item in entries
        }
        affected = [donor, successor]
        if not successor_id:
            # Any unrelated owner or destination-owned credentials are ambiguous.
            from .profile_backend import profile_backend_entry_id

            if profile_backend_entry_id(hass, profile_id) != donor.entry_id:
                return False
            recipient = _config(successor)
            if any(
                HISTORY_BINDINGS in values and not isinstance(values[HISTORY_BINDINGS], dict)
                for values in (successor.data, successor.options)
            ):
                return False
            previous_binding = _history_bindings(recipient).get(donor.entry_id, {})
            prepared = isinstance(previous_binding, dict) and previous_binding == {
                "version": 1,
                "state": "prepared",
                "profile_id": profile_id,
                "backend_id": backend.backend_id,
                "music_account_id": account.account_id,
                "provider_account_id": str(account.provider_account_id),
            }
            if previous_binding and not prepared:
                return False
            if prepared and any(
                recipient.get(key) != config.get(key) for key in _PROVIDER_CONFIG_KEYS
            ):
                return False
            if not prepared and any(
                recipient.get(key) for key in ("spotify_refresh_token", "music_assistant_player")
            ):
                return False
        affected.extend(
            item
            for item in entries
            if item not in affected
            and _config(item).get(PROFILE_BACKEND_ENTRY_ID) == donor.entry_id
        )
        # Include old references on resumed activation as well. Every existing
        # reference must agree with the original server-owned account binding.
        if any(
            _profile_for_entry(household, item) != profile_id
            or _config(item).get("music_account_id") != account.account_id
            or _config(item).get(CONF_MUSIC_BACKEND) != backend.backend_id
            for item in affected
        ):
            return False
        fence = data.setdefault(TRANSFER_FENCE, set())
        expected_runtimes = {item.entry_id: data.get(item.entry_id) for item in affected}
        owned_keys = (*_PROVIDER_CONFIG_KEYS, PROFILE_BACKEND_ENTRY_ID, HISTORY_BINDINGS)
        planned = {
            item.entry_id: (deepcopy(dict(item.data)), deepcopy(dict(item.options)))
            for item in affected
        }
        initial_latest_token = getattr(runtime, "latest_spotify_refresh_token", None)
        external_updates = set()
        fence.update(item.entry_id for item in affected)

        def update_owned(item, item_data, item_options):
            hass.config_entries.async_update_entry(item, data=item_data, options=item_options)
            planned[item.entry_id] = (deepcopy(item_data), deepcopy(item_options))

        def validate_current():
            if hass.data.get(DOMAIN) is not data or data.get(STORE_KEY) is not storage:
                raise ProfileStorageValidationError("profile_connection_unavailable")
            if any(
                item.entry_id not in expected_runtimes
                and _config(item).get(PROFILE_BACKEND_ENTRY_ID) == donor.entry_id
                for item in hass.config_entries.async_entries(DOMAIN)
            ):
                raise ProfileStorageValidationError("profile_connection_unavailable")
            current_issue = issue_registry.async_get(hass).async_get_issue(
                DOMAIN, "spotify_refresh_token_revoked"
            )
            if (
                {donor.entry_id, successor.entry_id}.intersection(
                    data.get("spotify_reauth_issue_throttle", {})
                )
                or current_issue is not None
                and (current_issue.data or {}).get("entry_id")
                in {donor.entry_id, successor.entry_id}
            ):
                raise ProfileStorageValidationError("profile_connection_unavailable")
            current = storage.household
            current_profile = current.profiles.get(profile_id)
            current_account = current.music_accounts.get(account.account_id)
            current_backend = current.music_backends.get(backend.backend_id)
            if (
                current_profile is None
                or str(current_profile.state) != "active"
                or current_account is None
                or str(current_account.state) != "active"
                or current_backend is None
                or str(current_backend.state) != "active"
                or current_account.backend_id != backend.backend_id
                or str(current_account.provider_account_id) != str(account.provider_account_id)
                or str(current_backend.provider) != str(backend.provider)
                or profile_id not in current_account.linked_profile_ids
                or current_profile.preferences.default_backend_id != backend.backend_id
                or current_profile.preferences.default_music_account_id != account.account_id
            ):
                raise ProfileStorageValidationError("profile_connection_unavailable")
            for item in affected:
                current_config = _config(item)
                expected_data, expected_options = planned[item.entry_id]
                if any(
                    (key in actual) != (key in expected) or actual.get(key) != expected.get(key)
                    for actual, expected in (
                        (item.data, expected_data),
                        (item.options, expected_options),
                    )
                    for key in owned_keys
                ):
                    external_updates.add(item.entry_id)
                    raise ProfileStorageValidationError("profile_connection_unavailable")
                if (
                    hass.config_entries.async_get_entry(item.entry_id) is not item
                    or item in (donor, successor)
                    and (
                        item.disabled_by is not None
                        or getattr(item.state, "value", item.state) != "loaded"
                    )
                    or data.get(item.entry_id) is not expected_runtimes[item.entry_id]
                    or _profile_for_entry(current, item) != profile_id
                    or current_config.get("music_account_id") != account.account_id
                    or current_config.get(CONF_MUSIC_BACKEND) != backend.backend_id
                ):
                    raise ProfileStorageValidationError("profile_connection_unavailable")
            from .client_identity import device_id_matches_client_type

            successor_config = _config(successor)
            if is_retired_entry(successor) or not device_id_matches_client_type(
                successor_config.get("device_id"), successor_config.get(CONF_CLIENT_TYPE)
            ):
                raise ProfileStorageValidationError("profile_connection_unavailable")
            if data.get(donor.entry_id) is not runtime:
                raise ProfileStorageValidationError("profile_connection_unavailable")
            if getattr(runtime, "latest_spotify_refresh_token", None) != initial_latest_token:
                external_updates.add(donor.entry_id)
                raise ProfileStorageValidationError("profile_connection_unavailable")

        try:
            validate_current()
            if not successor_id:
                binding = {
                    "version": 1,
                    "state": "prepared",
                    "profile_id": profile_id,
                    "backend_id": backend.backend_id,
                    "music_account_id": account.account_id,
                    "provider_account_id": str(account.provider_account_id),
                }
                target_data = dict(successor.data)
                target_options = dict(successor.options)
                for key in _PROVIDER_CONFIG_KEYS:
                    target_options.pop(key, None)
                    if key in config:
                        target_data[key] = config[key]
                target_options.pop(HISTORY_BINDINGS, None)
                target_data[HISTORY_BINDINGS] = {
                    **_history_bindings(recipient),
                    donor.entry_id: binding,
                }
                update_owned(successor, target_data, target_options)
                await _save_verified(hass)
                validate_current()
                # HA wraps the passed dictionaries without copying them. Never
                # mutate a previously passed mapping or its nested bindings.
                target_data = deepcopy(dict(successor.data))
                target_options = deepcopy(dict(successor.options))
                target_data.pop(PROFILE_BACKEND_ENTRY_ID, None)
                target_options.pop(PROFILE_BACKEND_ENTRY_ID, None)
                target_data[HISTORY_BINDINGS][donor.entry_id] = {**binding, "state": "active"}
                update_owned(successor, target_data, target_options)
                for item in affected:
                    if item is successor:
                        continue
                    item_data, item_options = dict(item.data), dict(item.options)
                    item_options.pop(PROFILE_BACKEND_ENTRY_ID, None)
                    item_data[PROFILE_BACKEND_ENTRY_ID] = successor.entry_id
                    update_owned(item, item_data, item_options)
                await _save_verified(hass)
                validate_current()
            elif any(
                item not in (donor, successor)
                and _config(item).get(PROFILE_BACKEND_ENTRY_ID) == donor.entry_id
                for item in affected
            ):
                for item in affected:
                    if item in (donor, successor):
                        continue
                    item_data, item_options = dict(item.data), dict(item.options)
                    item_options.pop(PROFILE_BACKEND_ENTRY_ID, None)
                    item_data[PROFILE_BACKEND_ENTRY_ID] = successor.entry_id
                    update_owned(item, item_data, item_options)
                await _save_verified(hass)
                validate_current()
            donor_data, donor_options = dict(donor.data), dict(donor.options)
            for key in _PROVIDER_CONFIG_KEYS:
                donor_data.pop(key, None)
                donor_options.pop(key, None)
            update_owned(donor, donor_data, donor_options)
            await _save_verified(hass)
            validate_current()
            successor_runtime = data.get(successor.entry_id)
            successor_runtime.latest_spotify_refresh_token = _config(successor).get(
                "spotify_refresh_token"
            )
            successor_runtime.spotify_access_token = None
            successor_runtime.spotify_access_token_expires_at = None
            runtime.latest_spotify_refresh_token = None
            runtime.spotify_access_token = None
            runtime.spotify_access_token_expires_at = None
            initial_latest_token = None
            return True
        except (Exception, asyncio.CancelledError):
            # Restore the complete prior ownership before releasing our listener
            # fence. Failure of the readback/rollback must not claim completion.
            for item in affected:
                before_data, before_options = original[item.entry_id]
                if hass.config_entries.async_get_entry(item.entry_id) is not item:
                    continue
                # Roll back only fields owned by this transfer. Preserve any
                # concurrent management change to identity/Profile/account.
                restored_data, restored_options = dict(item.data), dict(item.options)
                expected_data, expected_options = planned[item.entry_id]
                for actual, expected, before in (
                    (restored_data, expected_data, before_data),
                    (restored_options, expected_options, before_options),
                ):
                    for key in owned_keys:
                        if (key in actual) != (key in expected) or actual.get(key) != expected.get(
                            key
                        ):
                            external_updates.add(item.entry_id)
                            continue
                        actual.pop(key, None)
                        if key in before:
                            actual[key] = deepcopy(before[key])
                hass.config_entries.async_update_entry(
                    item, data=restored_data, options=restored_options
                )
                planned[item.entry_id] = (deepcopy(restored_data), deepcopy(restored_options))
            await _save_verified(hass)
            raise
        finally:
            fence.difference_update(item.entry_id for item in affected)
            # Only acknowledge our own changes. Replay concurrent management
            # updates after lifecycle locks are released, using the normal
            # listener; it may need to unload/reload that entry.
            from . import _async_update_listener, _entry_reload_signature

            signatures = data.setdefault("entry_reload_signatures", {})
            for item in affected:
                before_data, before_options = original[item.entry_id]
                actual = _config(item)
                before = {**before_data, **before_options}
                expected_data, expected_options = planned[item.entry_id]
                if any(
                    (key in current) != (key in expected) or current.get(key) != expected.get(key)
                    for current, expected in (
                        (item.data, expected_data),
                        (item.options, expected_options),
                    )
                    for key in owned_keys
                ):
                    external_updates.add(item.entry_id)
                if (
                    item is donor
                    and getattr(runtime, "latest_spotify_refresh_token", None)
                    != initial_latest_token
                ):
                    external_updates.add(item.entry_id)
                if {key: value for key, value in actual.items() if key not in owned_keys} != {
                    key: value for key, value in before.items() if key not in owned_keys
                }:
                    external_updates.add(item.entry_id)
                if item.entry_id in external_updates:
                    hass.async_create_task(_async_update_listener(hass, item))
                else:
                    signatures[item.entry_id] = _entry_reload_signature(item)


def historical_successor(
    hass: Any, donor_id: str, owner: str, captured: dict[str, Any]
) -> Any | None:
    """Resolve immutable captured history through a closed stored handoff only."""
    storage = hass.data.get(DOMAIN, {}).get(STORE_KEY)
    if storage is None:
        return None
    household = storage.household
    profile = household.profiles.get(owner)
    account = household.music_accounts.get(captured.get("music_account_id"))
    backend = household.music_backends.get(captured.get("backend_id"))
    if (
        profile is None
        or str(profile.state) != "active"
        or account is None
        or str(account.state) != "active"
        or backend is None
        or str(backend.state) != "active"
        or account.backend_id != backend.backend_id
        or owner not in account.linked_profile_ids
        or str(account.provider_account_id) != str(captured.get("provider_account_id") or "")
    ):
        return None
    matches = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        conf = _config(entry)
        binding = _history_bindings(conf).get(donor_id)
        if (
            not isinstance(binding, dict)
            or binding.get("version") != 1
            or binding.get("state") != "active"
        ):
            continue
        if (
            entry.disabled_by is not None
            or is_retired_entry(entry)
            or binding.get("profile_id") != owner
        ):
            continue
        from .client_identity import device_id_matches_client_type

        if _profile_for_entry(household, entry) != owner or not device_id_matches_client_type(
            conf.get("device_id"), conf.get(CONF_CLIENT_TYPE)
        ):
            continue
        if getattr(entry.state, "value", entry.state) != "loaded" or conf.get(
            PROFILE_BACKEND_ENTRY_ID
        ):
            continue
        if (
            conf.get("music_account_id") != account.account_id
            or conf.get(CONF_MUSIC_BACKEND) != backend.backend_id
        ):
            continue
        if any(
            str(binding.get(key) or "") != str(captured.get(key) or "")
            for key in ("backend_id", "music_account_id", "provider_account_id")
        ):
            continue
        matches.append(entry)
    return matches[0] if len(matches) == 1 else None
