"""Record synthetic wire bytes through the actual paired application and image owner.

Provider/CDN I/O is synthetic. No live credentials, HA config or model calls.
Run from the repository with its development Python environment.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]


async def build():
    from tests.test_captured_reply_artwork import CapturedReplyArtworkTests

    cls = CapturedReplyArtworkTests
    cls.setUpClass()
    case = cls()
    try:
        await case.asyncSetUp()
        app = case.app
        page, status = await app.f.handlers.async_handle_session_history_payload(
            case.hass,
            {
                **app.identity,
                "session_id": app.reference["session_id"],
                "history_contract_version": 2,
                "historical_playback_contract_version": 1,
            },
            operation="timeline",
            headers=app.headers,
        )
        assert status == 200
        entry = next(e for e in page["entries"] if e["entry_id"] == app.reference["entry_id"])
        offered, status = await app.call()
        assert status == 200 and offered["success"]
        assert app.effects == [("play", "spotify:track:" + "A" * 22)]
        reply, row = await case.accepted_reply()
        fetch = AsyncMock(
            return_value=(
                b"fixture-pixels",
                "image/png",
                "https://open.spotify.com/track/" + "A" * 22,
                case.media["album_uri"],
                1,
                1,
                "Synthetic recording",
            )
        )
        with patch.object(case.art, "_fetch", fetch):
            media = await case.art.prepare(
                case.hass,
                app.runtime,
                SimpleNamespace(profile_id="profile-a"),
                session_id=app.current.session_id,
                target={"entry_id": row["entry_id"]},
            )
        assert media["artwork"]["state"] == "ready"
        assert "reply_media_reference" not in json.dumps(reply)
        paths = [
            "historical_playback.py",
            "reply_artwork.py",
            "session_artwork.py",
            "ask_dj/dialogue.py",
            "ask_dj/service.py",
            "ask_dj/__init__.py",
            "api_handlers.py",
        ]
        return {
            "qualification": "ACTUAL_PAIRED_APPLICATION_SQLITE_AND_RAM_IMAGE_OWNER_SYNTHETIC_PROVIDER_IO",
            "historical_entry": entry,
            "command_value": app.reference,
            "observed_effects": app.effects,
            "captured_reply_media": media,
            "source_pins": {
                p: hashlib.sha256(
                    (ROOT / "custom_components/djconnect" / p).read_bytes()
                ).hexdigest()
                for p in paths
            },
            "paid_attempts": 0,
            "installed": "NOT_RUN",
            "native": "NOT_RUN",
            "audible": "NOT_RUN",
            "note": "Generated synthetic identifiers and recorded media lease are decoding examples, never executable grants.",
        }
    finally:
        if hasattr(case, "app"):
            await case.asyncTearDown()
        cls.tearDownClass()


if __name__ == "__main__":
    result = asyncio.run(build())
    destination = (
        ROOT / "examples/client_contracts/history_playback_reply_artwork_v1/producer-wire.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(destination.relative_to(ROOT))
