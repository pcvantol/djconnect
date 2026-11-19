"""Official HA frontend and config-flow manager on one owned loopback test port.

Management-user credentials are only for the genuine wizard, never device-auth
proof. All configuration and Assist pipeline metadata are synthetic fixtures.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import logging

from homeassistant import bootstrap, loader
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.components.http.config import async_get_and_load_store
from homeassistant.components.assist_pipeline.pipeline import (
    async_setup_pipeline_store,
    PipelineStore,
    STORAGE_VERSION,
    STORAGE_VERSION_MINOR,
    STORAGE_KEY,
)
from homeassistant.components.onboarding import OnboardingStorage
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from types import MappingProxyType


async def main():
    logging.basicConfig(level=logging.WARNING)
    source = Path(os.environ["DJC_SOURCE_ROOT"])
    sys.path.insert(0, str(source))
    lab = Path(os.environ["DJC_LAB_ROOT"])
    port = int(os.environ.get("DJC_WIZARD_PORT", "18199"))
    bind_host = os.environ.get("DJC_WIZARD_BIND_HOST", "127.0.0.1")
    if bind_host not in {"127.0.0.1", "0.0.0.0"}:
        raise ValueError("Unsupported isolated test binding")
    config = lab / "wizard-full-config"
    config.mkdir(parents=True, exist_ok=True)
    if not (config / "custom_components").exists():
        (config / "custom_components").symlink_to(
            source / "custom_components", target_is_directory=True
        )
    hass = HomeAssistant(str(config))
    loader.async_setup(hass)
    # Dependencies are installed only in the separate target test directory.
    # Never let HA's runtime installer modify the shared read-only SDK venv.
    hass.config.skip_pip = True
    http_store = await async_get_and_load_store(hass)
    await http_store.async_set_pending(
        {**http_store.default, "server_host": [bind_host], "server_port": port}
    )
    if http_store.pending is not None:
        await http_store.async_promote_pending()
    await http_store.async_mark_yaml_migration_done()
    await OnboardingStorage(hass, 4, "onboarding", private=True).async_save(
        {"done": ["user", "core_config", "integration", "analytics"]}
    )
    pipeline = {
        "id": "synthetic-pipeline",
        "name": "Synthetic pipeline metadata",
        "language": "en",
        "conversation_engine": "conversation.home_assistant",
        "conversation_language": "en",
        "stt_engine": "stt.synthetic",
        "stt_language": "en",
        "tts_engine": "tts.synthetic",
        "tts_language": "en",
        "tts_voice": None,
        "wake_word_entity": None,
        "wake_word_id": None,
    }
    await PipelineStore(
        hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR
    ).async_save({"items": [pipeline], "preferred_item": pipeline["id"]})
    initialized = await bootstrap.async_from_config_dict(
        {
            "homeassistant": {
                "name": "Synthetic Windows retirement lab",
                "internal_url": f"http://localhost:{port}",
                "time_zone": "Europe/Amsterdam",
                "country": "NL",
            },
            "frontend": {},
            "logger": {"default": "warning"},
            "system_log": {},
            "recorder": {
                "db_url": "sqlite:///" + str(config / "synthetic-recorder.sqlite3"),
                "auto_purge": False,
            },
        },
        hass,
    )
    if initialized is None:
        raise RuntimeError("Isolated official HA bootstrap failed")
    if hass.config.api.host != bind_host or hass.config.api.port != port:
        await hass.async_stop()
        raise RuntimeError("Isolated HTTP binding differs from reserved loopback target")
    user = await hass.auth.async_create_user(
        "Synthetic wizard owner", group_ids=[GROUP_ID_ADMIN], local_only=True
    )
    refresh = await hass.auth.async_create_refresh_token(
        user, client_id=f"http://localhost:{port}/"
    )
    access = hass.auth.async_create_access_token(refresh)
    # Do not print/store credentials in tracked evidence or device-auth receipts.
    (lab / "wizard-auth.json").write_text(
        json.dumps(
            {
                "access_token": access,
                "refresh_token": refresh.token,
                "expires": 4102444800000,
                "expires_in": 1800,
                "token_type": "Bearer",
                "hassUrl": f"http://localhost:{port}",
                "clientId": f"http://localhost:{port}/",
            }
        )
    )
    (lab / "wizard-auth.json").chmod(0o600)
    integration = await loader.async_get_integration(hass, "djconnect")
    await integration.async_get_platform("config_flow")
    await async_setup_pipeline_store(hass)
    if os.environ.get("DJC_WIZARD_REPAIR_FIXTURES") == "1":
        from custom_components.djconnect import _update_retirement_issue
        from homeassistant.helpers import issue_registry

        # Remove only warnings created by an earlier version of this own lab.
        for old_issue in ("config_entry_only_labs", "country_not_configured"):
            issue_registry.async_delete_issue(hass, "homeassistant", old_issue)

        for identifier, extra in (
            ("synthetic-retired-owner", {"spotify_refresh_token": "synthetic-unusable-grant"}),
            ("synthetic-retired-safe", {}),
        ):
            fixture = ConfigEntry(
                domain="djconnect",
                title="Synthetic retired Windows fixture",
                entry_id=identifier,
                data={
                    "client_type": "windows",
                    "device_id": "djconnect-windows-ABCDEF123456",
                    **extra,
                },
                options={},
                discovery_keys=MappingProxyType({}),
                source="user",
                unique_id=identifier,
                version=1,
                minor_version=1,
                subentries_data=None,
            )
            _update_retirement_issue(hass, fixture)
    await hass.async_start()
    (lab / "wizard-ready.json").write_text(
        json.dumps(
            {
                "url": f"http://localhost:{port}",
                "source": str(source),
                "official_frontend": "20260930.2",
                "device_auth_proof": "SEPARATE",
            }
        )
    )
    print(json.dumps({"ready": True, "url": f"http://localhost:{port}"}), flush=True)
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    try:
        await stop.wait()
    finally:
        await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
