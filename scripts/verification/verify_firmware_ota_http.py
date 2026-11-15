"""Exercise Core's OTA dispatch against synthetic loopback ESP endpoints."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer
from homeassistant.core import HomeAssistant

from custom_components import djconnect
from custom_components.djconnect import DJConnectRuntime
from custom_components.djconnect.github import FirmwareRelease
from verify_session_conversation_history_http import entry


async def main():
    calls = []
    reply_status = 202
    device = "djconnect-lilygo-t-embed-s3-123456ABCDEF"
    pairing_token = "synthetic-ota-pairing"
    release = FirmwareRelease(
        version="3.1.99", title="Synthetic firmware", body=None,
        firmware_url="https://example.invalid/synthetic.bin",
        firmware_asset="synthetic.bin", sha256="a" * 64, device="lilygo-t-embed-s3",
    )
    payload = {
        "version": release.version, "url": release.firmware_url, "sha256": release.sha256,
        "device": release.device, "asset": release.firmware_asset,
    }

    async def primary(request):
        calls.append("primary")
        assert request.headers.get("Authorization") == f"Bearer {pairing_token}"
        assert request.headers.get("X-DJConnect-Device-ID") == device
        assert await request.json() == payload
        return web.Response(status=reply_status, text="synthetic ESP response")

    async def fallback(_request):
        calls.append("fallback")
        return web.Response(status=202)

    def server(handler):
        app = web.Application()
        app.router.add_post("/api/device/ota", handler)
        return TestServer(app)

    lab = Path(os.environ["DJC_LAB_ROOT"])
    with TemporaryDirectory(prefix="ota-", dir=lab) as configuration:
        hass = HomeAssistant(configuration)
        try:
            async with ClientSession() as client, server(primary) as first, server(fallback) as second:
                with patch.object(djconnect, "async_get_clientsession", return_value=client):
                    for status in (202, 409):
                        reply_status = status
                        calls.clear()
                        runtime = DJConnectRuntime(entry("esp", {
                            "client_type": "esp32", "device_id": device, "device_token": pairing_token,
                        }), device_token=pairing_token)
                        runtime.device_status.update(
                            device_id=device, local_url=str(first.make_url("/")),
                            ota_url=str(second.make_url("/")),
                        )
                        if status == 202:
                            await runtime.start_ota(hass, release)
                            assert runtime.ota_in_progress is True
                            assert runtime.ota_last_error is None
                        else:
                            try:
                                await runtime.start_ota(hass, release)
                            except RuntimeError as exc:
                                assert "HTTP 409" in str(exc)
                            else:
                                raise AssertionError("OTA rejection must reach the caller")
                            assert runtime.ota_in_progress is False
                            assert "HTTP 409" in runtime.ota_last_error
                        assert calls == ["primary"]
        finally:
            await hass.async_stop(force=True)
    print(json.dumps({"status": "PASS", "cases": 2, "physical_device": False}))


if __name__ == "__main__":
    asyncio.run(main())
