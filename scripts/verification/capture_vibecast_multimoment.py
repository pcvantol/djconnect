"""Build a renderer-safe same-track Broadcast sequence from the real Runtime path.

This is a deterministic software simulator using the current Track Insight
field contract. It does not claim a live Spotify observation or physical Pi.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.test_vibecast_multimoment import VibeCastMultiMomentTest


async def capture() -> dict:
    fixture = VibeCastMultiMomentTest("test_same_observed_track_emits_two_different_meaningful_types")
    long_context = (
        "The bass leaves generous space for the melody while a steady pulse "
        "holds the arrangement together. The quieter passages make the next "
        "entrance of the rhythm feel deliberate. Small changes in texture keep "
        "the same groove recognizable without crowding the vocal line. "
        "Listen to how the percussion answers the bass, then how the melody "
        "moves across that space. The recurring pattern gives the track its "
        "shape, and the brief gaps let each return register clearly. Near the "
        "close, the pulse recedes for a moment before the arrangement gathers "
        "again. That small change keeps the same musical idea in view while "
        "giving the listener a new point of attention. The final phrases "
        "bring the bass and melody back into balance without rushing the ending. "
        "The arrangement keeps the same pulse while the vocal line moves "
        "through a narrower space. A short pause leaves the bass exposed, "
        "then the percussion returns in small steps. Those changes make the "
        "middle section feel connected to the opening without repeating its "
        "exact shape. The melody takes one final turn over the steady rhythm."
    )
    timestamp = [datetime(2026, 10, 6, 12, 0, tzinfo=UTC)]
    with patch.object(fixture.runtime, "_timestamp", lambda: timestamp[0].isoformat()):
        manager, session, first, media_id, now = await fixture._ready(content=long_context)
        events: list[dict] = []
        _, before = session.broadcast.subscribe(events.append)
        timestamp[0] += timedelta(seconds=15)
        await fixture._observe(manager, session, media_id, now, seconds=15, position_ms=15_000)
        assert await fixture._later(manager, session, media_id) is None
        timestamp[0] += timedelta(seconds=15)
        await fixture._observe(manager, session, media_id, now, seconds=15, position_ms=30_000)
        second = await fixture._later(manager, session, media_id)
    assert second is not None and second.moment_type is not first.moment_type
    after = session.broadcast.as_dict()
    return {
        "assignment_id": "DJC-CORE-VIBECAST-MULTIMOMENT-TIMELINE-V1-20261006",
        "source": "SessionRuntimeManager -> Planner -> Knowledge -> Moment -> Flow -> Broadcast",
        "simulator": True,
        "before": before,
        "events": events,
        "after": after,
        "moment_receipts": [
            {"moment_id": item.moment_id, "type": item.moment_type.value, "created_at": item.created_at}
            for item in (first, second)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    VibeCastMultiMomentTest.setUpClass()
    try:
        result = asyncio.run(capture())
    finally:
        VibeCastMultiMomentTest.tearDownClass()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Captured {len(result['moment_receipts'])} distinct Moments and {len(result['events'])} Broadcast events")


if __name__ == "__main__":
    main()
