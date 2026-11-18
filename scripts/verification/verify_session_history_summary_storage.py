"""Bounded real-SQLite acceptance/resource benchmark; not a runtime duration PASS."""

from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import sys
import time
import tempfile

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import (  # noqa: E402
    PersistentSessionRepository,
    ACTIVE,
    ENDED,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.historical_projection_query import HistoricalProjectionQueryService  # noqa: E402


async def main():
    with tempfile.TemporaryDirectory(prefix="djc-summary-storage-") as directory:
        path = Path(directory) / "summary.sqlite"
        provider = SQLitePersistenceProvider()
        service = PersistenceService(path, provider)
        await service.async_initialize()
        sessions, history = (
            PersistentSessionRepository(service),
            HistoricalProjectionRepository(service),
        )
        session = await sessions.async_create("owner", initial_mood="groove")
        await sessions.async_transition("owner", session.session_id, ACTIVE)
        started = time.perf_counter()
        for number in range(8192):
            await history.async_accept_moment(
                "owner", session.session_id, "moment-benchmark-" + str(number)
            )
        acceptance_seconds = time.perf_counter() - started
        assert not await history.async_accept_moment(
            "owner", session.session_id, "moment-benchmark-0"
        )
        try:
            await history.async_accept_moment("owner", session.session_id, "capacity-exceeded")
        except ValueError as exc:
            assert str(exc) == "session_summary_capacity"
        else:
            raise AssertionError("unbounded summary keys")
        await sessions.async_transition(
            "owner", session.session_id, ENDED, historical_projections=history
        )
        for number in range(99):
            short = await sessions.async_create("owner", initial_mood="groove")
            await sessions.async_transition("owner", short.session_id, ACTIVE)
            await sessions.async_transition(
                "owner", short.session_id, ENDED, historical_projections=history
            )
        statements = []
        provider._connection.set_trace_callback(statements.append)
        query = HistoricalProjectionQueryService(history)
        started = time.perf_counter()
        page = await query.async_session_page("owner", limit=20)
        query_seconds = time.perf_counter() - started
        queries = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
        assert len(page["sessions"]) == 20
        assert len(queries) == 4, queries
        assert not any("djconnect_session_entries" in q for q in queries)
        provider._connection.set_trace_callback(None)
        keys = provider._connection.execute(
            "SELECT COUNT(*) FROM djconnect_session_acceptances"
        ).fetchone()[0]
        neutral_bytes = provider._connection.execute(
            "SELECT SUM(LENGTH(session_id)+LENGTH(kind)+LENGTH(reference_id)+LENGTH(entry_id)) FROM djconnect_session_acceptances"
        ).fetchone()[0]
        assert keys == 8192
        row = await history.async_session_record(session.session_id)
        assert row["summary"]["moments_published"]["value"] == 8192
        await service.async_close()
        result = {
            "mode": "real_sqlite_storage_benchmark_not_elapsed_runtime",
            "accepted_keys": keys,
            "max_keys_per_session": 8192,
            "compact_identity_bytes": neutral_bytes,
            "database_bytes": path.stat().st_size,
            "acceptance_seconds": acceptance_seconds,
            "sessions": 100,
            "page_size": 20,
            "page_selects": len(queries),
            "timeline_selects": 0,
            "page_seconds": query_seconds,
            "reads_mutate_events": False,
        }
        output = Path(
            os.environ.get(
                "DJC_STORAGE_RECEIPT",
                str(
                    ROOT
                    / "artifacts/recovery/djc-core-session-history-summary-v1/storage-benchmark.json"
                ),
            )
        )
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
