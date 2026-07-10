"""Conversation agent support for DJConnect."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ai_tools import AI_TOOLS, async_call_ai_tool
from .const import CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME, DOMAIN
from .use_cases import run_text_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DJConnect conversation agent."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DJConnectConversationAgent(runtime)])


class DJConnectConversationAgent(conversation.ConversationEntity):
    """DJConnect Assist conversation agent."""

    _attr_has_entity_name = False
    _attr_name = "DJConnect DJ"
    _attr_should_poll = False
    _attr_state = "ready"

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_conversation"

        device_name = str(
            runtime.config.get(CONF_DEVICE_NAME)
            or runtime.config.get("name")
            or DEFAULT_DEVICE_NAME
        ).strip()

        self._attr_device_info = {
            "identifiers": {(DOMAIN, runtime.entry.entry_id)},
            "name": device_name or DEFAULT_DEVICE_NAME,
            "manufacturer": "DJConnect",
        }

    @property
    def available(self) -> bool:
        """Return whether the DJConnect conversation agent can process requests."""
        return True

    @property
    def state(self) -> str:
        """Expose a stable state instead of Home Assistant showing unknown."""
        return "ready"

    @property
    def supported_languages(self) -> list[str]:
        return ["nl", "nl-NL", "en", "en-US", "en-GB"]

    @property
    def conversation_tools(self) -> tuple[dict[str, Any], ...]:
        """Expose DJConnect tools available to AI conversation callers."""
        return AI_TOOLS

    async def async_call_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a DJConnect conversation tool through the shared backend helper."""
        return await async_call_ai_tool(
            self.hass,
            self._runtime,
            tool_name,
            parameters,
            user_id=None,
        )

    async def async_process(
        self,
        user_input: conversation.ConversationInput,
    ) -> conversation.ConversationResult:
        """Process Assist request."""

        text = str(getattr(user_input, "text", "") or "").strip()
        language = str(getattr(user_input, "language", None) or "nl-NL")

        response = intent.IntentResponse(language=language)

        if not text:
            response.async_set_speech("Ik heb niets verstaan. Probeer het nog eens.")

            return conversation.ConversationResult(
                response=response,
                conversation_id=getattr(user_input, "conversation_id", None),
            )

        try:
            context = getattr(user_input, "context", None)
            user_id = getattr(context, "user_id", None)
            result = await run_text_command(
                self.hass,
                self._runtime,
                text,
                play=True,
                correct_stt=False,
                user_id=str(user_id) if user_id else None,
                memory_payload=_voice_endpoint_request_context(user_input),
            )

            speech = str(result.get("dj_text") or "").strip()

            if not speech:
                speech = (
                    "Daar gaan we. Ik zet hem voor je klaar."
                    if language.lower().startswith("nl")
                    else "Here we go. I'll start it for you."
                )

        except Exception as exc:
            _LOGGER.exception("DJConnect conversation agent failed")

            self._runtime.update(
                last_error=f"Assist conversation failed: {exc}"
            )

            speech = (
                "Sorry, DJConnect kon je verzoek niet verwerken."
                if language.lower().startswith("nl")
                else "Sorry, DJConnect could not process your request."
            )

        response.async_set_speech(speech)

        return conversation.ConversationResult(
            response=response,
            conversation_id=getattr(user_input, "conversation_id", None),
        )


def _voice_endpoint_request_context(user_input: conversation.ConversationInput) -> dict[str, Any]:
    """Extract available HA Assist voice endpoint signals without inventing identity."""
    payload: dict[str, Any] = {"request_source": "voice_endpoint"}
    _copy_attr(payload, user_input, "conversation_id", "session_id")
    _copy_attr(payload, user_input, "agent_id", "assist_pipeline_id")
    _copy_attr(payload, user_input, "device_id", "ha_device_id")
    _copy_attr(payload, user_input, "area_id", "area_id")
    _copy_attr(payload, user_input, "satellite_id", "satellite_id")
    _copy_attr(payload, user_input, "voice_endpoint_id", "voice_endpoint_id")
    context = getattr(user_input, "context", None)
    if context is not None:
        _copy_attr(payload, context, "device_id", "ha_device_id")
        _copy_attr(payload, context, "area_id", "area_id")
        _copy_attr(payload, context, "entity_id", "voice_endpoint_id")
        _copy_attr(payload, context, "id", "session_id")
    extra = getattr(user_input, "extra_system_prompt", None)
    if isinstance(extra, dict):
        for source_key, target_key in (
            ("satellite_id", "satellite_id"),
            ("voice_endpoint_id", "voice_endpoint_id"),
            ("assist_pipeline_id", "assist_pipeline_id"),
            ("ha_device_id", "ha_device_id"),
            ("area_id", "area_id"),
            ("room_id", "room_id"),
            ("player_id", "player_id"),
        ):
            value = str(extra.get(source_key) or "").strip()
            if value:
                payload[target_key] = value
    return {key: value for key, value in payload.items() if value}


def _copy_attr(payload: dict[str, Any], source: Any, attr: str, key: str) -> None:
    value = str(getattr(source, attr, "") or "").strip()
    if value and not payload.get(key):
        payload[key] = value
