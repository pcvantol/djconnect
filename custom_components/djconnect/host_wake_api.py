"""Private API transport over an already loaded genuine Core installation.

No bootstrap, token lookup/rotation, redirect, retry, payload injection or log.
Closed reply decoding and original child once/admission belong to the owner.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

import aiohttp

from .const import (
    CONF_API_BASE_URL, CONF_DJCONNECT_INSTALL_TOKEN, CONF_HA_INSTALL_ID,
    DEFAULT_API_BASE_URL,
)
from .direct_rich_wire import IDENTIFIER, require
from .host_wake_api_wire import PREFIX, ROUTES, SCOPE_HEADERS
from . import host_wake_target_wire as target
from .host_wake_proxy_attempt import HostWakeAttempt
from .host_wake_proxy_wire import BODY_BYTES, decode_json

def _loaded(entry):
    # Read only the genuine already-captured local entry. runtime.config can
    # resolve provider configuration; that is neither needed nor allowed here.
    config = {**entry.data, **entry.options}
    bearer = config.get(CONF_DJCONNECT_INSTALL_TOKEN)
    install = config.get(CONF_HA_INSTALL_ID)
    origin = config.get(CONF_API_BASE_URL, DEFAULT_API_BASE_URL)
    require(type(bearer) is str and re.fullmatch(r"djci_[A-Za-z0-9_-]{43}", bearer), "rich_unavailable", 503)
    require(type(install) is str and IDENTIFIER.fullmatch(install), "rich_unavailable", 503)
    require(type(origin) is str and origin.isascii() and origin == origin.strip(), "rich_unavailable", 503)
    url = urlsplit(origin)
    require(url.scheme == "https"
        and url.hostname and url.username is None and url.password is None
        and url.path in {"", "/"} and not url.query and not url.fragment
        and not any(char.isspace() for char in origin), "rich_unavailable", 503)
    return origin.rstrip("/"), bearer, install


class HostWakeApiChannel:
    """A single outbound attempt owned by the SAME inbound request lifetime."""

    def __init__(self, attempt):
        require(type(attempt) is HostWakeAttempt, "rich_unavailable", 503)
        attempt.check()
        self.attempt = attempt
        self.runtime = attempt.pair.runtime
        self.entry = attempt.pair.entry
        self.original = None
        self.used = False
        try:
            self.original = _loaded(self.entry)
            attempt.dependents.add(self)
        except BaseException:
            self.close()
            raise

    def close(self):
        """Synchronous negative-only scrub, including never-sent channels."""
        attempt, self.attempt = self.attempt, None
        self.used = True
        self.runtime = self.entry = self.original = None
        if attempt is not None:
            attempt.dependents.discard(self)

    def _current(self):
        require(self.attempt is not None and self.original is not None, "rich_unavailable", 503)
        self.attempt.check()
        require(self.attempt.pair.runtime is self.runtime
            and self.attempt.pair.entry is self.entry
            and _loaded(self.entry) == self.original, "rich_unavailable", 503)

    async def post(self, route, body, scope=None, *, capability=None):
        """Return bounded status/raw bytes, never a generic success authority."""
        try:
            return await self._post_once(route, body, scope, capability)
        finally:
            self.close()  # Includes validation failures before the first await.

    async def _post_once(self, route, body, scope, capability):
        self._current()
        require(type(route) is str and route in ROUTES | target.ROUTES and not self.used)
        require(type(body) is bytes and 0 < len(body) <= BODY_BYTES)
        is_target = route in target.ROUTES
        if is_target:
            sent = target.request(route, decode_json(body))
            correlation = target.request_hash(route, sent)
            require(type(capability) is str and re.fullmatch(r"djchw_[A-Za-z0-9_-]{43}", capability))
        else:
            require(capability is None)
        if route == "authorization/resolve":
            require(scope is None)
        else:
            require(type(scope) is dict and scope.keys() == SCOPE_HEADERS.keys())
            require(all(type(value) is str and IDENTIFIER.fullmatch(value) for value in scope.values()))
        origin, bearer, _install = self.original
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + bearer}
        if scope is not None:
            headers.update({header: scope[key] for key, header in SCOPE_HEADERS.items()})
        if is_target:
            headers[target.CAPABILITY_HEADER] = capability
            if route in {"register", "wake"}:
                headers[target.OPERATION_HEADER] = sent["operation_id"]
        self.used = True  # No lost-response or same-object retry, even before IO.

        async def send():
            self._current()
            async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar(),
                    trust_env=False, auto_decompress=False) as session:
                self._current()
                async with session.post(origin + PREFIX + route, data=body, headers=headers,
                        allow_redirects=False, timeout=aiohttp.ClientTimeout(total=self.attempt.check())) as response:
                    self._current()
                    require(response.status in {200, 400, 401, 403, 404, 409, 413, 415, 503}
                        or (is_target and response.status == 202), "rich_unavailable", 503)
                    if is_target and response.status in {200, 202}:
                        values = response.headers.getall(target.CORRELATION_HEADER, [])
                        require(len(values) == 1 and values[0] == correlation, "rich_unavailable", 503)
                    media = response.headers.getall("Content-Type", [])
                    require(len(media) == 1 and media[0].lower().replace(" ", "")
                        in {"application/json", "application/json;charset=utf-8"}, "rich_unavailable", 503)
                    require("Content-Encoding" not in response.headers, "rich_unavailable", 503)
                    raw = bytearray()
                    try:
                        async for chunk in response.content.iter_chunked(2048):
                            self._current()
                            raw.extend(chunk)
                            require(len(raw) <= BODY_BYTES, "rich_unavailable", 503)
                        self._current()
                        require(bool(raw), "rich_unavailable", 503)
                        return response.status, bytes(raw)
                    finally:
                        raw.clear()

        try:
            return await self.attempt.wait(send)
        finally:
            headers.clear()
