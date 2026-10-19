"""Separate presence transport using the qualified ordinary-owner boundary."""
from .const import API_SESSION_PRESENCE
from .presence_policy import DEFAULT, POLICIES
from .session_mood import async_handle_owner_setting


def capability():
    return {"available": True, "version": 2, "transport_contract_version": 1,
            "path": API_SESSION_PRESENCE,
            "method": "POST", "authentication": "paired_device_bearer",
            "values": list(POLICIES), "default": DEFAULT,
            "ordering": "expected_presence_revision",
            "scope": "active_device_bound_owner_session"}


async def async_handle_presence(hass, data, *, headers=None):
    return await async_handle_owner_setting(hass, data, headers=headers, setting="presence")
