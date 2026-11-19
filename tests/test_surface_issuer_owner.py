"""Closed comparison metadata only; no owner enrolment, private key or RPC."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest

from tests.test_profile_dj_settings_persistence import operation
from custom_components.djconnect.surface_issuer_owner import EnrolledIssuerOwner, IssuerOwnerCapture
from custom_components.djconnect.surface_issuer_responses import ExpectedIssuerReply
from custom_components.djconnect.surface_issuer_wire import DOMAIN
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.surface_push_wire import canonical

START = 1792700000000


def capture():
    public = json.loads((Path(__file__).parent / 'fixtures/surface_push/api_2a6_issuer_public_vectors.json').read_text())
    policy = {'token_role': 'widget', 'platform': 'ios', 'apns_environment': 'sandbox',
        'target': {'app_bundle_id': 'com.example.synthetic', 'extension_bundle_id': 'com.example.synthetic.widget', 'widget_kind': 'synthetic'},
        'activity_profile': None, 'external_content_allowed': False,
        'original_grant_expires_at_ms': START + 3600000,
        'max_operations': 10, 'max_events': 10, 'max_challenges': 1}
    fields = {'binding_id': 'a' * 64, 'device_binding': 'b' * 64, 'owner_binding': 'c' * 64,
        'grant_binding': 'd' * 64, 'source_binding': 'e' * 64}
    scope = hashlib.sha256(canonical([DOMAIN, 'delegation', 'synthetic_delegation', 1,
        'synthetic_install', fields['device_binding'], fields['owner_binding'],
        fields['grant_binding'], fields['source_binding'], fields['binding_id'],
        public['key_thumbprint'], policy]).encode()).hexdigest()
    expected = ExpectedIssuerReply('synthetic_delegation', operation(START),
        public['key_thumbprint'], scope, START + 3600000, START, 100.0)
    return IssuerOwnerCapture(expected, 'https://synthetic.example.invalid', 'synthetic_install',
        canonical(public['public_key']), canonical(policy), **fields, witness=object())


class IssuerOwnerComparisonTests(unittest.TestCase):
    def test_exact_api_scope_and_secret_free_journal_hashes_are_not_owner_admission(self):
        original = capture()
        jwk, policy = original.comparisons()
        self.assertEqual(jwk['crv'], 'P-256')
        self.assertEqual(policy['token_role'], 'widget')
        keys = original.journal_keys()
        self.assertEqual(len(keys), 3)
        self.assertTrue(all(len(value) == 64 and value.isalnum() for value in keys))
        self.assertNotIn(original.install_id, repr(original))
        self.assertFalse(hasattr(original, 'sign'))
        with self.assertRaises(TypeError):
            EnrolledIssuerOwner()  # No default bool/paired identity/key creator.

    def test_new_uuid_cannot_change_identity_or_binding_hash_for_same_immutable_delegation(self):
        original = capture()
        changed = replace(original, expected=replace(original.expected, operation_id=operation(START + 1)))
        a, b = original.journal_keys(), changed.journal_keys()
        self.assertEqual(a[:2], b[:2])
        self.assertNotEqual(a[2], b[2])

    def test_origin_is_separate_from_signature_scope_and_has_no_equivalent_aliases(self):
        original = capture()
        changed = replace(original, origin='https://other.example.invalid')
        self.assertEqual(original.expected.scope_digest, changed.expected.scope_digest)
        self.assertNotEqual(original.journal_keys()[0], changed.journal_keys()[0])
        for value in ('http://synthetic.example.invalid', 'https://synthetic.example.invalid/',
                'https://SYNTHETIC.example.invalid', 'https://synthetic.example.invalid:443',
                'https://user@synthetic.example.invalid', 'https://synthetic.example.invalid?x=1',
                'https://synthetic.example.invalid#x', 'https://synthetic.example.invalid\\evil'):
            with self.subTest(origin=value), self.assertRaises(SurfacePushError):
                replace(original, origin=value).comparisons()

    def test_noncanonical_dns_cannot_create_another_identity_budget_for_same_delegation(self):
        original = capture()
        canonical_identity = original.journal_keys()[0]
        for origin in ('https://synthetic.example.invalid.', 'https://.',
                'https://%73ynthetic.example.invalid', 'https://127.0.0.1',
                'https://-synthetic.example.invalid', 'https://synthetic..invalid',
                'https://synthetic.example-.invalid', 'https://localhost'):
            with self.subTest(origin=origin), self.assertRaises(SurfacePushError):
                replace(original, origin=origin).journal_keys()
        self.assertEqual(original.journal_keys()[0], canonical_identity)

    def test_scope_fields_key_or_policy_cannot_silently_change_under_same_server_digest(self):
        original = capture()
        for field in ('binding_id', 'device_binding', 'owner_binding', 'source_binding', 'grant_binding'):
            with self.subTest(field=field), self.assertRaises(SurfacePushError):
                replace(original, **{field: 'f' * 64}).comparisons()
        with self.assertRaises(SurfacePushError):
            replace(original, expected=replace(original.expected, key_thumbprint='f' * 64)).comparisons()
        with self.assertRaises(SurfacePushError):
            replace(original, install_id='other_install').comparisons()

    def test_unknown_extra_duplicate_noncanonical_or_unqualified_activity_policy_is_rejected(self):
        original = capture()
        policy = json.loads(original.policy_json)
        patches = ({'token_role': 'live_activity_update'}, {'activity_profile': 'unknown'},
            {'external_content_allowed': True}, {'platform': 'tvos'}, {'platform': []},
            {'apns_environment': []}, {'max_challenges': True}, {'max_events': 1001},
            {'original_grant_expires_at_ms': START + 3600001}, {'unknown': True})
        for patch in patches:
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                replace(original, policy_json=canonical(policy | patch)).comparisons()
        for raw in ('{"a":1,"a":1}', json.dumps(policy), '\ud800', 'x' * 4097):
            with self.subTest(raw_size=len(raw)), self.assertRaises(SurfacePushError):
                replace(original, policy_json=raw).comparisons()

    def test_original_grant_anchors_and_witness_cannot_be_omitted(self):
        original = capture()
        with self.assertRaises(SurfacePushError):
            replace(original, witness=None).comparisons()
        for patch in ({'original_grant_wall_ms': START + 3600000},
                {'original_grant_expires_ms': START + 28800001},
                {'original_grant_monotonic': float('nan')}):
            with self.subTest(patch=tuple(patch)), self.assertRaises(SurfacePushError):
                replace(original, expected=replace(original.expected, **patch)).comparisons()
        changed = replace(original, expected=replace(original.expected, original_grant_monotonic=100.5))
        self.assertEqual(original.journal_keys()[0], changed.journal_keys()[0])
        self.assertNotEqual(original.journal_keys()[1], changed.journal_keys()[1])
