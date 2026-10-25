"""Cost-free official HA AI Task integration in an owned disposable /lab.

Mount candidate read-only; provider I/O is intercepted before network. Synthetic
configuration/turn fixtures prove transport guards, never paid quality, production
configuration, installed runtime or user acceptance. All original failures stay
separate. This verifier never reads credentials.
Explicit invalid-result scenarios tamper only the public result after the real
official task returns; they do not claim a model can choose HA session IDs.
"""

import asyncio
import json
import logging
import sys
import time
import os
from pathlib import Path

from types import MappingProxyType
from openai import AsyncOpenAI
from openai.types.responses import (
    Response,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseOutputItemAddedEvent,
    ResponseTextDeltaEvent,
    ResponseOutputItemDoneEvent,
    ResponseCompletedEvent,
    ResponseFunctionToolCall,
)
from homeassistant import loader, auth
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntries,
    ConfigEntryStore,
    ConfigEntryState,
)
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components import ai_task, conversation
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.helpers import device_registry, entity_registry, area_registry, frame

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
logging.basicConfig(level=logging.CRITICAL)


async def main():
    h = HomeAssistant("/lab")
    h.state = CoreState.running
    h.config.language = "en"
    device_registry.async_setup(h)
    await device_registry.async_load(h, load_empty=True)
    await entity_registry.async_load(h, load_empty=True)
    await area_registry.async_load(h, load_empty=True)
    from homeassistant.components.homeassistant.exposed_entities import ExposedEntities
    from homeassistant.components.homeassistant.const import DATA_EXPOSED_ENTITIES

    exposure = ExposedEntities(h)
    await exposure.async_initialize()
    h.data[DATA_EXPOSED_ENTITIES] = exposure
    h.auth = await auth.auth_manager_from_config(h, [{"type": "homeassistant"}], [])
    h.http = HomeAssistantHTTP(h, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await h.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    h.config.components.add("http")
    frame.async_setup(h)
    loader.async_setup(h)
    await conversation.async_setup(h, {})
    h.config.components.add("conversation")
    await ai_task.async_setup(h, {})
    h.config.components.add("ai_task")
    entry = ConfigEntry(
        domain="openai_conversation",
        title="Disposable public Task probe",
        entry_id="own-task-entry",
        data={"api_key": "UNUSED_NOT_SENT"},
        options={},
        discovery_keys=MappingProxyType({}),
        source="user",
        unique_id="own-task-entry",
        version=2,
        minor_version=7,
        subentries_data=[
            {
                "subentry_id": "own-task-subentry",
                "subentry_type": "ai_task_data",
                "title": "Disposable task",
                "data": {
                    "chat_model": "gpt-6-mini",
                    "max_tokens": 3000,
                    "reasoning_effort": "low",
                    "service_tier": "auto",
                    "store_responses": False,
                    "web_search": False,
                    "code_interpreter": False,
                },
            }
        ],
    )
    task_options = dict(entry.subentries["own-task-subentry"].data)
    conv_options = {
        **task_options,
        "llm_hass_api": [],
        "prompt": "Answer only the explicitly authorized DJConnect music data. No household tools.",
    }
    entry = ConfigEntry(
        domain="openai_conversation",
        title="Disposable public Task probe",
        entry_id="own-task-entry",
        data={"api_key": "UNUSED_NOT_SENT"},
        options={},
        discovery_keys=MappingProxyType({}),
        source="user",
        unique_id="own-task-entry",
        version=2,
        minor_version=7,
        subentries_data=[
            {
                "subentry_id": "own-task-subentry",
                "subentry_type": "ai_task_data",
                "title": "Disposable task",
                "data": task_options,
            },
            {
                "subentry_id": "own-conversation-subentry",
                "subentry_type": "conversation",
                "title": "Disposable conversation",
                "data": conv_options,
            },
        ],
    )
    await ConfigEntryStore(h).async_save({"entries": [entry.as_storage_fragment]})
    h.config_entries = ConfigEntries(h, {})
    await h.config_entries.async_initialize()
    entry = h.config_entries.async_get_entry(entry.entry_id)
    entry._async_set_state(h, ConfigEntryState.LOADED, None)
    api = AsyncOpenAI(api_key="UNUSED_NOT_SENT", max_retries=0)
    entry.runtime_data = api
    receipts = []
    attempts = 0
    cleanup = []
    scenario = os.environ.get("DJC_TASK_CASE", "valid")
    assert scenario in {
        "valid",
        "unsafe_store",
        "missing_task",
        "late_revoke",
        "task_ABA",
        "agent_revoke",
        "provider_error_cleanup_error",
        "cancel_cleanup_error",
        "mixed_budget",
        "unexpected_tool",
        "cancel_swallowed",
        "prior_session",
        "invalid_result_none",
        "invalid_result_integer",
        "invalid_result_empty",
        "invalid_result_foreign",
    }
    from tools.verification.run_catalogue_exact100_20261023 import product_hashes

    source_before = product_hashes(ROOT)
    text = json.dumps(
        {
            "schema": "playback_role_gaps_v3",
            "drafts": [
                {"gaps": {"media_kind": "I’m handing you the ", "title": " ", "status": ". "}}
            ],
        }
    )

    async def intercepted(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts > (3 if scenario == "mixed_budget" else 1):
            raise AssertionError("unexpected_extra_SDK_forbidden")
        generation = sp.current_generation.get()
        if scenario == "mixed_budget" and attempts != 2:
            assert generation is None
        else:
            assert type(generation) is sp.GenerationWitness
            assert generation.role_order == ("media_kind", "title", "status")
        from homeassistant.helpers import chat_session

        active = chat_session.current_session.get()
        assert active is not None
        active.async_on_cleanup(lambda: cleanup.append("own_cleaned"))
        if scenario in {"provider_error_cleanup_error", "cancel_cleanup_error"}:

            def cleanup_error():
                raise RuntimeError("synthetic_cleanup_failure")

            active.async_on_cleanup(cleanup_error)
        if scenario == "provider_error_cleanup_error":
            raise RuntimeError("synthetic_primary_provider_failure")
        assert not kwargs.get("tools") and kwargs.get("store") is False
        if scenario != "mixed_budget" or len(receipts) == 1:
            assert (
                kwargs["text"]["format"]["type"] == "json_schema"
                and kwargs["text"]["format"]["strict"] is True
            )
        else:
            assert not (kwargs.get("text") or {}).get("format")
        receipts.append(
            {
                "strict_format": (kwargs.get("text") or {}).get("format"),
                "model": kwargs["model"],
                "max_output_tokens": kwargs["max_output_tokens"],
                "tools_absent": not kwargs.get("tools"),
                "store_false": kwargs["store"] is False,
                "public_system_input": kwargs["input"][0],
            }
        )
        item = ResponseOutputMessage(
            id="msg_offline",
            role="assistant",
            status="completed",
            type="message",
            content=[
                ResponseOutputText(annotations=[], text=text, type="output_text", logprobs=[])
            ],
        )
        if scenario == "unexpected_tool":
            item = ResponseFunctionToolCall(
                id="synthetic_tool",
                call_id="synthetic_call",
                name="unexpected_unoffered_tool",
                arguments="{}",
                status="completed",
                type="function_call",
            )

        async def events():
            if scenario == "cancel_cleanup_error":
                await asyncio.Event().wait()
            if scenario == "cancel_swallowed":
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    pass  # Adversarial SDK stream; Core must stay cancelled.
            if scenario == "unexpected_tool":
                yield ResponseOutputItemAddedEvent.model_construct(
                    type="response.output_item.added", sequence_number=0, output_index=0, item=item
                )
                yield ResponseOutputItemDoneEvent.model_construct(
                    type="response.output_item.done", sequence_number=1, output_index=0, item=item
                )
                return
            if scenario in {"late_revoke", "task_ABA", "agent_revoke"}:
                sid = (
                    "own-conversation-subentry"
                    if scenario == "agent_revoke"
                    else "own-task-subentry"
                )
                sub = entry.subentries[sid]
                original = dict(sub.data)
                h.config_entries.async_update_subentry(
                    entry, sub, data={**original, "web_search": True}
                )
                if scenario == "task_ABA":
                    h.config_entries.async_update_subentry(
                        entry, entry.subentries[sid], data=original
                    )
            yield ResponseOutputItemAddedEvent.model_construct(
                type="response.output_item.added", sequence_number=0, output_index=0, item=item
            )
            yield ResponseTextDeltaEvent.model_construct(
                type="response.output_text.delta",
                sequence_number=1,
                output_index=0,
                content_index=0,
                item_id=item.id,
                delta=text,
                logprobs=[],
            )
            yield ResponseOutputItemDoneEvent.model_construct(
                type="response.output_item.done", sequence_number=2, output_index=0, item=item
            )
            yield ResponseCompletedEvent.model_construct(
                type="response.completed",
                sequence_number=3,
                response=Response.model_construct(
                    id="resp_offline",
                    output=[item],
                    status="completed",
                    model=kwargs["model"],
                    usage=None,
                ),
            )

        return events()

    api.responses.create = intercepted
    assert await h.data[conversation.DATA_COMPONENT].async_setup_entry(entry)
    assert await h.data["ai_task"].async_setup_entry(entry)
    reg = entity_registry.async_get(h)
    ids = [
        e.entity_id
        for e in reg.entities.values()
        if e.config_entry_id == entry.entry_id and e.domain == "ai_task"
    ]
    assert len(ids) == 1
    from custom_components.djconnect import structured_playback as sp
    from custom_components.djconnect.playback_request import (
        PlaybackRequestBrief,
        PlaybackAcceptance,
    )

    conv_id = next(
        e.entity_id
        for e in reg.entities.values()
        if e.config_entry_id == entry.entry_id and e.domain == "conversation"
    )
    brief = PlaybackRequestBrief(
        PlaybackAcceptance("synthetic-identity", time.monotonic() + 20),
        "en",
        "home_dj",
        "groove",
        "Fallback.",
        ("{media_kind}", "{title}", "{status}"),
        "Only actual dispatch.",
        "No extra facts.",
        (("{media_kind}", "playlist"), ("{title}", "SYNTHETIC_TITLE"), ("{status}", "Requested.")),
        selection_kind="playlist",
    )
    guards = []
    binding = sp.capture_task(h, conv_id, ids[0])
    assert binding.entry is entry
    if scenario == "mixed_budget":
        from types import SimpleNamespace
        from custom_components.djconnect.ask_dj.dialogue import current_turn, DialogueError
        from custom_components.djconnect.pipeline import (
            call_conversation_process_with_agent_retry,
            _call_structured_playback,
        )

        async def turn_guard():
            guards.append("synthetic_turn_guard")

        turn = SimpleNamespace(
            guard=turn_guard,
            accepted_playback_narration=True,
            effect_started=True,
            interpreted_artist_research=False,
            interpreted_context_research=False,
            interpreted_music_direction=False,
            agent_calls=0,
            prompt_bytes=0,
        )
        token = current_turn.set(turn)
        data = {"agent_id": conv_id, "text": brief.prompt(verified_drafts=True), "language": "en"}
        try:
            await call_conversation_process_with_agent_retry(h, data, model_guard=lambda: None)
            await _call_structured_playback(
                h, data, task_id=ids[0], brief=brief, model_guard=lambda: None
            )
            await call_conversation_process_with_agent_retry(h, data, model_guard=lambda: None)
            try:
                await _call_structured_playback(
                    h, data, task_id=ids[0], brief=brief, model_guard=lambda: None
                )
            except DialogueError as exc:
                assert exc.code == "conversation_call_budget"
            else:
                raise AssertionError("fourth_call_not_denied")
            assert turn.agent_calls == 3 and len(receipts) == 3 and attempts == 3
            assert sp.current_generation.get() is None
        finally:
            current_turn.reset(token)
        assert source_before == product_hashes(ROOT)
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "status": "PASS",
                    "scope": "synthetic_turn_budget_real_official_transports",
                    "SDK_boundary_calls": attempts,
                    "SDK_return_receipts": len(receipts),
                    "agent_calls": turn.agent_calls,
                    "fourth_denied_before_SDK": True,
                    "paid_calls": 0,
                    "product_hashes_before": source_before,
                    "product_hashes_after": product_hashes(ROOT),
                    "source_unchanged": True,
                },
                indent=2,
            )
        )
        await api.close()
        await h.async_stop(force=True)
        return
    if scenario in {"unsafe_store", "missing_task"}:
        if scenario == "unsafe_store":
            sub = entry.subentries["own-task-subentry"]
            h.config_entries.async_update_subentry(
                entry, sub, data={**dict(sub.data), "store_responses": True}
            )
        else:
            ids[0] = "ai_task.definitely_missing"
    failure = None
    wire = None
    from homeassistant.helpers import chat_session
    from contextlib import nullcontext
    from dataclasses import replace

    original_generate = ai_task.async_generate_data
    actual_result_ids = []
    foreign_cleaned = []
    foreign = None
    if scenario == "invalid_result_foreign":
        with chat_session.async_get_chat_session(h, "synthetic-owned-foreign") as foreign:
            foreign.async_on_cleanup(lambda: foreign_cleaned.append("foreign_cleaned"))
    if scenario.startswith("invalid_result_"):

        async def tampered_public_result(*args, **kwargs):
            actual = await original_generate(*args, **kwargs)
            actual_result_ids.append(actual.conversation_id)
            invalid_id = {
                "invalid_result_none": None,
                "invalid_result_integer": 42,
                "invalid_result_empty": "",
                "invalid_result_foreign": foreign.conversation_id if foreign is not None else None,
            }[scenario]
            return replace(actual, conversation_id=invalid_id)

        ai_task.async_generate_data = tampered_public_result

    parent_cleaned = []
    parent_context = (
        chat_session.async_get_chat_session(h, "synthetic-owned-parent")
        if scenario == "prior_session"
        else nullcontext(None)
    )
    try:
        with parent_context as parent:
            if parent is not None:
                parent.async_on_cleanup(lambda: parent_cleaned.append("parent_cleaned"))
            async with asyncio.timeout(
                0.05 if scenario in {"cancel_cleanup_error", "cancel_swallowed"} else 5
            ):
                wire = await sp.generate(
                    h,
                    agent_id=conv_id,
                    task_id=ids[0],
                    prompt=brief.prompt(verified_drafts=True),
                    brief=brief,
                    admission=lambda: guards.append("actual_guard"),
                )
            if parent is not None:
                assert chat_session.current_session.get() is parent and parent_cleaned == []
                parent.async_cleanup()  # Only the test owner releases its own parent.
    except BaseException as exc:
        failure = {
            "type": type(exc).__name__,
            "code": getattr(exc, "code", None),
            "message": str(exc)[:120],
            "notes": getattr(exc, "__notes__", []),
        }
    finally:
        ai_task.async_generate_data = original_generate
    assert sp.current_generation.get() is None
    if scenario.startswith("invalid_result_"):
        assert wire is None and failure is not None and attempts == 1
        expected_code = (
            "structured_playback_session_changed"
            if scenario in {"invalid_result_foreign", "invalid_result_empty"}
            else "structured_playback_result_invalid"
        )
        assert failure["code"] == expected_code, {"observed": failure["code"], "expected": expected_code}
        assert foreign_cleaned == [] and cleanup == []
        # The tamper layer still owns the true return handle. Core deliberately
        # cannot guess it from an invalid result or clean a different session.
        for actual_id in actual_result_ids:
            own = h.data[chat_session.DATA_CHAT_SESSION][actual_id]
            assert own is not foreign
            own.async_cleanup()
        assert cleanup == ["own_cleaned"]
        if foreign is not None:
            foreign.async_cleanup()
        assert source_before == product_hashes(ROOT)
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "status": "PASS",
                    "scope": "PUBLIC_RESULT_TAMPER_AFTER_REAL_OFFICIAL_TASK_NOT_MODEL_AUTHORITY",
                    "SDK_boundary_calls": attempts,
                    "SDK_return_receipts": len(receipts),
                    "paid_calls": 0,
                    "failure": failure,
                    "Core_foreign_cleanup": 0,
                    "true_handle_cleanup": "TAMPER_TEST_OWNER_ONLY",
                    "product_hashes_before": source_before,
                    "product_hashes_after": product_hashes(ROOT),
                    "source_unchanged": True,
                },
                indent=2,
            )
        )
        await api.close()
        await h.async_stop(force=True)
        return
    if scenario in {"valid", "prior_session"}:
        assert failure is None, failure
        assert json.loads(wire) == json.loads(text)
        compiled = brief.decode_drafts(wire, lambda x: x)
        assert compiled.texts == ("I’m handing you the {media_kind} {title}. {status}",)
        assert len(guards) == 2 and cleanup == ["own_cleaned"] and attempts == 1
    else:
        print(
            json.dumps(
                {
                    "original_failure": failure,
                    "SDK_boundary_calls": attempts,
                    "SDK_return_receipts": len(receipts),
                    "cleanup": cleanup,
                }
            ),
            file=sys.stderr,
        )
        assert wire is None and failure is not None
        if scenario in {"unsafe_store", "missing_task"}:
            assert (
                attempts == 0
                and len(receipts) == 0
                and failure["code"] == "structured_playback_task_unqualified"
            )
        elif scenario in {"late_revoke", "task_ABA", "agent_revoke"}:
            assert (
                len(receipts) == 1
                and failure["code"]
                == {
                    "late_revoke": "structured_playback_task_unqualified",
                    "task_ABA": "structured_playback_task_changed",
                    "agent_revoke": "conversation_agent_scope_unqualified",
                }[scenario]
                and cleanup == ["own_cleaned"]
            )
        elif scenario == "provider_error_cleanup_error":
            assert (
                failure["message"] == "synthetic_primary_provider_failure"
                and "structured_playback_cleanup_failed" in failure["notes"]
                and cleanup == ["own_cleaned"]
                and attempts == 1
                and len(receipts) == 0
            )
        elif scenario in {"cancel_cleanup_error", "cancel_swallowed"}:
            assert (
                failure["type"] == "TimeoutError" and cleanup == ["own_cleaned"] and attempts == 1
            )
        elif scenario == "unexpected_tool":
            assert (
                failure["type"] == "HomeAssistantError"
                and attempts == 1
                and cleanup == ["own_cleaned"]
            )
        else:
            raise AssertionError("unknown_case")
    if scenario not in {"valid", "prior_session"}:
        from homeassistant.helpers import chat_session

        assert chat_session.current_session.get() is None
        assert source_before == product_hashes(ROOT)
        print(
            json.dumps(
                {
                    "product_hashes_before": source_before,
                    "product_hashes_after": product_hashes(ROOT),
                    "source_unchanged": True,
                    "scenario": scenario,
                    "decision": "EXPECTED_FAILURE_REMAINS_CLOSED",
                    "SDK_boundary_calls": attempts,
                    "SDK_return_receipts": len(receipts),
                    "paid_calls": 0,
                    "failure": failure,
                    "cleanup": cleanup,
                    "context_restored": True,
                },
                indent=2,
            )
        )
        await api.close()
        await h.async_stop(force=True)
        return
    schema = receipts[0]["strict_format"]["schema"]

    def strict_objects(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for v in node.values():
                strict_objects(v)
        elif isinstance(node, list):
            for v in node:
                strict_objects(v)

    strict_objects(schema)
    assert source_before == product_hashes(ROOT)
    print(
        json.dumps(
            {
                "product_hashes_before": source_before,
                "product_hashes_after": product_hashes(ROOT),
                "source_unchanged": True,
                "decision": "OFFICIAL_PUBLIC_TASK_TO_SDK_STRICT_SCHEMA_PROVED_NO_NETWORK",
                "sdk_boundary_calls": attempts,
                "SDK_return_receipts": len(receipts),
                "paid_calls": 0,
                "product_capture_generate_compile": True,
                "real_entity_module": type(h.data["ai_task"].get_entity(ids[0])).__module__,
                "typed_result_valid": True,
                "receipts": receipts,
                "limitations": [
                    "Actual SDK schema has minItems1/maxItems2; not real provider acceptance",
                    "No original raw duplicate-key observability",
                    "No production task configuration or activation",
                    "Unexpected-tool and cancellation tests still required",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    await api.close()
    await h.async_stop(force=True)


asyncio.run(main())
