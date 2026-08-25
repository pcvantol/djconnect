"""Bounded, local-only preferences for the private Engineering dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from .storage import open_storage


DEFAULTS = {
    "log_retention_days": 30,
    "log_level": "INFO",
}
OPTIONS = {
    "log_retention_days": frozenset({30, 60, 90, 120, 180, 360}),
    "log_level": frozenset({"INFO", "DEBUG"}),
}
PREFIX = "dashboard_configuration."


def get(root: Path) -> dict[str, object]:
    connection = open_storage(root)
    try:
        values = dict(DEFAULTS)
        for key, raw in connection.execute(
            "SELECT key,value FROM engineering_metadata WHERE key LIKE ?", (PREFIX + "%",)
        ):
            name = str(key).removeprefix(PREFIX)
            try:
                value = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            if name in OPTIONS and value in OPTIONS[name]:
                values[name] = value
        return values
    finally:
        connection.close()


def update(root: Path, key: str, value: object) -> dict[str, object]:
    if key not in OPTIONS or value not in OPTIONS[key]:
        raise ValueError("Ongeldige dashboardinstelling.")
    connection = open_storage(root)
    try:
        previous = DEFAULTS[key]
        row = connection.execute(
            "SELECT value FROM engineering_metadata WHERE key=?", (PREFIX + key,)
        ).fetchone()
        if row is not None:
            try:
                stored = json.loads(row[0])
            except (TypeError, json.JSONDecodeError):
                stored = previous
            if stored in OPTIONS[key]:
                previous = stored
        connection.execute(
            "INSERT INTO engineering_metadata(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (PREFIX + key, json.dumps(value)),
        )
        return {"key": key, "previous": previous, "value": value,
                "changed_at": datetime.now(timezone.utc).isoformat()}
    finally:
        connection.close()
