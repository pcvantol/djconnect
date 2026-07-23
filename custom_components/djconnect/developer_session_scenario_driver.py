"""Deterministic execution of the one approved Session Intelligence scenario."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .developer_session_bootstrap import (
    GOLDEN_SCENARIO_ID,
    GOLDEN_SCENARIO_PROFILE_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_002_PROFILE_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_003_PROFILE_ID,
    SI_GOLDEN_004_ID,
    SI_GOLDEN_004_PROFILE_ID,
    SI_GOLDEN_005_ID,
    SI_GOLDEN_005_PROFILE_ID,
    SI_GOLDEN_006_ID,
    SI_GOLDEN_006_PROFILE_ID,
    async_advance_si_golden_002_clock,
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


@dataclass(frozen=True)
class SIGolden002Fixture:
    """The two fixed inputs needed to observe first-eligible repetition avoidance."""

    artist: str = "Northline"
    genre: str = "ambient electronic"

    def first_track_insight(self) -> dict[str, Any]:
        return SI_GOLDEN_001_FIXTURE.as_track_insight()

    def second_track_insight(self) -> dict[str, Any]:
        return {
            "track": {
                "title": "Afterimage",
                "artist": self.artist,
                "album": "Night Signals",
                "producer": self.artist,
            },
            "analysis": {
                "genre": self.genre,
                "summary": "A second track with an available genre story.",
                "full_text": "Northline's ambient electronic palette remains in focus.",
            },
        }


SI_GOLDEN_002_FIXTURE = SIGolden002Fixture()
_SI_GOLDEN_002_INTERVAL_SECONDS = 61.0


class _SIGolden003KnowledgeUnavailable(Exception):
    """Fixed unavailable Knowledge input for the one approved failure scenario."""


async def _si_golden_003_unavailable_insight_provider() -> dict[str, Any]:
    """Use the normal Runtime failure boundary; never return fabricated knowledge."""
    raise _SIGolden003KnowledgeUnavailable("approved deterministic unavailable knowledge")


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


async def async_execute_si_golden_002(hass: Any) -> dict[str, Any]:
    """Drive the fixed two-event repetition scenario through the Runtime only."""
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(SI_GOLDEN_002_PROFILE_ID)
    if active is None:
        return {
            "success": False,
            "status": "bootstrap_required",
            "scenario_id": SI_GOLDEN_002_ID,
        }

    async def first_insight_provider() -> dict[str, Any]:
        return SI_GOLDEN_002_FIXTURE.first_track_insight()

    first = await manager.async_process_track_started(
        owner_profile_id=SI_GOLDEN_002_PROFILE_ID,
        session_id=active.session_id,
        insight_provider=first_insight_provider,
    )
    if first is None:
        return _si_golden_002_not_executed(active.session_id)

    advanced = await async_advance_si_golden_002_clock(
        hass, _SI_GOLDEN_002_INTERVAL_SECONDS
    )
    if advanced is None:
        return _si_golden_002_not_executed(active.session_id)

    async def second_insight_provider() -> dict[str, Any]:
        return SI_GOLDEN_002_FIXTURE.second_track_insight()

    second = await manager.async_process_track_started(
        owner_profile_id=SI_GOLDEN_002_PROFILE_ID,
        session_id=active.session_id,
        insight_provider=second_insight_provider,
    )
    if second is None:
        return _si_golden_002_not_executed(active.session_id)
    return {
        "success": True,
        "status": "executed",
        "scenario_id": SI_GOLDEN_002_ID,
        "session_id": active.session_id,
        "first_moment_id": first.moment_id,
        "second_moment_id": second.moment_id,
    }


def _si_golden_002_not_executed(session_id: str) -> dict[str, Any]:
    return {
        "success": False,
        "status": "not_executed",
        "scenario_id": SI_GOLDEN_002_ID,
        "session_id": session_id,
    }


async def async_execute_si_golden_003(hass: Any) -> dict[str, Any]:
    """Drive one approved unavailable-Knowledge input through the Runtime only."""
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(SI_GOLDEN_003_PROFILE_ID)
    if active is None:
        return {
            "success": False,
            "status": "bootstrap_required",
            "scenario_id": SI_GOLDEN_003_ID,
        }
    moment = await manager.async_process_track_started(
        owner_profile_id=SI_GOLDEN_003_PROFILE_ID,
        session_id=active.session_id,
        insight_provider=_si_golden_003_unavailable_insight_provider,
    )
    if moment is None:
        return {
            "success": False,
            "status": "not_executed",
            "scenario_id": SI_GOLDEN_003_ID,
            "session_id": active.session_id,
        }
    return {
        "success": True,
        "status": "executed",
        "scenario_id": SI_GOLDEN_003_ID,
        "session_id": active.session_id,
        "moment_id": moment.moment_id,
    }


async def async_execute_si_golden_004(hass: Any) -> dict[str, Any]:
    """Exercise bounded Horizon replanning without realizing a Moment."""
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(SI_GOLDEN_004_PROFILE_ID)
    if active is None:
        return {"success": False, "status": "bootstrap_required", "scenario_id": SI_GOLDEN_004_ID}
    from .session_runtime import UpcomingPlaybackEntry, UpcomingPlaybackProjection
    initial = UpcomingPlaybackProjection.from_entries(
        (UpcomingPlaybackEntry("golden-a", 60), UpcomingPlaybackEntry("golden-b", 60)),
        confidence=0.8,
    )
    approved = await manager.async_replan_observed_playback(
        owner_profile_id=SI_GOLDEN_004_PROFILE_ID,
        session_id=active.session_id,
        upcoming_playback=initial,
        approve_earliest=True,
    )
    if not approved:
        return {"success": False, "status": "not_ready", "scenario_id": SI_GOLDEN_004_ID}
    extended = await manager.async_replan_observed_playback(
        owner_profile_id=SI_GOLDEN_004_PROFILE_ID,
        session_id=active.session_id,
        upcoming_playback=UpcomingPlaybackProjection.from_entries(
            (
                UpcomingPlaybackEntry("golden-a", 60),
                UpcomingPlaybackEntry("golden-b", 60),
                UpcomingPlaybackEntry("golden-c", 60),
            ),
            confidence=0.8,
        )
    )
    equivalent = await manager.async_replan_observed_playback(
        owner_profile_id=SI_GOLDEN_004_PROFILE_ID,
        session_id=active.session_id,
        upcoming_playback=UpcomingPlaybackProjection.from_entries(
            (
                UpcomingPlaybackEntry("golden-a", 60),
                UpcomingPlaybackEntry("golden-b", 60),
                UpcomingPlaybackEntry("golden-c", 60),
            ),
            confidence=0.8,
        ),
    )
    replacement = await manager.async_replan_observed_playback(
        owner_profile_id=SI_GOLDEN_004_PROFILE_ID,
        session_id=active.session_id,
        upcoming_playback=UpcomingPlaybackProjection.from_entries(
            (UpcomingPlaybackEntry("golden-a", 60),), confidence=0.8
        )
    )
    return {
        "success": extended and equivalent and replacement,
        "status": "executed",
        "scenario_id": SI_GOLDEN_004_ID,
        "session_id": active.session_id,
    }


async def async_execute_si_golden_005(hass: Any) -> dict[str, Any]:
    """Use the production Runtime path for two Silences and one resetting Update."""
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(SI_GOLDEN_005_PROFILE_ID)
    if active is None:
        return {"success": False, "status": "bootstrap_required", "scenario_id": SI_GOLDEN_005_ID}
    async def empty() -> dict[str, Any]: return {}
    moments = []
    for _ in range(3):
        moment = await manager.async_process_track_started(
            owner_profile_id=SI_GOLDEN_005_PROFILE_ID,
            session_id=active.session_id,
            insight_provider=empty,
        )
        if moment is None:
            return {
                "success": False,
                "status": "not_executed",
                "scenario_id": SI_GOLDEN_005_ID,
            }
        moments.append(moment)
    return {
        "success": True,
        "status": "executed",
        "scenario_id": SI_GOLDEN_005_ID,
        "session_id": active.session_id,
        "moment_ids": tuple(moment.moment_id for moment in moments),
    }


async def async_execute_si_golden_006(hass: Any) -> dict[str, Any]:
    """Use the existing coordinator's planned current-track Silence path."""
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(SI_GOLDEN_006_PROFILE_ID)
    if active is None:
        return {
            "success": False,
            "status": "bootstrap_required",
            "scenario_id": SI_GOLDEN_006_ID,
        }

    async def insight() -> dict[str, Any]:
        return {
            "track": {"title": "Still Water", "artist": "Northline", "producer": "Northline"},
            "analysis": {"summary": "Safe context.", "full_text": "Safe context."},
        }
    from .session_runtime import UpcomingPlaybackEntry, UpcomingPlaybackProjection
    moment = await manager.async_process_track_started(
        owner_profile_id=SI_GOLDEN_006_PROFILE_ID,
        session_id=active.session_id,
        insight_provider=insight,
        upcoming_playback=UpcomingPlaybackProjection.from_entries(
            (UpcomingPlaybackEntry("golden-silence", duration_seconds=60),), confidence=0.8
        ),
    )
    return {
        "success": moment is not None,
        "status": "executed" if moment else "not_executed",
        "scenario_id": SI_GOLDEN_006_ID,
        "session_id": active.session_id,
        "moment_id": moment.moment_id if moment else "",
    }
