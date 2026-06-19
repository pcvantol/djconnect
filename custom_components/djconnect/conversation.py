"""Conversation agent support for DJConnect."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME, DOMAIN
from .processor import process_text_command

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
    def supported_languages(self) -> list[str]:
        return ["nl", "nl-NL", "en", "en-US", "en-GB"]

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
            try:
                result = await process_text_command(
                    self.hass,
                    self._runtime,
                    text,
                    play=True,
                    correct_stt=False,
                    user_id=str(user_id) if user_id else None,
                )
            except TypeError as exc:
                if "unexpected keyword" not in str(exc):
                    raise
                result = await process_text_command(
                    self.hass,
                    self._runtime,
                    text,
                    play=True,
                    correct_stt=False,
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
