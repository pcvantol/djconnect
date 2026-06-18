from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def install_conversation_stubs() -> None:
    homeassistant = sys.modules.setdefault(
        "homeassistant",
        types.ModuleType("homeassistant"),
    )
    components = sys.modules.setdefault(
        "homeassistant.components",
        types.ModuleType("homeassistant.components"),
    )
    conversation = sys.modules.setdefault(
        "homeassistant.components.conversation",
        types.ModuleType("homeassistant.components.conversation"),
    )
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    core = sys.modules.setdefault(
        "homeassistant.core",
        types.ModuleType("homeassistant.core"),
    )
    helpers = sys.modules.setdefault(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    intent = sys.modules.setdefault(
        "homeassistant.helpers.intent",
        types.ModuleType("homeassistant.helpers.intent"),
    )
    entity_platform = sys.modules.setdefault(
        "homeassistant.helpers.entity_platform",
        types.ModuleType("homeassistant.helpers.entity_platform"),
    )

    class ConversationEntity:
        pass

    class ConversationInput:
        pass

    class ConversationResult:
        def __init__(self, *, response, conversation_id=None):
            self.response = response
            self.conversation_id = conversation_id

    class IntentResponse:
        def __init__(self, language):
            self.language = language
            self.speech = None

        def async_set_speech(self, speech):
            self.speech = speech

    conversation.ConversationEntity = ConversationEntity
    conversation.ConversationInput = ConversationInput
    conversation.ConversationResult = ConversationResult
    config_entries.ConfigEntry = object
    core.HomeAssistant = object
    intent.IntentResponse = IntentResponse
    entity_platform.AddEntitiesCallback = object
    homeassistant.components = components
    components.conversation = conversation
    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.helpers = helpers

    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules["custom_components.djconnect"] = package
    processor = types.ModuleType("custom_components.djconnect.processor")

    async def process_text_command(*args, **kwargs):
        return {"dj_text": ""}

    processor.process_text_command = process_text_command
    sys.modules["custom_components.djconnect.processor"] = processor


class ConversationAgentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_conversation_stubs()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.const = importlib.import_module("custom_components.djconnect.const")
        cls.conversation = importlib.import_module(
            "custom_components.djconnect.conversation"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        for module_name in (
            "custom_components.djconnect.conversation",
            "custom_components.djconnect.processor",
            "custom_components.djconnect.const",
            "custom_components.djconnect",
        ):
            sys.modules.pop(module_name, None)

    def test_setup_entry_adds_conversation_agent(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1")
        runtime = types.SimpleNamespace(
            entry=entry,
            config={self.const.CONF_DEVICE_NAME: "Studio"},
        )
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {entry.entry_id: runtime}})
        added = []

        asyncio.run(
            self.conversation.async_setup_entry(
                hass,
                entry,
                lambda entities: added.extend(entities),
            )
        )

        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]._attr_unique_id, "entry-1_conversation")
        self.assertEqual(added[0]._attr_name, "DJ")

    def test_process_returns_dj_text_from_command_flow(self) -> None:
        calls = []

        async def process_text_command(hass, runtime, text, *, play, correct_stt):
            calls.append((hass, runtime, text, play, correct_stt))
            return {"dj_text": "Daar is Strobe van Deadmau5."}

        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            config={},
            update=lambda **kwargs: None,
        )
        agent = self.conversation.DJConnectConversationAgent(runtime)
        hass = object()
        agent.hass = hass
        user_input = types.SimpleNamespace(
            text="speel Strobe van Deadmau5",
            language="nl-NL",
            conversation_id="conv-1",
        )
        original = self.conversation.process_text_command
        self.conversation.process_text_command = process_text_command
        try:
            result = asyncio.run(agent.async_process(user_input))
        finally:
            self.conversation.process_text_command = original

        self.assertEqual(result.response.speech, "Daar is Strobe van Deadmau5.")
        self.assertEqual(result.conversation_id, "conv-1")
        self.assertEqual(calls, [(hass, runtime, "speel Strobe van Deadmau5", True, False)])

    def test_process_error_returns_friendly_speech(self) -> None:
        async def process_text_command(hass, runtime, text, *, play, correct_stt):
            raise RuntimeError("boom")

        updates = []
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1"),
            config={},
            update=lambda **kwargs: updates.append(kwargs),
        )
        agent = self.conversation.DJConnectConversationAgent(runtime)
        agent.hass = object()
        user_input = types.SimpleNamespace(
            text="play something",
            language="en-US",
            conversation_id=None,
        )
        original = self.conversation.process_text_command
        self.conversation.process_text_command = process_text_command
        try:
            result = asyncio.run(agent.async_process(user_input))
        finally:
            self.conversation.process_text_command = original

        self.assertEqual(
            result.response.speech,
            "Sorry, DJConnect could not process your request.",
        )
        self.assertEqual(
            updates,
            [{"last_error": "Assist conversation failed: boom"}],
        )


if __name__ == "__main__":
    unittest.main()
