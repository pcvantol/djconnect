"""Pure ordinary-pair capture for the separate Direct rich family.

An existing PairJournal ACK is a necessary identity input, never display
permission. No reader records pairing, learns auth or adopts restored secrets.
The weak negative registry only lets the genuine runtime retirement hook fence
captures synchronously, including an auth A-to-B-to-A transition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hmac
import weakref

from .direct_rich_wire import DEVICE, RichError, original_uuid, require
from .persistence import PERSISTENCE_SERVICE_KEY, PersistenceService
from .surface_pair_journal import LocalPairRecord, PairRegistration
from .surface_registration import PairingRetirement, _coordinates, _header

_EPOCH = object()
if "_captures" not in globals():
    _captures = weakref.WeakSet()


def retire_runtime(runtime):
    """Negative only; called before the actual runtime token/device mutation."""
    for capture in tuple(_captures):
        if capture.runtime is runtime:
            capture.retire()


@dataclass(eq=False, repr=False)
class DirectRichPair:
    hass: object
    domain: object
    runtime: object
    entry: object
    data: object
    options: object
    coordinates: tuple
    registration: object
    acknowledgement: object
    persistence: object
    provider: object
    readiness: object
    path: str
    epoch: object = field(default_factory=lambda: _EPOCH)
    retired: bool = False

    @property
    def device_id(self):
        return self.coordinates[0] if self.coordinates is not None else None

    @property
    def client_type(self):
        return self.coordinates[1] if self.coordinates is not None else None

    def retire(self):
        self.retired = True
        _captures.discard(self)
        # A consumer may keep this closed handle indefinitely. It must not keep
        # the old ordinary bearer, entry dictionaries or owning object graph.
        for name in ("hass", "domain", "runtime", "entry", "data", "options",
                "coordinates", "registration", "acknowledgement", "persistence",
                "provider", "readiness", "path", "epoch"):
            setattr(self, name, None)

    def current(self):
        if self.retired:
            return False
        try:
            registration, persistence = self.registration, self.persistence
            valid = (self.epoch is _EPOCH and not self.hass.is_stopping
                and self.hass.data.get("djconnect") is self.domain
                and self.domain.get(self.entry.entry_id) is self.runtime
                and self.entry.data is self.data and self.entry.options is self.options
                and _coordinates(self.runtime, self.entry) == self.coordinates
                and self.runtime.surface_pair_registration is registration
                and registration.current() and registration.phase == "recorded"
                and registration.acknowledgement is self.acknowledgement
                and self.domain.get(PERSISTENCE_SERVICE_KEY) is persistence
                and registration.journal.persistence is persistence
                and persistence._provider is self.provider
                and persistence.readiness is self.readiness and self.readiness.ready
                and persistence._database_path == self.path)
        except (AttributeError, KeyError, TypeError):
            valid = False
        if not valid:
            self.retire()  # A later equality/replacement cannot rearm this original.
        return bool(valid)


def capture_pair(hass, headers, *, device_id, client_type):
    """Lookup only, before the caller's first await. No positive policy result.

    The older surface family's retired bit is not an ordinary credential
    revocation. Its genuine PairRegistration retirement/revision still applies;
    an absent, pending, replaced or retired original ACK is never synthesized.
    """
    from .client_retirement import is_retired_entry
    from .surface_registration import RegistrationReadError
    try:
        device = _header(headers, "X-DJConnect-Device-ID")
        client = _header(headers, "X-DJConnect-Client-Type")
        authorization = _header(headers, "Authorization")
    except RegistrationReadError:
        raise RichError("invalid_request", 400) from None
    require(type(device_id) is str and DEVICE.fullmatch(device_id) is not None
        and type(client_type) is str and client_type in {"ios", "macos"} and device == device_id
        and client == client_type and device.startswith("djconnect-" + client + "-"),
        "unauthorized", 401)
    require(authorization.startswith("Bearer ") and len(authorization) <= 4096,
        "unauthorized", 401)
    token = authorization[7:]
    require(bool(token) and token.isascii() and token == token.strip(), "unauthorized", 401)
    domain = hass.data.get("djconnect", {})
    matches = []
    for entry in hass.config_entries.async_entries("djconnect"):
        if entry.disabled_by is not None or entry.state.value != "loaded" or is_retired_entry(entry):
            continue
        runtime = domain.get(entry.entry_id)
        config = {**entry.data, **entry.options}
        if runtime is not None and runtime.entry is entry and config.get("device_id") == device:
            matches.append((runtime, entry, config))
    require(len(matches) == 1, "unauthorized", 401)
    runtime, entry, config = matches[0]
    known = getattr(runtime, "device_token", None)
    require(type(known) is str and known.isascii() and hmac.compare_digest(known, token)
        and config.get("device_token") == known, "unauthorized", 401)
    require(config.get("client_type") == client and runtime.pairing_device_id == device,
        "rich_not_allowed", 403)
    registration = getattr(runtime, "surface_pair_registration", None)
    persistence = domain.get(PERSISTENCE_SERVICE_KEY)
    require(type(registration) is PairRegistration and type(persistence) is PersistenceService
        and registration.hass is hass and registration.runtime is runtime
        and registration.entry is entry and registration.phase == "recorded"
        and registration.current() and not registration.retired
        and type(registration.fence) is PairingRetirement,
        "rich_unavailable", 503)
    ack = registration.acknowledgement
    require(type(ack) is LocalPairRecord and original_uuid(ack.instance_id)
        and original_uuid(ack.auth_generation), "rich_unavailable", 503)
    capture = DirectRichPair(hass, domain, runtime, entry, entry.data, entry.options,
        _coordinates(runtime, entry), registration, ack, persistence,
        persistence._provider, persistence.readiness, persistence._database_path)
    require(capture.current(), "rich_unavailable", 503)
    _captures.add(capture)
    return capture
