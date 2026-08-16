"""Read-only, run-scoped execution lifecycle projection for the console.

This module deliberately projects persisted Execution Host checkpoints only.  It
does not coordinate transitions, repair, retry, resume, liveness, or telemetry.
"""
from __future__ import annotations

import json
from pathlib import Path

from .storage import EngineeringStorageError, open_storage


TERMINAL = frozenset({"COMPLETE", "BLOCKED", "FAILED"})
_MANAGED_PATH = (
    "START", "INITIALIZE", "EXECUTE_AGENT", "REPAIR_AGENT",
    "WAIT_FOR_OPERATOR_MERGE", "FINALIZE_AGENT", "REPOSITORY_CLEANUP", "TERMINAL",
)
# Genesis has no pull-request merge boundary.  This is presentation of the
# existing mode contract, not a new execution sequence.
_GENESIS_PATH = (
    "START", "INITIALIZE", "EXECUTE_AGENT", "REPAIR_AGENT",
    "FINALIZE_AGENT", "REPOSITORY_CLEANUP", "TERMINAL",
)


def intended_path(execution_mode: object) -> tuple[str, ...]:
    """Return the canonical display path for one existing execution mode."""
    return _GENESIS_PATH if execution_mode == "GENESIS" else _MANAGED_PATH


def _checkpoint(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def projection(root: Path, run_id: str | None) -> dict[str, object]:
    """Project persisted lifecycle evidence for exactly one ``run_id``.

    Missing event history is explicitly represented as unavailable.  The
    terminal checkpoint may still be shown, but no intermediate progress is
    invented from reports, commits, timing or prompt content.
    """
    if not isinstance(run_id, str) or not run_id:
        return {"run_id": run_id, "available": False, "steps": []}
    try:
        connection = open_storage(root, create=False)
        try:
            row = connection.execute(
                "SELECT payload,phase FROM engineering_transactions WHERE run_id=?", (run_id,)
            ).fetchone()
            events = connection.execute(
                "SELECT phase,checkpoint,recorded_at FROM execution_lifecycle_events WHERE run_id=? ORDER BY id",
                (run_id,),
            ).fetchall()
            mode_row = connection.execute(
                "SELECT execution_mode FROM execution_runs WHERE run_id=?", (run_id,)
            ).fetchone()
        finally:
            connection.close()
    except EngineeringStorageError:
        return {"run_id": run_id, "available": False, "steps": []}
    if row is None:
        return {"run_id": run_id, "available": False, "steps": []}
    checkpoint = _checkpoint(row[0])
    phase = str(row[1])
    mode = checkpoint.get("execution_mode") or (mode_row[0] if mode_row else None) or "MANAGED"
    path = intended_path(mode)
    observed: dict[str, dict[str, object]] = {}
    repair_iterations = 0
    for event_phase, event_checkpoint, recorded_at in events:
        event = _checkpoint(event_checkpoint)
        if event_phase in path and event_phase not in {"START", "TERMINAL"}:
            observed[str(event_phase)] = {"started_at": recorded_at}
        if event_phase == "REPAIR_AGENT":
            repair_iterations = max(repair_iterations, _nonnegative_int(event.get("repair_iterations")))
    repair_iterations = max(repair_iterations, _nonnegative_int(checkpoint.get("repair_iterations")))
    evidence_available = bool(events)
    terminal_state = phase if phase in TERMINAL else None
    steps: list[dict[str, object]] = []
    for order, step_id in enumerate(path):
        state = "PENDING"
        step: dict[str, object] = {
            "id": step_id,
            "order": order,
            "presentation_key": f"lifecycle.step.{step_id.lower()}",
            "state": state,
        }
        if step_id == "START":
            step["state"] = "START"
        elif step_id == "TERMINAL":
            step["state"] = terminal_state or "PENDING"
            if terminal_state:
                step["terminal_outcome"] = terminal_state
        elif step_id in observed:
            step.update(observed[step_id])
            step["state"] = "ACTIVE" if phase == step_id and terminal_state is None else "COMPLETED"
        if step_id == "REPAIR_AGENT" and repair_iterations:
            step["iteration_count"] = repair_iterations
        steps.append(step)
    return {
        "run_id": run_id,
        "execution_mode": mode,
        "available": evidence_available,
        "terminal_state": terminal_state,
        "current_step": phase if phase in path else None,
        "steps": steps,
    }
