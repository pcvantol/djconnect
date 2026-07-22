"""Machine-invokable bootstrap for the first Session Intelligence Golden Scenario."""
from __future__ import annotations

from typing import Any

from .session_runtime import (
    ActiveSessionExistsError,
    DJPersona,
    SessionStartStrategy,
    session_runtime_manager,
)


DEVELOPER_SESSION_BOOTSTRAP_SERVICE = "developer_session_bootstrap"
GOLDEN_SCENARIO_ID = "SI-GOLDEN-001"
GOLDEN_SCENARIO_PROFILE_ID = "e2e-session-intelligence-golden-001"


async def async_handle_developer_session_bootstrap(
    hass: Any, action: str = "start"
) -> dict[str, Any]:
    """Start or stop the one isolated Runtime needed to enable SI-GOLDEN-001.

    This boundary holds no Runtime reference. The integration-wide Runtime
    Manager remains the sole owner of the active Session and all of its state.
    """
    normalized_action = str(action or "start").strip().lower()
    manager = session_runtime_manager(hass)

    if normalized_action == "start":
        try:
            session = await manager.async_start(
                owner_profile_id=GOLDEN_SCENARIO_PROFILE_ID,
                room="e2e",
                selected_mood="groove",
                dj_persona=DJPersona.HOME_DJ,
                locale="en",
                session_start_strategy=SessionStartStrategy.MANUAL,
            )
        except ActiveSessionExistsError:
            return {
                "success": False,
                "status": "already_active",
                "scenario_id": GOLDEN_SCENARIO_ID,
            }
        return _bootstrap_result(session, "ready")

    if normalized_action == "stop":
        active = await manager.async_get_active(GOLDEN_SCENARIO_PROFILE_ID)
        if active is None:
            return {
                "success": False,
                "status": "not_active",
                "scenario_id": GOLDEN_SCENARIO_ID,
            }
        ended = await manager.async_end(
            owner_profile_id=GOLDEN_SCENARIO_PROFILE_ID,
            session_id=active.session_id,
        )
        if ended is None:
            return {
                "success": False,
                "status": "not_active",
                "scenario_id": GOLDEN_SCENARIO_ID,
            }
        return _bootstrap_result(ended, "stopped")

    return {
        "success": False,
        "status": "invalid_action",
        "scenario_id": GOLDEN_SCENARIO_ID,
    }


def _bootstrap_result(session: Any, status: str) -> dict[str, Any]:
    """Return only the bounded data later automation requires."""
    return {
        "success": True,
        "status": status,
        "scenario_id": GOLDEN_SCENARIO_ID,
        "session_id": session.session_id,
        "lifecycle_state": session.runtime_state.value,
    }
