"""Machine-readable ownership boundary for DJConnect storage.

This registry classifies storage only.  It does not open storage, migrate data,
or authorize renderer persistence.  Home Assistant remains the authoritative
owner of canonical DJConnect data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StorageProfile(str, Enum):
    """The five supported host storage profiles."""

    SERVER = "server"
    RICH_NATIVE_CLIENT = "rich_native_client"
    BROWSER_RECEIVER = "browser_receiver"
    PUBLICATION_HOST = "persistent_publication_host"
    EMBEDDED_INTERACTION_HOST = "embedded_interaction_host"


class StorageClass(str, Enum):
    """Stable storage classes; runtime objects deliberately are not classes."""

    SECURE_DEVICE_STATE = "secure_device_state"
    PREFERENCES = "preferences"
    PROJECTION_STORE = "projection_store"
    PENDING_INTENT_STORE = "pending_intent_store"
    ASSET_CACHE = "asset_cache"
    VOICE_REPLAY_CACHE = "voice_replay_cache"
    PUBLICATION_ASSET_STORE = "publication_asset_store"
    EMBEDDED_INTERACTION_STATE = "embedded_interaction_state"
    CANONICAL_PROFILE_STORE = "canonical_profile_store"
    CANONICAL_HISTORY_STORE = "canonical_history_store"
    CANONICAL_DJPRINT_STORE = "canonical_djprint_store"
    SCHEMA_AND_MIGRATION_STATE = "schema_and_migration_state"


@dataclass(frozen=True)
class StorageOwnership:
    """One storage class's fixed ownership and recovery boundary."""

    storage_class: StorageClass
    canonical_owner: StorageProfile
    eligible_profiles: frozenset[StorageProfile]
    rebuildable: bool


SERVER = StorageProfile.SERVER

STORAGE_OWNERSHIP = {
    StorageClass.SECURE_DEVICE_STATE: StorageOwnership(
        StorageClass.SECURE_DEVICE_STATE,
        SERVER,
        frozenset({SERVER, StorageProfile.RICH_NATIVE_CLIENT, StorageProfile.EMBEDDED_INTERACTION_HOST}),
        False,
    ),
    StorageClass.PREFERENCES: StorageOwnership(
        StorageClass.PREFERENCES,
        SERVER,
        frozenset({profile for profile in StorageProfile}),
        True,
    ),
    StorageClass.PROJECTION_STORE: StorageOwnership(
        StorageClass.PROJECTION_STORE,
        SERVER,
        frozenset({profile for profile in StorageProfile}),
        True,
    ),
    StorageClass.PENDING_INTENT_STORE: StorageOwnership(
        StorageClass.PENDING_INTENT_STORE,
        SERVER,
        frozenset({SERVER, StorageProfile.RICH_NATIVE_CLIENT, StorageProfile.EMBEDDED_INTERACTION_HOST}),
        True,
    ),
    StorageClass.ASSET_CACHE: StorageOwnership(
        StorageClass.ASSET_CACHE, SERVER, frozenset({profile for profile in StorageProfile}), True
    ),
    StorageClass.VOICE_REPLAY_CACHE: StorageOwnership(
        StorageClass.VOICE_REPLAY_CACHE,
        SERVER,
        frozenset({SERVER, StorageProfile.RICH_NATIVE_CLIENT, StorageProfile.EMBEDDED_INTERACTION_HOST}),
        True,
    ),
    StorageClass.PUBLICATION_ASSET_STORE: StorageOwnership(
        StorageClass.PUBLICATION_ASSET_STORE,
        SERVER,
        frozenset({SERVER, StorageProfile.PUBLICATION_HOST}),
        True,
    ),
    StorageClass.EMBEDDED_INTERACTION_STATE: StorageOwnership(
        StorageClass.EMBEDDED_INTERACTION_STATE,
        SERVER,
        frozenset({SERVER, StorageProfile.EMBEDDED_INTERACTION_HOST}),
        True,
    ),
    StorageClass.CANONICAL_PROFILE_STORE: StorageOwnership(
        StorageClass.CANONICAL_PROFILE_STORE, SERVER, frozenset({SERVER}), False
    ),
    StorageClass.CANONICAL_HISTORY_STORE: StorageOwnership(
        StorageClass.CANONICAL_HISTORY_STORE, SERVER, frozenset({SERVER}), False
    ),
    StorageClass.CANONICAL_DJPRINT_STORE: StorageOwnership(
        StorageClass.CANONICAL_DJPRINT_STORE, SERVER, frozenset({SERVER}), False
    ),
    StorageClass.SCHEMA_AND_MIGRATION_STATE: StorageOwnership(
        StorageClass.SCHEMA_AND_MIGRATION_STATE, SERVER, frozenset({SERVER}), False
    ),
}


def storage_classes_for(profile: StorageProfile) -> frozenset[StorageClass]:
    """Return the classes a host profile may retain without gaining ownership."""
    return frozenset(
        storage_class
        for storage_class, ownership in STORAGE_OWNERSHIP.items()
        if profile in ownership.eligible_profiles
    )
