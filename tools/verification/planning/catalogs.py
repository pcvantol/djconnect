"""Catalog loading for verification planning assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PlanningCatalogs:
    def __init__(self, root: Path) -> None:
        self.root = root

    def modes(self) -> dict[str, dict[str, Any]]:
        return _by_id(_load_json(self.root / "verification/modes/catalog/modes.json").get("modes", []))

    def policies(self) -> dict[str, dict[str, Any]]:
        return _by_id(_load_json(self.root / "verification/policies/catalog/policies.json").get("policies", []))

    def data_profiles(self) -> dict[str, dict[str, Any]]:
        profiles: dict[str, dict[str, Any]] = {}
        profile_dir = self.root / "verification/data/profiles"
        for path in sorted(profile_dir.glob("*.json")):
            data = _load_json(path)
            profile_id = str(data.get("id") or path.stem)
            profiles[profile_id] = data
        return profiles


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in items if isinstance(item, dict) and item.get("id")}
