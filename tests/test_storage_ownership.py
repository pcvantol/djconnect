"""Regression tests for the canonical storage ownership registry."""

from __future__ import annotations

from pathlib import Path
import sys
import types
import unittest


package = types.ModuleType("custom_components.djconnect")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")
]
sys.modules.setdefault("custom_components.djconnect", package)

from custom_components.djconnect.persistence.ownership import (  # noqa: E402
    STORAGE_OWNERSHIP,
    StorageClass,
    StorageProfile,
    storage_classes_for,
)


class StorageOwnershipTest(unittest.TestCase):
    def test_every_storage_class_has_one_server_owned_contract(self) -> None:
        self.assertEqual(set(STORAGE_OWNERSHIP), set(StorageClass))
        self.assertTrue(
            all(item.canonical_owner is StorageProfile.SERVER for item in STORAGE_OWNERSHIP.values())
        )

    def test_renderer_profiles_cannot_retain_canonical_product_stores(self) -> None:
        forbidden = {
            StorageClass.CANONICAL_PROFILE_STORE,
            StorageClass.CANONICAL_HISTORY_STORE,
            StorageClass.CANONICAL_DJPRINT_STORE,
            StorageClass.SCHEMA_AND_MIGRATION_STATE,
        }
        for profile in (
            StorageProfile.RICH_NATIVE_CLIENT,
            StorageProfile.BROWSER_RECEIVER,
            StorageProfile.PUBLICATION_HOST,
            StorageProfile.EMBEDDED_INTERACTION_HOST,
        ):
            self.assertFalse(forbidden & storage_classes_for(profile))

    def test_browser_storage_is_limited_to_disposable_projection_and_cache_state(self) -> None:
        self.assertEqual(
            storage_classes_for(StorageProfile.BROWSER_RECEIVER),
            {StorageClass.PREFERENCES, StorageClass.PROJECTION_STORE, StorageClass.ASSET_CACHE},
        )

    def test_runtime_objects_are_not_registered_as_durable_storage_classes(self) -> None:
        runtime_only = {
            "session_runtime",
            "performance_memory",
            "session_flow",
            "broadcast_cursor",
        }
        self.assertFalse(runtime_only & {item.value for item in StorageClass})

    def test_projections_and_caches_are_rebuildable_and_publication_assets_are_not_canonical(self) -> None:
        for storage_class in (
            StorageClass.PROJECTION_STORE,
            StorageClass.ASSET_CACHE,
            StorageClass.VOICE_REPLAY_CACHE,
            StorageClass.PUBLICATION_ASSET_STORE,
        ):
            self.assertTrue(STORAGE_OWNERSHIP[storage_class].rebuildable)
        self.assertNotIn(
            StorageClass.CANONICAL_DJPRINT_STORE,
            storage_classes_for(StorageProfile.PUBLICATION_HOST),
        )
