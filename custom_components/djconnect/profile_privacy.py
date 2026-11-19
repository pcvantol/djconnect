"""Profile privacy policy helpers for DJConnect."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import ProfilePrivacyMode, ProfileType


@dataclass(frozen=True)
class ProfilePrivacyPolicy:
    """Resolved persistence/export policy for one Profile request."""

    mode: ProfilePrivacyMode
    private_session: bool = False
    allow_history_persistence: bool = True
    allow_music_dna_persistence: bool = True
    allow_recommendation_persistence: bool = True
    allow_mood_persistence: bool = True
    allow_personal_read: bool = True
    allow_profile_export: bool = True

    @property
    def suppresses_personal_persistence(self) -> bool:
        """Return whether this request must avoid personal state writes."""
        return not (
            self.allow_history_persistence
            or self.allow_music_dna_persistence
            or self.allow_recommendation_persistence
            or self.allow_mood_persistence
        )


def resolve_profile_privacy_policy(profile: Any, payload: dict[str, Any] | None = None) -> ProfilePrivacyPolicy:
    """Resolve the privacy policy for a Profile plus request payload."""
    payload = payload or {}
    mode = _privacy_mode(payload.get("privacy_mode") or getattr(profile, "privacy_mode", None))
    profile_type = getattr(profile, "profile_type", ProfileType.PERSONAL)
    if profile_type == ProfileType.GUEST:
        mode = ProfilePrivacyMode.GUEST_SAFE
    private_session = _truthy(payload.get("private_session")) or mode == ProfilePrivacyMode.PRIVATE
    if private_session:
        return ProfilePrivacyPolicy(
            mode=ProfilePrivacyMode.PRIVATE,
            private_session=True,
            allow_history_persistence=False,
            allow_music_dna_persistence=False,
            allow_recommendation_persistence=False,
            allow_mood_persistence=False,
            allow_personal_read=True,
            allow_profile_export=False,
        )
    if mode == ProfilePrivacyMode.GUEST_SAFE:
        return ProfilePrivacyPolicy(
            mode=mode,
            allow_history_persistence=False,
            allow_music_dna_persistence=False,
            allow_recommendation_persistence=False,
            allow_mood_persistence=False,
            allow_personal_read=False,
            allow_profile_export=False,
        )
    if mode == ProfilePrivacyMode.SHARED:
        return ProfilePrivacyPolicy(
            mode=mode,
            allow_history_persistence=False,
            allow_music_dna_persistence=False,
            allow_recommendation_persistence=False,
            allow_mood_persistence=False,
            allow_personal_read=False,
            allow_profile_export=True,
        )
    return ProfilePrivacyPolicy(mode=ProfilePrivacyMode.NORMAL)


def privacy_response_metadata(policy: ProfilePrivacyPolicy) -> dict[str, Any]:
    """Return client-visible privacy metadata."""
    return {
        "privacy_mode": policy.mode.value,
        "private_session": policy.private_session,
        "personal_persistence": {
            "ask_dj_history": policy.allow_history_persistence,
            "music_dna": policy.allow_music_dna_persistence,
            "recommendations": policy.allow_recommendation_persistence,
            "mood": policy.allow_mood_persistence,
        },
        "personal_read_allowed": policy.allow_personal_read,
        "profile_export_allowed": policy.allow_profile_export,
    }


def _privacy_mode(value: Any) -> ProfilePrivacyMode:
    try:
        return ProfilePrivacyMode(str(value))
    except (TypeError, ValueError):
        return ProfilePrivacyMode.NORMAL


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "private"}
    return bool(value)
