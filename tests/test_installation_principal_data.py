"""Actual closed codec checks; synthetic DATA never supplies live authority.

The 47 API design expectations include stateful owner/CAS cases; these codec
tests do not claim to execute that registry, a signer or native effects.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.test_profile_dj_settings_persistence import operation  # noqa: F401
from custom_components.djconnect import installation_principal_data as wire

FIXTURES = Path(__file__).parent / "fixtures/installation_principal"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fixture():
    return json.loads((FIXTURES / "expired-synthetic-records.json").read_text())


def bootstrap_inputs(f):
    return {argument: f["records"][kind]["canonical"] for argument, kind in {
        "generation": "custody_generation_preparation", "receipt": "custody_public_receipt",
        "subject": "installation_principal_subject", "context": "bootstrap_admission_context",
        "proof": "bootstrap_proof_preparation"}.items()} | {
        "original_expected_transcript": f["R1"]["canonical"]}


def withdrawal_inputs(f):
    return bootstrap_inputs(f) | {"intent": f["records"]["original_admission_intent"]["canonical"],
        "withdrawal": f["records"]["original_operation_withdrawal_preparation"]["canonical"]}


class InstallationPrincipalDataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture()
        self.records = self.fixture["records"]

    def test_actual_HA_original_codec_and_same_final_harness_parent_RED_remain_exact(self):
        root = Path(__file__).resolve().parents[1]
        joined = json.loads((root / "examples/client_contracts/installation_principal_data_v1/actual-ha-data-codec.json").read_text())
        receipt = joined["original_receipt"]
        self.assertEqual(receipt["state"], "PASS")
        self.assertEqual(len(receipt["cases"]), 6)
        self.assertEqual(len(receipt["preceding_source_origin_cases"]), 19)
        self.assertEqual(len(receipt["source_sha256"]), 302)
        for relative, digest in receipt["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest)
        actual = hashlib.sha256((root / joined["codec_harness"]).read_bytes()).hexdigest()
        self.assertEqual(actual, joined["codec_harness_sha256"])
        self.assertEqual(actual, joined["parent_causal_RED"]["same_harness_sha256"])
        self.assertEqual(joined["parent_causal_RED"]["actual_products"], 277)
        self.assertEqual(receipt["registry_CAS_or_once_or_signer_qualification"], "NOT_RUN")
        self.assertEqual(joined["installed"], "NOT_RUN")

    def test_exact_frozen_cross_owner_design_and_expectations_remain_declarative(self):
        raw = (FIXTURES / "frozen-r2-design.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), wire.DESIGN_SHA256)
        design = json.loads(raw)
        self.assertEqual({k: dict(v) for k, v in wire._SCHEMAS.items() if k != "operation_status"}, design["records"])
        cases = json.loads((FIXTURES / "frozen-r2-declarative-cases.json").read_text())
        self.assertEqual(cases["candidate_sha256"], wire.DESIGN_SHA256)
        self.assertEqual(len(cases["cases"]), 47)
        self.assertEqual(cases["cases_executed"], 0)

    def test_eleven_actual_record_decodes_match_independently_constructed_bytes_and_digests(self):
        self.assertEqual(len(self.records), 11)
        for kind, vector in self.records.items():
            with self.subTest(kind=kind):
                decoded = wire.decode_record(vector["canonical"], record_type=kind)
                self.assertEqual(decoded.digest, vector["digest"])
                self.assertEqual(decoded.canonical_text, vector["canonical"])
                self.assertEqual(decoded.classification, "INSTALLATION_PRINCIPAL_DATA_ONLY")

    def test_six_status_variants_are_exact_data_not_permission_to_retry(self):
        for vector in self.fixture["statuses"]:
            decoded = wire.decode_record(vector["canonical"], record_type="operation_status")
            self.assertEqual(decoded.digest, vector["digest"])
            bad = json.loads(vector["canonical"])
            bad["outcome"]["retry"] = True
            with self.assertRaises(wire.InstallationDataError):
                wire.decode_record(canonical(bad), record_type="operation_status")

    def test_unchanged_R1_exact_bytes_have_distinct_record_JWK_and_signing_domains(self):
        v = self.fixture["R1"]
        t = wire.decode_transcript(v["canonical"])
        self.assertEqual(t.body_sha256, v["body_sha256"])
        self.assertEqual(t.signing_input.hex(), v["signing_input_hex"])
        self.assertEqual(t.signing_input_sha256, v["signing_input_sha256"])
        self.assertNotEqual(wire.RECORD_DOMAIN, wire.POSSESSION_DOMAIN)
        self.assertEqual(wire.POSSESSION_DOMAIN.count(b"\n"), 1)
        self.assertNotIn(b"\\n", wire.POSSESSION_DOMAIN)

    def test_original_owning_API_public_bytes_decode_with_exact_R1_digests(self):
        raw = (FIXTURES / "api-b6e5-public-vectors.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "ab4ce0f5d69e87f2294a4abef26d73312b69f6667de025cb9771cc3e7d86f54d")
        vector = json.loads(raw)
        result = wire.decode_transcript(vector["body"])
        self.assertEqual(result.body_sha256, vector["body_sha256"])
        self.assertEqual(result.signing_input_sha256, vector["signing_input_sha256"])
        self.assertEqual(wire.decode_transcript(vector["r1_encoding_body"]).body_sha256, vector["r1_encoding_sha256"])

    def test_original_chain_joins_distinct_local_and_registry_epochs(self):
        values = wire.check_bootstrap_chain(**bootstrap_inputs(self.fixture))
        self.assertEqual(values[0].values["custody_epoch"], 3)
        self.assertEqual(values[2].values["principal_epoch"], 7)
        self.assertEqual(len(values), 6)
        for value in values:
            for effect in ("admitted", "sign", "generate", "enroll", "execute", "private_key"):
                self.assertFalse(hasattr(value, effect))

    def test_owned_records_and_nested_point_are_frozen_and_repr_does_not_export_input(self):
        record = wire.decode_record(self.records["custody_public_receipt"]["canonical"], record_type="custody_public_receipt")
        with self.assertRaises(TypeError):
            record.values["installation_id"] = "other"
        with self.assertRaises(TypeError):
            record.values["public_key_jwk"]["x"] = "other"
        with self.assertRaises(AttributeError):
            record.digest = "other"
        self.assertNotIn("fixture-installation", repr(record))
        self.assertNotIn(record.canonical_text, repr(record))

    def test_preparsed_objects_subclasses_and_forged_decoded_records_are_not_accepted(self):
        text = self.records["custody_generation_preparation"]["canonical"]
        class String(str):
            pass
        for value in (json.loads(text), String(text), text.encode(), None,
                      wire.decode_record(text, record_type="custody_generation_preparation")):
            with self.subTest(type=type(value)), self.assertRaises(wire.InstallationDataError):
                wire.decode_record(value, record_type="custody_generation_preparation")

    def test_every_record_rejects_missing_unknown_null_and_wrong_family(self):
        for kind, vector in self.records.items():
            data = json.loads(vector["canonical"])
            for key in data:
                absent = deepcopy(data)
                del absent[key]
                for bad in (absent, data | {key: None}):
                    with self.subTest(kind=kind, key=key), self.assertRaises(wire.InstallationDataError):
                        wire.decode_record(canonical(bad), record_type=kind)
            for bad in (data | {"unexpected": True}, data | {"kind": "other/1"}):
                with self.assertRaises(wire.InstallationDataError):
                    wire.decode_record(canonical(bad), record_type=kind)

    def test_bool_float_negative_exponent_and_unsafe_integer_aliases_reject(self):
        data = json.loads(self.records["custody_generation_preparation"]["canonical"])
        for key in ("version", "custody_epoch", "expected_local_revision", "original_generation_deadline_unix_ms", "attempt_limit"):
            for value in (True, False, -1, 1.0, 9007199254740992):
                with self.subTest(key=key, value=value), self.assertRaises(wire.InstallationDataError):
                    wire.decode_record(canonical(data | {key: value}), record_type="custody_generation_preparation")
        text = canonical(data)
        for alias in (text.replace('"expected_local_revision":0', '"expected_local_revision":-0'),
                      text.replace('"attempt_limit":1', '"attempt_limit":1e0')):
            with self.assertRaises(wire.InstallationDataError):
                wire.decode_record(alias, record_type="custody_generation_preparation")

    def test_UUID_hash_identifier_and_point_encodings_are_closed(self):
        data = json.loads(self.records["custody_public_receipt"]["canonical"])
        for key, value in (("custody_operation_id", "00000000-0000-7000-8000-000000000001"),
                           ("generation_preparation_sha256", "F" * 64), ("core_instance_id", "with space")):
            with self.assertRaises(wire.InstallationDataError):
                wire.decode_record(canonical(data | {key: value}), record_type="custody_public_receipt")
        for change in ({"d": "PRIVATE_NOT_IMPORTED"}, {"alg": "ES256"}, {"crv": "P-384"},
                       {"x": data["public_key_jwk"]["x"] + "="}, {"y": "A" * 42 + "B"}):
            bad = data | {"public_key_jwk": data["public_key_jwk"] | change}
            with self.assertRaises(wire.InstallationDataError):
                wire.decode_record(canonical(bad), record_type="custody_public_receipt")

    def test_key_pin_is_recomputed_and_not_accepted_from_same_response(self):
        data = json.loads(self.records["custody_public_receipt"]["canonical"])
        with self.assertRaises(wire.InstallationDataError):
            wire.decode_record(canonical(data | {"public_key_pin_sha256": "0" * 64}), record_type="custody_public_receipt")
        # Even a matching public point/pin is only DATA, never registered key trust.
        result = wire.decode_record(canonical(data), record_type="custody_public_receipt")
        self.assertEqual(result.classification, wire.CLASSIFICATION)

    def test_duplicates_noncanonical_whitespace_escapes_and_trailing_bytes_reject(self):
        text = self.records["custody_generation_preparation"]["canonical"]
        for bad in ('{"version":1,' + text[1:], " " + text, text + "\n", text + "{}",
                    text.replace('"fixture-core"', '"fixture-\\u0063ore"'), text.replace(",", ", ", 1)):
            with self.assertRaises(wire.InstallationDataError):
                wire.decode_record(bad, record_type="custody_generation_preparation")

    def test_nonfinite_large_number_and_malformed_numeric_inputs_raise_only_closed_error(self):
        text = self.records["custody_generation_preparation"]["canonical"]
        for value in ("1e999", "NaN", "Infinity", "00", "+1", "9" * 5000):
            bad = text.replace('"expected_local_revision":0', '"expected_local_revision":' + value)
            with self.subTest(value=value[:10]), self.assertRaises(wire.InstallationDataError) as error:
                wire.decode_record(bad, record_type="custody_generation_preparation")
            self.assertEqual(str(error.exception), "installation_principal_data_invalid")

    def test_depth_token_bytes_escape_and_unterminated_string_bounds_precede_generic_decode(self):
        cases = (" " * 32769, '{"x":' * 5 + '0' + '}' * 5,
                 "{" + ",".join(f'"k{i}":0' for i in range(128)) + "}",
                 '{"x":"\\q"}', '{"x":"\\u0"}', '{"x":"unterminated}', '{"x":"\x01"}')
        for bad in cases:
            with self.subTest(length=len(bad)), patch.object(wire.json, "loads") as generic:
                with self.assertRaises(wire.InstallationDataError):
                    wire.decode_record(bad, record_type="custody_generation_preparation")
                generic.assert_not_called()

    def test_embedded_R1_has_separate_bounds_before_its_generic_decode(self):
        proof = json.loads(self.records["bootstrap_proof_preparation"]["canonical"])
        original_loads = json.loads
        for body in (" " * 4097, '{"x":' * 5 + '0' + '}' * 5,
                     "{" + ",".join(f'"k{i}":0' for i in range(64)) + "}"):
            with patch.object(wire.json, "loads", wraps=original_loads) as generic:
                with self.assertRaises(wire.InstallationDataError):
                    wire.decode_record(canonical(proof | {"expected_transcript": body}), record_type="bootstrap_proof_preparation")
                self.assertEqual(generic.call_count, 1)  # Outer only, never the invalid inner document.

    def test_separately_required_expected_transcript_cannot_be_inferred_from_proof(self):
        inputs = bootstrap_inputs(self.fixture)
        wrong = json.loads(inputs["original_expected_transcript"])
        wrong["principal_id"] = "different-fixture-principal"
        with self.assertRaises(wire.InstallationDataError):
            wire.check_bootstrap_chain(**(inputs | {"original_expected_transcript": canonical(wrong)}))
        del inputs["original_expected_transcript"]
        with self.assertRaises(TypeError):
            wire.check_bootstrap_chain(**inputs)

    def test_each_original_chain_record_cannot_be_swapped_or_relabelled(self):
        inputs = bootstrap_inputs(self.fixture)
        for argument, key, value in (("generation", "custody_epoch", 9), ("receipt", "local_committed_revision", 3),
                                    ("subject", "principal_id", "other-principal"), ("context", "registry_identity_sha256", "0" * 64),
                                    ("proof", "custody_operation_id", "00000000-0000-4000-8000-000000000009")):
            data = json.loads(inputs[argument]) | {key: value}
            with self.subTest(argument=argument), self.assertRaises(wire.InstallationDataError):
                wire.check_bootstrap_chain(**(inputs | {argument: canonical(data)}))

    def test_self_consistent_presented_transcript_cannot_change_original_context(self):
        inputs = bootstrap_inputs(self.fixture)
        for field in ("principal_id", "challenge_nonce_sha256", "registry_identity_sha256", "policy_sha256"):
            body = json.loads(inputs["original_expected_transcript"])
            body[field] = "changed" if field == "principal_id" else "0" * 64
            bodytext = canonical(body)
            proof = json.loads(inputs["proof"]) | {"expected_transcript": bodytext}
            with self.subTest(field=field), self.assertRaises(wire.InstallationDataError):
                wire.check_bootstrap_chain(**(inputs | {"proof": canonical(proof), "original_expected_transcript": bodytext}))

    def test_signing_deadline_never_extends_original_registration_but_generation_is_separate(self):
        inputs = bootstrap_inputs(self.fixture)
        proof = json.loads(inputs["proof"])
        proof["original_signing_deadline_unix_ms"] = 1712345800001
        with self.assertRaises(wire.InstallationDataError):
            wire.check_bootstrap_chain(**(inputs | {"proof": canonical(proof)}))
        chain = wire.check_bootstrap_chain(**inputs)
        self.assertLess(chain[0].values["original_generation_deadline_unix_ms"], chain[4].values["original_signing_deadline_unix_ms"])

    def test_pending_withdrawal_needs_no_future_principal_result_or_current_revision(self):
        inputs = withdrawal_inputs(self.fixture)
        result = wire.check_original_withdrawal(**inputs)
        self.assertEqual(result[1].record_type, "original_operation_withdrawal_preparation")
        for field in ("principal_record_sha256", "expected_registry_revision"):
            self.assertNotIn(field, result[1].values)
        self.assertGreater(result[1].values["original_withdrawal_deadline_unix_ms"], result[-1].values["original_authorization_deadline_unix_ms"])

    def test_withdrawal_original_target_and_own_challenge_are_not_exchangeable(self):
        inputs = withdrawal_inputs(self.fixture)
        original = json.loads(inputs["withdrawal"])
        intent = json.loads(inputs["intent"])
        for key, value in (("original_admission_intent_sha256", "0" * 64), ("subject_sha256", "0" * 64),
                           ("withdrawal_challenge_id", intent["challenge_id"]),
                           ("withdrawal_challenge_nonce_sha256", intent["challenge_nonce_sha256"]),
                           ("registry_restore_policy_sha256", "0" * 64)):
            with self.subTest(key=key), self.assertRaises(wire.InstallationDataError):
                wire.check_original_withdrawal(**(inputs | {"withdrawal": canonical(original | {key: value})}))

    def test_withdrawal_rechecks_complete_primitive_bootstrap_chain(self):
        inputs = withdrawal_inputs(self.fixture)
        proof = json.loads(inputs["proof"]) | {"admission_context_sha256": "0" * 64}
        with self.assertRaises(wire.InstallationDataError):
            wire.check_original_withdrawal(**(inputs | {"proof": canonical(proof)}))

    def test_retirement_is_only_exact_claimed_data_and_has_no_commit_or_effect(self):
        inputs = withdrawal_inputs(self.fixture)
        text = self.records["original_admission_retirement_tombstone"]["canonical"]
        result = wire.check_retirement_data(tombstone=text, **inputs)
        self.assertEqual(result[0].classification, wire.CLASSIFICATION)
        for key in ("withdrawal_preparation_sha256", "original_admission_intent_sha256", "subject_sha256"):
            bad = json.loads(text) | {key: "0" * 64}
            with self.assertRaises(wire.InstallationDataError):
                wire.check_retirement_data(tombstone=canonical(bad), **inputs)

    def test_claimed_principal_record_is_bound_to_original_chain_and_separate_crypto_input(self):
        inputs = bootstrap_inputs(self.fixture)
        principal = self.records["installation_principal_record"]["canonical"]
        result = wire.check_principal_data(principal=principal, **inputs)
        self.assertEqual(result[0].classification, wire.CLASSIFICATION)
        for key in ("subject_sha256", "bootstrap_preparation_sha256", "crypto_possession_body_sha256", "crypto_signing_input_sha256"):
            with self.subTest(key=key), self.assertRaises(wire.InstallationDataError):
                wire.check_principal_data(principal=canonical(json.loads(principal) | {key: "0" * 64}), **inputs)

    def test_device_join_cannot_switch_claimed_parent_and_does_not_supply_pair_authority(self):
        inputs = bootstrap_inputs(self.fixture) | {"principal": self.records["installation_principal_record"]["canonical"]}
        pair_join = self.records["device_pair_join"]["canonical"]
        result = wire.check_device_pair_data(pair_join=pair_join, **inputs)
        self.assertEqual(result[0].classification, wire.CLASSIFICATION)
        for key in ("subject_sha256", "principal_record_sha256"):
            with self.subTest(key=key), self.assertRaises(wire.InstallationDataError):
                wire.check_device_pair_data(pair_join=canonical(json.loads(pair_join) | {key: "0" * 64}), **inputs)

    def test_committed_withdrawal_is_separate_known_result_variant_with_own_original_nonce(self):
        inputs = bootstrap_inputs(self.fixture) | {"principal": self.records["installation_principal_record"]["canonical"]}
        text = self.records["withdrawal_preparation"]["canonical"]
        self.assertEqual(wire.check_committed_withdrawal_data(withdrawal=text, **inputs)[0].classification, wire.CLASSIFICATION)
        pending = self.records["original_operation_withdrawal_preparation"]["canonical"]
        with self.assertRaises(wire.InstallationDataError):
            wire.check_committed_withdrawal_data(withdrawal=pending, **inputs)
        for key in ("principal_record_sha256", "registry_identity_sha256", "subject_sha256"):
            with self.assertRaises(wire.InstallationDataError):
                wire.check_committed_withdrawal_data(withdrawal=canonical(json.loads(text) | {key: "0" * 64}), **inputs)


if __name__ == "__main__":
    unittest.main()
