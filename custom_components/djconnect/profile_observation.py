"""Read-only committed Profile observations, owned by normal integration setup.

Readers never create, load, repair or replace this state. Losing either lifetime
anchor closes observations. A new manager cannot clear an uncertain old write.
This is presentation evidence, never request execution authority.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import wraps
import weakref

DOMAIN = "djconnect"
STORE_KEY = "djconnect_profile_platform"
_WITNESS = "djconnect_committed_profile_observation_owner"

# Keep history through importlib.reload, but do not accept an old module epoch.
# Values MUST also be weak: owner -> domain -> manager -> hass is a real cycle.
if "_owners" not in globals():
    _owners = weakref.WeakKeyDictionary()
_epoch = object()


class _Owner:
    def __init__(self, domain):
        self.epoch = _epoch
        self.domain = domain
        self.manager = None
        self.store = None
        self.revision = 0
        self.pending = 0
        self.uncertain = False


def _owner(hass):
    """Lookup only; absence, split anchors and module reload are unavailable."""
    try:
        reference = _owners.get(hass)
        owner = reference() if reference is not None else None
        if (type(owner) is not _Owner or owner.epoch is not _epoch
                or hass.data.get(_WITNESS) is not owner
                or hass.data.get(DOMAIN) is not owner.domain):
            return None
        return owner
    except (AttributeError, TypeError):
        return None


def bootstrap_from_integration_setup(hass):
    """Only the integration's normal HA async_setup calls this cold entry point.

    Neither a reader, storage factory nor async_setup_entry may bootstrap. HA's
    normal component setup is once per Hass lifetime. A pre-existing untracked
    manager, one surviving anchor or a hot module reload cannot be adopted.
    Arbitrary deletion of all Python history and manual setup calls is outside
    this supported lifecycle; absence alone is never reader authorization.
    """
    try:
        if hass in _owners or _WITNESS in hass.data:
            return _owner(hass)
        domain = hass.data.setdefault(DOMAIN, {})
        if type(domain) is not dict:
            return None
        owner = _Owner(domain)
        owner.uncertain = STORE_KEY in domain
        hass.data[_WITNESS] = owner
        _owners[hass] = weakref.ref(owner)
        return owner
    except (AttributeError, TypeError):
        return None


def register_manager(manager):
    """Called by the real constructor, before a factory publishes the manager."""
    owner = _owner(manager.hass)
    if owner is None:
        return None
    owner.revision += 1
    if owner.manager is not None:
        # Replacement is not a new safe storage lifetime, even after a reload.
        owner.uncertain = True
    owner.manager = weakref.ref(manager)
    owner.store = manager._store
    return weakref.ref(owner)


def manager_changed(manager, *, uncertain=False):
    """Advance before every supported staging/restore/commit, including A-A."""
    reference = getattr(manager, "_observation_owner", None)
    owner = reference() if reference is not None else None
    if owner is not None:
        owner.revision += 1
        if uncertain:
            owner.uncertain = True


def publish_manager(hass, domain, manager):
    """The two normal factories share the same pre-publication revision hook."""
    owner = _owner(hass)
    if owner is not None:
        owner.revision += 1
        if (owner.domain is not domain or owner.manager is None
                or owner.manager() is not manager):
            owner.uncertain = True
    domain[STORE_KEY] = manager


def invalidate(hass):
    """Normal entry lifecycle invalidates prior snapshots before any await."""
    owner = _owner(hass)
    if owner is not None:
        owner.revision += 1


def tracked_transition(method):
    """Keep queued/active writes and failed compensation visible to readers.

    Retain the original owner before the first await, including after manager
    replacement. Do not alter the existing method's locks, shield or result.
    """
    @wraps(method)
    async def observed(manager, *args, **kwargs):
        reference = getattr(manager, "_observation_owner", None)
        owner = reference() if reference is not None else None
        if owner is not None:
            owner.pending += 1
            owner.revision += 1
        try:
            return await method(manager, *args, **kwargs)
        except BaseException:
            if owner is not None:
                owner.uncertain = True
            raise
        finally:
            if owner is not None:
                # A swallowed cancel may outlive a shielded file operation.
                task = asyncio.current_task()
                if task is not None and task.cancelling():
                    owner.uncertain = True
                owner.pending -= 1
                owner.revision += 1
    return observed


@dataclass(frozen=True)
class CommittedProfileObservation:
    hass: object
    owner: object
    manager: object
    store: object
    household: object
    revision: int
    authority_revision: int
    write_intent_revision: int

    def current(self):
        owner, manager = self.owner, self.manager
        return (_owner(self.hass) is owner and not owner.uncertain
                and owner.pending == 0 and owner.revision == self.revision
                and owner.manager is not None and owner.manager() is manager
                and owner.domain.get(STORE_KEY) is manager
                and manager._store is self.store and owner.store is self.store
                and manager._loaded is True and not manager._write_lock.locked()
                and manager._household is self.household
                and manager._committed_household is self.household
                and manager.authority_revision == self.authority_revision
                and manager._write_intent_revision == self.write_intent_revision)


def capture_committed(hass):
    """No defaults, mutations, Store access or cold load on the read path."""
    owner = _owner(hass)
    if owner is None or owner.uncertain or owner.pending or owner.manager is None:
        return None
    manager = owner.manager()
    if manager is None:
        return None
    snapshot = CommittedProfileObservation(
        hass, owner, manager, manager._store, manager._committed_household,
        owner.revision, manager.authority_revision, manager._write_intent_revision)
    return snapshot if snapshot.current() else None
