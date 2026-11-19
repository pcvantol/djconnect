"""Playback targets for DJConnect music backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..models import clean_identifier


class PlaybackZoneKind(StrEnum):
    """Known playback target categories."""

    ROOM = "room"
    SPOTIFY_DEVICE = "spotify_device"
    MUSIC_ASSISTANT_PLAYER = "music_assistant_player"
    GROUP = "group"
    HEADPHONES = "headphones"
    FUTURE_TARGET = "future_target"


class PlaybackZoneState(StrEnum):
    """Playback Zone lifecycle."""

    ACTIVE = "active"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class PlaybackZone:
    """A playback target, not a playback implementation."""

    zone_id: str
    display_name: str
    kind: PlaybackZoneKind
    backend_id: str = ""
    provider_target_id: str = ""
    room_id: str = ""
    state: PlaybackZoneState = PlaybackZoneState.ACTIVE
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate playback zone identity."""
        if not clean_identifier(self.zone_id):
            raise ValueError("zone_id is required")
        if not clean_identifier(self.display_name):
            raise ValueError("display_name is required")
