"""Durable WidgetKit choice for one original ordinary pairing."""

from dataclasses import dataclass
import uuid

from .surface_push_contract import require

_MAX_REVISION = 9_007_199_254_740_991


@dataclass(frozen=True)
class WidgetConsent:
    enabled: bool
    revision: int

    def wire(self):
        return {"contract_version": 1, "enabled": self.enabled, "revision": self.revision}


def read_widget_consent_in_transaction(tx, pair):
    binding = pair.registration.binding
    identity = tx.fetchone("SELECT instance_id FROM djconnect_surface_pair_store WHERE singleton=1")
    row = tx.fetchone(
        "SELECT entry_id,auth_generation,state FROM djconnect_surface_pairs WHERE binding=?", (binding,))
    acknowledgement = pair.acknowledgement
    require(identity and identity[0] == acknowledgement.instance_id
            and row and tuple(row) == (pair.entry.entry_id, acknowledgement.auth_generation, "recorded"),
            "native_pair_changed", 403)
    current = tx.fetchone(
        "SELECT enabled,revision FROM djconnect_native_widget_consent "
        "WHERE local_binding=? ORDER BY revision DESC LIMIT 1", (binding,))
    return WidgetConsent(bool(current[0]), current[1]) if current else WidgetConsent(False, 0)


async def read_widget_consent(pair):
    require(pair.current(), "native_pair_changed", 403)
    consent = await pair.persistence.async_in_transaction(lambda tx: read_widget_consent_in_transaction(tx, pair))
    require(pair.current(), "native_pair_changed", 403)
    return consent


async def write_widget_consent(pair, *, enabled, operation_id, expected_revision):
    """Compare the original revision, then commit and read back an exact choice."""
    require(type(enabled) is bool and type(expected_revision) is int
            and 0 <= expected_revision < _MAX_REVISION and type(operation_id) is str
            and len(operation_id) == 36, "invalid_request")
    try:
        identifier = uuid.UUID(operation_id)
    except ValueError:
        require(False, "invalid_request")
    require(str(identifier) == operation_id and identifier.version == 4, "invalid_request")
    require(pair.current(), "native_pair_changed", 403)
    binding = pair.registration.binding

    def write(tx):
        current = read_widget_consent_in_transaction(tx, pair)
        previous = tx.fetchone(
            "SELECT enabled,revision FROM djconnect_native_widget_consent "
            "WHERE local_binding=? AND operation_id=?", (binding, operation_id))
        revision = expected_revision + 1
        if previous is not None:
            require(tuple(previous) == (int(enabled), revision), "native_widget_consent_conflict", 409)
            return WidgetConsent(enabled, revision)
        require(current.revision == expected_revision, "native_widget_consent_conflict", 409)
        # An off intent at an already-off revision must fence any queued on intent.
        tx.execute(
            "INSERT INTO djconnect_native_widget_consent(local_binding,operation_id,enabled,revision) "
            "VALUES(?,?,?,?)", (binding, operation_id, int(enabled), revision))
        return WidgetConsent(enabled, revision)

    result = await pair.persistence.async_in_transaction(
        write, authorize=pair.current, finalize_authorize=pair.current, require_full_sync=True)
    require(pair.current(), "native_pair_changed", 403)
    return result
