"""Read-only Home Assistant entity context for DJConnect Ask DJ."""
from __future__ import annotations

from typing import Any

from .const import CONF_SMART_HOME_CONTEXT_ENTITIES

MAX_CONTEXT_ENTITIES = 24
MAX_ATTR_VALUE_LENGTH = 80
CONTEXT_ATTRIBUTE_KEYS = (
    "unit_of_measurement",
    "device_class",
    "friendly_name",
    "current_position",
    "brightness",
    "temperature",
    "humidity",
    "battery_level",
)


def normalize_entity_allowlist(value: Any) -> list[str]:
    """Return a stable, de-duplicated entity allowlist."""
    if isinstance(value, str):
        raw_values = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = []
    seen: set[str] = set()
    result: list[str] = []
    for raw in raw_values:
        entity_id = str(raw or "").strip().lower()
        if not entity_id or "." not in entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        result.append(entity_id)
        if len(result) >= MAX_CONTEXT_ENTITIES:
            break
    return result


def configured_entity_allowlist(runtime: Any) -> list[str]:
    """Return entities explicitly exposed to DJConnect for read-only context."""
    config = getattr(runtime, "config", {}) or {}
    options = getattr(runtime, "options", {}) or {}
    return normalize_entity_allowlist(
        options.get(CONF_SMART_HOME_CONTEXT_ENTITIES)
        if options.get(CONF_SMART_HOME_CONTEXT_ENTITIES) is not None
        else config.get(CONF_SMART_HOME_CONTEXT_ENTITIES)
    )


def smart_home_context(hass: Any, runtime: Any) -> list[dict[str, Any]]:
    """Read current HA state for explicitly allowed entities only."""
    states = getattr(hass, "states", None)
    if states is None or not hasattr(states, "get"):
        return []
    items: list[dict[str, Any]] = []
    for entity_id in configured_entity_allowlist(runtime):
        state = states.get(entity_id)
        if state is None:
            continue
        attributes = getattr(state, "attributes", {}) or {}
        item: dict[str, Any] = {
            "entity_id": entity_id,
            "state": str(getattr(state, "state", "") or ""),
        }
        name = getattr(state, "name", None) or attributes.get("friendly_name")
        if name:
            item["name"] = str(name)
        exposed_attrs: dict[str, Any] = {}
        if isinstance(attributes, dict):
            for key in CONTEXT_ATTRIBUTE_KEYS:
                value = attributes.get(key)
                if value is None:
                    continue
                exposed_attrs[key] = str(value)[:MAX_ATTR_VALUE_LENGTH]
        if exposed_attrs:
            item["attributes"] = exposed_attrs
        items.append(item)
    return items


def smart_home_context_text(items: list[dict[str, Any]]) -> str:
    """Return compact prompt text for read-only smart-home context."""
    lines: list[str] = []
    for item in items:
        label = item.get("name") or item.get("entity_id")
        state = item.get("state")
        attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
        unit = attrs.get("unit_of_measurement") if isinstance(attrs, dict) else None
        state_text = f"{state} {unit}".strip() if unit else str(state)
        lines.append(f"{label} ({item.get('entity_id')}): {state_text}")
    return "\n".join(lines)
