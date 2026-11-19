"""Music Backend registrations and capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..models import clean_identifier


class BackendProvider(StrEnum):
    """Known and future DJConnect music backend providers."""

    SPOTIFY_DIRECT = "spotify_direct"
    MUSIC_ASSISTANT = "music_assistant"
    FUTURE_PROVIDER = "future_provider"


class MusicBackendState(StrEnum):
    """Music Backend registration lifecycle."""

    ACTIVE = "active"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MusicBackendCapabilities:
    """Normalized backend capabilities."""

    search: bool = False
    playlists: bool = False
    queue: bool = False
    outputs: bool = False
    volume: bool = False
    favorites: bool = False
    recently_played: bool = False
    top_items: bool = False
    recommendations: bool = False
    library_profile: bool = False
    shuffle: bool = False
    repeat: bool = False
    seek: bool = False
    groups: bool = False


@dataclass(frozen=True)
class MusicBackendRegistration:
    """Provider adapter registration.

    The backend owns provider playback behavior and configuration. It does not
    own DJConnect user identity.
    """

    backend_id: str
    provider: BackendProvider
    display_name: str
    state: MusicBackendState = MusicBackendState.ACTIVE
    capabilities: MusicBackendCapabilities = field(default_factory=MusicBackendCapabilities)
    configuration: dict[str, Any] = field(default_factory=dict)
    revision: int = 0

    def __post_init__(self) -> None:
        """Validate backend identity."""
        if not clean_identifier(self.backend_id):
            raise ValueError("backend_id is required")
        if not clean_identifier(self.display_name):
            raise ValueError("display_name is required")
