"""Interpretation-only fixture for the same bounded operational dialogue owner.

This does not claim pairing/Profile/Store acceptance; owning/real HA suites prove
those boundaries. Historical fixture messages are explicitly seeded operational
turns, never imported into the production service or its model grant.
"""

from __future__ import annotations
from copy import deepcopy
from uuid import uuid4


async def ask_operational(core, hass, runtime, payload, **kwargs):
    from custom_components.djconnect.ask_dj import dialogue
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
    from tests.test_ask_dj_history import FakeStore

    if dialogue.current_turn.get() is not None:
        return await core.async_handle_ask_dj(hass, runtime, payload, **kwargs)
    state = getattr(runtime, "_unit_dialogue_owner", None)
    if state is None:
        history = AskDJHistoryManager(store=FakeStore())
        state = runtime._unit_dialogue_owner = history
        frame = history.dialogue.frame("profile:unit-owner", "default", "unit-generation")
        seed = getattr(runtime, "ask_dj_history", None)
        # Only this explicit interpretation fixture seeds a functional window.
        for item in getattr(seed, "messages", []):
            frame.local_turns.append(deepcopy(item))
            if item.get("role") == "user":
                frame.messages.append({"role": "user", "text": str(item.get("text") or "")[:4000]})
        for item in reversed(frame.local_turns):
            if item.get("playback_actions"):
                frame.result_set = {
                    "result_set_id": "unit-fixture-set",
                    "items": deepcopy(item["playback_actions"]),
                    "deadline": history.dialogue.clock() + 600,
                    "generation": frame.generation,
                }
                for i, action in enumerate(frame.result_set["items"]):
                    action.setdefault("action_id", f"unit-{i}")
                break
    frame = state.dialogue.frame("profile:unit-owner", "default", "unit-generation")

    async def guard():
        pass  # No authorization proof; interpretation-only fixture.

    data = {
        **payload,
        "client_message_id": payload.get("client_message_id") or "unit-" + uuid4().hex,
        # Legacy interpretation cases explicitly use Dutch unless overridden;
        # another suite's installed HA stubs are not this fixture's locale.
        "language": payload.get("language") or "nl",
    }
    turn = dialogue.DialogueTurn(
        frame,
        "profile:unit-owner",
        "default",
        data["client_message_id"],
        "unit-digest",
        frame.generation,
        guard,
        state,
        style=dialogue.style_projection(data),
        fast_control=core.classify_ask_dj(str(data.get("text") or "")).category == "action",
        effect_grants=dialogue.request_effect_grants(str(data.get("text") or ""), core.classify_ask_dj(str(data.get("text") or ""))),
    )
    token = dialogue.current_turn.set(turn)
    try:
        result = await core.async_handle_ask_dj(hass, runtime, data, **kwargs)
        result["_dialogue_question"] = data.get("text", "")
        state.dialogue.complete(turn, result)
        result.pop("_dialogue_question", None)
        return result
    finally:
        dialogue.current_turn.reset(token)


async def owner_transport(runtime, directory):
    """Explicit interpretation transport fixture with actual Profile and SQLite owners."""
    from types import SimpleNamespace
    from pathlib import Path
    from custom_components.djconnect.domain.storage import ProfilePlatformStorage
    from custom_components.djconnect.domain.backend import BackendProvider
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
    from custom_components.djconnect.persistence.service import PersistenceService
    from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider
    from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.session_runtime import SessionRuntimeManager
    from tests.test_ask_dj_history import FakeStore

    storage = ProfilePlatformStorage()
    backend_id = str(getattr(runtime, "config", {}).get("music_backend") or "spotify_direct")
    provider = (
        BackendProvider.MUSIC_ASSISTANT
        if backend_id == "music_assistant"
        else BackendProvider.SPOTIFY_DIRECT
    )
    await storage.async_upsert_music_backend(
        backend_id, provider, display_name="Interpretation fixture"
    )
    await storage.async_create_profile(
        "Synthetic owner", profile_id="test-owner", default_backend_id=backend_id
    )
    device = runtime.device_status["device_id"]
    client_type = next(
        (
            kind
            for kind in ("ios", "macos", "watchos", "raspberry_pi")
            if device.startswith("djconnect-" + kind + "-")
        ),
        "ios",
    )
    await storage.async_upsert_device(device, client_type, linked_profile_id="test-owner")
    service = PersistenceService(Path(directory) / "history.sqlite3", SQLitePersistenceProvider())
    await service.async_initialize()
    history = AskDJHistoryManager(store=FakeStore())
    runtime.ask_dj_history = history
    hass = SimpleNamespace(
        data={
            "djconnect": {
                "runtime": runtime,
                "owner-entry": runtime,
                "djconnect_profile_platform": storage,
                "ask_dj_history_manager": history,
                "persistence_service": service,
                "session_runtime_manager": SessionRuntimeManager(
                    PersistentSessionRepository(service), HistoricalProjectionRepository(service)
                ),
            }
        },
        config=SimpleNamespace(language="nl"),
    )
    return hass, service


async def seed_pending_with_service(core_http, hass, runtime):
    """Interpretation fixture creates pending through the common producer/acceptance."""
    from unittest.mock import patch
    from custom_components.djconnect.api_handlers import async_handle_ask_dj_message_payload
    from custom_components.djconnect.ask_dj import _store_pending_followup

    async def offer(h, r, p, **kwargs):
        await _store_pending_followup(
            r,
            p,
            question="Play the shown morning selection?",
            proposed_intent="morning_music_suggestion",
            proposed_action="ask_dj_play_recommendation",
            proposed_payload={
                "kind": "track",
                "uri": "spotify:track:morning",
                "title": "Morning Track",
            },
        )
        return {
            "success": True,
            "text": "A pending interpretation fixture offer",
            "confirmation_actions": [{"response_value": "yes"}],
        }

    client_type = "ios"
    with patch.object(core_http, "async_handle_ask_dj", offer):
        result, status = await async_handle_ask_dj_message_payload(
            hass,
            {
                "device_id": runtime.device_status["device_id"],
                "client_type": client_type,
                "client_message_id": "unit-pending-offer",
                "text": "Show a morning suggestion",
                "audio_response": "never",
            },
            headers={"Authorization": "Bearer device-token"},
        )
    if status != 200 or not result.get("success"):
        raise AssertionError(("pending-fixture-rejected", status, result))


async def seed_results_with_service(core_http, hass, runtime, actions):
    """Unit catalog offer with actual shared acceptance/storage, not frame seeding.

    Interpretation output alone is a routing fixture. This does not qualify a
    provider, model, installed client or hardware.
    """
    from unittest.mock import patch
    from custom_components.djconnect.api_handlers import async_handle_ask_dj_message_payload

    async def catalog(*args, **kwargs):
        return {"success": True, "text": "Synthetic qualified catalog offer.",
                "items": deepcopy(actions), "playback_actions": deepcopy(actions)}

    with patch.object(core_http, "async_handle_ask_dj", catalog):
        response, status = await async_handle_ask_dj_message_payload(hass, {
            "device_id": runtime.device_status["device_id"], "client_type": "ios",
            "client_message_id": "offer-" + uuid4().hex, "text": "Find fixture choices",
            "audio_response": "never", "language": "nl",
        }, headers={"Authorization": "Bearer " + runtime.device_token})
    if status != 200 or not response.get("result_set", {}).get("items"):
        raise AssertionError(("catalog-fixture-rejected", status, response.get("error")))
    return response
