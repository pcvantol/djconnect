"""Offline real OpenAI SDK/HTTPX transport qualification; no credentials/network.

Run in the pinned HA image with --network none. All HTTP replies are explicit
transport fixtures. No native app, source admission or paid-model PASS results.
"""
from datetime import UTC, datetime, timedelta
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import httpx  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from tests.test_native_golden_attempts import admission, turn  # noqa: E402
from tools.verification.native_golden_attempts import AttemptJournal, wrap_responses_transport  # noqa: E402


def event():
    return ("data: " + json.dumps({"type": "response.completed", "sequence_number": 1,
        "response": {"id": "fixture-provider-response", "object": "response", "created_at": 1,
                     "status": "completed", "model": "fixture-model", "output": [],
                     "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}}})
            + "\n\n").encode()


class SDKTransportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / "attempts.json"

    async def consume(self, client):
        stream = await client.responses.create(model="fixture-model", input="PUBLIC_MUSIC_FIXTURE_SENTINEL", stream=True)
        try:
            return [e.type async for e in stream]
        finally:
            await stream.close()

    async def test_sdk_retry_reserves_each_actual_transport_and_retains_failure(self):
        journal = AttemptJournal.create(self.path, admission())
        network = []
        async def reply(request):
            # Reservation must be durable before the transport callback runs.
            network.append(len(json.loads(self.path.read_text())["attempts"]))
            if len(network) == 1:
                return httpx.Response(503, json={"error": {"message": "offline fixture"}}, headers={"retry-after-ms": "1"})
            return httpx.Response(200, stream=httpx.ByteStream(event()), headers={"content-type": "text/event-stream"})
        async with AsyncOpenAI(api_key="fixture-not-a-live-key", http_client=httpx.AsyncClient(
                transport=wrap_responses_transport(httpx.MockTransport(reply), journal))) as client:
            self.assertEqual(client.max_retries, 2)
            with turn(journal):
                events = await self.consume(client)
        self.assertEqual(network, [1, 2])
        self.assertEqual(events, ["response.completed"])
        report = journal.export()
        self.assertEqual([a["completed"] for a in report["provider_attempts"]], [False, True])
        self.assertEqual(report["provider_attempts"][1]["output_tokens"], 2)
        self.assertEqual(report["export_status"], "OBSERVED_NOT_QUALIFIED")
        for private in ("PUBLIC_MUSIC_FIXTURE_SENTINEL", "fixture-not-a-live-key", "fixture-provider-response"):
            self.assertNotIn(private, self.path.read_text())

    async def test_two_attempt_guard_stops_sdk_third_retry_before_transport(self):
        calls = []
        async def failure(request):
            calls.append(1)
            return httpx.Response(503, json={"error": {"message": "offline fixture"}}, headers={"retry-after-ms": "1"})
        # Same actual SDK defaults would issue three HTTP attempts without guard.
        async with AsyncOpenAI(api_key="fixture-not-a-live-key", http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(failure))) as unguarded:
            with self.assertRaises(Exception):
                await self.consume(unguarded)
        self.assertEqual(len(calls), 3)
        calls.clear()
        journal = AttemptJournal.create(self.path, admission())
        async with AsyncOpenAI(api_key="fixture-not-a-live-key", http_client=httpx.AsyncClient(
                transport=wrap_responses_transport(httpx.MockTransport(failure), journal))) as guarded:
            with turn(journal), self.assertRaises(Exception):
                await self.consume(guarded)
        self.assertEqual(len(calls), 2)
        self.assertEqual(journal.export()["observed_total_provider_attempts"], 2)
        self.assertFalse(any(a["completed"] for a in journal.export()["provider_attempts"]))

    async def test_nonadmitted_call_never_reaches_transport(self):
        calls = []
        async def reply(request):
            calls.append(1)
            raise AssertionError("unadmitted call reached transport")
        journal = AttemptJournal.create(self.path, admission())
        async with httpx.AsyncClient(transport=wrap_responses_transport(httpx.MockTransport(reply), journal)) as client:
            with self.assertRaises(ValueError):
                await client.post("https://api.openai.com/v1/responses", json={"model": "fixture-model", "stream": True})
            with turn(journal):
                for url, body in [("https://api.openai.com/v1/other", {"model": "fixture-model", "stream": True}),
                                  ("https://api.openai.com/v1/responses", {"model": "fixture-model", "stream": False}),
                                  ("https://user:pass@api.openai.com/v1/responses", {"model": "fixture-model", "stream": True})]:
                    with self.assertRaises(ValueError):
                        await client.post(url, json=body)
        self.assertEqual(calls, [])
        self.assertEqual(journal.export()["observed_total_provider_attempts"], 0)

    async def test_window_timeout_closes_stream_and_counts_uncertain_attempt(self):
        settings = admission()
        settings["expires_at"] = (datetime.now(UTC)+timedelta(seconds=.2)).isoformat()
        journal = AttemptJournal.create(self.path, settings)
        class NeverCompletes(httpx.AsyncByteStream):
            closed = False
            async def __aiter__(self):
                yield b'event: response.created\ndata: {"type":"response.created","sequence_number":0,"response":{"id":"fixture"}}\n\n'
                # Move UTC backwards inside the admission window. The original
                # monotone timeout must still expire and close this stream.
                rollback = datetime.fromisoformat(settings["starts_at"]).timestamp() + .5
                with patch("tools.verification.native_golden_attempts.time.time", return_value=rollback):
                    await asyncio.sleep(5)
            async def aclose(self):
                self.closed = True
        original = NeverCompletes()
        async def reply(request):
            return httpx.Response(200, stream=original, headers={"content-type": "text/event-stream"})
        async with AsyncOpenAI(api_key="fixture-not-a-live-key", http_client=httpx.AsyncClient(
                transport=wrap_responses_transport(httpx.MockTransport(reply), journal))) as client:
            with turn(journal), self.assertRaises(TimeoutError):
                await self.consume(client)
        self.assertTrue(original.closed)
        attempts = journal.export()["provider_attempts"]
        self.assertEqual(len(attempts), 1)
        self.assertFalse(attempts[0]["completed"])


if __name__ == "__main__":
    unittest.main()
