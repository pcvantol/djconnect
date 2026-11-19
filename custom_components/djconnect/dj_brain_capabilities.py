"""Trusted built-in DJ Brain capability metadata and policy resolution.

The registry is deliberately metadata-only.  It neither loads third-party code
nor owns planning, knowledge, moment realization, session flow or broadcast.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapabilityPolicyMode(StrEnum):
    """Profile-owned selection of trusted built-in DJ Brain capabilities."""

    FULL = "full"
    MINIMAL = "minimal"
    CUSTOM = "custom"


@dataclass(frozen=True)
class DJBrainCapability:
    """Bounded declaration for one built-in capability package."""

    capability_id: str
    supported_intents: tuple[str, ...]
    version: str = "1"
    owner: str = "dj_intelligence"
    maturity: str = "current"
    stability: str = "stable"
    required_inputs: tuple[str, ...] = ("safe_track_insight",)
    produced_outputs: tuple[str, ...] = ("planner_intent",)
    safety_policy: str = "existing_runtime_safety"
    failure_semantics: str = "silence"
    qualification_profile: str = "session_intelligence"
    enabled_by_default: bool = True
    minimal_profile: bool = False
    group: str = "session_intelligence"
    origin: str = "built_in"


_BUILT_INS = (
    DJBrainCapability(
        "track-insight",
        ("track_context",),
        minimal_profile=True,
    ),
    DJBrainCapability("artist-story", ("artist_story",)),
    DJBrainCapability("album-story", ("album_story",)),
    DJBrainCapability("genre-story", ("genre_story",)),
    DJBrainCapability("recommendation", ("recommendation",)),
    DJBrainCapability("transition", ("transition",), minimal_profile=True),
    DJBrainCapability("session-update", ("session_update",), minimal_profile=True),
    DJBrainCapability(
        "discover",
        ("recommendation",),
        maturity="partial",
        stability="partial",
        qualification_profile="discover_session_start",
    ),
)


class DJBrainCapabilityRegistry:
    """Fixed, trusted registry of repository-owned built-in declarations."""

    def __init__(self, capabilities: tuple[DJBrainCapability, ...] = _BUILT_INS) -> None:
        if len({item.capability_id for item in capabilities}) != len(capabilities):
            raise ValueError("DJ Brain capability ids must be unique")
        if any(item.origin != "built_in" for item in capabilities):
            raise ValueError("DJ Brain capabilities must be built in")
        self._capabilities = tuple(sorted(capabilities, key=lambda item: item.capability_id))

    def all(self) -> tuple[DJBrainCapability, ...]:
        """Return immutable capability metadata; never executable packages."""
        return self._capabilities

    def for_intent(self, intent: str) -> tuple[DJBrainCapability, ...]:
        """Return built-in declarations that may support a Planner intent."""
        return tuple(item for item in self._capabilities if intent in item.supported_intents)


@dataclass(frozen=True)
class CapabilityPolicy:
    """Server-stored Profile policy; unknown custom ids resolve to no capability."""

    mode: CapabilityPolicyMode = CapabilityPolicyMode.FULL
    allowed_capability_ids: frozenset[str] = frozenset()

    def allows(self, capability: DJBrainCapability) -> bool:
        """Return whether this policy enables one stable built-in capability."""
        if capability.stability != "stable":
            return False
        if self.mode is CapabilityPolicyMode.FULL:
            return capability.enabled_by_default
        if self.mode is CapabilityPolicyMode.MINIMAL:
            return capability.minimal_profile
        return capability.capability_id in self.allowed_capability_ids


def allowed_intents(
    policy: CapabilityPolicy,
    registry: DJBrainCapabilityRegistry | None = None,
) -> frozenset[str]:
    """Resolve a policy to Planner-eligible semantic intents.

    Silence is intentionally not a capability: the existing Planner and Moment
    fallback remains available regardless of policy selection.
    """
    active_registry = registry or DJBrainCapabilityRegistry()
    return frozenset(
        intent
        for capability in active_registry.all()
        if policy.allows(capability)
        for intent in capability.supported_intents
    )
