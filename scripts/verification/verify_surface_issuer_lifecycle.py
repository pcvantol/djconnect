"""Isolated actual-HA software crypto/SQL qualification with synthetic issuer.

Ephemeral test-only P256 private keys stay in this disposable process. No real
operator enrollment, DNS/HTTP/APNs/provider, HA configuration or device effects.
The RPC adapter is explicitly synthetic; real product signature verification,
original-owner guards and SQLite stage commits are exercised without stubbing.
"""
from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import types

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
for name, directory in (('custom_components', ROOT / 'custom_components'),
        ('custom_components.djconnect', ROOT / 'custom_components/djconnect')):
    package = types.ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package

from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, utils  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.surface_issuer_journal import IssuerStageJournal, IssuerStageStore  # noqa: E402
from custom_components.djconnect.surface_issuer_owner import EnrolledIssuerOwner, IssuerOwnerCapture  # noqa: E402
from custom_components.djconnect.surface_issuer_lifecycle import IssuerLifecycle  # noqa: E402
from custom_components.djconnect.surface_issuer_responses import ExpectedIssuerReply  # noqa: E402
from custom_components.djconnect.surface_issuer_transport import IssuerTransport, IssuerHTTPReply  # noqa: E402
from custom_components.djconnect.surface_issuer_wire import DOMAIN, public_key_thumbprint, verify_envelope  # noqa: E402
from custom_components.djconnect.surface_push_contract import SurfacePushError  # noqa: E402
from custom_components.djconnect.surface_push_wire import canonical  # noqa: E402

START = 1792700000000


def operation(ms, suffix=1):
    return f'{ms:012x}'[:8] + '-' + f'{ms:012x}'[8:] + f'-7000-8000-{suffix:012x}'


def encoded(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


class SyntheticPreEnrolledOwner(EnrolledIssuerOwner):
    def __init__(self):
        # NOT an enrollment implementation: this is a disposable test fixture.
        self.key = ec.generate_private_key(ec.SECP256R1())
        public = self.key.public_key().public_numbers()
        jwk = {'kty': 'EC', 'crv': 'P-256', 'x': encoded(public.x.to_bytes(32)),
            'y': encoded(public.y.to_bytes(32))}
        policy = {'token_role': 'widget', 'platform': 'ios', 'apns_environment': 'sandbox',
            'target': {'app_bundle_id': 'com.example.synthetic',
                'extension_bundle_id': 'com.example.synthetic.widget', 'widget_kind': 'synthetic'},
            'activity_profile': None, 'external_content_allowed': False,
            'original_grant_expires_at_ms': START + 3600000,
            'max_operations': 10, 'max_events': 10, 'max_challenges': 1}
        fields = {'binding_id': 'a'*64, 'device_binding': 'b'*64, 'owner_binding': 'c'*64,
            'grant_binding': 'd'*64, 'source_binding': 'e'*64}
        thumb = public_key_thumbprint(jwk)
        scope = hashlib.sha256(canonical([DOMAIN, 'delegation', 'synthetic_delegation', 1,
            'synthetic_install', fields['device_binding'], fields['owner_binding'],
            fields['grant_binding'], fields['source_binding'], fields['binding_id'], thumb, policy]).encode()).hexdigest()
        expected = ExpectedIssuerReply('synthetic_delegation', operation(START), thumb,
            scope, START+3600000, START, 100.0)
        self.original = IssuerOwnerCapture(expected, 'https://synthetic.example.invalid',
            'synthetic_install', canonical(jwk), canonical(policy), **fields, witness=object())
        self.witness = self.original.witness
        self.valid, self.status_valid, self.withdraw_valid = True, True, True
        self.der, self.on_sign, self.signs = False, None, []

    def capture_live(self, operation_id):
        return replace(self.original, expected=replace(self.original.expected, operation_id=operation_id))

    def validate_live(self, original):
        if not self.valid or original.witness is not self.witness:
            raise SurfacePushError('synthetic_owner_changed')

    def validate_status(self, original):
        if not self.status_valid or original.witness is not self.witness:
            raise SurfacePushError('synthetic_status_changed')

    def validate_withdrawal(self, original):
        if not self.withdraw_valid or original.witness is not self.witness:
            raise SurfacePushError('synthetic_withdraw_changed')

    async def sign(self, original, path, message, *, action):
        self.signs.append(action)
        if self.on_sign:
            await self.on_sign(action)
        der = self.key.sign(message, ec.ECDSA(hashes.SHA256()))
        if self.der:
            return encoded(der)
        r, s = utils.decode_dss_signature(der)
        return encoded(r.to_bytes(32) + s.to_bytes(32))


class SyntheticIssuerRPC(IssuerTransport):
    def __init__(self, persistence):
        self.persistence, self.calls, self.on_call = persistence, [], None
        self.status_code, self.replayed = 200, False

    async def row(self):
        row = await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT body FROM djconnect_surface_issuer_journal WHERE singleton=1'))
        return json.loads(row[0])

    async def post_once(self, original, action, envelope, *, guard, deadline):
        guard()
        verify_envelope('/v1/push/surface/issuer/' + action, envelope,
            json.loads(original.public_key_json))
        phase = next(iter((await self.row())['records'].values()))['phase']
        if action in ('challenge', 'issue', 'withdraw'):
            assert phase == {'challenge': 'challenge_reserved', 'issue': 'issue_reserved',
                'withdraw': 'withdrawn'}[action]
        self.calls.append((action, envelope['payload']['operation_id']))
        if self.on_call:
            await self.on_call(action)
        e = original.expected
        reply = {'contract_version': 1, 'success': True,
            'operation_id': envelope['payload']['operation_id'], 'delegation_id': e.delegation_id,
            'delegation_revision': 1, 'expires_at_ms': e.original_grant_expires_ms,
            'state': action, 'replayed': self.replayed}
        if action == 'challenge':
            reply.update(scope_digest=e.scope_digest, key_thumbprint=e.key_thumbprint,
                challenge_id='synthetic_challenge', nonce='A'*43, expires_at_ms=START+120125)
        elif action == 'issue':
            reply.update(scope_digest=e.scope_digest, state='issued',
                capability_id='synthetic_capability', credential='djcs_'+'A'*43)
        elif action == 'status':
            reply.update(scope_digest=e.scope_digest, state='issued', success=False,
                capability_id='synthetic_capability', credential_state='unavailable')
        else:
            reply['state'] = 'withdrawn'
        return IssuerHTTPReply(self.status_code, reply)


async def denied(callback):
    try:
        await callback()
    except SurfacePushError:
        return
    raise AssertionError('synthetic invalid issuer attempt accepted')


async def main():
    lab = Path(os.environ['DJC_LAB_ROOT'])
    cases = []
    for kind in ('success_history_withdraw', 'der_signature', 'owner_aba',
            'monotonic_phase_expiry', 'late_withdraw_ack', 'duplicate_response',
            'signer_cancel_count', 'restart_lost_response', 'owner_close', 'capture_before_schedule'):
        directory = lab / kind
        directory.mkdir()
        persistence = PersistenceService(directory/'synthetic.sqlite', SQLitePersistenceProvider())
        await persistence.async_initialize()
        assert persistence.readiness.schema_version == 20
        owner, clock = SyntheticPreEnrolledOwner(), [START, 100.0]
        rpc = SyntheticIssuerRPC(persistence)
        lifecycle = IssuerLifecycle(owner, IssuerStageJournal(IssuerStageStore(persistence)), rpc,
            wall=lambda: clock[0], monotonic=lambda: clock[1])
        def original():
            return next(iter(lifecycle._attempts.values())).handle
        async def latency(action):
            if action == 'challenge':
                clock[0], clock[1] = START+250, 100.25
        rpc.on_call = latency
        try:
            if kind == 'success_history_withdraw':
                purpose = await lifecycle.acquire(lifecycle.begin(operation(START)))
                assert purpose.is_current()
                assert purpose.original_wall_ms == START and purpose.original_monotonic == 100.0
                clock[:] = [START+3600001, 3700.001]
                owner.valid = False
                assert not purpose.is_current() and purpose.bearer == ''
                assert await lifecycle.status(original()) == {'available': False, 'state': 'issued'}
                assert await lifecycle.withdraw(original(), operation(clock[0])) == {'available': False, 'state': 'withdrawn'}
                assert rpc.calls == [('challenge', operation(START)), ('issue', operation(START)),
                    ('status', operation(START)), ('withdraw', operation(clock[0]))]
            elif kind == 'owner_close':
                handle = lifecycle.begin(operation(START))
                purpose = await lifecycle.acquire(handle)
                lifecycle.close()
                assert purpose.bearer == '' and not purpose.is_current()
                await denied(lambda: lifecycle.status(handle))
                assert len(rpc.calls) == 2
            elif kind == 'capture_before_schedule':
                handle = lifecycle.begin(operation(START))
                clock[:] = [START+120000, 220.0]
                await denied(lambda: lifecycle.acquire(handle))
                assert not rpc.calls and not owner.signs
            elif kind == 'der_signature':
                owner.der = True
                await denied(lambda: lifecycle.acquire(lifecycle.begin(operation(START))))
                assert not rpc.calls and owner.signs == ['challenge']
            elif kind == 'owner_aba':
                async def aba(_):
                    owner.witness = object()
                owner.on_sign = aba
                await denied(lambda: lifecycle.acquire(lifecycle.begin(operation(START))))
                assert not rpc.calls
            elif kind == 'monotonic_phase_expiry':
                async def slow(action):
                    if action == 'issue':
                        clock[:] = [START+500, 220.0]
                owner.on_sign = slow
                await denied(lambda: lifecycle.acquire(lifecycle.begin(operation(START))))
                assert len(rpc.calls) == 1
            elif kind == 'late_withdraw_ack':
                async def withdraw(action):
                    await latency(action)
                    if action == 'issue':
                        await lifecycle.withdraw(original(), operation(START+1))
                rpc.on_call = withdraw
                await denied(lambda: lifecycle.acquire(lifecycle.begin(operation(START))))
                assert next(iter(lifecycle._attempts.values())).purpose is None
                assert next(iter((await rpc.row())['records'].values()))['phase'] == 'withdrawn'
            elif kind == 'duplicate_response':
                rpc.status_code, rpc.replayed = 202, True
                await denied(lambda: lifecycle.acquire(lifecycle.begin(operation(START))))
                assert len(rpc.calls) == 1
            elif kind == 'signer_cancel_count':
                async def cancelled(_):
                    asyncio.current_task().cancel()
                    try:
                        await asyncio.sleep(0)
                    except asyncio.CancelledError:
                        pass
                owner.on_sign = cancelled
                async def run():
                    try:
                        await lifecycle.acquire(lifecycle.begin(operation(START)))
                    except asyncio.CancelledError:
                        return
                    raise AssertionError('cancellation swallowed')
                await asyncio.create_task(run())
                assert not rpc.calls
            else:
                async def lost(_):
                    raise SurfacePushError('synthetic_lost_response')
                rpc.on_call = lost
                await denied(lambda: lifecycle.acquire(lifecycle.begin(operation(START))))
                fresh = IssuerLifecycle(owner, IssuerStageJournal(IssuerStageStore(persistence)), rpc,
                    wall=lambda: clock[0], monotonic=lambda: clock[1])
                before = list(rpc.calls)
                await denied(lambda: fresh.acquire(fresh.begin(operation(START+1))))
                await denied(lambda: fresh.status(original()))
                assert rpc.calls == before
            data = await rpc.row()
            assert bool(data['records']) == (kind != 'capture_before_schedule')
            raw = canonical(data)
            for secret in ('djcs_', 'nonce', 'signature', 'private_key', 'synthetic_install', 'synthetic_delegation'):
                assert secret not in raw
            cases.append({'case': kind, 'pass': True, 'synthetic_rpc_count': len(rpc.calls)})
        finally:
            await persistence.async_close()
            owner.key = None  # Test process owns no retained or persisted key.
    record = {'scope': 'ACTUAL_HA_SQL15_ES256_REQUIRED_LIFECYCLE_SYNTHETIC_OWNER_RPC_ONLY',
        'cases': cases, 'operator_enrollments': 0, 'network_calls': 0,
        'native_provider_calls': 0, 'private_keys_persisted': 0,
        'real_owner_or_service_admission': False,
        'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'custom_components/djconnect').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}}
    (lab/'issuer-lifecycle-receipt.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'source_hashes'}))


if __name__ == '__main__':
    asyncio.run(main())
