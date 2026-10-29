"""Closed installation-principal DATA only; no signer, registry or authority.

Frozen private cross-owner R2 design7b44758; versioned old codecs are untouched.
Parsing/hash/relational equality proves neither custody, permission, currentness,
crypto validity, SQL commitment nor withdrawal. No production caller imports this
module. All APIs consume bounded primitive canonical JSON, never authority objects.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
import re
from types import MappingProxyType
from typing import Mapping

DESIGN_SHA256 = "7b44758c5f7bba76dd3f61b042a776330ee25697523d3bd05248a5697f76db4b"
RECORD_DOMAIN = b"DJC-PRIVATE-INSTALLATION-RECORD-CANDIDATE-V1\n"
POSSESSION_DOMAIN = b"DJC-CORE-INSTALL-PRINCIPAL-POSSESSION-CANDIDATE-V1\n"
CLASSIFICATION = "INSTALLATION_PRINCIPAL_DATA_ONLY"
_UUID = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}")
_HEX = re.compile(r"[a-f0-9]{64}")
_OPAQUE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")


class InstallationDataError(ValueError):
    """Closed input/relational error; never embeds input or sensitive values."""


def _require(ok):
    if not ok:
        raise InstallationDataError("installation_principal_data_invalid")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _scan(text, maximum_bytes, maximum_tokens):
    """Fixed depth/token lexical gate BEFORE generic JSON decoding."""
    _require(type(text) is str and len(text) <= maximum_bytes and text.isascii())
    _require(len(text.encode("utf-8")) <= maximum_bytes)
    stack = []  # At most four elements; rejected before appending a fifth.
    tokens = 0
    i = 0
    while i < len(text):
        c = text[i]
        if c in " \t\r\n,:":
            i += 1
            continue
        if c in "{[":
            _require(len(stack) < 4)
            stack.append(c)
            tokens += 1
            i += 1
        elif c in "}]":
            _require(bool(stack) and stack.pop() == ("{" if c == "}" else "["))
            i += 1
        elif c == '"':
            tokens += 1
            i += 1
            while i < len(text) and text[i] != '"':
                _require(ord(text[i]) >= 32)
                if text[i] == "\\":
                    i += 1
                    _require(i < len(text))
                    if text[i] == "u":
                        _require(i + 4 < len(text) and all(x in "0123456789abcdefABCDEF" for x in text[i+1:i+5]))
                        i += 4
                    else:
                        _require(text[i] in '\"\\/bfnrt')
                i += 1
            _require(i < len(text))
            i += 1
        elif c in "-0123456789":
            match = _NUMBER.match(text, i)
            _require(match is not None)
            i = match.end()
            tokens += 1
        else:
            literal = next((x for x in ("true", "false", "null") if text.startswith(x, i)), None)
            _require(literal is not None)
            i += len(literal)
            tokens += 1
        _require(tokens <= maximum_tokens)
    _require(not stack)


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result)
        result[key] = value
    return result


def _decode(text, maximum_bytes=32768, maximum_tokens=256):
    _scan(text, maximum_bytes, maximum_tokens)
    try:
        value = json.loads(text, object_pairs_hook=_pairs)
        _require(type(value) is dict and _canonical(value) == text)
    except (ValueError, RecursionError):
        raise InstallationDataError("installation_principal_data_invalid") from None
    return value


def _freeze(value):
    return MappingProxyType({k: _freeze(v) if type(v) is dict else v for k, v in value.items()})


@dataclass(frozen=True, slots=True)
class InstallationRecordData:
    record_type: str
    digest: str
    canonical_text: str = field(repr=False)
    values: Mapping = field(repr=False)
    classification: str = field(default=CLASSIFICATION, init=False)


@dataclass(frozen=True, slots=True)
class PossessionTranscriptData:
    body_sha256: str
    signing_input_sha256: str
    canonical_text: str = field(repr=False)
    signing_input: bytes = field(repr=False)
    values: Mapping = field(repr=False)
    classification: str = field(default=CLASSIFICATION, init=False)


_SCHEMAS = MappingProxyType({k: MappingProxyType(v) for k, v in {'bootstrap_admission_context': {'challenge_id': 'uuid4',
                                 'challenge_nonce_sha256': 'sha256',
                                 'clock_policy_sha256': 'sha256',
                                 'core_installation_binding_sha256': 'sha256',
                                 'custody_operation_id': 'uuid4',
                                 'custody_public_receipt_sha256': 'sha256',
                                 'expected_registry_revision': 'counter',
                                 'generation_preparation_sha256': 'sha256',
                                 'independent_installation_association_sha256': 'sha256',
                                 'kind': 'literal bootstrap-admission-context/1',
                                 'operator_authority_record_sha256': 'sha256',
                                 'original_authorization_deadline_unix_ms': 'utc_ms',
                                 'policy_sha256': 'sha256',
                                 'registration_operation_id': 'uuid4',
                                 'registry_identity_sha256': 'sha256',
                                 'registry_restore_policy_sha256': 'sha256',
                                 'subject_sha256': 'sha256',
                                 'version': 'literal1'},
 'bootstrap_proof_preparation': {'admission_context_sha256': 'sha256',
                                 'custody_operation_id': 'uuid4',
                                 'custody_public_receipt_sha256': 'sha256',
                                 'expected_transcript': 'exact_R1_canonical_body_string',
                                 'kind': 'literal bootstrap-proof-preparation/1',
                                 'original_signing_deadline_unix_ms': 'utc_ms',
                                 'registration_operation_id': 'uuid4',
                                 'signing_attempt_limit': 'literal1',
                                 'subject_sha256': 'sha256',
                                 'version': 'literal1'},
 'custody_generation_preparation': {'attempt_limit': 'literal1',
                                    'core_installation_binding_sha256': 'sha256',
                                    'core_instance_id': 'opaque',
                                    'custody_epoch': 'positive_counter',
                                    'custody_operation_id': 'uuid4',
                                    'custody_policy_sha256': 'sha256',
                                    'custody_restore_policy_sha256': 'sha256',
                                    'expected_local_revision': 'counter',
                                    'installation_id': 'opaque',
                                    'kind': 'literal custody-generation-preparation/1',
                                    'operator_admission_binding_sha256': 'sha256',
                                    'original_generation_deadline_unix_ms': 'utc_ms',
                                    'version': 'literal1'},
 'custody_public_receipt': {'core_instance_id': 'opaque',
                            'custody_epoch': 'positive_counter',
                            'custody_operation_id': 'uuid4',
                            'custody_policy_sha256': 'sha256',
                            'generation_preparation_sha256': 'sha256',
                            'installation_id': 'opaque',
                            'kind': 'literal custody-public-receipt/1',
                            'local_committed_revision': 'positive_counter',
                            'public_key_jwk': 'public_P256_point',
                            'public_key_pin_sha256': 'sha256',
                            'version': 'literal1'},
 'device_pair_join': {'join_revision': 'positive_counter',
                      'kind': 'literal installation-device-pair-join/2',
                      'original_pair_authority_record_sha256': 'sha256',
                      'original_pair_binding_sha256': 'sha256',
                      'original_pair_expires_at_unix_ms': 'utc_ms',
                      'original_pair_operation_id': 'uuid4',
                      'principal_record_sha256': 'sha256',
                      'purpose_policy_sha256': 'sha256',
                      'subject_sha256': 'sha256',
                      'version': 'literal2'},
 'installation_principal_record': {'accepted_independent_authority_bundle_sha256': 'sha256',
                                   'bootstrap_preparation_sha256': 'sha256',
                                   'challenge_id': 'uuid4',
                                   'crypto_possession_body_sha256': 'sha256',
                                   'crypto_signing_input_sha256': 'sha256',
                                   'kind': 'literal installation-principal-record/2',
                                   'original_authorization_deadline_unix_ms': 'utc_ms',
                                   'public_key_pin_sha256': 'sha256',
                                   'registration_operation_id': 'uuid4',
                                   'registry_committed_revision': 'positive_counter',
                                   'subject_sha256': 'sha256',
                                   'version': 'literal2'},
 'installation_principal_subject': {'core_installation_binding_sha256': 'sha256',
                                    'core_instance_id': 'opaque',
                                    'custody_epoch': 'positive_counter',
                                    'custody_operation_id': 'uuid4',
                                    'custody_public_receipt_sha256': 'sha256',
                                    'installation_id': 'opaque',
                                    'kind': 'literal installation-principal-subject/2',
                                    'policy_sha256': 'sha256',
                                    'principal_epoch': 'positive_counter',
                                    'principal_id': 'opaque',
                                    'public_key_pin_sha256': 'sha256',
                                    'version': 'literal2'},
 'operation_status': {'kind': 'literal operation-status/1',
                      'ledger_revision': 'counter',
                      'operation_id': 'uuid4',
                      'operation_kind': 'enum '
                                        'custody_generation|bootstrap_signing|registry_admission|withdrawal',
                      'outcome': 'closed_variant',
                      'preparation_sha256': 'sha256',
                      'version': 'literal1'},
 'original_admission_intent': {'admission_context_sha256': 'sha256',
                               'bootstrap_preparation_sha256': 'sha256',
                               'challenge_id': 'uuid4',
                               'challenge_nonce_sha256': 'sha256',
                               'expected_registry_revision': 'counter',
                               'kind': 'literal original-admission-intent/2',
                               'original_authorization_deadline_unix_ms': 'utc_ms',
                               'registration_operation_id': 'uuid4',
                               'subject_sha256': 'sha256',
                               'version': 'literal2',
                               'withdrawal_policy_sha256': 'sha256'},
 'original_admission_retirement_tombstone': {'kind': 'literal original-admission-retirement/2',
                                             'original_admission_intent_sha256': 'sha256',
                                             'registration_challenge_id': 'uuid4',
                                             'registration_challenge_nonce_sha256': 'sha256',
                                             'registration_operation_id': 'uuid4',
                                             'registry_committed_revision': 'positive_counter',
                                             'subject_sha256': 'sha256',
                                             'version': 'literal2',
                                             'withdrawal_operation_id': 'uuid4',
                                             'withdrawal_preparation_sha256': 'sha256'},
 'original_operation_withdrawal_preparation': {'kind': 'literal original-operation-withdrawal/2',
                                               'original_admission_intent_sha256': 'sha256',
                                               'original_withdrawal_deadline_unix_ms': 'utc_ms',
                                               'registration_challenge_id': 'uuid4',
                                               'registration_challenge_nonce_sha256': 'sha256',
                                               'registration_operation_id': 'uuid4',
                                               'registry_identity_sha256': 'sha256',
                                               'registry_restore_policy_sha256': 'sha256',
                                               'subject_sha256': 'sha256',
                                               'version': 'literal2',
                                               'withdrawal_authority_record_sha256': 'sha256',
                                               'withdrawal_challenge_id': 'uuid4',
                                               'withdrawal_challenge_nonce_sha256': 'sha256',
                                               'withdrawal_operation_id': 'uuid4',
                                               'withdrawal_policy_sha256': 'sha256'},
 'withdrawal_preparation': {'challenge_id': 'uuid4',
                            'challenge_nonce_sha256': 'sha256',
                            'expected_registry_revision': 'counter',
                            'kind': 'literal installation-principal-withdrawal/2',
                            'original_withdrawal_deadline_unix_ms': 'utc_ms',
                            'principal_record_sha256': 'sha256',
                            'registration_operation_id': 'uuid4',
                            'registry_identity_sha256': 'sha256',
                            'registry_restore_policy_sha256': 'sha256',
                            'subject_sha256': 'sha256',
                            'version': 'literal2',
                            'withdrawal_authority_record_sha256': 'sha256',
                            'withdrawal_operation_id': 'uuid4',
                            'withdrawal_policy_sha256': 'sha256'}} .items()})

_OUTCOMES = MappingProxyType({k: MappingProxyType(v) for k, v in {'COMMITTED': {'committed_revision': 'positive_counter',
               'result_sha256': 'sha256',
               'tag': 'literal COMMITTED'},
 'NOT_FOUND_DATA': {'tag': 'literal NOT_FOUND_DATA'},
 'REJECTED_NO_EFFECT': {'reason': 'enum '
                                  'INVALID_INPUT|UNTRUSTED_AUTHORITY|STALE_CONTEXT|CAPACITY|DEADLINE|CONFLICT',
                        'tag': 'literal REJECTED_NO_EFFECT'},
 'RESERVED': {'tag': 'literal RESERVED'},
 'RETIRED': {'committed_revision': 'positive_counter',
             'tag': 'literal RETIRED',
             'withdrawal_operation_id': 'uuid4'},
 'UNKNOWN': {'cause_class': 'enum LOST_ACK|INTERRUPTED_EFFECT|UNCERTAIN_PERSISTENCE',
             'tag': 'literal UNKNOWN'}} .items()})

_R1 = MappingProxyType({'audience': 'literal djc-private-principal-registry/1',
 'challenge_id': 'uuid4',
 'challenge_nonce_sha256': 'sha256',
 'core_installation_binding_sha256': 'sha256',
 'core_instance_id': 'opaque',
 'expected_registry_revision': 'counter',
 'installation_id': 'opaque',
 'operator_admission_binding_sha256': 'sha256',
 'original_authorization_deadline_unix_ms': 'utc_ms',
 'policy_sha256': 'sha256',
 'principal_epoch': 'positive_counter',
 'principal_id': 'opaque',
 'public_key_jwk': 'public_P256_point',
 'public_key_pin_sha256': 'sha256',
 'registration_operation_id': 'uuid4',
 'registry_identity_sha256': 'sha256',
 'registry_restore_policy_sha256': 'sha256',
 'version': 'literal1'})

def _point(value):
    _require(type(value) is dict and set(value) == {"crv", "kty", "x", "y"})
    _require(value["crv"] == "P-256" and value["kty"] == "EC")
    for key in ("x", "y"):
        coordinate = value[key]
        _require(type(coordinate) is str and re.fullmatch(r"[A-Za-z0-9_-]{43}", coordinate) is not None)
        try:
            decoded = base64.urlsafe_b64decode(coordinate + "=")
        except ValueError:
            raise InstallationDataError("installation_principal_data_invalid") from None
        _require(len(decoded) == 32 and base64.urlsafe_b64encode(decoded).decode().rstrip("=") == coordinate)
    # Point-on-curve/import/ES256 verification belongs to the separate crypto owner.


def _typed(value, kind):
    if kind in {"literal1", "literal2"}:
        _require(type(value) is int and value == int(kind[-1]))
    elif kind.startswith("literal "):
        _require(type(value) is str and value == kind[8:])
    elif kind.startswith("enum "):
        _require(type(value) is str and value in kind[5:].split("|"))
    elif kind in {"counter", "positive_counter", "utc_ms"}:
        low = 0 if kind == "counter" else 1
        high = 9007199254740991 if kind == "utc_ms" else 9007199254740990
        _require(type(value) is int and low <= value <= high)
    elif kind in {"uuid4", "sha256", "opaque"}:
        pattern = {"uuid4": _UUID, "sha256": _HEX, "opaque": _OPAQUE}[kind]
        _require(type(value) is str and pattern.fullmatch(value) is not None)
    elif kind == "public_P256_point":
        _point(value)
    elif kind == "exact_R1_canonical_body_string":
        _transcript(value)
    elif kind == "closed_variant":
        _require(type(value) is dict and type(value.get("tag")) is str and value["tag"] in _OUTCOMES)
        _validate(value, _OUTCOMES[value["tag"]])
    else:
        raise InstallationDataError("installation_principal_data_invalid")


def _validate(value, schema):
    _require(type(value) is dict and value.keys() == schema.keys())
    for key, kind in schema.items():
        _typed(value[key], kind)
    if "public_key_jwk" in value:
        pin = hashlib.sha256(_canonical(value["public_key_jwk"]).encode()).hexdigest()
        _require(value["public_key_pin_sha256"] == pin)


def _transcript(text):
    value = _decode(text, 4096, 128)
    _validate(value, _R1)
    raw = text.encode("ascii")
    signing_input = POSSESSION_DOMAIN + raw
    return PossessionTranscriptData(hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(signing_input).hexdigest(), text, signing_input, _freeze(value))


def decode_transcript(text):
    """Unchanged R1 DATA encoding; no signature verification or permission."""
    return _transcript(text)


def decode_record(text, *, record_type):
    """Exact required family; no fallback, import, identity allocation or effect."""
    _require(type(record_type) is str and record_type in _SCHEMAS)
    value = _decode(text)
    _validate(value, _SCHEMAS[record_type])
    digest = hashlib.sha256(RECORD_DOMAIN + text.encode("ascii")).hexdigest()
    return InstallationRecordData(record_type, digest, text, _freeze(value))


def _same(left, right, fields):
    _require(all(left[key] == right[key] for key in fields))


def check_bootstrap_chain(*, generation, receipt, subject, context, proof, original_expected_transcript):
    """Original primitive chain equality only. A caller-supplied chain is NOT authority.

    No decoded record/constructor is accepted as a trusted input. The separate
    original expected R1 string is required; it is not inferred from the proof.
    Numeric deadlines are DATA relationships, never validated current clocks.
    """
    g = decode_record(generation, record_type="custody_generation_preparation")
    r = decode_record(receipt, record_type="custody_public_receipt")
    s = decode_record(subject, record_type="installation_principal_subject")
    c = decode_record(context, record_type="bootstrap_admission_context")
    p = decode_record(proof, record_type="bootstrap_proof_preparation")
    gv, rv, sv, cv, pv = (x.values for x in (g, r, s, c, p))
    _require(rv["generation_preparation_sha256"] == g.digest)
    _same(rv, gv, ("custody_operation_id", "core_instance_id", "installation_id", "custody_epoch", "custody_policy_sha256"))
    _require(sv["custody_public_receipt_sha256"] == r.digest)
    _same(sv, rv, ("custody_operation_id", "core_instance_id", "installation_id", "custody_epoch", "public_key_pin_sha256"))
    _same(sv, gv, ("core_installation_binding_sha256",))
    _require(cv["subject_sha256"] == s.digest and cv["custody_public_receipt_sha256"] == r.digest
        and cv["generation_preparation_sha256"] == g.digest)
    _same(cv, sv, ("custody_operation_id", "core_installation_binding_sha256", "policy_sha256"))
    _require(pv["subject_sha256"] == s.digest and pv["custody_public_receipt_sha256"] == r.digest
        and pv["admission_context_sha256"] == c.digest)
    _same(pv, cv, ("registration_operation_id", "custody_operation_id"))
    original = _transcript(original_expected_transcript)
    _require(pv["expected_transcript"] == original.canonical_text)
    tv = original.values
    _require(tv["operator_admission_binding_sha256"] == c.digest)
    _same(tv, cv, ("registration_operation_id", "challenge_id", "challenge_nonce_sha256",
        "core_installation_binding_sha256", "registry_identity_sha256", "registry_restore_policy_sha256",
        "expected_registry_revision", "policy_sha256", "original_authorization_deadline_unix_ms"))
    _same(tv, sv, ("principal_id", "principal_epoch", "core_instance_id", "installation_id", "public_key_pin_sha256"))
    _same(tv, rv, ("public_key_jwk",))
    _require(pv["original_signing_deadline_unix_ms"] <= cv["original_authorization_deadline_unix_ms"])
    return (g, r, s, c, p, original)


def check_original_withdrawal(*, intent, withdrawal, generation, receipt, subject, context, proof, original_expected_transcript):
    """Exact pending-operation DATA relation, not a retirement/once/CAS effect."""
    i = decode_record(intent, record_type="original_admission_intent")
    w = decode_record(withdrawal, record_type="original_operation_withdrawal_preparation")
    chain = check_bootstrap_chain(generation=generation, receipt=receipt, subject=subject,
        context=context, proof=proof, original_expected_transcript=original_expected_transcript)
    p, original = chain[-2:]
    iv, wv, pv, tv = i.values, w.values, p.values, original.values
    _require(pv["expected_transcript"] == original.canonical_text)
    _require(iv["bootstrap_preparation_sha256"] == p.digest)
    _same(iv, pv, ("subject_sha256", "registration_operation_id", "admission_context_sha256"))
    _same(iv, tv, ("registration_operation_id", "challenge_id", "challenge_nonce_sha256",
        "expected_registry_revision", "original_authorization_deadline_unix_ms"))
    _require(wv["original_admission_intent_sha256"] == i.digest)
    _same(wv, iv, ("subject_sha256", "registration_operation_id", "withdrawal_policy_sha256"))
    _require(wv["registration_challenge_id"] == iv["challenge_id"]
        and wv["registration_challenge_nonce_sha256"] == iv["challenge_nonce_sha256"])
    _same(wv, tv, ("registry_identity_sha256", "registry_restore_policy_sha256"))
    _require(wv["withdrawal_challenge_id"] != iv["challenge_id"]
        and wv["withdrawal_challenge_nonce_sha256"] != iv["challenge_nonce_sha256"]
        and wv["withdrawal_operation_id"] != iv["registration_operation_id"])
    # Withdrawal has its OWN admitted deadline; it may occur after admission expiry.
    return (i, w, *chain)


def check_retirement_data(*, tombstone, intent, withdrawal, generation, receipt, subject, context, proof, original_expected_transcript):
    """Relate a claimed terminal DATA record; never certify its actual commit."""
    t = decode_record(tombstone, record_type="original_admission_retirement_tombstone")
    chain = check_original_withdrawal(intent=intent, withdrawal=withdrawal, generation=generation,
        receipt=receipt, subject=subject, context=context, proof=proof,
        original_expected_transcript=original_expected_transcript)
    i, w = chain[:2]
    tv, iv, wv = t.values, i.values, w.values
    _require(tv["original_admission_intent_sha256"] == i.digest and tv["withdrawal_preparation_sha256"] == w.digest)
    _same(tv, iv, ("subject_sha256", "registration_operation_id"))
    _same(tv, wv, ("registration_challenge_id", "registration_challenge_nonce_sha256", "withdrawal_operation_id"))
    return (t, *chain)


def check_principal_data(*, principal, generation, receipt, subject, context, proof, original_expected_transcript):
    """Relate a claimed principal record; matching DATA is not registry admission."""
    r = decode_record(principal, record_type="installation_principal_record")
    chain = check_bootstrap_chain(generation=generation, receipt=receipt, subject=subject,
        context=context, proof=proof, original_expected_transcript=original_expected_transcript)
    original_subject, original_proof, transcript = chain[2], chain[4], chain[5]
    rv, tv = r.values, transcript.values
    _require(rv["subject_sha256"] == original_subject.digest
        and rv["bootstrap_preparation_sha256"] == original_proof.digest
        and rv["crypto_possession_body_sha256"] == transcript.body_sha256
        and rv["crypto_signing_input_sha256"] == transcript.signing_input_sha256)
    _same(rv, tv, ("registration_operation_id", "challenge_id", "public_key_pin_sha256",
        "original_authorization_deadline_unix_ms"))
    # accepted_independent_authority_bundle_sha256 is a reference, NOT authority.
    return (r, *chain)


def check_device_pair_data(*, pair_join, principal, generation, receipt, subject, context, proof, original_expected_transcript):
    """Relate device join DATA; no pair/purpose/Session/native rights are granted."""
    j = decode_record(pair_join, record_type="device_pair_join")
    chain = check_principal_data(principal=principal, generation=generation, receipt=receipt,
        subject=subject, context=context, proof=proof, original_expected_transcript=original_expected_transcript)
    r = chain[0]
    _require(j.values["principal_record_sha256"] == r.digest
        and j.values["subject_sha256"] == r.values["subject_sha256"])
    return (j, *chain)


def check_committed_withdrawal_data(*, withdrawal, principal, generation, receipt, subject, context, proof, original_expected_transcript):
    """Distinct known-result DATA variant; never falls back to pending targeting."""
    w = decode_record(withdrawal, record_type="withdrawal_preparation")
    chain = check_principal_data(principal=principal, generation=generation, receipt=receipt,
        subject=subject, context=context, proof=proof, original_expected_transcript=original_expected_transcript)
    r, transcript = chain[0], chain[-1]
    wv, rv, tv = w.values, r.values, transcript.values
    _require(wv["principal_record_sha256"] == r.digest)
    _same(wv, rv, ("subject_sha256", "registration_operation_id"))
    _same(wv, tv, ("registry_identity_sha256", "registry_restore_policy_sha256"))
    _require(wv["challenge_id"] != tv["challenge_id"]
        and wv["challenge_nonce_sha256"] != tv["challenge_nonce_sha256"]
        and wv["withdrawal_operation_id"] != tv["registration_operation_id"])
    # A caller's expected revision and deadline cannot establish live CAS/time.
    return (w, *chain)
