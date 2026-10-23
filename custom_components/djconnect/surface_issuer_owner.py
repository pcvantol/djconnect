"""Required enrolled-key owner ports; comparison data is never an enrolment grant.

No concrete owner, key factory, operator secret, config discovery or service
admission is provided. Live, historical status and withdrawal authorities stay
separate. A future owner must validate the SAME original generation witness
before/after every await, including an original key/source/owner ABA transition.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
import re
from urllib.parse import urlsplit

from .surface_issuer_responses import ExpectedIssuerReply
from .surface_issuer_wire import DOMAIN, public_key_thumbprint
from .surface_push_contract import BUNDLE, IDENTIFIER, require
from .surface_push_purpose import POLICY
from .surface_push_wire import canonical, safe_integer

DNS_HOST = re.compile(r'(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+'
    r'[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?\Z')


def _digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _closed_json(raw, limit):
    try:
        require(type(raw) is str and len(raw.encode()) <= limit,
            'surface_issuer_owner_capture_invalid', 503)
        value = json.loads(raw)
        require(canonical(value) == raw, 'surface_issuer_owner_capture_invalid', 503)
        return value
    except (ValueError, UnicodeError, RecursionError):
        require(False, 'surface_issuer_owner_capture_invalid', 503)


@dataclass(frozen=True, repr=False)
class IssuerOwnerCapture:
    """Immutable original comparisons supplied by separately qualified owner code."""
    expected: ExpectedIssuerReply = field(repr=False)
    origin: str
    install_id: str = field(repr=False)
    public_key_json: str = field(repr=False)
    policy_json: str = field(repr=False)
    binding_id: str
    device_binding: str
    owner_binding: str
    grant_binding: str
    source_binding: str
    witness: object = field(repr=False)

    def comparisons(self):
        """Closed API2a6 scope consistency only, not live/operator/key admission."""
        require(type(self.expected) is ExpectedIssuerReply,
            'surface_issuer_owner_capture_invalid', 503)
        self.expected.validate()
        require(type(self.origin) is str and 1 <= len(self.origin) <= 2048
            and self.origin.isascii() and all(32 < ord(c) < 127 for c in self.origin),
            'surface_issuer_origin_invalid', 503)
        try:
            origin = urlsplit(self.origin)
            valid_origin = (origin.scheme == 'https' and bool(origin.hostname)
                and DNS_HOST.fullmatch(origin.hostname) is not None
                and origin.path == '' and origin.username is None and origin.password is None
                and not origin.query and not origin.fragment and '\\' not in self.origin
                and origin.port is None and self.origin == 'https://' + origin.hostname)
        except ValueError:
            valid_origin = False
        require(valid_origin, 'surface_issuer_origin_invalid', 503)
        require(type(self.install_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,128}', self.install_id),
            'surface_issuer_owner_capture_invalid', 503)
        require(all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
            for value in (self.binding_id, self.device_binding, self.owner_binding,
                self.grant_binding, self.source_binding)) and self.witness is not None,
            'surface_issuer_owner_capture_invalid', 503)
        jwk = _closed_json(self.public_key_json, 1024)
        policy = _closed_json(self.policy_json, 4096)
        require(public_key_thumbprint(jwk) == self.expected.key_thumbprint,
            'surface_issuer_owner_capture_invalid', 503)
        require(type(policy) is dict and set(policy) == POLICY
            and policy['token_role'] == 'widget' and policy['activity_profile'] is None
            and policy['external_content_allowed'] is False
            and type(policy['platform']) is str and policy['platform'] in
                {'ios', 'ipados', 'maccatalyst', 'macos', 'watchos', 'visionos'}
            and type(policy['apns_environment']) is str
            and policy['apns_environment'] in {'sandbox', 'production'}
            and policy['original_grant_expires_at_ms'] == self.expected.original_grant_expires_ms
            and type(policy['original_grant_expires_at_ms']) is int,
            'surface_issuer_policy_pending', 503)
        for key, limit in (('max_operations', 10000), ('max_events', 1000), ('max_challenges', 100)):
            require(safe_integer(policy[key], 1) and policy[key] <= limit,
                'surface_issuer_owner_capture_invalid', 503)
        target = policy['target']
        require(type(target) is dict and set(target) == {'app_bundle_id', 'extension_bundle_id', 'widget_kind'},
            'surface_issuer_owner_capture_invalid', 503)
        for key, value in target.items():
            pattern = BUNDLE if key.endswith('bundle_id') else IDENTIFIER
            require(type(value) is str and 1 <= len(value) <= 200 and pattern.fullmatch(value),
                'surface_issuer_owner_capture_invalid', 503)
        require(target['extension_bundle_id'].startswith(target['app_bundle_id'] + '.'),
            'surface_issuer_owner_capture_invalid', 503)
        scope = _digest([DOMAIN, 'delegation', self.expected.delegation_id, 1,
            self.install_id, self.device_binding, self.owner_binding, self.grant_binding,
            self.source_binding, self.binding_id, self.expected.key_thumbprint, policy])
        require(scope == self.expected.scope_digest, 'surface_issuer_owner_capture_invalid', 503)
        return jwk, policy

    def journal_keys(self):
        self.comparisons()
        # A changed UUID/key/scope cannot create a new identity for the same
        # original origin/install/delegation/revision. Original request is separate.
        identity = _digest([DOMAIN, 'identity', self.origin, self.install_id,
            self.expected.delegation_id, self.expected.delegation_revision])
        binding = _digest([DOMAIN, 'binding', identity, self.public_key_json, self.policy_json,
            self.expected.key_thumbprint, self.expected.scope_digest, self.binding_id,
            self.device_binding, self.owner_binding, self.grant_binding, self.source_binding,
            self.expected.original_grant_wall_ms, self.expected.original_grant_expires_ms,
            float(self.expected.original_grant_monotonic).hex()])
        return identity, binding, _digest([DOMAIN, 'operation', self.expected.operation_id])


class EnrolledIssuerOwner(ABC):
    """No default implementation: normal pairing/booleans cannot supply these ports.

    validate methods must return None after original authority validation or
    raise. Historical status/withdrawal may outlive the original grant but must
    retain their own current enrolled-key authority. sign never creates a key.
    """
    @abstractmethod
    def capture_live(self, operation_id: str) -> IssuerOwnerCapture:
        raise NotImplementedError

    @abstractmethod
    def validate_live(self, capture: IssuerOwnerCapture) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_status(self, capture: IssuerOwnerCapture) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_withdrawal(self, capture: IssuerOwnerCapture) -> None:
        raise NotImplementedError

    @abstractmethod
    async def sign(self, capture: IssuerOwnerCapture, path: str, message: bytes, *, action: str) -> str:
        raise NotImplementedError
