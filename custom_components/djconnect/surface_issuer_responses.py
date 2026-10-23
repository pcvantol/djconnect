"""Closed API2a6 reply comparisons; never owner or live admission.

No signer, HTTP client, key owner, journal, purpose credential or service wiring.
Only the eventual independently qualified lifecycle may adopt validated outputs.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .surface_issuer_wire import decoded
from .surface_push_contract import require
from .surface_push_wire import safe_integer
from .transport_operations import operation_created_ms

BASE = frozenset({'contract_version', 'success', 'operation_id', 'delegation_id',
    'delegation_revision', 'expires_at_ms', 'state', 'replayed'})
SCOPED = BASE | {'scope_digest'}


@dataclass(frozen=True, repr=False)
class ExpectedIssuerReply:
    """Frozen comparison values, NOT proof of owner/enrolment/permission."""
    delegation_id: str
    operation_id: str
    key_thumbprint: str
    scope_digest: str
    original_grant_expires_ms: int
    original_grant_wall_ms: int
    original_grant_monotonic: float
    delegation_revision: int = 1

    def validate(self):
        require(type(self.delegation_id) is str
            and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.delegation_id), 'surface_issuer_reply_invalid')
        operation_created_ms(self.operation_id)
        require(type(self.delegation_revision) is int and self.delegation_revision == 1,
            'surface_issuer_reply_invalid')
        require(all(type(v) is str and re.fullmatch(r'[a-f0-9]{64}', v)
            for v in (self.key_thumbprint, self.scope_digest)), 'surface_issuer_reply_invalid')
        require(safe_integer(self.original_grant_wall_ms, 1)
            and safe_integer(self.original_grant_expires_ms, 1)
            and self.original_grant_wall_ms < self.original_grant_expires_ms
                <= self.original_grant_wall_ms + 28800000
            and type(self.original_grant_monotonic) in (int, float)
            and math.isfinite(self.original_grant_monotonic), 'surface_issuer_reply_invalid')

    def live(self, now_ms, monotonic):
        self.validate()
        require(safe_integer(now_ms, 1) and type(monotonic) in (int, float)
            and math.isfinite(monotonic)
            and self.original_grant_wall_ms <= now_ms
            and self.original_grant_monotonic <= monotonic
            and now_ms < self.original_grant_expires_ms
            and monotonic < self.original_grant_monotonic +
                (self.original_grant_expires_ms-self.original_grant_wall_ms)/1000,
            'surface_issuer_reply_expired')

    def live_operation(self, now_ms):
        # API2a6 operationDeadline: historical status deliberately does not use
        # this guard. Live phases cannot move the UUID's original clock window.
        self.validate()
        created = operation_created_ms(self.operation_id)
        require(safe_integer(now_ms, 1) and created <= now_ms + 30000
            and now_ms < created + 300000, 'surface_issuer_operation_clock_invalid')


@dataclass(frozen=True, repr=False)
class ChallengeSecret:
    expected: ExpectedIssuerReply = field(repr=False)
    challenge_id: str
    nonce: str = field(repr=False)
    expires_at_ms: int
    request_wall_ms: int
    request_monotonic: float


@dataclass(frozen=True, repr=False)
class IssueSecret:
    capability_id: str
    bearer: str = field(repr=False)


def _closed(reply, fields):
    require(type(reply) is dict and set(reply) == fields, 'surface_issuer_reply_invalid')


def _identity(reply, expected):
    expected.validate()
    require(type(reply['contract_version']) is int and reply['contract_version'] == 1
        and type(reply['delegation_revision']) is int
        and reply['delegation_revision'] == expected.delegation_revision
        and reply['operation_id'] == expected.operation_id
        and reply['delegation_id'] == expected.delegation_id
        and safe_integer(reply['expires_at_ms'], 1)
        and type(reply['replayed']) is bool, 'surface_issuer_reply_invalid')


def _scoped(reply, expected):
    _identity(reply, expected)
    require(reply['scope_digest'] == expected.scope_digest, 'surface_issuer_reply_invalid')


def _identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value),
        'surface_issuer_reply_invalid')


def challenge_winner(reply, expected, *, status, request_wall_ms,
        request_monotonic, now_ms, monotonic):
    _closed(reply, SCOPED | {'key_thumbprint', 'challenge_id', 'nonce'})
    _scoped(reply, expected)
    expected.live(now_ms, monotonic)
    require(type(status) is int and status == 200 and reply['success'] is True
        and reply['state'] == 'challenge' and reply['replayed'] is False
        and reply['key_thumbprint'] == expected.key_thumbprint, 'surface_issuer_reply_invalid')
    require(safe_integer(request_wall_ms, 1) and type(request_monotonic) in (int,float)
        and math.isfinite(request_monotonic)
        and expected.original_grant_wall_ms <= request_wall_ms <= now_ms
        and expected.original_grant_monotonic <= request_monotonic <= monotonic,
        'surface_issuer_reply_invalid')
    expected.live_operation(request_wall_ms)
    expected.live_operation(now_ms)
    # The server starts120s at its receipt, after Core's original pre-await
    # anchor. Validate the returned bound, then retain the EARLIER local cap;
    # accepting network latency can never refresh the original Core lease.
    server_bound = min(now_ms+120000,
        operation_created_ms(expected.operation_id)+300000, expected.original_grant_expires_ms)
    deadline = min(reply['expires_at_ms'], request_wall_ms+120000,
        operation_created_ms(expected.operation_id)+300000, expected.original_grant_expires_ms)
    require(now_ms < reply['expires_at_ms'] <= server_bound and now_ms < deadline
        and monotonic < request_monotonic + (deadline-request_wall_ms)/1000,
        'surface_issuer_reply_expired')
    _identifier(reply['challenge_id'])
    decoded(reply['nonce'], 32)
    return ChallengeSecret(expected, reply['challenge_id'], reply['nonce'], deadline,
        request_wall_ms, request_monotonic)


def issue_winner(reply, expected, *, challenge, status, now_ms, monotonic):
    _closed(reply, SCOPED | {'capability_id', 'credential'})
    _scoped(reply, expected)
    expected.live(now_ms, monotonic)
    require(type(challenge) is ChallengeSecret
        and challenge.expected is expected
        and challenge.request_wall_ms <= now_ms < challenge.expires_at_ms
        and challenge.request_monotonic <= monotonic < challenge.request_monotonic
            + (challenge.expires_at_ms-challenge.request_wall_ms)/1000,
        'surface_issuer_reply_expired')
    expected.live_operation(challenge.request_wall_ms)
    expected.live_operation(now_ms)
    require(type(status) is int and status == 200 and reply['success'] is True
        and reply['state'] == 'issued' and reply['replayed'] is False
        and reply['expires_at_ms'] == expected.original_grant_expires_ms,
        'surface_issuer_reply_invalid')
    _identifier(reply['capability_id'])
    token = reply['credential']
    require(type(token) is str and token.startswith('djcs_'), 'surface_issuer_reply_invalid')
    decoded(token[5:],32)
    return IssueSecret(reply['capability_id'], token)


def status_unavailable(reply, expected):
    """Metadata only, may be expired/withdrawn; caller needs separate authority."""
    _closed(reply, SCOPED | {'capability_id','credential_state'})
    _scoped(reply, expected)
    require(reply['success'] is False and reply['credential_state'] == 'unavailable'
        and reply['state'] in ('issued','withdrawn','unknown')
        and reply['expires_at_ms'] == expected.original_grant_expires_ms,
        'surface_issuer_reply_invalid')
    if reply['capability_id'] is not None:
        _identifier(reply['capability_id'])
    return {'available':False, 'state':reply['state']}


def withdrawal_ack(reply, expected):
    """No live grant/bearer requirement; never restores readiness or send rights."""
    _closed(reply, BASE)
    _identity(reply, expected)
    require(reply['success'] is True and reply['state'] == 'withdrawn'
        and reply['expires_at_ms'] == expected.original_grant_expires_ms,
        'surface_issuer_reply_invalid')
    return {'available':False, 'state':'withdrawn'}
