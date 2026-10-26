"""Optional public HA AI Task generation; this is a typed, not raw-JSON, ABI.

Only an explicitly selected official task may produce playback gaps. HA parses
the provider response before returning it: raw duplicate-key observability is
not available here. Legacy raw decoders and the complete compiler/reviewer keep
their own boundaries. No task, credentials or provider configuration is created.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from contextvars import ContextVar
import hashlib
import json
import sys

SUPPORTED_HA_VERSION = "2026.10.0"
TASK_CONFIG = "assist_structured_task_id"

# Trusted, bounded structural rules, not a grammar or prose generator. The
# original compiler still rejects controls/braces and enforces whole-text bounds.
FIRST_GAP_PATTERN = r"^[^{}\r\n]*[ '’]$"
BETWEEN_GAP_PATTERN = r"^(?: |[ .!?;,:()—–-][^{}\r\n]*[ '’])$"
STATUS_GAP_PATTERN = r"^(?:[.!?] |[ .!?;,:()—–-][^{}\r\n]*[.!?] )$"


@dataclass(frozen=True)
class GenerationWitness:
    prompt_sha256: str
    role_order: tuple[str, ...]


current_generation: ContextVar[GenerationWitness | None] = ContextVar(
    "djconnect_structured_playback_generation", default=None)


def role_structure(brief):
    """Public service selectors describe only original Core-owned role names."""
    from .playback_request import PlaybackRequestBrief
    if type(brief) is not PlaybackRequestBrief:
        raise ValueError("structured_playback_scope")
    roles = brief.literal_gap_slots()
    if (not roles or len(set(roles)) != len(roles) or roles[-1] != "status"
            or not set(roles) <= {"media_kind", "title", "artist", "album", "status"}):
        raise ValueError("structured_playback_roles")
    def field(selector):
        return {"required": True, "selector": selector}
    return {
        "schema": field({"select": {"options": ["playback_role_gaps_v3"]}}),
        "drafts": field({"object": {"multiple": True, "fields": {
            "gaps": field({"object": {"fields": {
                role: field({"text": {}}) for role in roles}}})}}}),
    }


def freeze_typed_reply(value):
    """Freeze the official typed result; never repair a malformed model word."""
    if type(value) is not dict:
        raise ValueError("structured_playback_result")
    # The existing decoder below this boundary still owns exact roles, strings,
    # character/length/status checks and all-before-normalize batch admission.
    try:
        wire = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(wire.encode("utf-8")) > 8192:
            raise ValueError("structured_playback_result")
    except (TypeError, RecursionError, UnicodeError) as exc:
        raise ValueError("structured_playback_result") from exc
    return wire


def role_schema(brief):
    """The exported AI Task API accepts this exact public probatio schema."""
    import probatio
    fields = role_structure(brief)["drafts"]["selector"]["object"]["fields"]
    roles = tuple(fields["gaps"]["selector"]["object"]["fields"])
    rules = {}
    for index, role in enumerate(roles):
        if role == "title" and index > 0 and roles[index - 1] == "media_kind":
            rule = probatio.All(str, probatio.In([" "]))
        else:
            pattern = (STATUS_GAP_PATTERN if role == "status" else
                       FIRST_GAP_PATTERN if index == 0 else BETWEEN_GAP_PATTERN)
            rule = probatio.All(str, probatio.Length(max=700), probatio.Match(pattern))
        rules[probatio.Required(role)] = rule
    return probatio.Schema({
        probatio.Required("schema"): probatio.All(str, probatio.In(["playback_role_gaps_v3"])),
        probatio.Required("drafts"): probatio.All([
            {probatio.Required("gaps"): rules}
        ], probatio.Length(min=1, max=2)),
    })


def _same_typed_value(original, validated):
    if type(original) is not type(validated):
        return False
    if type(original) is dict:
        return (original.keys() == validated.keys()
                and all(_same_typed_value(value, validated[key])
                        for key, value in original.items()))
    if type(original) is list:
        return (len(original) == len(validated)
                and all(_same_typed_value(left, right)
                        for left, right in zip(original, validated, strict=True)))
    return original == validated


def validate_typed_reply(value, structure):
    """Validate a bounded copy; return only the unchanged pre-validation wire."""
    wire = freeze_typed_reply(value)
    # Never compare against an aliased validator input: even an in-place
    # mutation must differ from this private, pre-validation snapshot.
    snapshot = json.loads(wire)
    try:
        validated = structure(json.loads(wire))
        if not _same_typed_value(snapshot, validated):
            raise ValueError("structured_playback_result")
    except Exception:
        # No provider body, role values or library error details are logged.
        raise ValueError("structured_playback_result") from None
    return wire


@dataclass(frozen=True)
class TaskBinding:
    agent: object
    entity: object
    entry: object
    subentry: object
    fingerprint: str


def capture_task(hass, agent_id, task_id):
    """Missing, unsafe or changed explicit configuration never selects a default."""
    from homeassistant.const import __version__
    from homeassistant.components import ai_task
    from homeassistant.components.ai_task.const import DATA_COMPONENT
    from homeassistant.helpers import entity_registry
    from .ask_dj.dialogue import DialogueError, qualify_agent
    if (__version__ != SUPPORTED_HA_VERSION or type(task_id) is not str
            or not task_id.startswith("ai_task.") or len(task_id) > 255):
        raise DialogueError("structured_playback_task_unqualified", 503)
    agent = qualify_agent(hass, agent_id)
    component = hass.data.get(DATA_COMPONENT)
    entity = component.get_entity(task_id) if component is not None else None
    registry = entity_registry.async_get(hass)
    record = registry.async_get(task_id)
    if (entity is None or type(entity).__module__ != "homeassistant.components.openai_conversation.ai_task"
            or type(entity).__name__ != "OpenAITaskEntity" or not entity.available
            or not entity.supported_features & ai_task.AITaskEntityFeature.GENERATE_DATA
            or record is None or record.disabled_by is not None):
        raise DialogueError("structured_playback_task_unqualified", 503)
    entry, subentry = entity.entry, entity.subentry
    agent_record = registry.async_get(getattr(agent, "entity_id", ""))
    if (entry is not getattr(agent, "entry", None)
            or entry.domain != "openai_conversation" or entry.state.value != "loaded"
            or subentry.subentry_type != "ai_task_data"
            or record.config_entry_id != entry.entry_id
            or record.config_subentry_id != subentry.subentry_id
            or entry.subentries.get(subentry.subentry_id) is not subentry
            or entry.subentries.get(agent.subentry.subentry_id) is not agent.subentry
            or agent_record is None or agent_record.disabled_by is not None
            or agent_record.config_entry_id != entry.entry_id
            or agent_record.config_subentry_id != agent.subentry.subentry_id):
        raise DialogueError("structured_playback_task_unqualified", 503)
    options = subentry.data
    required = {"chat_model", "max_tokens", "reasoning_effort", "store_responses",
                "web_search", "code_interpreter", "service_tier"}
    if (not isinstance(options, Mapping) or not required.issubset(options)
            or any(options[name] is not False for name in
                   ("store_responses", "web_search", "code_interpreter"))
            or options["service_tier"] not in {"auto", "default"}
            or type(options["max_tokens"]) is not int
            or not 1 <= options["max_tokens"] <= 3000
            or type(options["chat_model"]) is not str or not options["chat_model"]
            or type(options["reasoning_effort"]) is not str):
        raise DialogueError("structured_playback_task_unqualified", 503)
    original = agent.subentry.data
    if (any(original.get(key) != options[key] for key in
            ("chat_model", "max_tokens", "reasoning_effort"))
            or original.get("service_tier", "auto") != options["service_tier"]):
        raise DialogueError("structured_playback_task_unqualified", 503)
    # Entire public option maps plus revision timestamps detect configuration
    # changes, including an update and restore during the model await.
    fingerprint = json.dumps({"task": dict(options), "agent": dict(original),
        "entry_modified": str(entry.modified_at), "registry_modified": str(record.modified_at),
        "registry_id": record.id, "agent_subentry": agent.subentry.subentry_id,
        "agent_registry_id": agent_record.id,
        "agent_registry_modified": str(agent_record.modified_at)},
        sort_keys=True, ensure_ascii=False, allow_nan=False)
    return TaskBinding(agent, entity, entry, subentry, fingerprint)


async def generate(hass, *, agent_id, task_id, prompt, brief=None, admission, artist=None):
    """One public task in this coroutine, with same-task cancellation cleanup."""
    from homeassistant.components import ai_task
    from homeassistant.helpers import chat_session
    from .ask_dj.dialogue import DialogueError
    binding = capture_task(hass, agent_id, task_id)
    admission()
    # Call the exported API with its public schema type, never an entity
    # method, private provider client or preferred-entity lookup.
    if not hass.services.has_service("ai_task", "generate_data"):
        raise DialogueError("structured_playback_task_unqualified", 503)
    from .structured_artist import ArtistTask, current_operation, schema as artist_schema
    if artist is not None:
        if (type(artist) is not ArtistTask or brief is not None
                or artist.prompt_sha256 != hashlib.sha256(prompt.encode()).hexdigest()):
            raise DialogueError("structured_artist_scope", 503)
        structure = artist_schema(artist)
        task_name = "DJConnect " + artist.operation
    else:
        structure = role_schema(brief)
        task_name = "DJConnect playback handover"
    args = {"task_name": task_name, "entity_id": task_id,
            "instructions": prompt, "structure": structure}
    session_var = getattr(chat_session, "current_session", None)
    if session_var is None:
        raise DialogueError("structured_playback_task_unqualified", 503)
    generation = (GenerationWitness(hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                                   tuple(brief.literal_gap_slots())) if artist is None else None)
    prior = session_var.get()
    prior_ids = frozenset(hass.data.get(chat_session.DATA_CHAT_SESSION, {}))
    token = session_var.set(prior)
    generation_token = current_generation.set(generation)
    operation_token = current_operation.set(artist)
    result = None
    wire = None
    owned_session = None
    try:
        # Do not use wait_for/create_task: their separate ContextVar context
        # would hide the public task's session when its await is cancelled.
        async with asyncio.timeout(30):
            result = await ai_task.async_generate_data(hass, **args, llm_api=None, attachments=None)
            if (task := asyncio.current_task()) is not None and task.cancelling():
                raise asyncio.CancelledError
            if type(result) is not ai_task.GenDataTaskResult:
                raise DialogueError("structured_playback_result_invalid", 502)
            try:
                wire = validate_typed_reply(result.data, structure)
            except ValueError:
                raise DialogueError("structured_playback_result_invalid", 502) from None
    finally:
        primary = sys.exception()
        try:
            active = session_var.get()
            if active is not None and active is not prior:
                if active.conversation_id in prior_ids:
                    raise DialogueError("structured_playback_session_changed", 503)
                owned_session = active
                active.async_cleanup()
            elif (type(result) is ai_task.GenDataTaskResult
                    and type(result.conversation_id) is str
                    and (prior is None or result.conversation_id != prior.conversation_id)):
                if (result.conversation_id in prior_ids
                        or result.conversation_id not in hass.data.get(chat_session.DATA_CHAT_SESSION, {})):
                    raise DialogueError("structured_playback_session_changed", 503)
                with chat_session.async_get_chat_session(hass, result.conversation_id) as own:
                    if own.conversation_id != result.conversation_id or own is prior:
                        raise DialogueError("structured_playback_session_changed", 503)
                    owned_session = own
                    own.async_cleanup()
        except BaseException:
            if primary is None:
                raise
            # Cleanup must not replace the original provider failure or
            # cancellation. No provider text or private IDs enter the note.
            primary.add_note("structured_playback_cleanup_failed")
        finally:
            try:
                session_var.reset(token)
            finally:
                try:
                    current_generation.reset(generation_token)
                finally:
                    current_operation.reset(operation_token)
    if (task := asyncio.current_task()) is not None and task.cancelling():
        raise asyncio.CancelledError
    current = capture_task(hass, agent_id, task_id)
    if (current.agent is not binding.agent or current.entity is not binding.entity
            or current.entry is not binding.entry or current.subentry is not binding.subentry
            or current.fingerprint != binding.fingerprint):
        raise DialogueError("structured_playback_task_changed", 503)
    admission()
    if (type(result) is not ai_task.GenDataTaskResult
            or type(result.conversation_id) is not str or not result.conversation_id
            or result.conversation_id in prior_ids
            or (prior is not None and result.conversation_id == prior.conversation_id)
            or owned_session is None or owned_session.conversation_id != result.conversation_id
            or hass.data.get(chat_session.DATA_CHAT_SESSION, {}).get(result.conversation_id) is not owned_session):
        raise DialogueError("structured_playback_result_invalid", 502)
    return wire
