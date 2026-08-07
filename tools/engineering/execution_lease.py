"""Canonical active-run ownership leases backed solely by Engineering SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import socket
import uuid

from .storage import EngineeringStorageError, open_storage

LEASE_VERSION = 1
HEARTBEAT_INTERVAL_SECONDS = 15
LEASE_TIMEOUT_SECONDS = 90
TERMINAL_PHASES = frozenset({"COMPLETE", "BLOCKED", "FAILED"})


class LeaseConflictError(EngineeringStorageError):
    """Raised when another non-expired host instance owns the run."""


@dataclass(frozen=True)
class Lease:
    lease_id: str
    run_id: str
    host_identity: str
    host_instance_id: str
    acquired_at: str
    last_heartbeat_at: str
    expires_at: str
    lease_state: str


def host_identity() -> str:
    return socket.gethostname()[:120] or "execution-host"


def host_instance_id() -> str:
    return f"{uuid.uuid4()}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _event(connection: object, lease_id: str, run_id: str, event: str, outcome: str | None = None) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO execution_lease_events(lease_id,run_id,event_type,outcome,recorded_at) VALUES(?,?,?,?,?)",
        (lease_id, run_id, event, outcome, _now().isoformat()),
    )


def acquire(root: Path, run_id: str, *, identity: str, instance_id: str, process_id: int | None = None, timeout_seconds: int = LEASE_TIMEOUT_SECONDS) -> Lease:
    if not 0 < HEARTBEAT_INTERVAL_SECONDS < timeout_seconds:
        raise EngineeringStorageError("Active-run lease policy is invalid.")
    now = _now()
    expiry = now + timedelta(seconds=timeout_seconds)
    connection = open_storage(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE execution_run_leases SET lease_state='EXPIRED',updated_at=? WHERE run_id=? AND lease_state='ACTIVE' AND expires_at<?",
            (now.isoformat(), run_id, now.isoformat()),
        )
        active = connection.execute(
            "SELECT lease_id,host_instance_id FROM execution_run_leases WHERE run_id=? AND lease_state='ACTIVE'", (run_id,)
        ).fetchone()
        if active:
            raise LeaseConflictError("A live Execution Host instance already owns this run.")
        lease_id = f"lease-{uuid.uuid4()}"
        values = (lease_id, run_id, identity, instance_id, process_id, now.isoformat(), now.isoformat(), expiry.isoformat(), "ACTIVE", LEASE_VERSION, now.isoformat(), now.isoformat())
        connection.execute("INSERT INTO execution_run_leases(lease_id,run_id,host_identity,host_instance_id,process_id,acquired_at,last_heartbeat_at,expires_at,lease_state,lease_version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", values)
        _event(connection, lease_id, run_id, "LEASE_ACQUIRED")
        connection.execute("COMMIT")
        return Lease(lease_id, run_id, identity, instance_id, now.isoformat(), now.isoformat(), expiry.isoformat(), "ACTIVE")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()


def heartbeat(root: Path, lease: Lease, *, timeout_seconds: int = LEASE_TIMEOUT_SECONDS) -> Lease:
    now = _now(); expiry = now + timedelta(seconds=timeout_seconds)
    connection = open_storage(root)
    try:
        updated = connection.execute("UPDATE execution_run_leases SET last_heartbeat_at=?,expires_at=?,updated_at=? WHERE lease_id=? AND run_id=? AND host_instance_id=? AND lease_state='ACTIVE'", (now.isoformat(), expiry.isoformat(), now.isoformat(), lease.lease_id, lease.run_id, lease.host_instance_id)).rowcount
        if updated != 1:
            raise LeaseConflictError("Execution Host no longer owns the active-run lease.")
    finally:
        connection.close()
    return Lease(lease.lease_id, lease.run_id, lease.host_identity, lease.host_instance_id, lease.acquired_at, now.isoformat(), expiry.isoformat(), "ACTIVE")


def release(root: Path, lease: Lease) -> None:
    connection = open_storage(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        changed = connection.execute("UPDATE execution_run_leases SET lease_state='RELEASED',updated_at=? WHERE lease_id=? AND host_instance_id=? AND lease_state='ACTIVE'", (_now().isoformat(), lease.lease_id, lease.host_instance_id)).rowcount
        if changed:
            _event(connection, lease.lease_id, lease.run_id, "LEASE_RELEASED")
        connection.execute("COMMIT")
    finally:
        connection.close()


def reconcile_stale(root: Path) -> list[dict[str, str]]:
    """Expire only stale nonterminal ownership; never fabricate a terminal state."""
    now = _now().isoformat(); outcomes: list[dict[str, str]] = []
    connection = open_storage(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute("SELECT lease_id,run_id,host_instance_id,last_heartbeat_at FROM execution_run_leases WHERE lease_state='ACTIVE' AND expires_at<?", (now,)).fetchall()
        for lease_id, run_id, instance, heartbeat_at in rows:
            phase = connection.execute("SELECT phase FROM engineering_transactions WHERE run_id=?", (run_id,)).fetchone()
            outcome = "TERMINAL_EVIDENCE_PRESENT" if phase and phase[0] in TERMINAL_PHASES else "RECOVERABLE"
            connection.execute("UPDATE execution_run_leases SET lease_state='EXPIRED',updated_at=? WHERE lease_id=?", (now, lease_id))
            _event(connection, lease_id, run_id, "LEASE_EXPIRED")
            _event(connection, lease_id, run_id, "STALE_DETECTED", outcome)
            _event(connection, lease_id, run_id, "STALE_RECONCILED", outcome)
            outcomes.append({"run_id": run_id, "host_instance_id": instance, "last_heartbeat": heartbeat_at, "outcome": outcome})
        connection.execute("COMMIT")
    finally:
        connection.close()
    return outcomes


def liveness(root: Path, run_id: object) -> dict[str, object]:
    """Project canonical liveness without consulting status files or processes."""
    if not isinstance(run_id, str):
        return {"state": "UNAVAILABLE"}
    now = _now().isoformat(); connection = open_storage(root)
    try:
        row = connection.execute("SELECT host_identity,host_instance_id,last_heartbeat_at,expires_at,lease_state FROM execution_run_leases WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run_id,)).fetchone()
    finally:
        connection.close()
    if not row:
        return {"state": "STALE"}
    identity, instance, heartbeat_at, expires_at, state = row
    return {"state": "LIVE" if state == "ACTIVE" and expires_at >= now else "STALE", "lease_state": state, "host_identity": identity, "host_instance_id": instance, "last_heartbeat": heartbeat_at, "lease_expiry": expires_at}
