"""Dedicated single-attempt issuer HTTPS; no installation bearer or bootstrap.

The original owner and lifecycle supply admission and immutable deadlines.
This transport neither enrolls nor discovers a key, origin or operator secret.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import json
import re
import time

from .surface_issuer_owner import DNS_HOST, IssuerOwnerCapture
from .surface_issuer_wire import PREFIX, signing_bytes
from .surface_push_contract import SurfacePushError, require
from .surface_push_wire import canonical


@dataclass(frozen=True, repr=False)
class IssuerHTTPReply:
    status: int
    body: dict = field(repr=False)


class IssuerTransport(ABC):
    @abstractmethod
    async def post_once(self, capture, action, envelope, *, guard, deadline):
        """One exact-origin request; guard before/after every suspending step."""
        raise NotImplementedError


def strict_body(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'surface_issuer_response_invalid', 502)
            result[key] = value
        return result
    def constant(_):
        raise SurfacePushError('surface_issuer_response_invalid', 502)
    require(type(raw) is bytes and len(raw) <= 8192,
        'surface_issuer_response_invalid', 502)
    try:
        body = json.loads(raw.decode('utf-8', errors='strict'),
            object_pairs_hook=pairs, parse_constant=constant)
        require(type(body) is dict, 'surface_issuer_response_invalid', 502)
        canonical(body)
        return body
    except (ValueError, UnicodeError, RecursionError):
        raise SurfacePushError('surface_issuer_response_invalid', 502) from None


_FIRST_KEY_PREFIX = "/v1/push/native/key/"
_FIRST_KEY_REGISTER = _FIRST_KEY_PREFIX + "register"
_DEFAULT_REQUEST_LIMIT = 16_384
_FIRST_KEY_REGISTER_LIMIT = 32_768


class IssuerHTTPS(IssuerTransport):
    """A fresh no-cookie, no-proxy, no-auth session for each original attempt."""
    def __init__(self, *, monotonic=time.monotonic):
        self.monotonic = monotonic

    async def post_once(self, capture, action, envelope, *, guard, deadline):
        require(type(capture) is IssuerOwnerCapture,
            'surface_issuer_owner_capture_invalid', 503)
        capture.comparisons()
        path = PREFIX + action
        require(type(envelope) is dict and set(envelope) == {'payload', 'signature'},
            'surface_issuer_wire_invalid')
        signing_bytes(path, envelope['payload'])
        return await self._post(capture.origin, path, envelope, {},
            guard=guard, deadline=deadline)

    async def _post(self, origin, path, body, auth_headers, *, guard, deadline):
        import aiohttp  # Supplied by HA; pure journal/owner users need no SDK.

        encoded = canonical(body).encode('utf-8')
        limit = {_FIRST_KEY_REGISTER: _FIRST_KEY_REGISTER_LIMIT,
                 _FIRST_KEY_PREFIX + "retire": 4096,
                 "/v1/install/bootstrap-proof": 4096}.get(path, _DEFAULT_REQUEST_LIMIT)
        if path.startswith("/v1/internal/widget-core/"):
            limit = 4096
        require(len(encoded) <= limit, 'surface_issuer_request_too_large',
            413 if path.startswith(_FIRST_KEY_PREFIX) else 400)
        guard()
        remaining = min(10.0, deadline - self.monotonic())
        require(0 < remaining <= 10, 'surface_issuer_reply_expired')
        try:
            async with asyncio.timeout(remaining):
                # A per-attempt session has no persistent connection to retry,
                # ambient bearer/default-auth, cookie jar or environment proxy.
                async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar(),
                        trust_env=False, auth=None, raise_for_status=False,
                        auto_decompress=False, read_bufsize=8192,
                        timeout=aiohttp.ClientTimeout(total=remaining)) as session:
                    guard()
                    async with session.post(origin + path, data=encoded,
                            headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                'Accept-Encoding': 'identity', **auth_headers},
                            allow_redirects=False, proxy=None, auth=None) as response:
                        guard()
                        require(type(response.status) is int and response.status in (200, 202),
                            'surface_issuer_outcome_unknown', 502)
                        encodings = response.headers.getall('Content-Encoding', [])
                        media = response.headers.getall('Content-Type', [])
                        require((not encodings or (len(encodings) == 1
                                and encodings[0].strip().lower() == 'identity'))
                            and len(media) == 1 and re.fullmatch(
                                r'application/json(?:\s*;\s*charset=(?:utf-8|"utf-8"))?',
                                media[0].strip().lower()) is not None,
                            'surface_issuer_response_invalid', 502)
                        raw = bytearray()
                        while True:
                            guard()
                            chunk = await response.content.read(min(2048, 8193 - len(raw)))
                            guard()
                            if not chunk:
                                break
                            raw.extend(chunk)
                            require(len(raw) <= 8192, 'surface_issuer_response_invalid', 502)
                        body = strict_body(bytes(raw))
                        guard()
                        return IssuerHTTPReply(response.status, body)
        except asyncio.CancelledError:
            raise
        except SurfacePushError:
            raise
        except Exception:
            # Upstream content, signatures, nonces and URLs never escape as errors.
            raise SurfacePushError('surface_issuer_outcome_unknown', 502) from None


class FirstKeyHTTPS(IssuerHTTPS):
    """Send first-key requests using the credential captured by the pairing owner."""

    def __init__(self, origin, *, machine_headers=None, monotonic=time.monotonic):
        super().__init__(monotonic=monotonic)
        require(type(origin) is str and origin.startswith("https://")
            and DNS_HOST.fullmatch(origin.removeprefix("https://")) is not None,
            "surface_first_key_origin_invalid", 503)
        self._origin = origin
        self._machine_headers = machine_headers

    @property
    def origin(self):
        return self._origin

    def _headers(self):
        require(self._machine_headers is not None, "native_machine_authority_unavailable", 503)
        headers = self._machine_headers(self._origin)
        require(type(headers) is dict and set(headers) == {"CF-Access-Client-Id", "CF-Access-Client-Secret"}
                and all(type(value) is str and re.fullmatch(r"[!-~]{1,256}", value) for value in headers.values()),
                "native_machine_authority_unavailable", 503)
        return dict(headers)

    async def post_bootstrap_proof(self, body, *, guard, deadline):
        guard()
        return await self._post(self._origin, "/v1/install/bootstrap-proof", body, self._headers(),
                                guard=guard, deadline=deadline)

    async def post_install_token(self, body, *, guard, deadline):
        guard()
        return await self._post(self._origin, "/v1/install/token", body, self._headers(),
                                guard=guard, deadline=deadline)

    async def post_retirement(self, body, *, guard, deadline):
        guard()
        return await self._post(self._origin, _FIRST_KEY_PREFIX + "retire", body, self._headers(),
                                guard=guard, deadline=deadline)

    async def post_first_key(self, action, body, install_token, *, currentness, guard, deadline):
        require(type(action) is str and action in {"challenge", "register", "status/challenge", "status"},
            "surface_first_key_operation_invalid")
        require(type(install_token) is str and re.fullmatch(r"djci_[A-Za-z0-9_-]{1,256}", install_token),
            "surface_first_key_install_auth_required", 401)
        require(type(body) is dict, "surface_first_key_request_invalid")
        header = canonical(currentness)
        require(header.isascii() and len(header) <= 2048, "native_currentness_invalid")
        guard()
        headers = self._headers()
        headers["Authorization"] = "Bearer " + install_token
        headers["X-DJC-First-Key-Currentness"] = header
        return await self._post(self._origin, _FIRST_KEY_PREFIX + action, body,
                                headers, guard=guard, deadline=deadline)


class WidgetPublisherHTTPS(FirstKeyHTTPS):
    """Publish exact WidgetKit authority with separate Access credentials."""

    async def publish(self, action, body, *, guard, deadline):
        require(action in ("bind", "operation", "withdraw"), "native_publisher_action_invalid")
        guard()
        reply = await self._post(self.origin, "/v1/internal/widget-core/" + action, body,
                                 self._headers(), guard=guard, deadline=deadline)
        require(reply.status == 200 and canonical(reply.body) == '{"ok":true}',
                "native_publisher_ack_invalid", 502)
