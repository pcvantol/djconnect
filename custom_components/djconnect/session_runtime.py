"""Ephemeral server-owned DJ Session Runtime lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .const import DOMAIN


class SessionRuntimeState(StrEnum):
    """Canonical lifecycle states for the first v4 runtime slice."""

    IDLE = "idle"
    CREATING = "creating"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"


class PlannerState(StrEnum):
    """Lifecycle state for the ephemeral Session Planner foundation."""

    READY = "ready"


class MusicalDirection(StrEnum):
    """Canonical placeholder directions for future planner decisions."""

    MAINTAIN = "maintain"
    INCREASE_ENERGY = "increase_energy"
    DECREASE_ENERGY = "decrease_energy"
    EXPLORE = "explore"
    RECOVER = "recover"


class PlannerEventType(StrEnum):
    """Planner inputs that future runtime capabilities may submit."""

    TRACK_FINISHED = "track_finished"
    PLAYBACK_CHANGED = "playback_changed"
    MOOD_CHANGED = "mood_changed"
    AUDIENCE_SIGNAL = "audience_signal"
    CONVERSATION = "conversation"
    PLANNER_TICK = "planner_tick"


@dataclass(frozen=True)
class SessionPlannerOutput:
    """Planner-owned placeholder for the future Session Flow output."""

    session_flow: None = None

    def as_dict(self) -> dict[str, None]:
        """Return the transport-neutral placeholder without generating flow."""
        return {"session_flow": self.session_flow}


@dataclass(frozen=True)
class DJSessionPlanner:
    """One ephemeral Planner, owned exclusively by one active Runtime.

    The Planner owns the future: its rolling horizon, future Session Flow and
    future Broadcast generation. The Runtime owns the present, including mood;
    the Planner only consumes that runtime-owned context in later slices.
    """

    planner_state: PlannerState
    planning_horizon_minutes: int
    created_at: str
    last_replan_at: str
    current_direction: MusicalDirection
    current_goal: str
    pending_events: tuple[PlannerEventType, ...]
    output: SessionPlannerOutput

    def as_dict(self) -> dict[str, Any]:
        """Return the public planner foundation without planning a flow."""
        return {
            "planner_state": str(self.planner_state),
            "planning_horizon_minutes": self.planning_horizon_minutes,
            "created_at": self.created_at,
            "last_replan_at": self.last_replan_at,
            "current_direction": str(self.current_direction),
            "current_goal": self.current_goal,
            "pending_events": [str(event) for event in self.pending_events],
            "output": self.output.as_dict(),
        }


class ActiveSessionExistsError(RuntimeError):
    """Raised when a Profile already owns an active DJ Session."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Profile already has an active DJ Session: {profile_id}")


@dataclass(frozen=True)
class DJSessionRuntime:
    """Minimum ephemeral state for one active DJ Session."""

    session_id: str
    owner_profile_id: str
    room: str
    selected_mood: str
    music_backend: str
    runtime_state: SessionRuntimeState
    created_at: str
    started_at: str
    planner: DJSessionPlanner

    def as_dict(self) -> dict[str, Any]:
        """Return the public, transport-neutral runtime representation."""
        runtime = {
            key: str(value)
            for key, value in asdict(self).items()
            if key != "planner"
        }
        runtime["planner"] = self.planner.as_dict()
        return runtime


class SessionRuntimeManager:
    """Own active DJ Session Runtimes for this Home Assistant instance."""

    def __init__(self) -> None:
        self._active_by_profile: dict[str, DJSessionRuntime] = {}
        self._lock = asyncio.Lock()

    async def async_start(
        self,
        *,
        owner_profile_id: str,
        room: str = "",
        selected_mood: str = "",
        music_backend: str = "",
    ) -> DJSessionRuntime:
        """Create the one active Runtime allowed for a Profile."""
        async with self._lock:
            if owner_profile_id in self._active_by_profile:
                raise ActiveSessionExistsError(owner_profile_id)
            now = _timestamp()
            creating = DJSessionRuntime(
                session_id=f"session-{uuid4().hex}",
                owner_profile_id=owner_profile_id,
                room=room,
                selected_mood=selected_mood,
                music_backend=music_backend,
                runtime_state=SessionRuntimeState.CREATING,
                created_at=now,
                started_at="",
                planner=_create_session_planner(now),
            )
            active = DJSessionRuntime(
                **{
                    **creating.__dict__,
                    "runtime_state": SessionRuntimeState.ACTIVE,
                    "started_at": _timestamp(),
                }
            )
            self._active_by_profile[owner_profile_id] = active
            return active

    async def async_get_active(self, owner_profile_id: str) -> DJSessionRuntime | None:
        """Return the active Runtime for a Profile, if one exists."""
        async with self._lock:
            return self._active_by_profile.get(owner_profile_id)

    async def async_end(
        self,
        *,
        owner_profile_id: str,
        session_id: str = "",
    ) -> DJSessionRuntime | None:
        """End and dispose of the active Runtime for a Profile."""
        async with self._lock:
            active = self._active_by_profile.get(owner_profile_id)
            if active is None:
                return None
            if session_id and active.session_id != session_id:
                return None
            ending = DJSessionRuntime(
                **{**active.__dict__, "runtime_state": SessionRuntimeState.ENDING}
            )
            ended = DJSessionRuntime(
                **{**ending.__dict__, "runtime_state": SessionRuntimeState.ENDED}
            )
            self._active_by_profile.pop(owner_profile_id, None)
            return ended


def session_runtime_manager(hass: Any) -> SessionRuntimeManager:
    """Return the integration-wide ephemeral Session Runtime Manager."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("session_runtime_manager")
    if manager is None:
        manager = SessionRuntimeManager()
        domain_data["session_runtime_manager"] = manager
    return manager


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _create_session_planner(created_at: str) -> DJSessionPlanner:
    """Create the one non-persistent Planner for a newly created Runtime."""
    return DJSessionPlanner(
        planner_state=PlannerState.READY,
        planning_horizon_minutes=15,
        created_at=created_at,
        last_replan_at="",
        current_direction=MusicalDirection.MAINTAIN,
        current_goal="",
        pending_events=(),
        output=SessionPlannerOutput(),
    )
