"""Isolated real HA SDK/loopback proof; synthetic input, no installed/live-provider claim.

Run in the already available HA image with the source mounted readonly, network
none, and an empty temporary configuration/output directory. Never use HA-dev's
configuration, credentials or bindings. Native microphone/render proof is Apple-owned.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import secrets
import sys
from types import MappingProxyType, SimpleNamespace

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.helpers import device_registry, entity_registry, area_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components.http import HomeAssistantHTTP

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))

from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.persistence import (  # noqa: E402
    async_initialize_persistence,
    async_shutdown_persistence,
)  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402


def entry(identifier, data):
    return ConfigEntry(
        domain="djconnect",
        title="Synthetic isolated qualification",
        entry_id=identifier,
        data=data,
        options={},
        discovery_keys=MappingProxyType({}),
        source="user",
        unique_id=identifier,
        version=1,
        minor_version=1,
        subentries_data=None,
    )


def source_hashes():
    files = [
        path
        for path in (ROOT / "custom_components" / "djconnect").rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".js", ".css"}
    ]
    files.extend(
        [
            ROOT / "scripts/verification/verify_session_conversation_history_http.py",
            ROOT / "examples/client_contracts/session_conversation_history/schema.json",
        ]
    )
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
    }


async def main():
    qualified_sources = source_hashes()
    directory = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
    config = directory / ("config-" + secrets.token_hex(4))
    config.mkdir(parents=True, exist_ok=True)
    hass = HomeAssistant(str(config))
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.state = CoreState.running
    hass.config.language = "nl"
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    device_id = "djconnect-ios-ABCDEF123456"
    token = secrets.token_urlsafe(32)
    client_entry = entry(
        "owner-entry",
        {
            "device_id": device_id,
            "client_type": "ios",
            "music_backend": "later_manual",
            "profile_id": "profile-a",
        },
    )
    source_entry = entry(
        "source-entry",
        {
            "music_account_id": "source-account",
            "spotify_refresh_token": "synthetic-source-grant-never-sent",
        },
    )
    # Source/account registration is synthetic fixture metadata; no provider setup/OAuth.
    hass.config_entries = SimpleNamespace(
        async_entries=lambda domain: [client_entry, source_entry],
        async_update_entry=lambda *args, **kwargs: None,
    )
    runtime = DJConnectRuntime(client_entry, device_token=token)
    runtime.device_status.update(device_id=device_id, client_type="ios")
    history = AskDJHistoryManager(hass)
    runtime.ask_dj_history = history
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"] = {
        "owner-entry": runtime,
        "runtime": runtime,
        "djconnect_profile_platform": storage,
        "ask_dj_history_manager": history,
    }
    await storage.async_upsert_music_backend(
        "later_manual", BackendProvider.FUTURE_PROVIDER, display_name="Synthetic manual"
    )
    await storage.async_create_profile(
        "Owner", profile_id="profile-a", default_backend_id="later_manual"
    )
    await storage.async_create_profile(
        "Other", profile_id="profile-other", default_backend_id="later_manual"
    )
    await storage.async_upsert_device(
        device_id, "ios", display_name="Synthetic iPhone", linked_profile_id="profile-a"
    )
    await storage.async_upsert_music_backend(
        "source-spotify", BackendProvider.SPOTIFY_DIRECT, display_name="Synthetic source"
    )
    await storage.async_upsert_music_account(
        "source-account",
        "source-spotify",
        kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic account",
        linked_profile_ids=frozenset({"profile-a"}),
    )
    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service), HistoricalProjectionRepository(service)
    )
    hass.data["djconnect"]["session_runtime_manager"] = manager
    register_http_views(hass)
    identity = {"device_id": device_id, "client_type": "ios"}
    headers = {"Authorization": "Bearer " + token, "X-DJConnect-Device-ID": device_id}
    receipts = []
    async with TestClient(TestServer(hass.http.app)) as client:

        async def request(method, path, data=None, authorized=True):
            kwargs = {"headers": headers if authorized else {}}
            if method == "GET":
                kwargs["params"] = {**identity, **(data or {})}
            else:
                kwargs["json"] = {**identity, **(data or {})}
            response = await client.request(method, path, **kwargs)
            body = await response.json()
            if "session/history" in path or "ask_dj" in path:
                assert response.headers.get("Cache-Control") == "no-store"
            receipts.append(
                {
                    "method": method,
                    "path": path,
                    "query": dict(kwargs.get("params", {})) if method == "GET" else None,
                    "status": response.status,
                    "cache_control": response.headers.get("Cache-Control"),
                    "body": body,
                }
            )
            return body, response.status

        caps, status = await request("GET", "/api/djconnect/v1/capabilities")
        assert status == 200 and caps["capabilities"]["session_flow_text_search"]
        _, status = await request("GET", "/api/djconnect/v1/session/history", authorized=False)
        assert status == 401
        session = await manager.async_start(
            owner_profile_id="profile-a",
            selected_mood="energy",
            locale="nl",
            history_source_context={
                "backend_id": "source-spotify",
                "music_account_id": "source-account",
                "provider_entry_id": "source-entry",
            },
        )
        await manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity="spotify:track:0123456789abcdefghijkL",
            title="One",
            artist="Metallica",
            album="…And Justice for All",
            duration_ms=120000,
            position_ms=1000,
        )

        async def insight():
            return {}

        moment = await manager.async_process_track_started(
            owner_profile_id="profile-a", session_id=session.session_id, insight_provider=insight
        )
        assert moment is not None
        timeline_path = "/api/djconnect/v1/session/history/" + session.session_id
        timeline, status = await request("GET", timeline_path, {"window": "tail"})
        assert status == 200
        assert any(e["kind"] == "dj_moment" for e in timeline["entries"]), {
            "moment": moment.as_dict(),
            "timeline": timeline,
        }
        selected = next(e for e in timeline["entries"] if e["kind"] == "dj_moment")
        result, status = await request(
            "POST",
            "/api/djconnect/v1/ask_dj/message",
            {
                "client_message_id": "loopback-text",
                "text": "Vertel over deze bijdrage",
                "language": "nl",
                "conversation_context": {
                    "session_id": session.session_id,
                    "selected_entry": {
                        "session_id": session.session_id,
                        "entry_id": selected["entry_id"],
                    },
                },
            },
        )
        assert status == 200 and result["conversation"]["input_type"] == "text"
        history_path = "/api/djconnect/v1/ask_dj/history"
        scoped, status = await request("GET", history_path, {"conversation_scope": "profile"})
        assert status == 200 and scoped.get("owner_profile_id") == "profile-a", scoped
        assert scoped["user_id"] is None and scoped["history_scope"] == "profile"
        assert [m["id"] for m in scoped["messages"]] == [m["id"] for m in result["messages"]]
        unchanged, status = await request("GET", history_path, {
            "conversation_scope": "profile", "since_revision": scoped["history_revision"],
        })
        assert status == 200 and unchanged["messages"] == []
        for negative in ({"profile_id": "profile-other"}, {"privacy_mode": "shared"}):
            denied, status = await request("GET", history_path, {
                "conversation_scope": "profile", **negative,
            })
            assert status == 403 and "messages" not in denied, denied
        denied, status = await request("GET", history_path, {
            "conversation_scope": "profile", "client_type": "macos",
        })
        assert status == 401 and "messages" not in denied, denied
        denied, status = await request("GET", history_path, {"conversation_scope": "profile"}, authorized=False)
        assert status == 401 and "messages" not in denied
        safe, status = await request("GET", history_path, {
            "conversation_scope": "profile", "owner_profile_id": "forged", "user_id": "forged",
        })
        assert status == 200 and safe["owner_profile_id"] == "profile-a" and safe["user_id"] is None
        legacy, status = await request("GET", history_path)
        assert status == 200 and legacy["user_id"] == "anonymous" and not legacy.get("owner_profile_id")
        assert legacy["messages"] == []
        from unittest.mock import patch
        from custom_components.djconnect import http as producer_http

        async def fixture_stt(hass, wav, config):
            # Declared STT adapter fixture; never native-microphone evidence.
            return "Vertel over deze bijdrage"

        voice_headers = {
            **headers,
            "Content-Type": "audio/wav",
            "X-DJConnect-Client-Type": "ios",
            "X-DJConnect-Conversation-Scope": "profile",
            "X-DJConnect-Client-Message-ID": "loopback-voice",
            "X-DJConnect-Session-ID": session.session_id,
            "X-DJConnect-Entry-ID": selected["entry_id"],
            "X-DJConnect-Reference-Session-ID": session.session_id,
            "X-DJConnect-Language": "nl",
        }
        with patch.object(producer_http, "transcribe_wav_with_assist", fixture_stt):
            response = await client.post(
                "/api/djconnect/v1/voice", data=b"synthetic-audio-fixture", headers=voice_headers
            )
            result = await response.json()
        assert response.status == 200, result
        assert response.headers["Cache-Control"] == "no-store"
        assert result["conversation"]["input_type"] == "voice"
        receipts.append(
            {
                "method": "POST",
                "path": "/api/djconnect/v1/voice",
                "status": response.status,
                "cache_control": response.headers.get("Cache-Control"),
                "body": result,
                "input_qualification": "declared synthetic STT adapter completion, no microphone",
            }
        )
        assert "Vertel over deze bijdrage" not in json.dumps(session.broadcast.as_dict())
        await manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        await service.async_close()
        await service.async_initialize()
        hass.data["djconnect"].pop("session_history_query", None)
        history = AskDJHistoryManager(hass)
        runtime.ask_dj_history = history
        hass.data["djconnect"]["ask_dj_history_manager"] = history
        saved, status = await request("GET", timeline_path)
        assert status == 200 and len(saved["entries"]) == 6 and saved["session"]["read_only"]
        later, status = await request(
            "POST",
            "/api/djconnect/v1/ask_dj/message",
            {
                "client_message_id": "loopback-later",
                "text": "Wanneer heb ik eerder naar Metallica geluisterd?",
                "language": "nl",
                "conversation_context": {"session_id": None},
            },
        )
        assert status == 200 and len(later["historical_matches"]) == 1
        opened, status = await request(
            "POST",
            "/api/djconnect/v1/session/history/open",
            {"action": later["navigation_actions"][0]},
        )
        assert status == 200 and opened["read_only"]
        search, status = await request("GET", timeline_path + "/search", {"q": "METALLICA"})
        assert status == 200 and search["matches"]
        _, status = await request("GET", timeline_path, {"profile_id": "profile-other"})
        assert status == 403
        _, status = await request("GET", timeline_path, {"privacy_mode": "shared"})
        assert status == 403
        restored, status = await request("GET", history_path, {"conversation_scope": "profile"})
        assert status == 200 and restored["owner_profile_id"] == "profile-a" and len(restored["messages"]) == 6
        entered, release = asyncio.Event(), asyncio.Event()
        original_history = history.async_history

        async def delayed_history(*args, **kwargs):
            result = await original_history(*args, **kwargs)
            entered.set()
            await release.wait()
            return result

        with patch.object(history, "async_history", delayed_history):
            pending_read = asyncio.create_task(request("GET", history_path, {"conversation_scope": "profile"}))
            await asyncio.wait_for(entered.wait(), timeout=10)
            try:
                cleared, status = await request("POST", history_path + "/clear", {"conversation_scope": "profile"})
                assert status == 200 and cleared["owner_profile_id"] == "profile-a"
            finally:
                release.set()
            raced, status = await pending_read
            assert status == 409 and "messages" not in raced, raced
        after_clear, status = await request("GET", history_path, {"conversation_scope": "profile"})
        assert status == 200 and after_clear["messages"] == []
        assert after_clear["clear_revision"] > restored["clear_revision"]
        withdrawn, status = await request("GET", timeline_path)
        assert status == 200 and all(not e["kind"].startswith("conversation_") for e in withdrawn["entries"])
    await async_shutdown_persistence(hass)
    assert source_hashes() == qualified_sources, "source changed during qualification"
    from homeassistant.const import __version__ as sdk_version

    result = {
        "source_files_sha256": qualified_sources,
        "ha_sdk_version": sdk_version,
        "assignment_id": "DJC-CORE-PROFILE-HISTORY-HTTP-SCOPE-FIX-V1-20261009",
        "qualification": "real HA SDK, DJConnectRuntime paired authorization, HA HTTP view registration, loopback HTTP, SQLite and HA Store reload; synthetic source account/metadata and voice-derived text, no microphone/native/provider/installed proof",
        "server_time": datetime.now(UTC).isoformat(),
        "requests": receipts,
    }
    output = directory / "http-producer-receipt.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps({"result": "PASS", "requests": len(receipts), "receipt": str(output)}))


if __name__ == "__main__":
    asyncio.run(main())
