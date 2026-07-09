"""Device-owned DJConnect runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..models import clean_identifier


class DevicePairingState(StrEnum):
    """Device pairing lifecycle."""

    UNPAIRED = "unpaired"
    PENDING = "pending"
    PAIRED = "paired"
    STALE = "stale"


@dataclass(frozen=True)
class DeviceCapabilities:
    """Hardware/client runtime capabilities."""

    microphone: bool = False
    speaker: bool = False
    display: bool = False
    touch: bool = False
    notifications: bool = False
    voice: bool = False
    ask_dj: bool = False
    ask_dj_voice: bool = False
    playback_controls: bool = True
    ota: bool = False


@dataclass(frozen=True)
class DeviceRuntimeMetadata:
    """Local runtime metadata reported by a device/client."""

    firmware_version: str = ""
    app_version: str = ""
    protocol_version: str = ""
    local_url: str = ""
    ip_address: str = ""
    battery_percent: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Device:
    """Hardware, client and runtime context.

    Personal state is intentionally absent. Devices link to profiles; they do
    not own Music DNA, conversation history, recommendations, mood or style.
    """

    device_id: str
    client_type: str
    display_name: str = ""
    linked_profile_id: str = ""
    room_id: str = ""
    default_playback_zone_id: str = ""
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)
    pairing_state: DevicePairingState = DevicePairingState.UNPAIRED
    last_seen: str = ""
    runtime: DeviceRuntimeMetadata = field(default_factory=DeviceRuntimeMetadata)

    def __post_init__(self) -> None:
        """Validate required device identity."""
        if not clean_identifier(self.device_id):
            raise ValueError("device_id is required")
        if not clean_identifier(self.client_type):
            raise ValueError("client_type is required")
