"""Machine-invokable bootstrap for the first Session Intelligence Golden Scenario."""
from __future__ import annotations

from typing import Any

from .const import DOMAIN
from .session_runtime import (
    ActiveSessionExistsError,
    DJPersona,
    SessionStartStrategy,
    session_runtime_manager,
)
from .verification_clock import VerificationClock


DEVELOPER_SESSION_BOOTSTRAP_SERVICE = "developer_session_bootstrap"
SI_GOLDEN_001_ID = "SI-GOLDEN-001"
SI_GOLDEN_001_PROFILE_ID = "e2e-session-intelligence-golden-001"
SI_GOLDEN_002_ID = "SI-GOLDEN-002"
SI_GOLDEN_002_PROFILE_ID = "e2e-session-intelligence-golden-002"

# Kept as the original fixed-scenario names for the completed SI-GOLDEN-001 API.
GOLDEN_SCENARIO_ID = SI_GOLDEN_001_ID
GOLDEN_SCENARIO_PROFILE_ID = SI_GOLDEN_001_PROFILE_ID
_VERIFICATION_CLOCKS_KEY = "verification_clocks"


async def async_handle_developer_session_bootstrap(
    hass: Any, action: str = "start", scenario_id: str = SI_GOLDEN_001_ID
) -> dict[str, Any]:
    """Start or stop the isolated Runtime for one explicitly approved scenario.

    This boundary holds no Runtime reference. The integration-wide Runtime
    Manager remains the sole owner of the active Session and all of its state.
    """
    normalized_action = str(action or "start").strip().lower()
    scenario = str(scenario_id or SI_GOLDEN_001_ID).strip().upper()
    profile_id = _scenario_profile_id(scenario)
    if not profile_id:
        return {"success": False, "status": "invalid_scenario", "scenario_id": scenario}
    manager = session_runtime_manager(hass)

    if normalized_action == "start":
        clock = VerificationClock() if scenario == SI_GOLDEN_002_ID else None
        try:
            session = await manager.async_start(
                owner_profile_id=profile_id,
                room="e2e",
                selected_mood="groove",
                dj_persona=DJPersona.HOME_DJ,
                locale="en",
                session_start_strategy=SessionStartStrategy.MANUAL,
                elapsed_time_source=clock.monotonic if clock is not None else None,
            )
        except ActiveSessionExistsError:
            return {
                "success": False,
                "status": "already_active",
                "scenario_id": scenario,
            }
        if clock is not None:
            _verification_clocks(hass)[scenario] = (session.session_id, clock)
        return _bootstrap_result(session, "ready", scenario)

    if normalized_action == "stop":
        active = await manager.async_get_active(profile_id)
        if active is None:
            return {
                "success": False,
                "status": "not_active",
                "scenario_id": scenario,
            }
        ended = await manager.async_end(
            owner_profile_id=profile_id,
            session_id=active.session_id,
        )
        if ended is None:
            return {
                "success": False,
                "status": "not_active",
                "scenario_id": scenario,
            }
        _verification_clocks(hass).pop(scenario, None)
        return _bootstrap_result(ended, "stopped", scenario)

    return {
        "success": False,
        "status": "invalid_action",
        "scenario_id": scenario,
    }


async def async_advance_si_golden_002_clock(hass: Any, seconds: float) -> float | None:
    """Advance only SI-GOLDEN-002's active, composed verification Clock."""
    entry = _verification_clocks(hass).get(SI_GOLDEN_002_ID)
    if entry is None:
        return None
    session_id, clock = entry
    active = await session_runtime_manager(hass).async_get_active(SI_GOLDEN_002_PROFILE_ID)
    if active is None or active.session_id != session_id:
        return None
    return clock.advance(seconds)


def si_golden_002_clock_evidence(hass: Any) -> tuple[float, int] | None:
    """Return bounded Clock evidence for the immutable SI-GOLDEN-002 capture."""
    entry = _verification_clocks(hass).get(SI_GOLDEN_002_ID)
    if entry is None:
        return None
    _, clock = entry
    return (clock.elapsed_seconds, clock.advance_count)


def _verification_clocks(hass: Any) -> dict[str, tuple[str, VerificationClock]]:
    return hass.data.setdefault(DOMAIN, {}).setdefault(_VERIFICATION_CLOCKS_KEY, {})


def _scenario_profile_id(scenario_id: str) -> str:
    if scenario_id == SI_GOLDEN_001_ID:
        return SI_GOLDEN_001_PROFILE_ID
    if scenario_id == SI_GOLDEN_002_ID:
        return SI_GOLDEN_002_PROFILE_ID
    return ""


def _bootstrap_result(session: Any, status: str, scenario_id: str) -> dict[str, Any]:
    """Return only the bounded data later automation requires."""
    return {
        "success": True,
        "status": status,
        "scenario_id": scenario_id,
        "session_id": session.session_id,
        "lifecycle_state": session.runtime_state.value,
    }
