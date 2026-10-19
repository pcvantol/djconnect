"""Live Persona transport over the existing qualified Session-setting owner."""
from .const import API_SESSION_PERSONA
from .session_mood import async_handle_owner_setting


def capability():
    from .persona_reactions import capability as reaction_capability
    return {"available": True, "version": 1, "path": API_SESSION_PERSONA,
            "method": "POST", "authentication": "paired_device_bearer",
            "values": ["home_dj", "radio_dj", "club_dj", "festival_dj"],
            "ordering": "expected_persona_revision",
            "scope": "active_device_bound_owner_session",
            "touch_reaction": reaction_capability()}


async def async_handle_persona(hass, data, *, headers=None):
    return await async_handle_owner_setting(hass, data, headers=headers, setting="persona")
