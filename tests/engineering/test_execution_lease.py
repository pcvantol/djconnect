from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.engineering.agent_state import StateStore, TransactionState
from tools.engineering.execution_lease import LeaseConflictError, acquire, heartbeat, reconcile_stale, release
from tools.engineering.storage import open_storage


class ExecutionLeaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        StateStore(self.root / ".engineering" / "engineering-runs").save(
            TransactionState("inbox-lease", "repo", "prompt.md", "INITIALIZE")
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_acquires_heartbeats_and_releases_one_canonical_lease(self) -> None:
        lease = acquire(self.root, "inbox-lease", identity="host", instance_id="instance-a")
        renewed = heartbeat(self.root, lease)
        release(self.root, renewed)
        with open_storage(self.root) as connection:
            self.assertEqual(connection.execute("SELECT lease_state FROM execution_run_leases WHERE lease_id=?", (lease.lease_id,)).fetchone()[0], "RELEASED")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM execution_lease_events").fetchone()[0], 2)

    def test_conflicting_live_owner_fails_closed(self) -> None:
        acquire(self.root, "inbox-lease", identity="host", instance_id="instance-a")
        with self.assertRaises(LeaseConflictError):
            acquire(self.root, "inbox-lease", identity="host", instance_id="instance-b")

    def test_expired_active_run_is_reconciled_without_terminal_fabrication(self) -> None:
        lease = acquire(self.root, "inbox-lease", identity="host", instance_id="instance-a")
        with open_storage(self.root) as connection:
            connection.execute("UPDATE execution_run_leases SET expires_at='2020-01-01T00:00:00+00:00' WHERE lease_id=?", (lease.lease_id,))
        outcome = reconcile_stale(self.root)
        self.assertEqual(outcome[0]["outcome"], "RECOVERABLE")
        with open_storage(self.root) as connection:
            self.assertEqual(connection.execute("SELECT phase FROM engineering_transactions WHERE run_id='inbox-lease'").fetchone()[0], "INITIALIZE")
