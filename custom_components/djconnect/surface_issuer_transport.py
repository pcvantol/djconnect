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

from .surface_issuer_owner import IssuerOwnerCapture
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


class IssuerHTTPS(IssuerTransport):
    """A fresh no-cookie, no-proxy, no-auth session for each original attempt."""
    def __init__(self, *, monotonic=time.monotonic):
        self.monotonic = monotonic

    async def post_once(self, capture, action, envelope, *, guard, deadline):
        import aiohttp  # Supplied by HA; pure journal/owner users need no SDK.

        require(type(capture) is IssuerOwnerCapture,
            'surface_issuer_owner_capture_invalid', 503)
        capture.comparisons()
        path = PREFIX + action
        require(type(envelope) is dict and set(envelope) == {'payload', 'signature'},
            'surface_issuer_wire_invalid')
        signing_bytes(path, envelope['payload'])
        encoded = canonical(envelope).encode('utf-8')
        require(len(encoded) <= 16384, 'surface_issuer_request_too_large')
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
                    async with session.post(capture.origin + path, data=encoded,
                            headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                'Accept-Encoding': 'identity'},
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
