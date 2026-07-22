"""Deterministic execution of the one approved Session Intelligence scenario."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .developer_session_bootstrap import (
    GOLDEN_SCENARIO_ID,
    GOLDEN_SCENARIO_PROFILE_ID,
)
from .session_runtime import session_runtime_manager


DEVELOPER_SESSION_SCENARIO_DRIVER_SERVICE = "developer_session_scenario_driver"


@dataclass(frozen=True)
class SIGolden001Fixture:
    """The sole deterministic observable input required by SI-GOLDEN-001."""

    title: str = "Harbor Lights"
    artist: str = "Northline"
    album: str = "Night Signals"
    artist_context: str = "Northline builds its songs around restrained nocturnal textures."

    def as_track_insight(self) -> dict[str, Any]:
        """Return bounded Track Insight input, not a resolved Knowledge result."""
        return {
            "track": {
                "title": self.title,
                "artist": self.artist,
                "album": self.album,
                "producer": self.artist,
            },
            "analysis": {
                "summary": "A calm, atmospheric track with a focused artist story.",
                "full_text": self.artist_context,
            },
        }


SI_GOLDEN_001_FIXTURE = SIGolden001Fixture()


async def async_execute_si_golden_001(hass: Any) -> dict[str, Any]:
    """Drive one Track Started event through the canonical Runtime boundary."""
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(GOLDEN_SCENARIO_PROFILE_ID)
    if active is None:
        return {
            "success": False,
            "status": "bootstrap_required",
            "scenario_id": GOLDEN_SCENARIO_ID,
        }

    async def insight_provider() -> dict[str, Any]:
        return SI_GOLDEN_001_FIXTURE.as_track_insight()

    moment = await manager.async_process_track_started(
        owner_profile_id=GOLDEN_SCENARIO_PROFILE_ID,
        session_id=active.session_id,
        insight_provider=insight_provider,
    )
    if moment is None:
        return {
            "success": False,
            "status": "not_executed",
            "scenario_id": GOLDEN_SCENARIO_ID,
            "session_id": active.session_id,
        }
    return {
        "success": True,
        "status": "executed",
        "scenario_id": GOLDEN_SCENARIO_ID,
        "session_id": active.session_id,
        "moment_id": moment.moment_id,
    }
