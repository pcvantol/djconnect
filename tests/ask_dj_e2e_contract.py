from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


PLAYBACK_MUTATION_COMMANDS = {
    "ask_dj_play_recommendation",
    "next",
    "pause",
    "play",
    "play_context_at",
    "previous",
    "save_current_track",
    "seek_relative",
    "set_current_track_favorite",
    "set_output",
    "set_repeat",
    "set_shuffle",
    "set_volume",
    "start_liked_proxy",
    "start_playlist",
    "volume_delta",
}


@dataclass
class AskDjE2ETrace:
    music_commands: list[str] = field(default_factory=list)
    followups: list[dict[str, Any]] = field(default_factory=list)
    tts_requests: list[str] = field(default_factory=list)
    process_text_requests: list[str] = field(default_factory=list)

    @property
    def spotify_commands(self) -> list[str]:
        """Backward-compatible alias for older tests."""
        return self.music_commands


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list):
        raise ValueError("Ask DJ E2E case file must contain a JSON list.")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate Ask DJ E2E case ids: {', '.join(duplicates)}")
    return cases


def validate_case_result(
    case: dict[str, Any],
    response: dict[str, Any],
    trace: AskDjE2ETrace | None = None,
) -> list[str]:
    expect = case.get("expect") or {}
    trace = trace or AskDjE2ETrace()
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(f"{case.get('id', '<unknown>')}: {message}")

    if "success" in expect and bool(response.get("success")) is not bool(expect["success"]):
        fail(f"success expected {expect['success']!r}, got {response.get('success')!r}")

    intent = response.get("intent") if isinstance(response.get("intent"), dict) else {}
    _expect_equal(expect, response, "action", fail)
    _expect_equal(expect, intent, "intent", fail)
    _expect_equal(expect, intent, "intent_category", fail, actual_key="category")
    _expect_equal(expect, intent, "intent_item_type", fail, actual_key="item_type")

    text = _response_text(response)
    for expected in expect.get("contains_all") or []:
        if expected.lower() not in text.lower():
            fail(f"text should contain {expected!r}; got {text!r}")
    contains_any = expect.get("contains_any") or []
    if contains_any and not any(value.lower() in text.lower() for value in contains_any):
        fail(f"text should contain one of {contains_any!r}; got {text!r}")
    for forbidden in expect.get("not_contains") or []:
        if forbidden.lower() in text.lower():
            fail(f"text should not contain {forbidden!r}; got {text!r}")

    if expect.get("no_audio_url") and response.get("audio_url"):
        fail(f"audio_url should be absent, got {response.get('audio_url')!r}")

    _expect_count(expect, response, "images", fail)
    _expect_count(expect, response, "items", fail)
    _expect_count(expect, response, "playback_actions", fail)
    _expect_count(expect, response, "confirmation_actions", fail)
    _expect_min_count(expect, response, "items", fail)

    _expect_values_include(
        expect,
        response.get("playback_actions") or [],
        "playback_action_kinds_include",
        "kind",
        fail,
    )
    confirmation_values = [
        action.get("response_value")
        for action in response.get("confirmation_actions") or []
        if isinstance(action, dict)
    ]
    if "confirmation_response_values" in expect:
        expected_values = expect["confirmation_response_values"]
        if confirmation_values != expected_values:
            fail(f"confirmation response values expected {expected_values!r}, got {confirmation_values!r}")
    _expect_values_include(
        expect,
        response.get("sources") or [],
        "source_values_include",
        "source",
        fail,
    )

    commands = list(trace.music_commands)
    if "required_music_commands" in expect:
        for command in expect["required_music_commands"]:
            if command not in commands:
                fail(f"required music command {command!r} was not called; got {commands!r}")
    if "allowed_music_commands" in expect:
        allowed = set(expect["allowed_music_commands"])
        unexpected = [command for command in commands if command not in allowed]
        if unexpected:
            fail(f"unexpected music commands {unexpected!r}; allowed {sorted(allowed)!r}")
    if expect.get("forbid_music_mutations") or expect.get("forbid_spotify_mutations"):
        mutations = [command for command in commands if command in PLAYBACK_MUTATION_COMMANDS]
        if mutations:
            fail(f"music playback mutations were forbidden but called {mutations!r}")
    if expect.get("required_process_text") and not trace.process_text_requests:
        fail("run_text_command was expected but not called")
    for subset in expect.get("playback_actions_include") or []:
        if not _contains_mapping_subset(response.get("playback_actions") or [], subset):
            fail(f"playback_actions should include {subset!r}; got {response.get('playback_actions')!r}")
    for subset in expect.get("items_include") or []:
        if not _contains_mapping_subset(response.get("items") or [], subset):
            fail(f"items should include {subset!r}; got {response.get('items')!r}")
    for key, value in (expect.get("top_level_fields") or {}).items():
        if response.get(key) != value:
            fail(f"top-level {key!r} expected {value!r}, got {response.get(key)!r}")

    return errors


def _response_text(response: dict[str, Any]) -> str:
    values = [
        response.get("text"),
        response.get("dj_text"),
        response.get("message"),
    ]
    assistant = response.get("assistant_message")
    if isinstance(assistant, dict):
        values.append(assistant.get("text"))
    return "\n".join(str(value) for value in values if value)


def _expect_equal(
    expect: dict[str, Any],
    actual: dict[str, Any],
    expect_key: str,
    fail: Any,
    *,
    actual_key: str | None = None,
) -> None:
    if expect_key not in expect:
        return
    actual_key = actual_key or expect_key
    if actual.get(actual_key) != expect[expect_key]:
        fail(f"{expect_key} expected {expect[expect_key]!r}, got {actual.get(actual_key)!r}")


def _expect_count(expect: dict[str, Any], response: dict[str, Any], key: str, fail: Any) -> None:
    expect_key = f"{key}_count"
    if expect_key not in expect:
        return
    value = response.get(key) or []
    if len(value) != int(expect[expect_key]):
        fail(f"{key} count expected {expect[expect_key]}, got {len(value)}")


def _expect_min_count(expect: dict[str, Any], response: dict[str, Any], key: str, fail: Any) -> None:
    expect_key = f"{key}_min_count"
    if expect_key not in expect:
        return
    value = response.get(key) or []
    if len(value) < int(expect[expect_key]):
        fail(f"{key} count expected at least {expect[expect_key]}, got {len(value)}")


def _expect_values_include(
    expect: dict[str, Any],
    values: list[Any],
    expect_key: str,
    value_key: str,
    fail: Any,
) -> None:
    if expect_key not in expect:
        return
    actual = [
        item.get(value_key)
        for item in values
        if isinstance(item, dict) and item.get(value_key) is not None
    ]
    missing = [value for value in expect[expect_key] if value not in actual]
    if missing:
        fail(f"{expect_key} missing {missing!r}; got {actual!r}")


def _contains_mapping_subset(items: list[Any], subset: dict[str, Any]) -> bool:
    for item in items:
        if not isinstance(item, dict):
            continue
        if all(item.get(key) == value for key, value in subset.items()):
            return True
    return False
