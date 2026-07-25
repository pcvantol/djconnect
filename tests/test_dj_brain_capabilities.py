"""Tests for trusted DJ Brain capability metadata and Planner policy gates."""

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

from custom_components.djconnect.dj_brain_capabilities import (  # noqa: E402
    CapabilityPolicy,
    CapabilityPolicyMode,
    DJBrainCapabilityRegistry,
    allowed_intents,
)
from custom_components.djconnect.domain import (  # noqa: E402
    Household,
    Profile,
)
from custom_components.djconnect.domain.storage import (  # noqa: E402
    household_from_storage,
    household_to_storage,
)
from custom_components.djconnect.session_runtime import (  # noqa: E402
    CandidatePlanningSlot,
    PlannerIntentSelector,
    PlanningWindow,
)


class DJBrainCapabilityRegistryTest(unittest.TestCase):
    """Keep the registry built-in, stable and policy-resolved."""

    def test_registry_exposes_only_trusted_built_ins(self) -> None:
        """No declaration is a dynamically supplied or executable package."""
        registry = DJBrainCapabilityRegistry()

        self.assertTrue(registry.all())
        self.assertTrue(all(item.origin == "built_in" for item in registry.all()))
        self.assertTrue(all(item.failure_semantics == "silence" for item in registry.all()))

    def test_full_minimal_and_custom_modes_resolve_deterministically(self) -> None:
        """Custom allowlists ignore unknown ids and partial capabilities."""
        registry = DJBrainCapabilityRegistry()

        self.assertIn("artist_story", allowed_intents(CapabilityPolicy(), registry))
        self.assertEqual(
            allowed_intents(
                CapabilityPolicy(CapabilityPolicyMode.MINIMAL), registry
            ),
            frozenset({"track_context", "transition", "session_update"}),
        )
        self.assertEqual(
            allowed_intents(
                CapabilityPolicy(
                    CapabilityPolicyMode.CUSTOM,
                    frozenset({"artist-story", "unknown", "discover"}),
                ),
                registry,
            ),
            frozenset({"artist_story"}),
        )


class CapabilityPolicyPersistenceTest(unittest.TestCase):
    """Keep the policy server-stored with the existing Profile record."""

    def test_profile_policy_round_trips_through_household_storage(self) -> None:
        """Profile policy remains portable without creating another store."""
        profile = Profile(
            profile_id="profile-capability-policy",
            display_name="Capability Policy",
            capability_policy=CapabilityPolicy(
                CapabilityPolicyMode.CUSTOM,
                frozenset({"artist-story", "unknown"}),
            ),
        )
        stored = household_to_storage(
            Household(
                household_id="household-policy",
                display_name="Policy Household",
                profiles={profile.profile_id: profile},
            )
        )

        loaded = household_from_storage(stored).profiles[profile.profile_id]

        self.assertEqual(loaded.capability_policy, profile.capability_policy)


class CapabilityPolicyPlannerGateTest(unittest.TestCase):
    """Verify policy filters planning before Knowledge or Moment realization."""

    def test_disallowed_candidate_is_not_selected(self) -> None:
        """An empty policy keeps the existing safe no-intent result."""
        window = PlanningWindow(
            starts_at="now",
            ends_at="now",
            candidate_slots=(CandidatePlanningSlot("artist_story", 0, 0, True),),
        )

        self.assertIsNone(
            PlannerIntentSelector.select(window, allowed_intents=frozenset())
        )
