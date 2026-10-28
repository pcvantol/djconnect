"""Passive ordinary-pair observation and synchronous local retirement.

There is deliberately no affirmative admission factory here. Ordinary HA
pairing/storage is not an acknowledged push-purpose commit. These records are
process-local negative fences, never an epoch, lease, signature or SDK grant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hmac
import re

ROLES = ("widget_transport", "status_activity_transport")
_MISSING = object()
_PREFIX = {"ios": "ios", "macos": "macos", "watchos": "watchos"}


@dataclass(repr=False)
class PairingRetirement:
    """Monotonic negative state; no method can reactivate this process record."""

    retired: bool = False
    revision: int = 0

    def retire(self):
        if not self.retired:
            self.retired = True
            self.revision += 1


def retire_runtime(runtime):
    fence = getattr(runtime, "surface_registration_retirement", None)
    if type(fence) is PairingRetirement:
        fence.retire()


def fence_pairing_change(runtime, *, token=_MISSING, device_id=_MISSING):
    """Call BEFORE assigning an actual new token/device, without scheduling."""
    if ((token is not _MISSING and token != getattr(runtime, "device_token", None))
            or (device_id is not _MISSING
                and device_id != getattr(runtime, "pairing_device_id", None))):
        retire_runtime(runtime)


def _header(headers, key):
    values = headers.getall(key, []) if hasattr(headers, "getall") else [headers.get(key)]
    if len(values) != 1 or type(values[0]) is not str:
        raise RegistrationReadError(400)
    return values[0]


class RegistrationReadError(ValueError):
    def __init__(self, status):
        super().__init__("surface_registration_unavailable")
        self.status = status


def _config(entry):
    return {**entry.data, **entry.options}


def _coordinates(runtime, entry):
    data = _config(entry)
    return (data.get("device_id"), data.get("client_type"),
            data.get("device_token"), data.get("ha_install_id"),
            getattr(runtime, "device_token", None),
            getattr(runtime, "pairing_device_id", None))


@dataclass(frozen=True, repr=False)
class PairedObservation:
    """Private comparison data from loaded objects, never persisted or exported."""

    runtime: object = field(repr=False)
    entry: object = field(repr=False)
    data: object = field(repr=False)
    options: object = field(repr=False)
    coordinates: tuple = field(repr=False)
    fence: object = field(repr=False)
    revision: int

    def current(self, hass):
        from .client_retirement import is_retired_entry
        from .retired_provider import TRANSFER_FENCE
        entry, runtime = self.entry, self.runtime
        domain = hass.data.get("djconnect", {})
        return (not hass.is_stopping
                and domain.get(entry.entry_id) is runtime
                and runtime.entry is entry
                and any(e is entry for e in hass.config_entries.async_entries("djconnect"))
                and entry.disabled_by is None and entry.state.value == "loaded"
                and not is_retired_entry(entry)
                and entry.entry_id not in domain.get(TRANSFER_FENCE, set())
                and entry.data is self.data and entry.options is self.options
                and _coordinates(runtime, entry) == self.coordinates
                and getattr(runtime, "surface_registration_retirement", None) is self.fence
                and type(self.fence) is PairingRetirement
                and not self.fence.retired
                and self.fence.revision == self.revision)


def observe_pair(hass, headers):
    """Pure exact authentication: no runtime.config, learning, Store or I/O."""
    from .client_retirement import is_retired_entry

    device_id = _header(headers, "X-DJConnect-Device-ID")
    client_type = _header(headers, "X-DJConnect-Client-Type")
    authorization = _header(headers, "Authorization")
    prefix = _PREFIX.get(client_type)
    if (prefix is None or re.fullmatch(r"djconnect-" + prefix + r"-[A-Za-z0-9]{12}", device_id) is None
            or not authorization.startswith("Bearer ") or len(authorization) > 4096):
        raise RegistrationReadError(401)
    token = authorization[7:]
    if not token or not token.isascii() or token != token.strip():
        raise RegistrationReadError(401)
    matches = []
    domain = hass.data.get("djconnect", {})
    for entry in hass.config_entries.async_entries("djconnect"):
        if entry.disabled_by is not None or entry.state.value != "loaded" or is_retired_entry(entry):
            continue
        runtime = domain.get(entry.entry_id)
        config = _config(entry)
        if runtime is not None and runtime.entry is entry and config.get("device_id") == device_id:
            matches.append((runtime, entry, config))
    if len(matches) != 1:
        raise RegistrationReadError(401)
    runtime, entry, config = matches[0]
    known = getattr(runtime, "device_token", None)
    if (type(known) is not str or not known.isascii() or not hmac.compare_digest(known, token)
            or config.get("device_token") != known):
        raise RegistrationReadError(401)
    if config.get("client_type") != client_type or runtime.pairing_device_id != device_id:
        raise RegistrationReadError(403)
    fence = getattr(runtime, "surface_registration_retirement", None)
    if type(fence) is not PairingRetirement:
        raise RegistrationReadError(503)
    snapshot = PairedObservation(runtime, entry, entry.data, entry.options,
                                 _coordinates(runtime, entry), fence, fence.revision)
    if not snapshot.current(hass):
        raise RegistrationReadError(503)
    return snapshot
