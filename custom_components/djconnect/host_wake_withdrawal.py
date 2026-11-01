"""Original installation custody attenuated to one issuer withdrawal only.

No positive pair, Session, purpose capability or native authority is retained.
The original owning child must capture this before any issuer effect. A failed
withdrawal never reopens local custody or refunds consumed SQL/RAM state.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from fractions import Fraction
import time
import weakref

import aiohttp

from .direct_rich_wire import canonical, digest, require
from .host_wake_api import _loaded
from . import host_wake_api_wire as wire
from .host_wake_proxy_wire import BODY_BYTES, decode_json

if "_ports" not in globals():
    _ports = weakref.WeakSet()


def invalidate_entry(entry):
    """Actual entry unload fences original installation custody before await."""
    for port in tuple(_ports):
        if port.entry is entry:
            port.close()


def close_service(service):
    for port in tuple(_ports):
        if port.service is not None and port.service() is service:
            port.close()


class _IssuerWithdrawal:
    """Private exact-child capture, never a caller-supplied scope constructor."""

    def __init__(self, child):
        from .host_wake_child_runtime import _Child

        self.closed = self.used = False
        self.task = self.started = None
        self.hass = self.domain = self.entry = self.data = self.options = None
        self.service = self.runtime = self.installation = None
        self.sent = self.original = self.proof_kind = None
        require(type(child) is _Child, "rich_unavailable", 503)
        child._continue_prepare()
        try:
            claim, request, metadata = child._issuer_claim, child._issuer_request, child.metadata
            require(claim is not None and request is not None and metadata.phase == "issuing"
                and claim.pending_phase == "issuing" and claim.kind == "issuer_issue"
                and claim.pending_revision == metadata.cas_revision and claim.ordinal == metadata.consumed_attempts
                and claim.attempt_id == request["issuer_operation_id"]
                and claim.request_hash == wire.request_hash("issuer/issue", request)
                and digest(request["original"]) == metadata.original_hash
                and digest(child._original) == metadata.original_hash
                and child._resolved_role is not None
                and digest(child._role) == digest(child._resolved_role) == metadata.role_hash
                and request["authorization_id"] == child._resolved_role["authorization_id"]
                and request["core_purpose_id"] == child.reservation.parent.purpose_id,
                "rich_unavailable", 503)
            pair, service = child.initial_attempt.pair, child.registry.service
            self.hass, self.domain, self.entry = pair.hass, pair.domain, pair.entry
            self.data, self.options = self.entry.data, self.entry.options
            self.service, self.runtime = weakref.ref(service), weakref.ref(pair.runtime)
            self.installation = _loaded(self.entry)
            self.sent = {"version": wire.VERSION, **{key: request[key] for key in wire.SCOPE_HEADERS}}
            wire.request("issuer/withdraw", self.sent)
            self.original, self.proof_kind = deepcopy(child._original), child._resolved_role["native_proof_kind"]
            self._current()
            _ports.add(self)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.closed:
            return
        self.closed = self.used = True
        _ports.discard(self)
        task, self.task = self.task, None
        self.hass = self.domain = self.entry = self.data = self.options = None
        self.service = self.runtime = self.installation = None
        self.sent = self.original = self.proof_kind = self.started = None
        if task is not None and not task.done() and task is not asyncio.current_task():
            task.cancel()

    def _current(self):
        require(not self.closed and self.service is not None, "rich_unavailable", 503)
        service, runtime = self.service(), self.runtime()
        require(service is not None and runtime is not None and not service.closed
            and not self.hass.is_stopping and self.hass.data.get("djconnect") is self.domain
            and self.domain.get("direct_rich_service") is service
            and self.domain.get(self.entry.entry_id) is runtime
            and self.entry.data is self.data and self.entry.options is self.options
            and _loaded(self.entry) == self.installation, "rich_unavailable", 503)

    def _remaining(self):
        self._current()
        wall, mono = self.started
        elapsed_wall, elapsed_mono = Fraction(time.time()) - wall, Fraction(time.monotonic()) - mono
        require(0 <= elapsed_wall < 30 and 0 <= elapsed_mono < 30, "rich_unavailable", 503)
        return float(min(30 - elapsed_wall, 30 - elapsed_mono))

    def schedule(self):
        """Consume and anchor BEFORE scheduling; not a renewed native lease."""
        # A second caller cannot close/cancel the first original attempt.
        require(not self.used, "rich_purpose_consumed", 409)
        try:
            self._current()
            self.used = True
            self.started = Fraction(time.time()), Fraction(time.monotonic())
            self.task = asyncio.create_task(self._run())
            self.task.add_done_callback(lambda _: self.close())  # Also never-started cancellation.
            return self.task
        except BaseException:
            self.close()
            raise

    async def _run(self):
        headers, raw = {}, bytearray()
        try:
            require(self.task is asyncio.current_task(), "rich_unavailable", 503)
            async with asyncio.timeout(self._remaining()):
                origin, bearer, _install = self.installation
                headers.update({"Content-Type": "application/json", "Authorization": "Bearer " + bearer,
                    **{header: self.sent[key] for key, header in wire.SCOPE_HEADERS.items()}})
                body = canonical(self.sent)
                async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar(), trust_env=False,
                        auto_decompress=False) as session:
                    self._remaining()
                    async with session.post(origin + wire.PREFIX + "issuer/withdraw", data=body, headers=headers,
                            allow_redirects=False, timeout=aiohttp.ClientTimeout(total=self._remaining())) as response:
                        self._remaining()
                        require(response.status in {200, 400, 401, 403, 404, 409, 413, 415, 503},
                            "rich_unavailable", 503)
                        media = response.headers.getall("Content-Type", [])
                        require(len(media) == 1 and media[0].lower().replace(" ", "") in
                            {"application/json", "application/json;charset=utf-8"}
                            and "Content-Encoding" not in response.headers, "rich_unavailable", 503)
                        async for chunk in response.content.iter_chunked(2048):
                            self._remaining()
                            raw.extend(chunk)
                            require(len(raw) <= BODY_BYTES, "rich_unavailable", 503)
                        self._remaining()
                        value = decode_json(bytes(raw))
                        if response.status == 200:
                            wire.reply("issuer/withdraw", value, self.sent, self.original, self.proof_kind)
                        else:
                            wire.error(response.status, value)
                        return response.status, value  # Strict negative DATA, never positive authority.
        finally:
            headers.clear()
            raw.clear()
            self.close()
